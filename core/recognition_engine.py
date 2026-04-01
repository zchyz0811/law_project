import re
import jieba
import jieba.posseg as pseg
from dataclasses import dataclass
from typing import List, Tuple
import os

@dataclass
class RecognitionCandidate:
    """识别候选项"""
    suggested_name: str
    original_value: str
    start_pos: int
    end_pos: int
    confidence: float  # 0-1，置信度
    rule_type: str  # regex/ner/context

class RecognitionEngine:
    # 第一层：正则规则
    REGEX_RULES = [
        ("签订日期", r"\d{4}年\d{1,2}月\d{1,2}日", 0.95),
        ("签订日期", r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", 0.9),
        ("合同金额", r"[￥¥]\s?\d{1,3}(,\d{3})*(\.\d{1,2})?元?", 0.9),
        ("合同金额", r"人民币[零一二三四五六七八九十百千万亿壹贰叁肆伍陆柒捌玖拾佰仟萬億]+元整?", 0.95),
        ("统一社会信用代码", r"[0-9A-HJ-NP-RT-UWXY]{2}\d{6}[0-9A-HJ-NP-RT-UWXY]{10}", 0.98),
        ("身份证号", r"\d{17}[\dXx]", 0.95),
        ("联系电话", r"1[3-9]\d{9}", 0.9),
        ("联系电话", r"0\d{2,3}-\d{7,8}", 0.9),
        ("银行账号", r"\d{16,19}", 0.85),
        ("邮政编码", r"\d{6}", 0.8),
    ]

    # 第三层：上下文规则
    CONTEXT_PATTERNS = [
        ("甲方", r"甲\s*方[：:]\s*([^\n，。；]{2,50})"),
        ("乙方", r"乙\s*方[：:]\s*([^\n，。；]{2,50})"),
        ("丙方", r"丙\s*方[：:]\s*([^\n，。；]{2,50})"),
        ("法定代表人", r"法定代表人[：:]\s*([^\n，。；]{2,10})"),
        ("注册地址", r"(?:注册)?地址[：:]\s*([^\n。；]{5,100})"),
        ("联系人", r"联系人[：:]\s*([^\n，。；]{2,10})"),
    ]

    def __init__(self):
        # 加载法律领域词典
        dict_path = os.path.join(os.path.dirname(__file__), "..", "assets", "legal_dict.txt")
        if os.path.exists(dict_path):
            jieba.load_userdict(dict_path)

    def recognize(self, text: str) -> List[RecognitionCandidate]:
        """执行三层识别"""
        candidates = []

        # 第一层：正则规则
        candidates.extend(self._regex_recognize(text))

        # 第二层：NER
        candidates.extend(self._ner_recognize(text))

        # 第三层：上下文
        candidates.extend(self._context_recognize(text))

        # 去重和排序
        return self._deduplicate(candidates)

    def _regex_recognize(self, text: str) -> List[RecognitionCandidate]:
        """正则规则识别"""
        results = []
        for name, pattern, confidence in self.REGEX_RULES:
            for match in re.finditer(pattern, text):
                results.append(RecognitionCandidate(
                    suggested_name=name,
                    original_value=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=confidence,
                    rule_type="regex"
                ))
        return results

    def _ner_recognize(self, text: str) -> List[RecognitionCandidate]:
        """NER识别（公司名、人名、地址）"""
        results = []
        words = pseg.cut(text)
        pos = 0

        for word, flag in words:
            word_len = len(word)
            if flag == 'nt' and len(word) > 3:  # 机构名
                results.append(RecognitionCandidate(
                    suggested_name="公司名称",
                    original_value=word,
                    start_pos=pos,
                    end_pos=pos + word_len,
                    confidence=0.8,
                    rule_type="ner"
                ))
            elif flag == 'nr' and 2 <= len(word) <= 4:  # 人名
                results.append(RecognitionCandidate(
                    suggested_name="姓名",
                    original_value=word,
                    start_pos=pos,
                    end_pos=pos + word_len,
                    confidence=0.75,
                    rule_type="ner"
                ))
            elif flag == 'ns' and len(word) > 4:  # 地名
                results.append(RecognitionCandidate(
                    suggested_name="地址",
                    original_value=word,
                    start_pos=pos,
                    end_pos=pos + word_len,
                    confidence=0.7,
                    rule_type="ner"
                ))
            pos += word_len

        return results

    def _context_recognize(self, text: str) -> List[RecognitionCandidate]:
        """上下文规则识别"""
        results = []
        for name, pattern in self.CONTEXT_PATTERNS:
            for match in re.finditer(pattern, text):
                value = match.group(1).strip()
                if value:
                    results.append(RecognitionCandidate(
                        suggested_name=name,
                        original_value=value,
                        start_pos=match.start(1),
                        end_pos=match.end(1),
                        confidence=0.9,
                        rule_type="context"
                    ))
        return results

    def _deduplicate(self, candidates: List[RecognitionCandidate]) -> List[RecognitionCandidate]:
        """去重：相同位置保留置信度最高的"""
        position_map = {}
        for c in candidates:
            key = (c.start_pos, c.end_pos)
            if key not in position_map or c.confidence > position_map[key].confidence:
                position_map[key] = c

        result = sorted(position_map.values(), key=lambda x: x.start_pos)
        return result
