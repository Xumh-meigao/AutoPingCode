from jsonpath import jsonpath  # noqa

from conf.ping_code_conf import (
    COOKIE,
    PING_CODE_BASE_URL,
    PING_CODE_VIEWS_ID,
    PING_CODE_PROJECT_ID,
    PING_CODE_BUG_STATUS,
)
from utils.log_utils import logger
from utils.request_utils import RetryableRequest
from utils.utils import Utils


class PingCodeClient:
    """
    PingCode客户端类，用于与PingCode系统进行交互
    """

    def __init__(self, base_url=None, cookies=None):
        """
        初始化PingCode客户端

        Args:
            base_url (str): PingCode基础URL
        """
        self.base_url = base_url or PING_CODE_BASE_URL
        self.headers = {"Content-Type": "application/json", "Cookie": cookies or COOKIE}

        self.request_client = RetryableRequest(retries=3, backoff_factor=2)

    def search_bug_list(self, request_data=None):
        """
        搜索PingCode缺陷列表
        """
        search_url = (
            f"{self.base_url}/api/agile/projects/{PING_CODE_PROJECT_ID}/defect/views/{PING_CODE_VIEWS_ID}/content"
        )
        if request_data is None:
            request_data = {"addon_setting_id": "6847a64c4c9434fbbce54bcf", "is_brief": 1, "pi": 0, "ps": 1000}

        try:
            response = self.request_client.post(url=search_url, headers=self.headers, json=request_data, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"搜索PingCode缺陷失败: {e}")
            return None

    def search_bug_by_id(self, bug_id):
        """
        根据ID搜索PingCode缺陷

        Args:
            bug_id (str): 缺陷ID

        Returns:
            dict: 搜索结果
        """
        search_url = (
            f"{self.base_url}/api/agile/projects/{PING_CODE_PROJECT_ID}/defect/views/{PING_CODE_VIEWS_ID}/content"
        )
        search_data = {
            "addon_setting_id": "6847a64c4c9434fbbce54bcf",
            "criteria": {
                "search": {"keywords": "", "scopes": ["identifier", "title"]},
                "condition_logic": 1,
                "sort_by": "identifier",
                "sort_direction": -1,
                "conditions": [{"operation": 1, "property_key": "identifier", "value": 11, "logic": 1}],
                "mode": 1,
                "pql": "",
                "pql_snapshot": {},
                "group_by": "",
                "show_type": 2,
                "sort_type": -1,
            },
            "pi": 0,
            "ps": 50,
        }
        search_data["criteria"]["conditions"] = [
            {"operation": 1, "property_key": "identifier", "value": bug_id, "logic": 1}
        ]

        try:
            response = self.request_client.post(url=search_url, headers=self.headers, json=search_data, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"搜索PingCode缺陷失败: {e}")
            return None

    def get_bug_comments(self, bug_id):
        """
        获取缺陷的评论

        Args:
            bug_id (str): 缺陷ID

        Returns:
            dict: 评论数据
        """
        try:
            comment_url = f"{self.base_url}/api/agile/work-items/{bug_id}/comments"
            response = self.request_client.get(url=comment_url, headers=self.headers)
            return response.json()
        except Exception as e:
            logger.error(f"获取缺陷评论失败: {e}")
            return None

    def format_comments(self, comment_id, old_comment_data=""):
        """
        格式化评论数据给飞书，并判断是否需要更新

        Args:
            comment_id (str): 评论原始数据
            old_comment_data (str): 评论原始数据

        Returns:
            list: 格式化后的评论列表
        """
        comment_data = self.get_bug_comments(comment_id)
        if not comment_data.get("data"):
            return []

        comment_value_list = comment_data.get("data", {}).get("value", [])
        comment_users_list = comment_data.get("data", {}).get("references", {}).get("users", [])
        comment_request_list = []
        is_new_comment = old_comment_data == ""
        for comment_value in comment_value_list:
            comment_text = jsonpath(comment_value, "$..text")
            if not comment_text:
                continue
            if not is_new_comment:
                is_new_comment = not all(item in old_comment_data for item in comment_text)
            created_id = comment_value.get("created_by")
            user_display_name = Utils.search_list_json(comment_users_list, "uid", created_id).get("display_name")
            comment_request_list.append(
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": f"{user_display_name}：", "attrs": {"bold": "true"}},
                        {"type": "text", "text": f"{comment_text}"},
                    ],
                }
            )

        return comment_request_list if is_new_comment else []

    def get_comment_text(self, comment_id):
        """
        获取评论的文本内容

        Args:
            comment_id (str): 评论ID

        Returns:
            list: 评论文本列表
        """
        comment_data = self.get_bug_comments(comment_id)
        if not comment_data.get("data"):
            return []

        comment_value_list = comment_data.get("data", {}).get("value", [])
        comment_users_list = comment_data.get("data", {}).get("references", {}).get("users", [])
        comment_request_list = []
        for comment_value in comment_value_list:
            comment_text = jsonpath(comment_value, "$..text")
            if not comment_text:
                continue
            comment_text = list(filter(lambda s: s.strip(), comment_text))
            created_id = comment_value.get("created_by")
            user_display_name = Utils.search_list_json(comment_users_list, "uid", created_id).get("display_name")
            comment_request_list.append(f"{user_display_name}：{comment_text}")

        return comment_request_list

    @staticmethod
    def get_bug_status_name(state_id):
        """
        根据状态ID获取状态名称

        Args:
            state_id (str): 状态ID

        Returns:
            str: 状态名称
        """
        status_dict = PING_CODE_BUG_STATUS
        return status_dict.get(state_id)

    def get_bug_url(self, short_id):
        """
        获取缺陷URL

        Args:
            short_id (str): 缺陷短ID

        Returns:
            str: 完整的缺陷URL
        """

        return f"{self.base_url}/pjm/workitems/{short_id}"

    def get_bug_info(self, short_id):
        """
        获取缺陷信息
        """
        try:
            url = f"{self.base_url}/api/agile/work-items/{short_id}"
            response = self.request_client.get(url=url, headers=self.headers)
            return response.json()
        except Exception as e:
            logger.error(f"获取缺陷详情失败: {e}")
            return None

    def put_work_item_info(self, work_item_id, request_data):
        """
        更新工作项信息

        Args:
            work_item_id (str): 工作项 id
            request_data (dict): 更新数据
        Returns:
            dict: 更新结果
        """
        url = f"{self.base_url}/api/agile/work-items/{work_item_id}/iteration"
        try:
            response = self.request_client.put(url=url, headers=self.headers, json=request_data)
            return response.json()
        except Exception as e:
            logger.error(f"更新工作项信息失败: {e}")
            return None

    def get_sprints_info(self, search_key_words=None):
        """
        获取迭代信息
        Returns:
            dict: 迭代信息列表  search
        """
        search_url = f"{self.base_url}/api/agile/projects/{PING_CODE_PROJECT_ID}/sprint/sprints-by-status"
        params = {"search": search_key_words} if search_key_words else {}
        try:
            response = self.request_client.get(url=search_url, headers=self.headers, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"搜索PingCode缺陷失败: {e}")
            return None

    def get_public_image_token(self):
        """
        获取项目信息
        https://siyouyun.pingcode.com/api/typhon/secret/file/public-image-token
        """
        url = f"{self.base_url}/api/typhon/secret/file/public-image-token"
        try:
            response = self.request_client.get(url=url, headers=self.headers)
            return response.json().get("data", {}).get("value")
        except Exception as e:
            logger.error(f"更新工作项信息失败: {e}")
            return None

    def download_image_as_base64(self, image_url):
        """下载图片并返回 Base64 data URI"""
        try:
            print(f"正在下载图片: {image_url}")
            response = self.request_client.get(url=image_url, timeout=15)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "image/jpeg")
            if not content_type.startswith("image/"):
                print(f"⚠️ 非图片内容类型: {content_type}")

            import base64

            b64_data = base64.b64encode(response.content).decode("utf-8")
            return f"data:{content_type};base64,{b64_data}"
        except Exception as e:
            print(f"❌ 下载或编码图片失败: {e}")
            return None

    def process_html_with_tokenized_images(self, html_content):
        """获取 token → 替换所有 img src 为带 token 的 Base64"""
        token = self.get_public_image_token()
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        img_tags = soup.find_all("img", src=True)

        for img in img_tags:
            original_src = img["src"]
            clean_src = original_src.strip()
            if not clean_src:
                continue

            # 构造带 token 的 URL
            tokenized_url = clean_src + "?token=" + token

            # 下载并转 Base64
            data_uri = self.download_image_as_base64(tokenized_url)
            if data_uri:
                img["src"] = data_uri
                # 清理冗余属性（可选）
                img.attrs = {k: v for k, v in img.attrs.items() if k in ["src", "alt", "style", "class"]}
            else:
                print(f"⚠️ 跳过图片: {original_src}")

        return str(soup)

    def add_token_to_img_urls(self, html_content):
        """
        给 HTML 中所有 <img> 标签的 src URL 添加 token 参数
        :param html_content: 原始 HTML 字符串
        :return: 修改后的 HTML 字符串
        """
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

        soup = BeautifulSoup(html_content, "html.parser")
        img_tags = soup.find_all("img", src=True)

        token = self.get_public_image_token()

        for img in img_tags:
            src = img["src"].strip()  # 去除首尾空格（你的 URL 末尾有空格！）
            if not src:
                continue

            # 解析 URL
            parsed = urlparse(src)

            # 解析现有查询参数
            query_params = parse_qs(parsed.query, keep_blank_values=True)

            # 设置 token（覆盖已有 token）
            query_params["token"] = [token]

            # 重新编码查询字符串（保留原有参数顺序可能打乱，但功能正确）
            new_query = urlencode(query_params, doseq=True)

            # 重建 URL
            new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

            # 更新 img 的 src
            img["src"] = new_url

        return str(soup)

    def get_format_bug_info(self, search_dict):
        """
        获取格式化后的缺陷信息
        """
        pc_bugs_res = self.search_bug_list(search_dict)

        # short_id_list = jsonpath(pc_bugs_res, "$.data.value[*].short_id")
        pc_bugs_list = pc_bugs_res.get("data", {}).get("value", [])
        references = pc_bugs_res.get("data", {}).get("references")
        members = references.get("members")
        priority_dict = Utils.search_list_json(references.get("properties"), "key", "priority").get("options")
        severity_dict = Utils.search_list_json(references.get("properties"), "key", "severity").get("options")

        bug_info = []
        for pc_bug_info in pc_bugs_list:
            temp_bug_dict = {
                "identifier": pc_bug_info.get("identifier"),
                "title": pc_bug_info.get("title"),
                "created_at": pc_bug_info.get("created_at"),
            }

            priority_id = pc_bug_info.get("priority")
            severity_id = pc_bug_info.get("properties", {}).get("severity")
            assignee_id = pc_bug_info.get("assignee")
            created_by = pc_bug_info.get("created_by")

            state_id = pc_bug_info.get("state_id")
            short_id = pc_bug_info.get("short_id")
            comment_id = pc_bug_info.get("_id")
            description = pc_bug_info.get("description")

            temp_bug_dict["bug_url"] = self.get_bug_url(short_id)
            temp_bug_dict["state_name"] = self.get_bug_status_name(state_id)
            temp_bug_dict["priority"] = Utils.search_list_json(priority_dict, "_id", priority_id).get("text")
            temp_bug_dict["severity"] = Utils.search_list_json(severity_dict, "_id", severity_id).get("text")
            temp_bug_dict["assignee"] = (
                Utils.search_list_json(members, "uid", assignee_id).get("display_name") if assignee_id else ""
            )
            temp_bug_dict["created_by"] = Utils.search_list_json(members, "uid", created_by).get("display_name")

            temp_bug_dict["description"] = self.process_html_with_tokenized_images(description) if description else ""

            # 处理PingCode Bug 评论
            pc_comment_request_list = self.get_comment_text(comment_id)
            temp_bug_dict["comments"] = pc_comment_request_list

            bug_info.append(temp_bug_dict)

        return bug_info
