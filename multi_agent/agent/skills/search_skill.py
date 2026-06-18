# agent/skills/search_skill.py
import requests
import logging
from typing import List, Dict

SEARXNG_URL = "http://127.0.0.1:8888/search"
SEARCH_TIMEOUT = 15

def searxng_search(query: str) -> List[Dict[str, str]]:
    """Skill：调用本地SearXNG搜索"""
    logging.info(f"【执行searxng_searchskill】，入参query={query}")
    try:
        resp = requests.get(
            SEARXNG_URL,
            params={"q": query, "format": "json"},
            timeout=SEARCH_TIMEOUT
        )
        data = resp.json()
        return [
            {"title": r.get("title", ""), "content": r.get("content", "")}
            for r in data.get("results", [])[:3]
        ]
    except Exception as e:
        logging.error(f"搜索请求失败: {e}")
        raise