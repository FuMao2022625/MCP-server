"""
MCP MySQL Server - 提供 MySQL 查询工具的 MCP 服务器
支持：查询表列表、查询表结构、执行只读 SELECT 查询
"""
from mcp.server import Server
from mcp.types import Tool, TextContent
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = Server("mysql-mcp-server")

# MySQL 连接工具
def get_mysql_conn():
    """
    创建 MySQL 数据库连接
    Returns:
        tuple: (connection, error) - 连接成功时 error 为 None
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT")),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return conn, None
    except Error as e:
        return None, str(e)

# 安全校验：只允许查询语句
def is_safe_sql(sql: str) -> bool:
    """
    安全校验：仅允许 SELECT 语句，禁止增删改操作
    Args:
        sql: 待校验的 SQL 语句
    Returns:
        bool: True 表示安全，False 表示不安全
    """
    sql_upper = sql.strip().upper()
    forbidden = ["INSERT", "DELETE", "UPDATE", "DROP", "ALTER", "TRUNCATE", "CREATE"]
    if not sql_upper.startswith("SELECT"):
        return False
    for keyword in forbidden:
        if keyword in sql_upper:
            return False
    return True

@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    列出所有可用的 MCP 工具
    """
    return [
        Tool(
            name="list_all_tables",
            description="获取数据库内所有数据表名称列表",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_table_schema",
            description="查询指定数据表的字段结构",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "数据表名称"
                    }
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="execute_select_sql",
            description="执行只读 SELECT 查询 SQL 语句，禁止增删改操作",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "纯 SELECT 查询语句"
                    }
                },
                "required": ["sql"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> TextContent:
    """
    处理工具调用请求
    """
    try:
        if name == "list_all_tables":
            return TextContent(type="text", text=await list_all_tables())
        elif name == "get_table_schema":
            return TextContent(type="text", text=await get_table_schema(arguments.get("table_name")))
        elif name == "execute_select_sql":
            return TextContent(type="text", text=await execute_select_sql(arguments.get("sql")))
        else:
            return TextContent(type="text", text=f"未知工具: {name}")
    except Exception as e:
        logger.error(f"工具调用异常: {e}")
        return TextContent(type="text", text=f"工具执行异常: {str(e)}")

async def list_all_tables() -> str:
    """
    获取数据库内所有数据表名称列表
    """
    conn, err = get_mysql_conn()
    if err:
        return f"数据库连接失败：{err}"
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    tables = [item[0] for item in cursor.fetchall()]
    cursor.close()
    conn.close()
    return f"数据库表列表：{tables}"

async def get_table_schema(table_name: str) -> str:
    """
    查询指定数据表的字段结构
    Args:
        table_name: 数据表名称
    """
    conn, err = get_mysql_conn()
    if err:
        return f"数据库连接失败：{err}"
    cursor = conn.cursor()
    try:
        cursor.execute(f"DESC {table_name};")
        schema = cursor.fetchall()
        res = f"表 {table_name} 结构(字段名|类型|是否为空|主键|默认值|备注)：\n{schema}"
    except Exception as e:
        res = f"查询表结构失败：{str(e)}"
    cursor.close()
    conn.close()
    return res

async def execute_select_sql(sql: str) -> str:
    """
    执行只读 SELECT 查询 SQL 语句，禁止增删改操作
    Args:
        sql: 纯 SELECT 查询语句
    """
    if not is_safe_sql(sql):
        return "SQL不安全，仅支持SELECT查询，禁止增删改删表等操作"
    conn, err = get_mysql_conn()
    if err:
        return f"数据库连接失败：{err}"
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]
        result = {"columns": cols, "data": rows}
    except Exception as e:
        result = f"SQL执行异常：{str(e)}"
    cursor.close()
    conn.close()
    return str(result)

async def main():
    """启动 MCP stdio 服务器"""
    import mcp
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())