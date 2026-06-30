# 项目全局通用规范（所有会话永久生效）
## 1. 文件访问约束
仅允许读写 langchain_rag_team/ai_knowledge_crawler_mcp/ 目录内文件；
顶层 agent 文件夹、scripts、docs、根目录entry.py 禁止修改，仅可读取参考。
只读依赖文件：base_adapter.py、config_reader.py、url_manager.py、file_manager.py，仅读取上下文，不修改源码。

## 2. Python 环境强制规则
本项目使用 uv 管理虚拟环境，所有执行命令必须带 uv run：
- 运行脚本：uv run python xxx.py
- 代码检查：uv run ruff check
- 单元测试：uv run pytest
禁止直接使用 python / python3 裸命令。

## 3. 代码通用开发规范
1. 日志统一使用项目封装工具，禁止原生 logging 零散初始化；
2. 异常统一分层自定义异常，禁止裸 except Exception 捕获；
3. 新增工具类统一放置在 utils 目录；
4. 所有业务逻辑保留，优化仅做健壮性改造，不删减原有功能；
5. 修改完成后输出独立 Changelog 变更清单。