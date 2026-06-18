# agent/skills/file_skill.py
import json
import os
import logging
from typing import List, Dict, Any

def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    """Skill：加载JSON文件"""
    logging.info(f"【执行加载skill】，入参file_path={file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"文件读取失败: {e}")
        raise

def save_json_file(file_path: str, data: Any):
    """Skill：保存JSON文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)