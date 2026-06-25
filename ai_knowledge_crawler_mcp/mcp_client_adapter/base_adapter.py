"""
MCP Adapter Base Class

基础适配器类，封装 FastMCPClient 的通用调用逻辑。
"""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

# 添加项目根路径到 sys.path，以便导入 multi_agent.agent.mcp_client
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.agent.mcp_client import FastMCPClient

logger = logging.getLogger(__name__)


class MCPAdapterBase:
    """MCP 适配器基类，封装 FastMCPClient 调用逻辑"""

    def __init__(self, base_url: str, timeout: int = 50, adapter_name: str = "base"):
        """
        初始化 MCP 适配器

        Args:
            base_url: MCP 服务 HTTP 地址，如 "http://127.0.0.1:8011/mcp"
            timeout: 调用超时时间（秒）
            adapter_name: 适配器名称，用于日志标识
        """
        self.adapter_name = adapter_name
        self.client = FastMCPClient(base_url=base_url, timeout=timeout)
        self.base_url = base_url
        self.timeout = timeout
        logger.info(f"[{adapter_name}] MCP Adapter initialized: {base_url}")

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具返回结果（自动解析 JSON 或返回原始文本）
        """
        try:
            logger.debug(f"[{self.adapter_name}] Calling tool: {tool_name}, args: {arguments}")
            result = await self.client.call_tool(tool_name, arguments)
            logger.debug(f"[{self.adapter_name}] Tool {tool_name} completed successfully")
            return result
        except TimeoutError as e:
            logger.error(f"[{self.adapter_name}] Tool {tool_name} timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.adapter_name}] Tool {tool_name} failed: {e}")
            raise

    async def read_resource(self, resource_uri: str) -> Optional[str]:
        """
        读取 MCP 资源

        Args:
            resource_uri: 资源 URI

        Returns:
            资源内容文本
        """
        try:
            logger.debug(f"[{self.adapter_name}] Reading resource: {resource_uri}")
            content = await self.client.read_resource(resource_uri)
            logger.debug(f"[{self.adapter_name}] Resource {resource_uri} read successfully")
            return content
        except Exception as e:
            logger.error(f"[{self.adapter_name}] Failed to read resource {resource_uri}: {e}")
            raise
