from jsonpath import jsonpath

from utils.ping_code_utils import PingCodeClient
from utils.utils import Utils
from utils.yunxiao_utils import YunXiaoUtils

yxc = YunXiaoUtils()

bugs = yxc.search_work_items()

search_data = {
    "addon_setting_id": "6847a64c4c9434fbbce54bcf",
    "criteria": {
        # "search": {"keywords": "52", "scopes": ["identifier", "title"]},
        "sort_by": "updated_at",
        "sort_direction": -1,
        "conditions": [
            {"operation": 7, "property_key": "title", "value": "虚拟机，修改虚拟机配置保存失败报错", "logic": 1}
        ],
    },
    "columns": [
        "identifier",
        "title",
        "kehuduanxitongpingtai",
    ],
    "is_brief": 1,
    "pi": 0,
    "ps": 50,
}


# module_field_info = Utils.search_list_json(yxc.work_item_field, "name", "功能模块")
# module_field_id = module_field_info.get("id")
env_field_info = Utils.search_list_json(yxc.work_item_field, "name", "环境类型")
env_field_id = env_field_info.get("id")
# module_name = jsonpath(module_field_info.get("options"), "$..id")

pcc = PingCodeClient()

for bug in bugs:
    subject = bug.get("subject")
    condition = {"operation": 7, "property_key": "title", "value": subject, "logic": 1}
    search_data["criteria"]["conditions"] = [condition]

    pc_bug_info = pcc.format_bug_info_for_feishu(search_data)

    for pc_bug in pc_bug_info:
        if pc_bug.get("title") == subject:
            env_list = pc_bug.get("test_env")
            update_dict = {env_field_id: env_list}
            yxc.update_work_item(bug.get("id"), update_dict)

    # subject_start_str = subject[: subject.find("，")]
    # if subject_start_str in module_name:
    #     update_dict = {module_field_id: subject_start_str}
    #     yxc.update_work_item(bug.get("id"), update_dict)
    pass
