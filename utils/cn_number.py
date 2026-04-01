import re

def to_chinese_yuan(amount_str: str) -> str:
    """将数字金额转换为中文大写"""
    try:
        # 提取数字
        amount_str = re.sub(r'[^\d.]', '', amount_str)
        if not amount_str:
            return ""

        amount = float(amount_str)

        # 处理负数
        if amount < 0:
            return "负" + to_chinese_yuan(str(-amount))

        # 处理零
        if amount == 0:
            return "零元整"

        # 中文数字
        cn_nums = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
        cn_units = ["", "拾", "佰", "仟"]
        cn_big_units = ["", "万", "亿"]

        # 分离整数和小数部分
        int_part = int(amount)
        decimal_part = round((amount - int_part) * 100)

        # 转换整数部分
        result = ""
        if int_part == 0:
            result = "零"
        else:
            str_int = str(int_part)
            length = len(str_int)

            for i, digit in enumerate(str_int):
                digit_val = int(digit)
                pos = length - i - 1

                if digit_val != 0:
                    result += cn_nums[digit_val] + cn_units[pos % 4]
                else:
                    if result and result[-1] != "零":
                        result += "零"

                # 添加万、亿
                if pos % 4 == 0 and pos > 0:
                    unit_idx = pos // 4
                    if unit_idx <= len(cn_big_units) - 1:
                        result += cn_big_units[unit_idx]

        result += "元"

        # 处理小数部分
        if decimal_part == 0:
            result += "整"
        else:
            jiao = decimal_part // 10
            fen = decimal_part % 10

            if jiao > 0:
                result += cn_nums[jiao] + "角"
            if fen > 0:
                if jiao == 0:
                    result += "零"
                result += cn_nums[fen] + "分"

        return result

    except:
        return amount_str
