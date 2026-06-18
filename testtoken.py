import tiktoken
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 配置
BASE_CHUNK_SIZE = 200
BASE_CHUNK_OVERLAP = 40
DOC_DIR = "./team_doc"

# 初始化 text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=BASE_CHUNK_SIZE,
    chunk_overlap=BASE_CHUNK_OVERLAP,
    length_function=len,
)

# 收集所有文本块
all_chunks = []

# 支持的纯文本扩展名
TEXT_EXTENSIONS = {".txt", ".md", ".text", ".rst", ".py", ".json", ".yaml", ".yml", ".csv"}

# 编码尝试列表
ENCODINGS = ['utf-8', 'utf-16', 'gbk', 'gb18030', 'latin-1']

for file_path in Path(DOC_DIR).rglob("*"):
    if not file_path.is_file():
        continue
    if file_path.suffix.lower() not in TEXT_EXTENSIONS:
        continue
    # 尝试不同编码读取文件
    for enc in ENCODINGS:
        try:
            with open(file_path, "r", encoding=enc) as f:
                text = f.read()
            break  # 成功读取，跳出编码循环
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        print(f"⚠️ 无法解码文件: {file_path}，已跳过")
        continue
    
    # 分块
    chunks = text_splitter.split_text(text)
    all_chunks.extend(chunks)

print(f"📊 总共 {len(all_chunks)} 个文本块")

# 如果没有文本块，退出
if not all_chunks:
    print("❌ 没有找到任何文本块，请检查 team_doc 目录下是否有支持的文本文件。")
    exit(1)

# 使用 tiktoken 计算 token 数（智谱兼容）
encoding = tiktoken.get_encoding("cl100k_base")

# 检查每个 chunk 是否超过 512 tokens
overlong = []
for i, chunk in enumerate(all_chunks):
    token_len = len(encoding.encode(chunk))
    if token_len > 512:
        overlong.append((i, token_len))
        print(f"⚠️ 块 {i} 长度 {token_len} tokens (超过512)")

if overlong:
    print(f"❌ 发现 {len(overlong)} 个块超过单条限制，请减小 chunk_size")
else:
    print("✅ 所有块都 ≤512 tokens")

# 检查总 token 数和批次
total_tokens = sum(len(encoding.encode(chunk)) for chunk in all_chunks)
print(f"📈 所有块总 token 数: {total_tokens}")

batch_size_limit = 25  # 你打算每批发送的数量
max_tokens_per_batch = 8000
estimated_batches = (total_tokens + max_tokens_per_batch - 1) // max_tokens_per_batch
print(f"预估需分 {estimated_batches} 批，每批最多 {batch_size_limit} 条")

# 模拟分批（按数量）
print("模拟分批结果：")
for batch_idx in range(0, len(all_chunks), batch_size_limit):
    batch_chunks = all_chunks[batch_idx:batch_idx+batch_size_limit]
    batch_tokens = sum(len(encoding.encode(chunk)) for chunk in batch_chunks)
    batch_num = batch_idx // batch_size_limit + 1
    if batch_tokens > max_tokens_per_batch:
        print(f"⚠️  第 {batch_num} 批 token 数 {batch_tokens} > 8000，请减小 batch_size")
    else:
        print(f"✅ 第 {batch_num} 批 token 数 {batch_tokens}")