"""
Fetch 云端服务连通性测试脚本

用于验证云端 streamable_http Fetch MCP 服务是否可用。

注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址。
当前有效地址：https://mcp.api-inference.modelscope.net/f8c8c47b0f7f4a/mcp
"""

import asyncio
import logging

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from ai_knowledge_crawler_mcp.mcp_client_adapter import FetchAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_health_check():
    """测试健康检测功能"""
    print("=" * 60)
    print("Fetch 云端服务连通性测试")
    print("=" * 60)

    config = CrawlerConfig()
    print(f"\n[配置] 云端 MCP 地址：{config.FETCH_MCP_STREAM_URL}")
    print(f"[配置] 超时时间：{config.FETCH_MCP_TIMEOUT} 秒")

    adapter = FetchAdapter(config=config)

    print("\n[测试] 开始健康检测...")
    is_healthy = await adapter.health_check()

    print("\n" + "=" * 60)
    if is_healthy:
        print("✓ Fetch 云端服务状态：正常")
    else:
        print("✗ Fetch 云端服务状态：异常")
        print("\n可能原因：")
        print("  1. 云端 MCP 服务已过期，需重新部署获取新地址")
        print("  2. 网络连接问题")
        print("  3. 服务端暂时不可用")
    print("=" * 60)

    return is_healthy


async def test_single_fetch():
    """测试单次抓取功能"""
    print("\n" + "=" * 60)
    print("Fetch 单次抓取测试")
    print("=" * 60)

    config = CrawlerConfig()
    adapter = FetchAdapter(config=config)

    test_url = "https://www.example.com"
    print(f"\n[测试] 抓取 URL: {test_url}")

    result = await adapter.fetch_url(test_url, max_length=500)

    print("\n[结果]:")
    print(f"  状态：{result.get('status')}")
    print(f"  标题：{result.get('title', '')[:50]}...")
    print(f"  Markdown 长度：{len(result.get('markdown', ''))} 字符")
    if result.get('error'):
        print(f"  错误：{result.get('error')}")

    print("=" * 60)

    return result.get("status") == "success"


async def main():
    """主测试流程"""
    # 测试 1: 健康检测
    health_ok = await test_health_check()

    if not health_ok:
        print("\n[警告] 健康检测失败，跳过单次抓取测试")
        return

    # 测试 2: 单次抓取
    fetch_ok = await test_single_fetch()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"  健康检测：{'✓ 通过' if health_ok else '✗ 失败'}")
    print(f"  单次抓取：{'✓ 通过' if fetch_ok else '✗ 失败'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
