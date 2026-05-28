import logging
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor  # 并行核心
from .graph import build_agent_graph

logging.basicConfig(level=logging.INFO, format="%(asc'itime)s | %(levelname)s | %(message)s")
load_dotenv()

# ======================
# 单个任务执行逻辑（你原来的代码不动）
# ======================
def run_single_agent(task_id):
    logging.info(f"🚀 启动任务 {task_id}")
    app = build_agent_graph()
    
    initial_state = {
        "raw_data": [],
        "analysis_result": None,
        "html_content": None,
        "status": "pending",
        "error": None,
        "retry_count": 0
    }
    
    try:
        result = app.invoke(initial_state)
        logging.info(f"🏁 任务 {task_id} 完成 | 状态: {result['status']}")
        return result
    except Exception as e:
        logging.error(f"❌ 任务 {task_id} 失败: {str(e)}")
        return None

# ======================
# 🔥 并行运行 12 个任务（核心！）
# ======================
def run_batch_agents():
    # 你要跑 12 个任务
    total_tasks = [f"第{i}个数据" for i in range(1, 13)]

    # 一次并行跑 5 个（不会卡死 SearXNG，速度最快）
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(run_single_agent, total_tasks)

# ======================
# 主入口
# ======================
if __name__ == "__main__":
    run_batch_agents()  # 并行启动 12 个任务