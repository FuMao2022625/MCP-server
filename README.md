# MCP MySQL 查询系统 API 文档

## 1. 系统概述

MCP MySQL 查询系统是一个基于 Model Context Protocol (MCP) 的数据库分析解决方案，提供安全可控的 MySQL 数据库查询能力。

### 1.1 核心功能
- 提供三个安全工具：`list_all_tables`、`get_table_schema`、`execute_select_sql`
- SQL 安全限制：仅允许 SELECT，禁止 DROP/ALTER/INSERT/DELETE
- 支持与 DeepSeek 大模型对接，实现自然语言转 SQL

### 1.2 技术架构
```
┌─────────────┐     MCP stdio      ┌──────────────────┐
│ DeepSeek    │◄──────────────────►│  MySQL MCP       │
│ Client      │                     │  Server          │
└─────────────┘                     └────────┬─────────┘
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │   MySQL      │
                                     │   Database   │
                                     └──────────────┘
```

## 2. 环境配置

### 2.1 环境变量 (.env)

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| DEEPSEEK_API_KEY | DeepSeek API 密钥 | sk-xxxx |
| DEEPSEEK_BASE_URL | DeepSeek API 地址 | https://api.deepseek.com/v1 |
| DEEPSEEK_MODEL | 模型名称 | deepseek-chat |
| MYSQL_HOST | MySQL 主机地址 | 127.0.0.1 |
| MYSQL_PORT | MySQL 端口 | 3306 |
| MYSQL_USER | MySQL 用户名 | root |
| MYSQL_PASSWORD | MySQL 密码 | password |
| MYSQL_DATABASE | 数据库名称 | test_db |

### 2.2 安装依赖
```bash
pip install -r requirements.txt
```

## 3. MCP 工具 API

### 3.1 list_all_tables

**功能**: 获取数据库内所有数据表名称列表

**参数**: 无

**返回值**: 字符串，格式为 `数据库表列表：[table1, table2, ...]`

**示例**:
```
数据库表列表：['orders', 'products', 'users']
```

### 3.2 get_table_schema

**功能**: 查询指定数据表的字段结构

**参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| table_name | string | 是 | 数据表名称 |

**返回值**: 字符串，包含字段名、类型、是否为空、主键、默认值、备注

**示例**:
```
表 orders 结构(字段名|类型|是否为空|主键|默认值|备注)：
[('id', 'int', 'NO', 'PRI', None, ''), ('amount', 'decimal', 'YES', '', None, '')]
```

### 3.3 execute_select_sql

**功能**: 执行只读 SELECT 查询 SQL 语句

**参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| sql | string | 是 | 纯 SELECT 查询语句 |

**返回值**: 字符串，包含查询结果列名和数据

**示例**:
```
{'columns': ['id', 'name'], 'data': [(1, 'Alice'), (2, 'Bob')]}
```

**安全限制**:
- 仅允许 SELECT 语句
- 禁止：INSERT、DELETE、UPDATE、DROP、ALTER、TRUNCATE、CREATE

## 4. MCP Client API

### 4.1 mcp_to_function()

将 MCP 工具转换为 OpenAI Function Call 格式。

**参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| tool | Tool | MCP 工具对象 |

**返回值**: dict，符合 OpenAI Function Call 规范

### 4.2 agent_loop()

Agent 主循环，处理 DeepSeek 交互和工具调用。

**参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| session | ClientSession | MCP 客户端会话 |
| user_query | str | 用户查询问题 |

**返回值**: str，分析结果

**执行流程**:
1. 获取 MCP 可用工具列表
2. 调用 DeepSeek 分析任务
3. 决策并执行工具调用
4. 循环直到返回最终结果或达到最大轮数(5轮)

### 4.3 main()

启动 MCP Client 并执行数据分析。

**参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_question | str | 否 | 自定义查询问题，默认使用内置示例 |

## 5. 安全机制

### 5.1 SQL 安全校验

`is_safe_sql()` 函数提供以下安全限制：

| 检查项 | 说明 |
|--------|------|
| 语句类型 | 必须以 SELECT 开头 |
| 关键字过滤 | 禁止 INSERT、DELETE、UPDATE、DROP、ALTER、TRUNCATE、CREATE |
| 大小写不敏感 | 关键字检查不区分大小写 |

### 5.2 安全建议

1. **SQL 白名单**: 可增加字段权限隔离，限制只能访问指定数据表
2. **查询行数限制**: 增加 `LIMIT` 限制，防止超大结果集
3. **调用日志**: MCP 增加调用日志，记录所有执行的 SQL 用于审计

## 6. 使用示例

### 6.1 启动数据分析

```python
from client_deepseek_mcp import main
import asyncio

# 使用默认问题
asyncio.run(main())

# 自定义问题
asyncio.run(main("查询2025年所有有效订单的总数量和总交易额"))
```

### 6.2 测试查询问题

1. 查看数据库所有表，找出用户相关表并查看结构
2. 查询2025年所有有效订单的总数量和总交易额并做简单分析
3. 统计每个用户的下单频次，给出简要用户分层分析

## 7. 文件结构

```
MCP-server/
├── .env                 # 环境变量配置
├── .env.example         # 环境变量示例
├── requirements.txt     # Python 依赖
├── mysql_mcp_server.py  # MCP Server 实现
├── client_deepseek_mcp.py  # MCP Client 实现
├── README.md            # API 文档
└── tests/
    ├── __init__.py
    └── test_mcp_server.py  # 单元测试
```

## 8. 错误处理

| 错误类型 | 返回信息 |
|----------|----------|
| 数据库连接失败 | `数据库连接失败：{error_message}` |
| SQL 不安全 | `SQL不安全，仅支持SELECT查询，禁止增删改删表等操作` |
| 查询表结构失败 | `查询表结构失败：{error_message}` |
| SQL 执行异常 | `SQL执行异常：{error_message}` |
| 达到最大轮数 | `达到最大执行轮数，任务终止` |

## 9. 扩展建议

1. **HTTP-SSE 模式**: 支持远程 MCP，脱离本地 stdio 分布式调用
2. **多数据库支持**: 扩展支持 PostgreSQL、MongoDB 等
3. **查询缓存**: 增加查询结果缓存提升性能
4. **权限分级**: 实现更细粒度的表/字段访问控制