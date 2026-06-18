# import sys
# from pathlib import Path
# ROOT = Path(__file__).parent.parent
# sys.path.append(str(ROOT))

# import asyncio
# from multi_agent.agent.mcp_client import init_all_mcp_clients, close_all_mcp_clients, file_mcp_client

# async def test_file_mcp():
#     try:
#         print("1. 开始初始化所有 MCP 连接...")
#         # 加整体超时，防止无限卡死
#         await asyncio.wait_for(init_all_mcp_clients(), timeout=10)
#         print("2. MCP 连接初始化完成")

#         print("3. 调用 savejson 工具...")
#         res = await asyncio.wait_for(
#             file_mcp_client.call_tool("savejson", {"file_path": "demo.json", "data": {"hello": "mcp"}}),
#             timeout=8
#         )
#         print(f"✅ 写入结果: {res}")

#         print("4. 调用 loadjson 工具...")
#         res2 = await asyncio.wait_for(
#             file_mcp_client.call_tool("loadjson", {"file_path": "demo.json"}),
#             timeout=8
#         )
#         print(f"✅ 读取结果: {res2}")

#     except asyncio.TimeoutError:
#         print("❌ 调用超时：客户端与 MCP 服务通信阻塞")
#     except Exception as e:
#         print(f"❌ 执行异常: {type(e).__name__}: {e}")
#     finally:
#         print("5. 开始关闭连接...")
#         await close_all_mcp_clients()
#         print("6. 连接已关闭")

# if __name__ == "__main__":
#     asyncio.run(test_file_mcp())

import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

import asyncio
from multi_agent.agent.mcp_client import (
    close_all_mcp_clients,
    file_mcp_client
)

async def test_file_mcp1():
    try:
        # print("1. 并发初始化所有 MCP 长连接...")
        # await init_all_mcp_clients()

        print("2. 调用 savejson")
        res = await file_mcp_client.call_tool("savejson", {"file_path": "demo.json", "data": [{"test": "ok"}]})
        print("写入结果:", res)

        print("3. 调用 loadjson")
        res2 = await file_mcp_client.call_tool("loadjson", {"file_path": "demo.json"})
        print("读取结果:", res2)
        print("✅ 功能正常")

    except Exception as e:
        print(f"❌ 异常: {e}")
    finally:
        print("4. 统一关闭所有连接")
        await close_all_mcp_clients()

async def test_file_mcp():
    try:
        print("2. 调用 savejson")
        res = await asyncio.wait_for(
            file_mcp_client.call_tool("savejson", {"file_path": "demo.json", "data": [{"test": "ok"}]}),
            timeout=8
        )
        print("写入结果:", res)

        print("3. 调用 loadjson")
        res2 = await asyncio.wait_for(
            file_mcp_client.call_tool("loadjson", {"file_path": "demo.json"}),
            timeout=8
        )
        print("读取结果:", res2)
        print("✅ 功能正常")

    except asyncio.TimeoutError:
        print("❌ 异常: MCP调用超时，通信阻塞")
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {e}")
    finally:
        print("4. 统一关闭所有连接")
        await close_all_mcp_clients()
        print("连接清理完成\n")

if __name__ == "__main__":
    asyncio.run(test_file_mcp())