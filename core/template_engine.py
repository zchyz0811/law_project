import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

PLACEHOLDER_PATTERN = re.compile(r'\{\{([^}|]+)(?:\|([^}]+))?\}\}')

@dataclass
class VariableOccurrence:
    """文档中变量的一次出现"""
    id: str
    var_name: str
    original_text: str
    start_pos: int
    end_pos: int
    modifier: str = ""

@dataclass
class Variable:
    name: str
    modifier: str = ""
    value: str = ""
    original_value: str = ""
    occurrences: int = 1

class TemplateEngine:
    def extract_variables(self, text: str) -> List[Variable]:
        """从模板文本中提取所有变量（去重）"""
        seen = set()
        variables = []
        for match in PLACEHOLDER_PATTERN.finditer(text):
            name = match.group(1).strip()
            modifier = match.group(2) or ""
            if name not in seen:
                seen.add(name)
                variables.append(Variable(name=name, modifier=modifier))
        return variables

    def fill(self, text: str, values: Dict[str, str]) -> str:
        """用填写的值替换占位符"""
        def replacer(match):
            name = match.group(1).strip()
            modifier = match.group(2) or ""
            raw = values.get(name, "")
            return self._apply_modifier(raw, modifier)
        return PLACEHOLDER_PATTERN.sub(replacer, text)

    def _apply_modifier(self, value: str, modifier: str) -> str:
        """应用格式化修饰符"""
        if not value:
            return ""
        if modifier == "upper":
            from utils.cn_number import to_chinese_yuan
            return to_chinese_yuan(value)
        if modifier == "date":
            value = value.replace("-", "年", 1).replace("-", "月", 1)
            if not value.endswith("日"):
                value += "日"
            return value
        return value

    def create_placeholder(self, var_name: str, modifier: str = "") -> str:
        """创建占位符字符串"""
        if modifier:
            return f"{{{{{var_name}|{modifier}}}}}"
        return f"{{{{{var_name}}}}}"
