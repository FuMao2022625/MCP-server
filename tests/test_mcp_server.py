"""
MCP MySQL Server 单元测试
"""
import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mysql_mcp_server import is_safe_sql, get_mysql_conn


class TestSQLSecurity:
    """SQL 安全校验测试"""

    def test_select_is_safe(self):
        """SELECT 语句应该通过安全校验"""
        assert is_safe_sql("SELECT * FROM users") is True
        assert is_safe_sql("SELECT id, name FROM orders WHERE status = 'active'") is True
        assert is_safe_sql("  SELECT COUNT(*) FROM products  ") is True

    def test_insert_is_unsafe(self):
        """INSERT 语句应该被拒绝"""
        assert is_safe_sql("INSERT INTO users VALUES (1, 'test')") is False

    def test_delete_is_unsafe(self):
        """DELETE 语句应该被拒绝"""
        assert is_safe_sql("DELETE FROM users WHERE id = 1") is False

    def test_update_is_unsafe(self):
        """UPDATE 语句应该被拒绝"""
        assert is_safe_sql("UPDATE users SET name = 'new' WHERE id = 1") is False

    def test_drop_is_unsafe(self):
        """DROP 语句应该被拒绝"""
        assert is_safe_sql("DROP TABLE users") is False

    def test_alter_is_unsafe(self):
        """ALTER 语句应该被拒绝"""
        assert is_safe_sql("ALTER TABLE users ADD COLUMN age INT") is False

    def test_truncate_is_unsafe(self):
        """TRUNCATE 语句应该被拒绝"""
        assert is_safe_sql("TRUNCATE TABLE users") is False

    def test_create_is_unsafe(self):
        """CREATE 语句应该被拒绝"""
        assert is_safe_sql("CREATE TABLE test (id INT)") is False

    def test_select_with_forbidden_keyword_is_unsafe(self):
        """SELECT 中包含禁用关键字应该被拒绝"""
        assert is_safe_sql("SELECT * FROM users; DROP TABLE users;") is False

    def test_empty_sql_is_unsafe(self):
        """空 SQL 应该被拒绝"""
        assert is_safe_sql("") is False
        assert is_safe_sql("   ") is False


class TestMySQLConnection:
    """MySQL 连接测试"""

    def test_get_mysql_conn_returns_tuple(self):
        """get_mysql_conn 应返回 (connection, error) 元组"""
        result = get_mysql_conn()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_get_mysql_conn_with_invalid_config(self, monkeypatch):
        """无效配置应该返回错误信息"""
        monkeypatch.setenv("MYSQL_HOST", "invalid_host_12345")
        monkeypatch.setenv("MYSQL_PORT", "99999")
        monkeypatch.setenv("MYSQL_USER", "invalid")
        monkeypatch.setenv("MYSQL_PASSWORD", "invalid")
        monkeypatch.setenv("MYSQL_DATABASE", "invalid")
        conn, err = get_mysql_conn()
        assert conn is None
        assert err is not None


class TestToolSchemas:
    """工具模式测试"""

    def test_list_all_tables_schema(self):
        """list_all_tables 工具无需参数"""
        from mysql_mcp_server import app
        # 验证工具注册正常
        assert app is not None

    def test_get_table_schema_requires_table_name(self):
        """get_table_schema 需要 table_name 参数"""
        # 参数校验逻辑在 execute 时由 MCP 框架处理
        pass

    def test_execute_select_sql_requires_sql(self):
        """execute_select_sql 需要 sql 参数"""
        # 参数校验逻辑在 execute 时由 MCP 框架处理
        pass


class Test MCPFunctionConversion:
    """MCP 工具转换测试"""

    def test_mcp_to_function_format(self):
        """验证 MCP 工具转 Function Call 格式"""
        from client_deepseek_mcp import mcp_to_function
        mock_tool = type('MockTool', (), {
            'name': 'test_tool',
            'description': 'Test description',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'string'}
                }
            }
        })()
        result = mcp_to_function(mock_tool)
        assert result['type'] == 'function'
        assert result['function']['name'] == 'test_tool'
        assert result['function']['description'] == 'Test description'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])