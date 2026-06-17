"""
MCP Client - 对接 DeepSeek 做数据分析
客户端拉起 MCP 子进程，自动加载 MySQL 工具，交给 DeepSeek 自主决策
"""
import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

load_dotenv()

# 初始化 DeepSeek 客户端（兼容 OpenAI SDK）
llm_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL")
)
MODEL_NAME = os.getenv("DEEPSEEK_MODEL")

# 将 MCP 工具转换为 OpenAI Function Call 格式
def mcp_to_function(tool):
    """
    将 MCP 工具转换为 OpenAI Function Call 格式
    Args:
        tool: MCP 工具对象
    Returns:
        dict: OpenAI Function Call 格式的工具定义
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        }
    }

async def agent_loop(session: ClientSession, user_query: str) -> str:
    """
    Agent 循环：调用 DeepSeek 进行数据分析
    Args:
        session: MCP ClientSession
        user_query: 用户查询
    Returns:
        str: 分析结果
    """
    # 获取 MCP 全部可用工具
    tools_list = await session.list_tools()
    functions = [mcp_to_function(t) for t in tools_list.tools]
    messages = [
        {
            "role": "system",
            "content": """你是数据库数据分析智能助手，可以调用MySQL工具完成分析任务。
执行流程：
1. 不清楚表结构先调用 list_all_tables 查看所有表
2. 确定目标表后调用 get_table_schema 获取字段结构
3. 根据需求生成安全SELECT语句调用 execute_select_sql 查询数据
4. 拿到数据后做数据分析、汇总、趋势解读，禁止编造数据
仅使用工具返回真实数据回答用户问题。"""
        },
        {"role": "user", "content": user_query}
    ]

    max_round = 10
    for _ in range(max_round):
        resp = await llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=functions,
            tool_choice="auto"
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            # 无工具调用，直接返回分析结果
            return msg.content

        # 执行 MCP 工具调用
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})
        
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = eval(tool_call.function.arguments)
            tool_res = await session.call_tool(func_name, arguments=func_args)
            # 存入上下文
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_res.content)
            })
    return "达到最大执行轮数，任务终止"

async def main(user_question: str = None):
    """
    主函数：启动 MCP Server 并执行数据分析
    Args:
        user_question: 用户查询问题，默认使用内置示例
    """
    from mcp.client.stdio import StdioServerParameters
    # 启动本地 MCP Server 子进程
    server_params = StdioServerParameters(command="python", args=["mysql_mcp_server.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # 自定义你的数据库分析问题
            question = user_question or "帮我查看数据库里有哪些表，查看订单表结构，并统计订单总金额"
            result = await agent_loop(session, question)
            print("=====DeepSeek数据分析结果=====\n", result)
            return result

if __name__ == "__main__":
    asyncio.run(main())