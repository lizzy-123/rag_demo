# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **LangChain-based RAG (Retrieval-Augmented Generation) system** with two main components:

1. **RAG Core (`rag_main.py`)**: Document Q&A system with hybrid retrieval (FAISS + BM25)
2. **Multi-Agent Analysis (`multi_agent/`)**: LangGraph-based workflow for analyzing RAG Q&A records and generating email reports


## Prerequisites: Start SearXNG (Required for Multi-Agent)

Before running multi-agent workflow, start SearXNG:

```bash
cd ~/code/SearXNG/searxng

# Activate virtual environment if needed (skip if prompt shows (searxng))
source .venv/bin/activate

# Start SearXNG
export SEARXNG_SECRET=$(openssl rand -hex 32)
python searx/webapp.py
```
SearXNG must be accessible at http://127.0.0.1:8888

## Run Commands

```bash
# Install dependencies
uv sync

# Run RAG chatbot
uv run python rag_main.py

# Run multi-agent workflow
uv run python -m multi_agent.main
```

## Configuration

Environment variables are configured in Defined in `.env` (LLM provider, embedding model, email settings):

## RAG Core (`rag_main.py`)

**Pipeline:**
```
Document Loading → Text Cleaning → Smart Chunking → FAISS Index → Hybrid Retrieval → LLM Answer
```

**Key Classes:**
- `ModelFactory`: Factory for LLM/embedding providers (dashscope/zhipu/openai)
- `BatchedZhipuAIEmbeddings`: Handles Zhipu's 64-document API limit
- `VectorStoreManager`: Incremental updates - rebuilds on file modification/deletion, incremental add on new files
- `RAGChain`: Query pipeline with caching and history
- `DocumentProcessor`: Async loading (PDF/TXT/DOCX/MD/XLSX/PPTX) with encoding detection

**Config (`Config` dataclass):**
- `RETRIEVE_TOP_K`: Retrieval count (default 3)
- `ENABLE_MIXED_RETRIEVAL`: FAISS+BM25 ensemble (default True, weights [0.4, 0.6])
- `BASE_CHUNK_SIZE/OVERLAP`: Chunking parameters (800/150)
- `ENABLE_CACHE`: LRU cache for repeated queries

## Multi-Agent System (`multi_agent/`)

**Structure:**
```
multi_agent/
├── main.py              # Entry point
└── agent/
    ├── main_graph.py    # Orchestrator graph
    ├── state.py         # State schema
    ├── sub_agents/      # Individual agents
    │   ├── data_agent.py
    │   ├── analysis_agent.py
    │   ├── search_agent.py
    │   └── report_agent.py
    └── harness/         # Execution utilities
```

**Workflow:**
```
data_agent → analysis_agent → [search_agent?] → report_agent → END
```

**State Schema (`agent/state.py`):**
Tracks Q&A records, analysis results, search status, and workflow state. See multi_agent/agent/state.py for schema details.

**Analysis Prompt:** 
Analysis: Categorizes questions into fixed categories for 软考架构师 exam. Categories defined in code.

**Dependencies:**
- SearXNG at `http://127.0.0.1:8888` for web search (if needed)

## Key Files

```
.
├── rag_main.py              # RAG chatbot entry point
├── multi_agent/main.py      # Multi-agent entry point
├── .env                     # Environment variables
├── team_doc/                # Knowledge base documents
└── faiss_team_vector_db/    # Vector store (gitignored)
```

## Known Constraints

- **Zhipu Embedding API**: 64-document batch limit (handled automatically)
- **TXT Encoding**: Multiple fallbacks (utf-8, gbk, gb18030) + chardet
- **Vector Store**: File modifications trigger full rebuild; only new files are incremental
- **SearXNG**: Required for web search in agent workflow
