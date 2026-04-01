import sqlite3
import json
from typing import List, Dict, Optional
from pathlib import Path

class Database:
    def __init__(self, db_path: str = "data.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 模板表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 变量组表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS variable_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                variables TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 历史记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                output_path TEXT NOT NULL,
                variables_used TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES templates(id)
            )
        """)

        conn.commit()
        conn.close()

    def add_template(self, name: str, file_path: str, file_type: str) -> int:
        """添加模板"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO templates (name, file_path, file_type) VALUES (?, ?, ?)",
            (name, file_path, file_type)
        )
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return template_id

    def get_templates(self) -> List[Dict]:
        """获取所有模板"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_template(self, template_id: int, name: str, file_path: str, file_type: str):
        """更新模板"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE templates SET name = ?, file_path = ?, file_type = ? WHERE id = ?",
            (name, file_path, file_type, template_id)
        )
        conn.commit()
        conn.close()

    def delete_template(self, template_id: int):
        """删除模板"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        conn.commit()
        conn.close()

    def save_variable_group(self, name: str, variables: Dict[str, str]):
        """保存变量组"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        variables_json = json.dumps(variables, ensure_ascii=False)

        cursor.execute("""
            INSERT INTO variable_groups (name, variables)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET
                variables = excluded.variables,
                updated_at = CURRENT_TIMESTAMP
        """, (name, variables_json))

        conn.commit()
        conn.close()

    def get_variable_groups(self) -> List[Dict]:
        """获取所有变量组"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM variable_groups ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            data = dict(row)
            data['variables'] = json.loads(data['variables'])
            result.append(data)
        return result

    def get_variable_group(self, name: str) -> Optional[Dict]:
        """获取指定变量组"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM variable_groups WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            data = dict(row)
            data['variables'] = json.loads(data['variables'])
            return data
        return None

    def delete_variable_group(self, name: str):
        """删除变量组"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM variable_groups WHERE name = ?", (name,))
        conn.commit()
        conn.close()

    def add_history(self, template_id: int, output_path: str, variables: Dict[str, str]):
        """添加历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        variables_json = json.dumps(variables, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO history (template_id, output_path, variables_used) VALUES (?, ?, ?)",
            (template_id, output_path, variables_json)
        )
        conn.commit()
        conn.close()
