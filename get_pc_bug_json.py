import json
from pathlib import Path

from utils.ping_code_utils import PingCodeClient
from utils.utils import Utils

pcc = PingCodeClient()

search_data = {
    "addon_setting_id": "6847a64c4c9434fbbce54bcf",
    "criteria": {
        "sort_by": "updated_at",
        "sort_direction": -1,
        "conditions": [
            {"operation": 6, "property_key": "iteration", "value": ["693f63f3771a55b9f73f302f"], "logic": 1}
        ],
    },
    "columns": [
        "identifier",
        "title",
        "description",
        "state_id",
        "priority",
        "severity",
        "iteration",
        "assignee",
        "updated_by",
        "updated_at",
        "created_by",
        "created_at",
    ],
    "is_brief": 1,
    "pi": 0,
    "ps": 1000,
}

bugs = pcc.get_format_bug_info(search_data)

bug_info_file = Path(f"bug_info_{Utils.get_time('%Y%m%d%H%M%S%f')}.json")
print(f"保存文件: {bug_info_file}")

json.dump(bugs, bug_info_file.open("w", encoding="utf-8"), ensure_ascii=False)

