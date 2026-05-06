#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG 团队知识助手 - 可切换模型（智谱AI / OpenAI）
使用 LangChain 1.x 组件，兼容 langchain-zhipu 包
"""

"""
之后需要调整实验的：
1.FAISS向量数据库更换为另外数据库，不同数据库有什么优缺点或者特点
2.文档加载器还有其他的吗？如果需要图片处理怎么办？
3.文本分割器方式，有什么优化方法
4.经典检索问答：为啥需要问答链，还有其他的吗？
5.加载模型时参数温度：控制输出随机性是什么意思？
6.如果加载其他模型，同样是if else吗？
7.向量嵌入模型有哪几类？不同的大模型有自己的向量模型吗？OpenAiEmbeddings和ZhipuEmbeddingd
8.chain_type=stuff是什么意思？简单场景是这个？其他场景是什么？
"""
import os
from dotenv import load_dotenv

# 文档加载与处理（通用）
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# 经典链（LangChain 1.x 需要从 classic 导入）
from langchain_classic.chains import RetrievalQA

# 加载 .env 文件
load_dotenv()

# ===================== 模型工厂函数 =====================
def get_llm(provider: str = None, temperature: float = 0.1, **kwargs):
    """
    根据 provider 返回对应的 LLM 实例
    provider: 'zhipu' 或 'openai'（默认从环境变量 LLM_PROVIDER 读取，若未设置则使用 zhipu）
    """
    provider = provider or os.getenv("LLM_PROVIDER", "zhipu").lower()
    temperature = kwargs.get("temperature", temperature)

    if provider == "openai":
        # 延迟导入，避免未安装该包时报错
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", None),
        )
    elif provider == "zhipu":
        from langchain_community.chat_models import ChatZhipuAI
        return ChatZhipuAI(
            model=os.getenv("ZHIPU_MODEL", "glm-4"),
            temperature=temperature,
            api_key=os.getenv("ZHIPUAI_API_KEY"),
            base_url=os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
        )
    else:
        raise ValueError(f"不支持的 LLM provider: {provider}，请在 .env 中设置 LLM_PROVIDER=zhipu 或 openai")

def get_embeddings(provider: str = None):
    """
    根据 provider 返回对应的 Embeddings 实例
    """
    provider = provider or os.getenv("EMBEDDING_PROVIDER", "zhipu").lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", None),
        )
    elif provider == "zhipu":
        from langchain_community.embeddings import ZhipuAIEmbeddings
        return ZhipuAIEmbeddings(
            model=os.getenv("ZHIPU_EMBEDDING_MODEL", "text-embedding"),
            api_key=os.getenv("ZHIPUAI_API_KEY"),
            base_url=os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
        )
    else:
        raise ValueError(f"不支持的 Embedding provider: {provider}")

# ===================== 文档处理函数 =====================
def load_document(file_path: str):
    """根据扩展名自动选择加载器"""
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path, encoding="utf-8")
    elif file_path.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
    else:
        raise Exception(f"不支持的文件格式: {file_path}，仅支持 .pdf / .txt / .docx")
    return loader.load()

def split_documents(docs, chunk_size: int = 800, chunk_overlap: int = 150):
    """文档分块"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "，", " ", ""],
    )
    return text_splitter.split_documents(docs)

def build_vector_store(split_docs, embeddings, persist_dir: str = "faiss_team_vector_db"):
    """构建 FAISS 向量库并保存"""
    vector_store = FAISS.from_documents(split_docs, embeddings)
    vector_store.save_local(persist_dir)
    return vector_store

def load_vector_store(embeddings, persist_dir: str = "faiss_team_vector_db"):
    """加载本地的 FAISS 向量库"""
    return FAISS.load_local(persist_dir, embeddings, allow_dangerous_deserialization=True)

def build_rag_chain(vector_store, llm, top_k: int = 3):
    """构建 RetrievalQA 链"""
    retriever = vector_store.as_retriever(search_kwargs={"k": top_k})
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )

# ===================== 主程序 =====================
if __name__ == "__main__":
    # ----- 配置区 -----
    DOC_PATH = "./team_doc/2015年系统架构师考试科目三：论文真题.pdf"   # 请修改为你的文档路径
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150
    RETRIEVE_TOP_K = 3
    VECTOR_DB_DIR = "faiss_team_vector_db"

    print("🚀 正在初始化模型...")
    llm = get_llm()
    embeddings = get_embeddings()
    print(f"✅ 当前使用 LLM: {type(llm).__name__}, Embeddings: {type(embeddings).__name__}")

    # ----- 首次运行：构建向量库 -----
    # 如果已经构建过，可以注释掉下面三行，并取消注释 load_vector_store 那一行
    print(f"📄 正在加载文档: {DOC_PATH}")
    docs = load_document(DOC_PATH)
    print(f"📑 文档加载完成，共 {len(docs)} 页/段落")
    split_docs = split_documents(docs, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"✂️ 文档分割完成，共 {len(split_docs)} 个文本块")
    vector_store = build_vector_store(split_docs, embeddings, VECTOR_DB_DIR)
    print(f"💾 向量库已保存至 {VECTOR_DB_DIR}")

    # 后续运行时，可以直接加载已有的向量库（避免重复解析）
    # vector_store = load_vector_store(embeddings, VECTOR_DB_DIR)
    # print("💾 已从本地加载向量库")

    # ----- 构建 RAG 问答链 -----
    rag_chain = build_rag_chain(vector_store, llm, RETRIEVE_TOP_K)

    # ----- 命令行交互 -----
    print("\n===== 团队知识助手已启动，输入 q 退出 =====\n")
    while True:
        question = input("💬 请输入问题：").strip()
        if question.lower() == "q":
            break
        if not question:
            continue
        try:
            result = rag_chain.invoke(question)
            print("\n🤖 助手回答：")
            print(result["result"])
            print("\n📚 引用知识库原文：")
            for idx, doc in enumerate(result["source_documents"]):
                preview = doc.page_content[:200].replace("\n", " ")
                print(f"【参考片段 {idx+1}】{preview}...")
            print("-" * 60)
        except Exception as e:
            print(f"❌ 发生错误: {e}")

    print("👋 已退出知识助手")