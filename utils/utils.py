# --*-- conding:utf-8 --*--
# @Time : 2024/2/27 11:59
# @Author : Xumh
import ast
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from dateutil.relativedelta import relativedelta

from utils.log_utils import logger


class Utils:

    @classmethod
    def get_time(cls, str_format="%Y-%m-%d %H:%M:%S.%f", offset=0, offset_type="seconds", given_time=None):
        """
        获取时间
        :param given_time: 给定时间
        :param offset: 偏移量
        :param offset_type: 偏移类型 ["days", "seconds", "microseconds", "milliseconds", "minutes", "hours", "weeks"]
        :param str_format: 时间格式 "%Y-%m-%d %H:%M:%S.%f"
        :return:
        """
        try:
            if given_time:
                temp_time = datetime.strptime(given_time, str_format)
            else:
                temp_time = datetime.now()

            if offset_type in ["days", "seconds", "microseconds", "milliseconds", "minutes", "hours", "weeks"]:
                param = {offset_type: int(offset)}
                _time = temp_time + timedelta(**param)
            elif offset_type in ["months", "years"]:
                param = {offset_type: int(offset)}
                _time = temp_time + relativedelta(**param)
            else:
                raise Exception("offset_type 参数错误")
            return _time.strftime(str_format)
        except Exception as e:
            logger.error(f"获取时间失败:{e}")
            raise e

    @classmethod
    def custom_compare_string(cls, left_data: str, right_data: str, filter_conf: list = None):
        """
        比对两个字符串，比对前会对数据进行处理，替换掉不需要比对的数据
        :param filter_conf: 正则替换规则，比对前修改比对数据
        :param left_data:
        :param right_data:
        :return:
        """
        if not filter_conf:
            # from conf.filter_element_conf import re_patterns_conf
            # filter_conf = re_patterns_conf
            filter_conf = {}

        for pattern, value in filter_conf:
            left_data = re.sub(pattern, value, left_data, flags=re.I)
            right_data = re.sub(pattern, value, right_data, flags=re.I)

        temp_opcodes = SequenceMatcher(None, left_data, right_data).get_opcodes()
        diff_opcodes = [line_opcode for line_opcode in temp_opcodes if line_opcode[0] != "equal"]

        return diff_opcodes

    @classmethod
    def compare_list(cls, left_data: list, right_data: list, iteration=False):
        """
        获取比对差异值
        :param iteration: 是否为迭代调用
        :param left_data:
        :param right_data:
        :return:
        """
        # 创建 SequenceMatcher 对象
        seq_matcher = SequenceMatcher(None, left_data, right_data)

        # 获取匹配块
        opcodes = seq_matcher.get_opcodes()
        diff_data = []
        for operation, i1, i2, j1, j2 in opcodes:
            if operation == 'equal':
                continue
            if operation == 'replace':
                if i2 - i1 == j2 - j1:
                    for index, right_diff_data in enumerate(right_data[j1:j2]):
                        left_diff_data = left_data[i1:i2][index]
                        line_diff_opcodes = cls.custom_compare_string(left_diff_data, right_diff_data)
                        if line_diff_opcodes:
                            diff_data.append({
                                "operation": operation,
                                "left_data": left_diff_data,
                                "right_data": right_diff_data,
                                "line_diff_opcodes": line_diff_opcodes
                            })
                else:
                    temp_diff_data = []
                    if not iteration:
                        temp_diff_data = cls.compare_list(left_data[i1:i2], right_data[j1:j2], True)
                    else:
                        left_diff_data = left_data[i1:i2]
                        right_diff_data = right_data[j1:j2]
                        for data in left_diff_data:
                            temp_diff_data.append({"operation": "delete", "left_data": data, "right_data": ""})
                        for data in right_diff_data:
                            temp_diff_data.append({"operation": "insert", "left_data": "", "right_data": data})
                    diff_data = diff_data + temp_diff_data

                    # left_diff_data = "\n".join(left_data[i1:i2])
                    # right_diff_data = "\n".join(right_data[j1:j2])
                    # # temp_opcodes = SequenceMatcher(None, left_diff_data, right_diff_data).get_opcodes()
                    # # line_diff_opcodes = [line_opcode for line_opcode in temp_opcodes if line_opcode[0] != "equal"]
                    # line_diff_opcodes = cls.custom_compare_string(left_diff_data, right_diff_data)
                    # if line_diff_opcodes:
                    #     diff_data.append({
                    #         "operation": operation,
                    #         "left_data": left_diff_data,
                    #         "right_data": right_diff_data,
                    #         "line_diff_opcodes": line_diff_opcodes
                    #     })
            elif operation == 'delete':
                for left_diff_data in left_data[i1:i2]:
                    diff_data.append({"operation": operation, "left_data": left_diff_data, "right_data": ""})
            elif operation == 'insert':
                for right_diff_data in right_data[j1:j2]:
                    diff_data.append({"operation": operation, "left_data": "", "right_data": right_diff_data})

        return diff_data

    @classmethod
    def get_method_names_from_file(cls, file_path: Path):
        """
        从文件中获取函数名
        :param file_path:
        :return:
        """
        with file_path.open("r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=file_path)

        method_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                method_names.append(node.name)

        return method_names

    @classmethod
    def get_method_names_in_directory(cls, directory):
        """
        在指定目录中获取所有函数名
        :param directory:
        :return:
        """
        path = Path(directory)
        method_name = []
        for file_path in path.rglob("*.py"):  # 递归遍历所有 .py 文件
            methods = cls.get_method_names_from_file(file_path)
            if methods:
                method_name += methods
        return method_name

    @classmethod
    def search_list_json(cls, json_data, _key, _value):
        """
        查找 list[json] 数据
        :param json_data:
        :param _key:
        :param _value:
        :return:
        """
        for idx, item in enumerate(json_data):
            if item.get(_key) == _value:
                return item
        return {}
