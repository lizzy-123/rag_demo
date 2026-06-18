from langchain_text_splitters import RecursiveCharacterTextSplitter

text = "人工智能技术的快速发展正在深刻改变各行各业的生产方式。大语言模型凭借强大的语义理解能力，已成为企业数字化转型的核心引擎。然而，通用模型在处理垂直领域问题时，往往面临知识滞后与事实幻觉等挑战。为此，检索增强生成架构应运而生。它通过将外部专业知识库与模型推理过程深度融合，显著提升了输出的准确性。在构建检索系统时，文档的预处理环节至关重要。原始语料通常夹杂大量格式符号与噪声数据，若直接送入向量数据库，将严重干扰语义匹配的精度。因此，文本分块成为数据清洗流水线中的标准步骤。理想的切分策略需要在控制片段长度的同时，最大限度保留上下文连贯性。递归字符切分器正是基于这一理念设计，它采用多级分隔符降级机制。优先识别自然语义边界，仅在超长片段中逐层细化切分粒度。配合重叠窗口技术，该算法能有效防止关键实体被强行截断。合理配置参数是打造高效检索链路的前提条件。随着长上下文技术的普及，动态分块算法将持续演进，为智能应用提供更高质量的数据支撑。"

splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "；", "，", " ", ""],
    length_function=len
)

chunks = splitter.split_text(text)

print(f"📏 原文长度: {len(text)}\n")
for i in range(len(chunks)-1):
    prev = chunks[i]
    curr = chunks[i+1]
    
    # 从上一块末尾往前找，直到与下一块开头完全一致
    actual_overlap_len = 0
    for l in range(min(len(prev), len(curr)), 0, -1):
        if prev[-l:] == curr[:l]:
            actual_overlap_len = l
            break
            
    print(f"✅ Chunk_{i} → Chunk_{i+1}")
    print(f"   实际重叠长度: {actual_overlap_len} (预算≤50)")
    print(f"   重叠内容: 「{prev[-actual_overlap_len:]}」")
    print("-" * 60)