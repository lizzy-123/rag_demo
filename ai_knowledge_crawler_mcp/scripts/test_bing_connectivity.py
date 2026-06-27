"""
Bing 云端服务连通性测试脚本

用于验证云端 streamable_http Bing MCP 服务是否可用。

注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址。
当前有效地址：https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp
"""

import asyncio
import logging

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from ai_knowledge_crawler_mcp.mcp_client_adapter import BingSearchAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_health_check():
    """测试健康检测功能"""
    print("=" * 60)
    print("Bing 云端服务连通性测试")
    print("=" * 60)

    config = CrawlerConfig()
    print(f"\n[配置] 云端 MCP 地址：{config.BING_SEARCH_MCP_STREAM_URL}")
    print(f"[配置] 超时时间：{config.BING_MCP_TIMEOUT} 秒")

    adapter = BingSearchAdapter(config=config)

    print("\n[测试] 开始健康检测...")
    is_healthy = await adapter.health_check()

    print("\n" + "=" * 60)
    if is_healthy:
        print("✓ Bing 云端服务状态：正常")
    else:
        print("✗ Bing 云端服务状态：异常")
        print("\n可能原因：")
        print("  1. 云端 MCP 服务已过期，需重新部署获取新地址")
        print("  2. 网络连接问题")
        print("  3. 服务端暂时不可用")
    print("=" * 60)

    return is_healthy


async def test_single_search():
    """测试单次搜索功能"""
    print("\n" + "=" * 60)
    print("Bing 单次搜索测试")
    print("=" * 60)

    config = CrawlerConfig()
    adapter = BingSearchAdapter(config=config)

    test_keyword = "RAG"
    print(f"\n[测试] 搜索关键词：{test_keyword}")

    result = await adapter.search_single_keyword(keyword=test_keyword, limit=3)

    print("\n[结果]:")
    print(f"  返回结果数量：{len(result)}")
    if result:
        print(f"  第一条结果标题：{result[0].get('title', '')[:50]}...")
        print(f"  第一条结果 URL: {result[0].get('url', '')[:50]}...")
    else:
        print("  未获取到搜索结果")

    print("=" * 60)

    return len(result) > 0


async def main():
    """主测试流程"""
    # 测试 1: 健康检测
    health_ok = await test_health_check()

    if not health_ok:
        print("\n[警告] 健康检测失败，跳过单次搜索测试")
        return

    # 测试 2: 单次搜索
    search_ok = await test_single_search()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"  健康检测：{'✓ 通过' if health_ok else '✗ 失败'}")
    print(f"  单次搜索：{'✓ 通过' if search_ok else '✗ 失败'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
