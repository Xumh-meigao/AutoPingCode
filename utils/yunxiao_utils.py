# --*-- conding:utf-8 --*--
# @Time : 2026/01/06 18:03
# @Author : Xumh
from conf.yunxiao_conf import YUNXIAO_API_URL, x_yunxiao_token, organization_id, project_id
from utils.log_utils import logger
from utils.request_utils import RetryableRequest


class YunXiaoUtils:
    """
    云效客户端类，用于与云效系统进行交互
    """

    def __init__(self, base_url=None, token=None):
        """
            初始化云效客户端
        Args:
            base_url (str): 云效基础URL
        """
        self.base_url = base_url or YUNXIAO_API_URL
        self.headers = {"Content-Type": "application/json", "x-yunxiao-token": token or x_yunxiao_token}
        self.request_client = RetryableRequest(retries=3, backoff_factor=2)
        self.user_list = self.list_project_members()
        self.work_item_field = self.get_work_item_type_field_config(self.get_work_item_type_id())

    def list_project_members(self):
        """
        获取项目成员列表

        Returns:
            list: 项目成员列表
        """
        try:
            url = f"{self.base_url}/oapi/v1/projex/organizations/{organization_id}/projects/{project_id}/members"
            response = self.request_client.get(url=url, headers=self.headers)
            return response.json()
        except Exception as e:
            logger.error(f"获取项目成员列表失败: {e}")
            return None

    def get_user_id(self, username):
        """
        获取用户ID

        Args:
            username (str): 用户名

        Returns:
            str: 用户ID
        """
        try:
            users = self.user_list
            for user in users:
                if user["userName"] == username:
                    return user["userId"]
            return None
        except Exception as e:
            logger.error(f"获取用户ID失败: {e}")
            return None

    def get_work_item_type_id(self, category="Bug", name="缺陷"):
        """
        获取工作项类型ID

        Args:
            category (str): 工作项类型类别 ["Req","Risk","Bug","Task","Request","Topic"]
            name (str): 工作项类型名称

        Returns:
            str: 工作项类型ID
        """

        try:
            url = f"{self.base_url}/oapi/v1/projex/organizations/{organization_id}/projects/{project_id}/workitemTypes"
            data = {"category": category}
            response = self.request_client.get(url=url, headers=self.headers, params=data)
            for item in response.json():
                if item["name"] == name:
                    return item["id"]
            return None
        except Exception as e:
            logger.error(f"获取工作项类型列表失败: {e}")
            return None

    def get_work_item_type_field_config(self, work_item_type_id):
        """
        获取工作项类型字段配置

        Args:
            work_item_type_id (str): 工作项类型ID

        Returns:
            dict: 工作项类型字段配置
        """

        try:
            url = f"{self.base_url}/oapi/v1/projex/organizations/{organization_id}/projects/{project_id}/workitemTypes/{work_item_type_id}/fields"
            response = self.request_client.get(url=url, headers=self.headers)
            return response.json()
        except Exception as e:
            logger.error(f"获取工作项类型字段配置失败: {e}")
            return None

    def create_work_item(self, data_dict=None):
        """
        创建工作项

        Args:
            data_dict (dict): 工作项信息

        Returns:
            dict: 创建的工作项信息
        """
        try:
            if not data_dict:
                data_dict = {
                    "assignedTo": "69363a48f95578dee4f984b3",  # 指派人 userId
                    "description": "描述test",  # 工作项描述
                    "spaceId": "{{project_id}}",  # 空间 ID，如果是项目就是项目的 ID。
                    "subject": "标题test",  # 工作项标题
                    "customFieldValues": {
                        "seriousLevel": "8cffbfa06b1faa2ebf3c2807bd",  # 工作项严重级别
                        "priority": "7956b23e9d26f0e97d3274fa86",  # 工作项优先级
                    },
                    "workitemTypeId": "37da3a07df4d08aef2e3b393",  # 工作项类型 ID
                }
            url = f"{self.base_url}/oapi/v1/projex/organizations/{organization_id}/workitems"
            response = self.request_client.post(url=url, headers=self.headers, json=data_dict)
            return response.json()
        except Exception as e:
            logger.error(f"创建工作项失败: {e}")
            return None

    def search_work_items(self, data_dict=None):
        """
        搜索工作项

        Args:
            data_dict (dict): 搜索条件
            {
                "category": "Bug",
                // "conditions": "{\"conditionGroups\":[[{\"fieldIdentifier\":\"subject\",\"operator\":\"CONTAINS\",\"value\":[\"任务中心\"],\"toValue\":null,\"className\":\"string\",\"format\":\"input\"}]]}",
                "orderBy": "gmtCreate",
                "page": 1,
                "perPage": 200,
                "sort": "desc",
                "spaceId": "{{project_id}}"
            }

        Returns:
            list: 搜索结果
        """
        try:
            url = f"{self.base_url}/oapi/v1/projex/organizations/{organization_id}/workitems:search"
            if not data_dict:
                data_dict = {
                    "category": "Bug",
                    "orderBy": "gmtCreate",
                    "page": 1,
                    "perPage": 200,
                    "sort": "desc",
                    "spaceId": project_id,
                }
            response = self.request_client.post(url=url, headers=self.headers, json=data_dict)
            return response.json()

        except Exception as e:
            logger.error(f"搜索工作项失败: {e}")
            return None

    def update_work_item(self, work_item_id, data_dict):
        """
        更新工作项

        Args:
            work_item_id (str): 工作项ID
            data_dict (dict): 更新数据

        Returns:
            dict: 更新后的工作项信息
        """
        try:
            url = f"{self.base_url}/oapi/v1/projex/organizations/{organization_id}/workitems/{work_item_id}"
            response = self.request_client.put(url=url, headers=self.headers, json=data_dict)
            if response.status_code != 204:
                logger.error(f"更新工作项失败: {response.text}")
            return response.text
        except Exception as e:
            logger.error(f"更新工作项失败: {e}")
            return None
