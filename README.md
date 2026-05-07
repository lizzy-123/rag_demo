# 团队知识助手 - RAG 问答系统

基于 LangChain 和智谱 AI 的 RAG（检索增强生成）问答系统。支持批量文档、多文件类型、历史记忆、混合检索、自定义 Prompt 等功能。


## 功能特点

### 📄 文档处理
- 自动扫描 `team_doc` 目录，支持递归子目录加载
- 支持格式：PDF、TXT、DOCX、MD、XLSX、PPTX（可轻松扩展）
- 智能分块：根据文档长度自动调整 chunk_size 和 overlap
- 噪音清洗：自动移除 QQ 群、URL、水印、多余空行

### 🧠 检索与问答
- **混合检索**：FAISS 向量检索（语义匹配）+ BM25 关键词检索（加权融合），提升召回率与准确率
- **缓存机制**：LRU 缓存相同问题的检索结果，重复提问秒回
- 答案可溯源：返回引用文档片段

### 💬 对话体验
- **历史记忆**：本地 JSON 持久化，重启不丢失；自动限制最大轮数
- **收藏功能**：输入 `collect` 保存优质问答
- **自定义 Prompt**：实时输入自定义模板
- 命令支持：`help`、`history`、`clear`、`prompt`、`collect`

### ⚙️ 架构与性能
- 异步文档加载，多文件并行处理
- 自动检测已有向量库，增量添加新文件（删除/修改触发全量重建）
- 模块化设计，易于切换模型（智谱/OpenAI）或向量库（Chroma/Pinecone 等）

## 项目结构

```text
.
├── rag_main.py           # 主程序
├── pyproject.toml        # 项目依赖声明 (uv 使用)
├── uv.lock               # 精确锁定依赖版本
├── .env.example          # 环境变量模板
├── team_doc/             # 存放知识文档的目录
├── faiss_team_vector_db/ # 向量库存储目录（自动生成）
├── chat_history.json     # 历史对话记录（自动生成）
├── collection.json       # 收藏记录（自动生成）
└── cache/                # 检索缓存目录（自动生成）
```


## 环境要求
- Python 3.10 或更高版本
- UV 包管理工具（推荐）或 pip

## 安装与配置

### 1. 克隆仓库

```bash
git clone <你的仓库地址>
cd langchain_rag_team
```
### 2. 安装依赖
使用 uv（推荐）：
uv sync

### 3.配置环境变量
- 复制 .env.example 为 .env：
```python 
cp .env.example .env
```
- 编辑 .env，填入你的智谱 AI API 密钥：
```python 
ZHIPUAI_API_KEY=你的真实API密钥
ZHIPU_MODEL=glm-4-flash
ZHIPU_EMBEDDING_MODEL=embedding-2
```
### 4. 准备文档
- 将你的知识文档（PDF、TXT、DOCX）放入 team_doc/ 目录下，并修改 rag_main.py 中的 DOC_PATH 指向你的文件（或修改代码支持批量加载）。
### 运行
```python
uv run python rag_main.py
```

首次运行时会：

- 加载、分割文档

- 调用智谱嵌入 API 生成向量并保存到 FAISS

- 启动命令行问答交互

- 输入问题后按回车，输入 q 退出。
## 切换模型
项目已预留 OpenAI 支持。若要使用 OpenAI：

1. 安装 langchain-openai：uv add langchain-openai

2. 修改 .env 中的 LLM_PROVIDER 和 EMBEDDING_PROVIDER 为 openai

3. 填入 OPENAI_API_KEY 等配置

4. 删除旧的向量库目录，重新运行（因为嵌入向量不兼容）

### 常见问题
**Q: 提示“模型不存在”错误？**  
A: 智谱 AI 的嵌入模型名称应为 embedding-2 或 embedding-3，不是 text-embedding。请检查 .env 中的 ZHIPU_EMBEDDING_MODEL。

**Q: 文档分割后得到 0 个文本块？**  
A: 确保 PDF 不是扫描件（无文字层）。可尝试用其他 PDF 测试，或使用 OCR 工具预处理。

**Q: 如何分享给团队？**  
A: 提交代码时请勿包含 .env 文件（已在 .gitignore），其他人需自行创建 .env 并填入自己的 API 密钥。

### 后续优化方向
1. 批量加载文件夹下所有文档

2. 支持更多向量库（Chroma、Pinecone）

3. 添加 Web 界面（Streamlit / Gradio）

4. 支持历史对话记忆
