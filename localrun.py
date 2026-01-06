# --*-- conding:utf-8 --*--
# @Time : 2025/11/25 17:39
# @Author : Xumh
from utils.feishu_project_utils import FeiShuProjectUtils

feishu_client = FeiShuProjectUtils()


result = feishu_client.update_bug_info_from_ping_code()