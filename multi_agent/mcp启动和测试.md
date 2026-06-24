# mcp有2中方式，一种是stdio 一种是Streanable Http
## stdio测试：
- # 用 uv run 启动 Python，保证虚拟环境依赖生效
npx @modelcontextprotocol/inspector uv run python multi_agent/agent/mcp_servers/email_server.py    
- npx @modelcontextprotocol/inspector python xxx.py → 只能走 Stdio，不能连 Streamable HTTP

## streamable http
- 连 Streamable HTTP 必须分开两个终端，分别启动服务、启动 Inspector
1. 代码中transport = "streamable-http"
2. 启动服务(终端A):  uv run python multi_agent/agent/mcp_servers/email_server.py
2.1 看到日志即代表服务就绪：
Uvicorn running on http://0.0.0.0:8010 (Press CTRL+C to quit)
Starting MCP server 'email-mcp' with transport 'streamable-http' on http://0.0.0.0:8010/mcp

3. 单独启动mcp inspector（终端B，不带python脚本
   基础启动命令（解决端口占用可选自定义端口）
   bash
   # 默认端口6274网页面板、6277代理
npx @modelcontextprotocol/inspector

# 若端口被占用，自定义端口启动
npx @modelcontextprotocol/inspector --port 6280 --inspector-port 6275

执行后终端会输出网页地址，复制链接打开浏览器：
🔗 Open inspector with token pre-filled: http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=xxx

第三步：浏览器面板配置 Streamable HTTP（关键界面操作）
Transport Type 下拉框：选择 Streamable HTTP
URL 输入框：完整填写 http://127.0.0.1:8010/mcp（末尾必须带 /mcp）
Authentication 折叠面板：完全不要点开、不要填任何 token（本地 FastMCP 默认无外部鉴权，session 由 SSE 自动生成）
下方不要切换 Server Entry / Servers File，保持默认
直接点击 Connect 按钮



Streamable HTTP 完整连接教程（FastMCP + MCP Inspector）
一、整体流程（分两大块）
终端 1：启动 Streamable HTTP 模式的 MCP 服务（常驻后台）
终端 2：单独启动 MCP Inspector 网页面板（不携带 python 命令）
浏览器面板配置 Streamable HTTP 参数连接
重点区分：
npx @modelcontextprotocol/inspector python xxx.py → 只能走 Stdio，不能连 Streamable HTTP
连 Streamable HTTP 必须分开两个终端，分别启动服务、启动 Inspector
二、第一步：修改代码，开启 Streamable HTTP
你的 email_server.py 启动代码必须保留 streamable-http，注释掉 stdio：
python
运行
if __name__ == "__main__":
    # 开启流式HTTP，监听0.0.0.0:8010
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8010
    )
    # 注释掉stdio模式
    # mcp.run(transport="stdio")
启动服务（终端 A）
bash
运行
uv run python multi_agent/agent/mcp_servers/email_server.py
看到日志即代表服务就绪：
plaintext
Uvicorn running on http://0.0.0.0:8010 (Press CTRL+C to quit)
Starting MCP server 'email-mcp' with transport 'streamable-http' on http://0.0.0.0:8010/mcp
三、第二步：单独启动 MCP Inspector（终端 B，不带 python 脚本）
基础启动命令（解决端口占用可选自定义端口）
bash
运行
# 默认端口6274网页面板、6277代理
npx @modelcontextprotocol/inspector

# 若端口被占用，自定义端口启动
npx @modelcontextprotocol/inspector --port 6280 --inspector-port 6275
执行后终端会输出网页地址，复制链接打开浏览器：
plaintext
🔗 Open inspector with token pre-filled: http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=xxx
四、第三步：浏览器面板配置 Streamable HTTP（关键界面操作）
Transport Type 下拉框：选择 Streamable HTTP
URL 输入框：完整填写 http://127.0.0.1:8010/mcp（末尾必须带 /mcp）
Authentication 折叠面板：完全不要点开、不要填任何 token（本地 FastMCP 默认无外部鉴权，session 由 SSE 自动生成）
下方不要切换 Server Entry / Servers File，保持默认
直接点击 Connect 按钮
正确配置对照你的截图
第一张 8002 正常截图就是标准配置：
Transport：Streamable HTTP
URL：http://127.0.0.1:8002/mcp
Authentication 折叠不展开
点击 Reconnect 后绿色 Connected
五、你之前报错 Proxy Authentication Required 的 4 个核心避坑点
坑 1：浏览器缓存 / 旧会话冲突（最高概率）
解决：
完全关闭所有 Inspector 标签页，重启浏览器
使用无痕 / 隐私窗口打开 Inspector 链接（无 LocalStorage 缓存）
手动完整输入 URL，不要从历史记录选择
坑 2：host 写 127.0.0.1，浏览器同源阻断 SSE
服务代码写 host="0.0.0.0"，URL 填 http://127.0.0.1:8010/mcp；
不要服务绑定 127.0.0.1，浏览器会隔离 SSE 长连接，拿不到 session_token。
坑 3：混用 Stdio 启动命令（致命错误）
不要执行：
bash
运行
# 错误！这条强制走stdio，和streamable http服务不兼容
npx @modelcontextprotocol/inspector uv run python email_server.py
必须分两个终端，服务单独跑，Inspector 单独启动。
坑 4：浏览器安全策略拦截 SSE（Chrome 最严重）
Chrome 对本地localhost SSE 限制严格，换 Firefox / Edge 无痕窗口重试，90% 能直接连通。
六、Streamable HTTP 完整握手原理（对应你之前的疑问）
GET /mcp（SSE 长连接握手）
浏览器发起 GET，携带 Accept: text/event-stream，服务生成唯一 session_token，通过 SSE 数据流下发给 Inspector，浏览器内存保存该 token，长连接持续打开。
POST /mcp（工具调用鉴权）
所有调用工具、读取资源的 POST 请求，自动携带刚才拿到的 session_token；
服务校验内存中存在绑定该 token 的活跃 SSE 长连接，鉴权通过，执行工具；
报错 Proxy Authentication Required = SSE 建立失败，浏览器没拿到 session_token，POST 无凭证被拦截。
七、排错自检清单（按顺序排查）
✅ 服务终端日志确认 streamable-http 监听 0.0.0.0:8010/mcp，无报错
✅ Inspector 是单独启动，命令末尾没有python 脚本
✅ 浏览器用无痕窗口，URL 完整带 /mcp
✅ Transport Type 严格选 Streamable HTTP，Authentication 不展开
✅ 关闭 Chrome 插件 / 代理，或切换 Edge/Firefox
✅ 先 Ctrl+C 关闭旧服务、旧 Inspector，清理残留端口进程再重启
八、两种调试方式对比
表格
模式	启动方式	优缺点	适用场景
Streamable HTTP	双终端分开启动服务 + Inspector	支持远程部署、多客户端同时连接；本地浏览器易 SSE 拦截报错	线上部署、多客户端共享服务
Stdio	单条 npx 命令拉起服务	无 HTTP 鉴权、无 SSE 报错，调试稳定	本地单机开

## 解决端口占用6274
方案1：杀掉占用6274的残留进程(WSL/Linux)
lsof -i :6274
#杀掉进程，替换PID查到数字
kill -9 pid

方案2：自定义端口启动 inspector,避开占用
用 --inspector-port 指定新网页端口，同时保留代理端口参数:
npx @modelcontextprotocol/inspector --port 6280 -- inspector-port 6275 uv run python multi_agent/agent/mcp_servers/email_server.py

--port 6280 :代理服务端口(替代6277)
--inspector-port 6275:前端网页端口(替换6274)


## 解析命令npx @modelcontextprotocol/inspector python hello_server.py
1. npx:Node.js 自带工具，临时下载并运行 npm 包，不用手动安装。
不用执行 npm install -g xxx 全局安装工具；
执行完自动清理临时文件，不会污染本地环境。

2. @modelcontextprotocol/inspector
官方 MCP 调试可视化工具包（MCP Inspector），相当于 MCP 协议的「Postman」，专门用来调试你写的 FastMCP 服务。
内置网页可视化界面，能查看工具、资源、提示词、收发协议日志；
自带代理中转程序，可以打通浏览器和本地 stdio 模式的 MCP 服务。

3. python hello_server.py
传给 Inspector 的子进程启动命令：
让 Inspector 自动执行 python hello_server.py，拉起你的 Python MCP 服务，走 stdio 传输 建立连接。

### 整条命令完整作用
  这条命令一次性完成两件事：
  1. 自动启动你的python mcp服务
     inspector 内部新开子进程，运行 python *.py，读取进程标准输入输出(stido)和mcp服务通信
  2. 启动可视化调试网页
     自动打开浏览器，访问http:localhost:6274 页面默认使用stdio 传输直连服务

     优势：
     1.完全绕开 streamable Http 的sse/session_token 鉴权报错
     stdio 不走http\sse\浏览器长连接，没有Proxy Authentication required \Missing session ID拦截
     2.一键启动，不用手动分2个终端
      不用一个终端跑服务，另一个开inspector;一条命令同时拉起服务+调试面板
     3.环境变量、python路径自动透传
3. 底层运行流程
  1. 终端执行命令-》npx下载inspector Node工具
  2. inspector启动内置代理程序
  3. 代理自动创建子进程，执行python .py启动mcp
  4. 代理通过标准输入输出和python mcp双向传输mcp json-rpc消息；
  5. 代理同时开启本地网页服务，浏览器页面和代理通过 WebSocket 通信；
  6. 你在网页点调用工具、读资源，指令会中转给 Python 服务，返回结果可视化展示。

一、先拆解 Streamable HTTP 完整握手流程（MCP 官方标准）
FastMCP 实现的 streamable-http 是 MCP 协议官方推荐的 HTTP 传输方案，核心靠 SSE（Server-Sent Events）长连接 做会话绑定，分两段逻辑：
1. 第一步：GET /mcp —— 建立 SSE 长连接，下发 session_token（会话凭证）
1.1 SSE 是什么？
普通 HTTP 是短连接：客户端发请求 → 服务返回数据 → 连接立刻断开。
SSE 是单向长连接：客户端发起一次 GET 请求后，TCP 连接持续保持打开，服务可以源源不断主动推送消息给客户端，不用客户端反复轮询。
1.2 这一步发生了什么？
浏览器 / Inspector 发起 GET 请求，必须带请求头 Accept: text/event-stream，告诉服务 “我要建立 SSE 长连接”；
服务收到合法 SSE 请求后：
生成一个全局唯一的字符串 session_token（随机 UUID，作为本次会话身份证）；
在内存中保存这条 SSE 长连接 + 绑定这个 token；
通过 SSE 数据流把 session_token 推送给前端 Inspector；
Inspector 拿到 token 后，存在浏览器内存 / 本地存储，标记 “当前已建立有效会话”。
1.3 session_token 本质是什么？
它是当前 SSE 长连接的唯一身份凭证：
一个 SSE 长连接 = 一个唯一 session_token，一一绑定；
只要这条 SSE 不断开，token 永久有效；
关闭页面 / 断开 SSE，token 立刻失效，服务销毁会话。
举个例子，服务下发的 SSE 消息类似：
plaintext
data: {"sessionId":"sess_9f2d7810-xxxx-xxxx-xxxx"}
这里的 sess_9f2d7810-xxxx 就是 session_token。
2. 第二步：POST /mcp —— 所有业务请求必须携带 token 鉴权
MCP 的工具调用、读取资源、执行 prompt，全部走 POST /mcp 接口传输 JSON-RPC 消息。
鉴权规则：
服务会校验每一条 POST 请求：请求对应的客户端，是否存在一条活跃、持有相同 session_token 的 SSE 长连接。
✅ 匹配成功：放行，执行你的 send_email、calculate 等工具；
❌ 匹配失败：直接拦截，抛出鉴权错误（就是你看到的 Proxy Authentication Required / Missing session ID）。
为什么要这么设计？
MCP Streamable HTTP 是有状态会话协议：
SSE 长连接负责服务主动推送通知、日志；
POST 请求负责客户端下发调用指令；
必须用同一个 session_token 绑定两条通道，防止跨会话伪造请求、多客户端串数据。

