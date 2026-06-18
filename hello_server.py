from fastmcp import FastMCP
import math
import datetime
import random



#初始化MCP服务，设置服务器名称和版本
mcp = FastMCP("demo-service",version="1.0.0")

#----------------------------------
#1. 工具示例：不同参数类型+实用功能
#----------------------------------



@mcp.tool()
def greet(name:str,formal:bool = False)->str:
    """
    向指定的人打招呼,支持正式、非正式两种语气
    :param name:对方名字
    :param formal:是否使用正式语气，默认False
    """
    if formal:
        return f"尊敬的{name},您好！很高兴为您服务。"
    else:
        return f"嗨,{name}!有什么可以帮你的吗？"

@mcp.tool()
def calculate(operation:str,a:float,b:float)->dict:
    """
    执行基础的数学运算(加减乘除平方根)
    :param operation:运算操作，支持add/subtract/multiply/divide/power/sqrt
    :param a:第一个数字(平方根运算时为被开方数)
    :param b:第2个数字(平方根运算时可忽略)
    """
    result = None
    if operation=="add":
        result = a + b
    elif operation == "subtract":
        result = a-b
    elif operation=="multiply":
        result = a*b
    elif operation=="divide":
        if b==0:
            return{"status":"error","message":"除数不能为0"}
        result = a/b
    elif operation =="power":
        result = math.pow(a.b)
    elif operation == "sqrt":
        if a<0:
            return {"status":"error","message":"负数无法开方根"}
        result = math.sqrt(a)
    else:
        return{"status":"error","message":"不支持的运算类型"}
    return{
        "status":"success",
        "operation":operation,
        "input":{"a":a,"b":b},
        "result":round(result,4)
    }


@mcp.tool()
def get_current_time(timezone:str = "Asia/Shanghai")->dict:
    """
    获取当前时间，支持指定时区
    :param timezone:时区，默认Asia/Shanghai(北京时间)
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    if timezone=="Asia/Shanghai":
        tz = datetime.timezone(datetime.timedelta(hours=8))
        now = now.astimezone(tz)
    return{
        "timezone":timezone,
        "datetime":now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday":now.strftime("%A"),
        "timestamp":now.timestamp()
    }


@mcp.tool()
def random_number(min_num:int,max_num:int,count:int =1 )->dict:
    """
    生成指定范围内的随机数
    :param min_num:最小值(包含)
    :param max_num:最大值(包含)
    :param count:生成数量，默认1
    """
    if min_num>=max_num:
        return {"status":"error","message":"最小值必须小于最大值"}
    if count<1 or count>100:
        return {"status":"error","message":"生成梳理必须在1~100之间"}
    
    numbers = [random.randint(min_num,max_num) for _ in range(count)]
    return{
        "status":"success",
        "min":min_num,
        "max":max_num,
        "count":count,
        "numbers":numbers
    }

#-------------------------------------
# 2. 资源示例：结构化数据资源
#-------------------------------------

@mcp.resource("system://info")
def get_system_info()->dict:
    """
    获取服务运行的基本信息
    """
    return{
        "service_name":"demo-service",
        "version":"1.0.0",
        "transfort":"stdio",
        "start_time":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tools":["greet","calcute","get_current_time","random_number"],
        "resources":["system://info","quote://daily"]
    }

@mcp.resource("quote://daily")
def get_daily_quote()->str:
    """
    获取每日一句励志名言
    """
    quotes = [
        "种一棵树最好的时间是十年前，其次是现在。",
        "慢慢来，谁还没有一个努力的过程。",
        "你若盛开，清风自来。",
        "星光不问赶路人，时光不负有心人。",
        "道阻且长，行则将至。"
    ]
    return random.choice(quotes)

#-------------------------------
# 提示词示例，可复用的提示词模版
#-------------------------------
@mcp.prompt()
def code_help(language:str,problem:str)->str:
    """
    生成代码问题的辅助提示词
    :param language:编程语言(如Python/java/JavaScript)
    :param problem:遇到问题描述
    """
    return f"""你是一位资深的{language}开发工程师，请帮我解决一下问题：
    {problem}

    请按照一下格式回复：
    1. 问题原因分析
    2. 解决方案步骤
    3. 示例代码
    4  注意事项
    """

@mcp.prompt()
def meeting_summary(topic:str,conent:str)->str:
    """
    生成会议纪要的辅助提示词
    :param topic:会议主题
    :param content:会议内容要点
    """
    return f"""请根据以下会议内容，生成一份间距清晰的会议纪要:
    会议主题：{topic}
    会议内容: {conent}

    请包含以下部分:
    - 会议核心议题
    - 达成共识
    - 待办事项(含负责人和截止时间)
    - 下一步计划         
    """
if __name__=="__main__":
   # mcp.run(transport="stdio")
   # transport = "sse" 开启SSE:host/port 指定监听地址和端口
   mcp.run(
       transport="streamable-http",
       host="0.0.0.0",#0.0.0.允许局域网所有设备访问：本地测试可用127.0.0.1
       port = 8002    #自定义端口，确保未被占用
   )