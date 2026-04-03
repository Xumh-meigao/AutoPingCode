from utils.feishu_project_api_utils import PingCodeToFeishuUtils

if __name__ == "__main__":
    fsc = PingCodeToFeishuUtils()

    search_data = {
        "addon_setting_id": "6847a64c4c9434fbbce54bcf",
        "criteria": {
            # "search": {"keywords": "52", "scopes": ["identifier", "title"]},
            "sort_by": "updated_at",
            "sort_direction": -1,
            "conditions": [
                # {"operation": 6, "property_key": "iteration", "value": ["6959e353c7330c2b08ab9761"], "logic": 1}
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
        "ps": 50,
    }

    fsc.set_ping_code_client()
    res = fsc.import_ping_code_bugs(search_data)

    while res:
        search_data["pi"] += 1
        res = fsc.import_ping_code_bugs(search_data)

    pass
