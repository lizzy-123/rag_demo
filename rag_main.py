#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG 团队知识助手 - 完整优化版
功能：批量文档、多文件类型、历史记忆、自定义Prompt、收藏、噪音清洗
性能：自动检测文件变化，新增文件增量添加，修改/删除触发全量重建
架构：模块化、面向对象、支持增量更新
"""
import os
import json
import asyncio
import time
import hashlib
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# 文档处理
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, Docx2txtLoader,
    UnstructuredExcelLoader, UnstructuredPowerPointLoader, UnstructuredMarkdownLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever

# 混合检索相关
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# 缓存机制
from functools import lru_cache

load_dotenv()

# ===================== 全局配置 =====================
@dataclass
class Config:
    DOC_DIR: str = "./team_doc"
    VECTOR_DB_DIR: str = "faiss_team_vector_db"
    HISTORY_FILE: str = "chat_history.json"
    COLLECTION_FILE: str = "collection.json"
    CACHE_DIR: str = "./cache"
    FILE_META_FILE: str = "file_metadata.json"
    
    BASE_CHUNK_SIZE: int = 800
    BASE_CHUNK_OVERLAP: int = 150
    RETRIEVE_TOP_K: int = 5
    ENABLE_MIXED_RETRIEVAL: bool = True
    TEMPERATURE: float = 0.1
    
    ENABLE_CACHE: bool = True
    ENABLE_HISTORY: bool = True
    MAX_HISTORY_LENGTH: int = 10

config = Config()
Path(config.CACHE_DIR).mkdir(exist_ok=True)
Path(config.DOC_DIR).mkdir(exist_ok=True)

# ===================== 数据模型 =====================
@dataclass
class ChatMessage:
    question: str
    answer: str
    sources: List[str]
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ===================== 模型工厂 =====================
class ModelFactory:
    @staticmethod
    def get_llm(provider: str = None, temperature: float = config.TEMPERATURE):
        provider = provider or os.getenv("LLM_PROVIDER", "zhipu").lower()
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
        elif provider == "zhipu":
            from langchain_community.chat_models import ChatZhipuAI
            return ChatZhipuAI(
                model=os.getenv("ZHIPU_MODEL", "glm-4-flash"),
                temperature=temperature,
                api_key=os.getenv("ZHIPUAI_API_KEY"),
                base_url=os.getenv("ZHIPU_BASE_URL"),
            )
        raise ValueError(f"不支持的模型提供商: {provider}")

    @staticmethod
    def get_embeddings(provider: str = None):
        provider = provider or os.getenv("EMBEDDING_PROVIDER", "zhipu").lower()
        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
        elif provider == "zhipu":
            from langchain_community.embeddings import ZhipuAIEmbeddings
            return ZhipuAIEmbeddings(
                model=os.getenv("ZHIPU_EMBEDDING_MODEL", "embedding-2"),
                api_key=os.getenv("ZHIPUAI_API_KEY"),
                base_url=os.getenv("ZHIPU_BASE_URL"),
            )
        raise ValueError(f"不支持的向量模型提供商: {provider}")

# ===================== FAISS 包装器（支持增量） =====================
class DocumentAwareFAISSRetriever(BaseRetriever):
    """为FAISS向量库增加 add_documents 方法，并统一检索接口"""
    vector_store: FAISS
    k: int = config.RETRIEVE_TOP_K

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str) -> List[Document]:
        return self.vector_store.similarity_search(query, k=self.k)

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        return self._get_relevant_documents(query)

    def get_relevant_documents(self, query: str) -> List[Document]:
        return self._get_relevant_documents(query)

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        return await self._aget_relevant_documents(query)

    def add_documents(self, new_docs: List[Document]) -> List[str]:
        return self.vector_store.add_documents(new_docs)

# ===================== 噪音清洗工具 =====================
class TextCleaner:
    @staticmethod
    def clean(text: str) -> str:
        """清洗文本：移除QQ群、URL、多余空行、水印等"""
        # 移除 QQ 群相关行
        text = re.sub(r'(?i)^.*QQ[：:]\s*[\d\s]+.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^.*QQ.*群.*$', '', text, flags=re.MULTILINE)
        # 移除 URL
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        # 移除水印
        text = re.sub(r'(?i)^.*Evaluation Warning.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^.*Spire\.PDF.*$', '', text, flags=re.MULTILINE)
        # 移除页码
        text = re.sub(r'第\s*\d+\s*页\s*共\s*\d+\s*页', '', text)
        # 移除单独的数字行
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        # 合并多余空行
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # 去除每行首尾空白，再重组
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)

# ===================== 文档处理器 =====================
class DocumentProcessor:
    SUPPORTED_EXT = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".docx": Docx2txtLoader,
        ".md": UnstructuredMarkdownLoader,
        ".xlsx": UnstructuredExcelLoader,
        ".pptx": UnstructuredPowerPointLoader
    }
    
    @staticmethod
    async def async_load_single_file(file_path: str) -> List[Document]:
        try:
            ext = Path(file_path).suffix.lower()
            if ext not in DocumentProcessor.SUPPORTED_EXT:
                print(f"⚠️ 跳过不支持的文件: {file_path}")
                return []
            loader_cls = DocumentProcessor.SUPPORTED_EXT[ext]
            if ext == ".txt":
                loader = loader_cls(file_path, encoding="utf-8")
            else:
                loader = loader_cls(file_path)
            docs = loader.load()
            for doc in docs:
                doc.page_content = TextCleaner.clean(doc.page_content)
            return docs
        except Exception as e:
            print(f"❌ 加载文件失败 {file_path}: {str(e)}")
            return []

    @staticmethod
    async def batch_load_documents(file_paths: List[str]) -> List[Document]:
        if not file_paths:
            return []
        print(f"📄 加载 {len(file_paths)} 个文档...")
        tasks = [DocumentProcessor.async_load_single_file(p) for p in file_paths]
        docs_list = await asyncio.gather(*tasks)
        return [doc for sublist in docs_list for doc in sublist]

    @staticmethod
    def smart_split_documents(docs: List[Document]) -> List[Document]:
        total_length = sum(len(doc.page_content) for doc in docs)
        avg_length = total_length / len(docs) if docs else 0
        if avg_length > 5000:
            chunk_size, chunk_overlap = 1500, 300
        elif avg_length < 1000:
            chunk_size, chunk_overlap = 500, 100
        else:
            chunk_size, chunk_overlap = config.BASE_CHUNK_SIZE, config.BASE_CHUNK_OVERLAP
        print(f"📏 智能分块参数：chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "，", " ", ""],
            length_function=len
        )
        return text_splitter.split_documents(docs)

# ===================== 向量库管理器（文件级变更追踪 + 增量新增/全量重建） =====================
class VectorStoreManager:
    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.vector_db_path = Path(config.VECTOR_DB_DIR).absolute()
        self.file_meta_path = self.vector_db_path / config.FILE_META_FILE
        self.corpus_path = self.vector_db_path / "corpus.json"
        self.fingerprint_path = self.vector_db_path / "fingerprints.json"
        self.vector_db_path.mkdir(exist_ok=True)
        self.doc_dir = Path(config.DOC_DIR).absolute()
        self.doc_dir.mkdir(exist_ok=True)

    # ---------- 文件级元数据管理 ----------
    def _get_file_metadata(self, file_path: Path) -> dict:
        stat = file_path.stat()
        return {"mtime": stat.st_mtime, "size": stat.st_size}

    def _get_rel_path(self, abs_path: Path) -> str:
        return str(abs_path.relative_to(self.doc_dir))

    def _scan_directory_files(self) -> List[Path]:
        all_files = []
        for p in self.doc_dir.rglob("*"):
            if p.suffix.lower() in DocumentProcessor.SUPPORTED_EXT:
                all_files.append(p.absolute())
        return all_files

    def _scan_directory_metadata(self) -> dict:
        meta = {}
        for abs_path in self._scan_directory_files():
            rel_path = self._get_rel_path(abs_path)
            meta[rel_path] = self._get_file_metadata(abs_path)
        return meta

    def _load_old_metadata(self) -> dict:
        if not self.file_meta_path.exists():
            return {}
        with open(self.file_meta_path, "r") as f:
            return json.load(f)

    def _save_metadata(self, meta: dict):
        with open(self.file_meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    def _detect_changes(self) -> tuple:
        old_meta = self._load_old_metadata()
        new_meta = self._scan_directory_metadata()
        old_paths = set(old_meta.keys())
        new_paths = set(new_meta.keys())
        added = new_paths - old_paths
        deleted = old_paths - new_paths
        modified = set()
        for path in old_paths & new_paths:
            if old_meta[path] != new_meta[path]:
                modified.add(path)
        return list(added), list(modified), list(deleted)

    # ---------- 指纹工具 ----------
    @staticmethod
    def _get_doc_fingerprint(doc: Document) -> str:
        content = doc.page_content
        meta_str = str(sorted(doc.metadata.items()))
        return hashlib.sha256(f"{content}{meta_str}".encode()).hexdigest()

    def _save_corpus_and_fingerprints(self, docs: List[Document]):
        corpus = [doc.page_content for doc in docs]
        with open(self.corpus_path, "w", encoding="utf-8") as f:
            json.dump(corpus, f, ensure_ascii=False, indent=2)
        fingerprints = [self._get_doc_fingerprint(doc) for doc in docs]
        with open(self.fingerprint_path, "w") as f:
            json.dump(fingerprints, f)

    def _build_bm25_from_corpus(self) -> BM25Retriever:
        with open(self.corpus_path, "r", encoding="utf-8") as f:
            corpus_texts = json.load(f)
        bm25 = BM25Retriever.from_texts(corpus_texts)
        bm25.k = config.RETRIEVE_TOP_K
        return bm25

    def check_vector_db_exists(self) -> bool:
        return (self.vector_db_path / "index.faiss").exists()

    # ---------- 全量重建 ----------
    async def full_rebuild(self) -> dict:
        print("🔄 全量重建向量库...")
        all_files = self._scan_directory_files()
        if not all_files:
            raise Exception(f"目录 {self.doc_dir} 中未找到支持的文档")
        docs = await DocumentProcessor.batch_load_documents([str(p) for p in all_files])
        if not docs:
            raise Exception("加载文档后内容为空，请检查文件格式")
        split_docs = DocumentProcessor.smart_split_documents(docs)
        print(f"🔨 构建 FAISS 索引（共 {len(split_docs)} 个文本块）...")
        vs = FAISS.from_documents(split_docs, self.embeddings)
        vs.save_local(str(self.vector_db_path))
        self._save_corpus_and_fingerprints(split_docs)
        bm25 = self._build_bm25_from_corpus()
        current_meta = self._scan_directory_metadata()
        self._save_metadata(current_meta)
        print("✅ 全量重建完成")
        return {"vs": vs, "bm25": bm25}

    # ---------- 增量添加 ----------
    async def incremental_add(self, added_rel_paths: List[str]) -> dict:
        print(f"📎 发现 {len(added_rel_paths)} 个新增文件，执行增量添加...")
        added_abs_paths = [str(self.doc_dir / rel_path) for rel_path in added_rel_paths]
        new_docs = await DocumentProcessor.batch_load_documents(added_abs_paths)
        if not new_docs:
            print("⚠️ 新增文件无有效内容，跳过")
            return None
        split_new = DocumentProcessor.smart_split_documents(new_docs)
        if not split_new:
            print("⚠️ 新增文件分块后为空，跳过")
            return None
        
        vs = FAISS.load_local(str(self.vector_db_path), self.embeddings, allow_dangerous_deserialization=True)
        vs.add_documents(split_new)
        vs.save_local(str(self.vector_db_path))
        
        old_corpus = []
        if self.corpus_path.exists():
            with open(self.corpus_path, "r", encoding="utf-8") as f:
                old_corpus = json.load(f)
        new_corpus = old_corpus + [doc.page_content for doc in split_new]
        with open(self.corpus_path, "w", encoding="utf-8") as f:
            json.dump(new_corpus, f, ensure_ascii=False, indent=2)
        
        old_fps = []
        if self.fingerprint_path.exists():
            with open(self.fingerprint_path, "r") as f:
                old_fps = json.load(f)
        new_fps = old_fps + [self._get_doc_fingerprint(doc) for doc in split_new]
        with open(self.fingerprint_path, "w") as f:
            json.dump(new_fps, f)
        
        bm25 = self._build_bm25_from_corpus()
        
        old_meta = self._load_old_metadata()
        for rel_path in added_rel_paths:
            abs_path = self.doc_dir / rel_path
            old_meta[rel_path] = self._get_file_metadata(abs_path)
        self._save_metadata(old_meta)
        
        print(f"✅ 增量添加完成，新增 {len(split_new)} 个文本块")
        return {"vs": vs, "bm25": bm25}

    # ---------- 主入口 ----------
    async def build_or_load_vector_store(self):
        if not self.check_vector_db_exists():
            return await self.full_rebuild()
        added, modified, deleted = self._detect_changes()
        if modified or deleted:
            print(f"⚠️ 检测到 {len(modified)} 个文件修改，{len(deleted)} 个文件删除，将执行全量重建。")
            return await self.full_rebuild()
        elif added:
            return await self.incremental_add(added)
        else:
            print("✅ 文件无任何变化，直接加载现有向量库。")
            vs = FAISS.load_local(str(self.vector_db_path), self.embeddings, allow_dangerous_deserialization=True)
            bm25 = self._build_bm25_from_corpus()
            return {"vs": vs, "bm25": bm25}

    def get_mixed_retriever(self, faiss_retriever_wrapper, bm25_retriever):
        if not config.ENABLE_MIXED_RETRIEVAL:
            return faiss_retriever_wrapper
        return EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever_wrapper],
            weights=[0.4, 0.6]
        )

# ===================== 对话管理器 =====================
class ChatManager:
    def __init__(self):
        self.history: List[ChatMessage] = self._load_json(config.HISTORY_FILE, [])
        self.collections: List[ChatMessage] = self._load_json(config.COLLECTION_FILE, [])
        self.prompt_template = self._default_prompt()

    @staticmethod
    def _load_json(file_path: str, default: list) -> list:
        try:
            if Path(file_path).exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return [ChatMessage(**item) for item in json.load(f)]
        except:
            pass
        return default

    @staticmethod
    def _save_json(file_path: str, data: List[ChatMessage]):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([asdict(item) for item in data], f, ensure_ascii=False, indent=2)

    def save_history(self):
        self.history = self.history[-config.MAX_HISTORY_LENGTH:]
        self._save_json(config.HISTORY_FILE, self.history)

    def save_collections(self):
        self._save_json(config.COLLECTION_FILE, self.collections)

    def add_history(self, msg: ChatMessage):
        if config.ENABLE_HISTORY:
            self.history.append(msg)
            self.save_history()

    def add_collection(self, msg: ChatMessage):
        self.collections.append(msg)
        self.save_collections()

    def _default_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", "你是团队知识助手，基于提供的知识库内容回答问题，回答要准确、简洁、专业。\n知识库内容：{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

    def set_custom_prompt(self, template_str: str):
        self.prompt_template = ChatPromptTemplate.from_template(template_str)

# ===================== RAG核心链 =====================
class RAGChain:
    def __init__(self, retriever, llm, prompt, chat_manager: ChatManager):
        self.retriever = retriever
        self.llm = llm
        self.prompt = prompt
        self.chat_manager = chat_manager
        self.parser = StrOutputParser()

    @lru_cache(maxsize=100)
    def _cached_retrieve(self, question: str) -> str:
        docs = self.retriever.invoke(question)
        return "\n\n".join([doc.page_content for doc in docs])

    def _format_chat_history(self) -> List:
        from langchain_core.messages import HumanMessage, AIMessage
        messages = []
        for msg in self.chat_manager.history[-5:]:
            messages.append(HumanMessage(content=msg.question))
            messages.append(AIMessage(content=msg.answer))
        return messages

    def ask(self, question: str) -> ChatMessage:
        if config.ENABLE_CACHE:
            context = self._cached_retrieve(question)
        else:
            docs = self.retriever.invoke(question)
            context = "\n\n".join([doc.page_content for doc in docs])
        
        chain = self.prompt | self.llm | self.parser
        answer = chain.invoke({
            "context": context,
            "question": question,
            "chat_history": self._format_chat_history()
        })
        sources = context.split("\n\n")[:3]
        msg = ChatMessage(question=question, answer=answer, sources=sources)
        self.chat_manager.add_history(msg)
        return msg

# ===================== 主应用 =====================
class RAGAssistant:
    def __init__(self):
        print("🚀 初始化RAG团队知识助手...")
        self.llm = ModelFactory.get_llm()
        self.embeddings = ModelFactory.get_embeddings()
        self.chat_manager = ChatManager()
        self.vector_manager = VectorStoreManager(self.embeddings)
        self.rag_chain = None

    async def initialize(self):
        components = await self.vector_manager.build_or_load_vector_store()
        faiss_vs = components["vs"]
        bm25 = components["bm25"]
        
        faiss_retriever = DocumentAwareFAISSRetriever(vector_store=faiss_vs, k=config.RETRIEVE_TOP_K)
        retriever = self.vector_manager.get_mixed_retriever(faiss_retriever, bm25)
        
        self.rag_chain = RAGChain(
            retriever=retriever,
            llm=self.llm,
            prompt=self.chat_manager.prompt_template,
            chat_manager=self.chat_manager
        )
        print("✅ RAG助手初始化完成！")

    def show_help(self):
        print("""
📚 命令帮助：
q / quit    - 退出程序
help        - 显示帮助
collect     - 收藏上一轮对话
prompt      - 自定义Prompt模版
history     - 查看历史对话
clear       - 清空历史对话
""")

    async def run(self):
        await self.initialize()
        last_msg = None
        print("\n===== 🤖 团队知识助手已启动 =====")
        self.show_help()
        while True:
            query = input("\n💬 请输入问题/命令：").strip()
            if not query:
                continue
            if query.lower() in ["q", "quit"]:
                print("👋 再见！")
                break
            elif query.lower() == "help":
                self.show_help()
                continue
            elif query.lower() == "history":
                print(f"\n📜 历史对话（最近{len(self.chat_manager.history)}条）：")
                for i, msg in enumerate(self.chat_manager.history[-5:]):
                    print(f"{i+1}. Q: {msg.question}")
                continue
            elif query.lower() == "clear":
                self.chat_manager.history = []
                self.chat_manager.save_history()
                print("✅ 历史对话已清空")
                continue
            elif query.lower() == "collect" and last_msg:
                self.chat_manager.add_collection(last_msg)
                continue
            elif query.lower() == "prompt":
                print("\n✏️ 请输入自定义Prompt模版（输入end结束）：")
                lines = []
                while True:
                    line = input()
                    if line == "end":
                        break
                    lines.append(line)
                custom_template = "\n".join(lines)
                self.chat_manager.set_custom_prompt(custom_template)
                if self.rag_chain:
                    self.rag_chain.prompt = self.chat_manager.prompt_template
                continue

            try:
                start = time.time()
                msg = self.rag_chain.ask(query)
                last_msg = msg
                print(f"\n🤖 回答（耗时{time.time()-start:.2f}s）：")
                print(msg.answer)
                print("\n📚 参考来源：")
                for i, src in enumerate(msg.sources):
                    content = src[:200].replace("\n", " ")
                    print(f"【来源{i+1}】{content}...")
            except Exception as e:
                print(f"❌ 出错：{str(e)}")

if __name__ == "__main__":
    try:
        assistant = RAGAssistant()
        asyncio.run(assistant.run())
    except Exception as e:
        print(f"💥 系统异常：{str(e)}")