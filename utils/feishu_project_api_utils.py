import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from conf.feishu_conf import (
    USER_KEY,
    PLUGIN_SECRET,
    PLUGIN_ID,
    PROJECT_KEY,
    FEISHU_PROJECT_URL,
    STATUS_PING_CODE_TO_FEISHU,
)
from utils.ping_code_utils import PingCodeClient
from utils.request_utils import RetryableRequest
from utils.log_utils import logger
from utils.utils import Utils


class BaseClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.http_client = RetryableRequest()

    def _request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str] = None,
        json: Any = None,
        params: Dict[str, Any] = None,
        data: Any = None,
        files: Any = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self.http_client.request(
                method, url, headers=headers, json=json, params=params, data=data, files=files
            )
            logger.info(f"API request: {method} {url} | Response status_code: {response.status_code}")
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {method} {url} | Error: {e}")
            raise e


class AuthClient(BaseClient):
    def get_plugin_token(self, plugin_id: str, plugin_secret: str, _type=1) -> Dict:
        """获取 plugin_token"""
        path = "/open_api/authen/plugin_token"
        payload = {"plugin_id": plugin_id, "plugin_secret": plugin_secret, "type": _type}
        return self._request("POST", path, json=payload)

    def get_auth_code(self, plugin_id: str, cookie: str, state: str = "111") -> Dict:
        """获取 code (用于测试或特定场景)"""
        path = "/open_api/authen/auth_code"
        headers = {"cookie": cookie}
        payload = {"plugin_id": plugin_id, "state": state}
        return self._request("POST", path, headers=headers, json=payload)

    def get_user_plugin_token(self, plugin_token: str, code: str) -> Dict:
        """获取 user_plugin_token"""
        path = "/open_api/authen/user_plugin_token"
        headers = {"X-Plugin-Token": plugin_token}
        payload = {"code": code, "grant_type": "authorization_code"}
        return self._request("POST", path, headers=headers, json=payload)

    def refresh_token(self, plugin_token: str, refresh_token: str) -> Dict:
        """刷新 token"""
        path = "/open_api/authen/refresh_token"
        headers = {"X-Plugin-Token": plugin_token}
        payload = {"refresh_token": refresh_token, "type": 1}
        return self._request("POST", path, headers=headers, json=payload)


class FileClient(BaseClient):
    def __init__(self, base_url: str, plugin_token: str, user_key: Optional[str] = None):
        super().__init__(base_url)
        self.headers = {"X-PLUGIN-TOKEN": plugin_token}
        if user_key:
            self.headers["X-USER-KEY"] = user_key

    def add_attachment(
        self,
        project_key: str,
        work_item_id: int,
        file_path: str = "",
        work_item_type_key: str = "issue",
        file_bytes: bytes = None,
        file_name: str = "",
        field_key: str = "multi_attachment",
    ) -> Dict:
        """添加附件到工作项"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/{work_item_id}/file/upload"
        if file_bytes:
            files = {"file": (file_name, file_bytes) if file_name else file_bytes}
            data = {"field_key": field_key}
            res = self._request("POST", path, headers=self.headers, files=files, data=data)
        elif file_path:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f) if file_name else f}
                data = {"field_key": field_key}
                res = self._request("POST", path, headers=self.headers, files=files, data=data)
        else:
            raise ValueError("file_path or file_bytes must be provided")

        return res

    def upload_file(self, project_key: str, file_path: str = "", file_bytes: bytes = None, file_name: str = "") -> Dict:
        """上传文件"""
        path = f"/open_api/{project_key}/file/upload"
        if file_bytes:
            files = {"file": (file_name, file_bytes) if file_name else file_bytes}
            res = self._request("POST", path, headers=self.headers, files=files)
        elif file_path:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f) if file_name else f}
                res = self._request("POST", path, headers=self.headers, files=files)
        else:
            raise ValueError("file_path or file_bytes must be provided")

        return res

    def download_file(self, project_key: str, work_item_id: int, file_uuid: str) -> Dict:
        """下载附件"""
        path = f"/open_api/{project_key}/work_item/story/{work_item_id}/file/download"
        payload = {"uuid": file_uuid}
        return self._request("POST", path, headers=self.headers, json=payload)

    def delete_file(self, project_key: str, work_item_id: str, field_key: str, uuids: List[str]) -> Dict:
        """删除附件"""
        path = "/open_api/file/delete"
        payload = {"project_key": project_key, "work_item_id": work_item_id, "field_key": field_key, "uuids": uuids}
        return self._request("POST", path, headers=self.headers, json=payload)


class SpaceClient(BaseClient):
    def __init__(self, base_url: str, plugin_token: str, user_key: Optional[str] = None):
        super().__init__(base_url)
        self.headers = {"X-PLUGIN-TOKEN": plugin_token}
        if user_key:
            self.headers["X-USER-KEY"] = user_key

    def get_projects(self, user_key: str = "", tenant_group_id: int = 0) -> Dict:
        """获取空间列表"""
        path = "/open_api/projects"
        payload = {"user_key": user_key, "tenant_group_id": tenant_group_id}
        return self._request("POST", path, headers=self.headers, json=payload)

    def get_project_detail(self, project_keys: List[str]) -> Dict:
        """获取空间详情"""
        path = "/open_api/projects/detail"
        payload = {"project_keys": project_keys}
        return self._request("POST", path, headers=self.headers, json=payload)


class ConfigClient(BaseClient):
    def __init__(self, base_url: str, plugin_token: str, user_key: Optional[str] = None):
        super().__init__(base_url)
        self.headers = {"X-PLUGIN-TOKEN": plugin_token}
        if user_key:
            self.headers["X-USER-KEY"] = user_key

    def get_business_lines(self, project_key: str) -> Dict:
        """获取空间下业务线详情"""
        path = f"/open_api/{project_key}/business/all"
        return self._request("GET", path, headers=self.headers)

    def get_work_item_types(self, project_key: str) -> Dict:
        """获取空间下工作项类型"""
        path = f"/open_api/{project_key}/work_item/all-types"
        return self._request("GET", path, headers=self.headers)

    def get_fields(self, project_key: str, work_item_type_key: str) -> Dict:
        """获取字段信息"""
        path = f"/open_api/{project_key}/field/all"
        payload = {"work_item_type_key": work_item_type_key}
        return self._request("POST", path, headers=self.headers, json=payload)

    def create_field(self, project_key: str, work_item_type_key: str, field_data: Dict) -> Dict:
        """创建自定义字段"""
        path = f"/open_api/{project_key}/field/{work_item_type_key}/create"
        return self._request("POST", path, headers=self.headers, json=field_data)

    def update_field(self, project_key: str, work_item_type_key: str, field_data: Dict) -> Dict:
        """更新自定义字段"""
        path = f"/open_api/{project_key}/field/{work_item_type_key}"
        return self._request("PUT", path, headers=self.headers, json=field_data)

    def get_relations(self, project_key: str) -> Dict:
        """获取工作项关系列表"""
        path = f"/open_api/{project_key}/work_item/relation"
        return self._request("GET", path, headers=self.headers)

    def create_relation(self, relation_data: Dict) -> Dict:
        """新增工作项关系"""
        path = "/open_api/work_item/relation/create"
        return self._request("POST", path, headers=self.headers, json=relation_data)

    def get_templates(self, project_key: str, work_item_type_key: str) -> Dict:
        """获取流程模板列表"""
        path = f"/open_api/{project_key}/template_list/{work_item_type_key}"
        return self._request("GET", path, headers=self.headers)

    def get_roles(self, project_key: str, work_item_type_key: str) -> Dict:
        """获取流程角色配置"""
        path = f"/open_api/{project_key}/flow_roles/{work_item_type_key}"
        return self._request("GET", path, headers=self.headers)


class UserClient(BaseClient):
    def __init__(self, base_url: str, plugin_token: str, user_key: Optional[str] = None):
        super().__init__(base_url)
        self.headers = {"X-PLUGIN-TOKEN": plugin_token}
        if user_key:
            self.headers["X-USER-KEY"] = user_key

    def get_team_members(self, project_key: str) -> Dict:
        """获取空间下团队成员"""
        path = f"/open_api/{project_key}/teams/all"
        return self._request("GET", path, headers=self.headers)

    def get_user_detail(self, user_keys: List[str] = None, emails: List[str] = None) -> Dict:
        """获取用户详情"""
        path = "/open_api/user/query"
        payload = {}
        if user_keys:
            payload["user_keys"] = user_keys
        if emails:
            payload["emails"] = emails
        return self._request("POST", path, headers=self.headers, json=payload)

    def search_users(self, query: str, project_key: str) -> Dict:
        """搜索租户内的用户列表"""
        path = "/open_api/user/search"
        payload = {"query": query, "project_key": project_key}
        return self._request("POST", path, headers=self.headers, json=payload)


class WorkItemClient(BaseClient):
    def __init__(self, base_url: str, plugin_token: str, user_key: Optional[str] = None):
        super().__init__(base_url)
        self.headers = {"X-PLUGIN-TOKEN": plugin_token}
        if user_key:
            self.headers["X-USER-KEY"] = user_key

    def filter(self, project_key: str, payload: Dict) -> Dict:
        """获取指定的工作项列表（单空间）"""
        path = f"/open_api/{project_key}/work_item/filter"
        return self._request("POST", path, headers=self.headers, json=payload)

    def get_detail(self, project_key: str, work_item_type_key: str, work_item_ids: List[int]) -> Dict:
        """获取工作项详情"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/query"
        payload = {"work_item_ids": work_item_ids}
        return self._request("POST", path, headers=self.headers, json=payload)

    def create(self, project_key: str, payload: Dict) -> Dict:
        """创建工作项"""
        path = f"/open_api/{project_key}/work_item/create"
        return self._request("POST", path, headers=self.headers, json=payload)

    def update(self, project_key: str, work_item_type_key: str, work_item_id: int, payload: Dict) -> Dict:
        """更新工作项"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/{work_item_id}"
        return self._request("PUT", path, headers=self.headers, json=payload)

    def delete(self, project_key: str, work_item_type_key: str, work_item_id: int) -> Dict:
        """删除工作项"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/{work_item_id}"
        return self._request("DELETE", path, headers=self.headers, json={})

    def get_workflow(
        self, project_key: str, work_item_type_key: str, work_item_id: int, flow_type: int = 1, _payload: Dict = None
    ) -> Dict:
        """获取工作流详情"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/{work_item_id}/workflow/query"
        if _payload:
            payload = _payload
        else:
            payload = {"flow_type": flow_type}
        return self._request("POST", path, headers=self.headers, json=payload)

    def get_transition_id(
        self,
        project_key: str,
        work_item_type_key: str,
        work_item_id: int,
        flow_type: int = 1,
        _payload: Dict = None,
        source_state_name: str = "新增",
        target_state_name: str = "",
    ):
        """获取工作流流转id"""

        if source_state_name == target_state_name:
            return None
        res_json = self.get_workflow(project_key, work_item_type_key, work_item_id, flow_type, _payload)

        state_flow_nodes = res_json.get("data", {}).get("state_flow_nodes", [])
        source_state_key = Utils.search_list_json(state_flow_nodes, "name", source_state_name).get("id")
        target_state_key = Utils.search_list_json(state_flow_nodes, "name", target_state_name).get("id")

        try:
            from jsonpath import jsonpath

            transition_id = jsonpath(
                res_json,
                f"""$..[?(@.source_state_key == "{source_state_key}" && @.target_state_key == "{target_state_key}")].transition_id""",
            )[0]
        except Exception as e:
            logger.warning(f"获取工作流流转id失败: {source_state_name}, {target_state_name}\n {e}")
            transition_id = None

        return transition_id

    def operate_node(
        self, project_key: str, work_item_type_key: str, work_item_id: int, node_id: str, payload: Dict
    ) -> Dict:
        """节点完成/回滚"""
        path = f"/open_api/{project_key}/workflow/{work_item_type_key}/{work_item_id}/node/{node_id}/operate"
        return self._request("POST", path, headers=self.headers, json=payload)

    def state_change(self, project_key: str, work_item_type_key: str, work_item_id: int, payload: Dict) -> Dict:
        """状态流转"""
        path = f"/open_api/{project_key}/workflow/{work_item_type_key}/{work_item_id}/node/state_change"
        return self._request("POST", path, headers=self.headers, json=payload)

    # 子任务相关
    def get_subtasks(self, project_key: str, work_item_type_key: str, work_item_id: int, node_id: str) -> Dict:
        """获取子任务详情"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/{work_item_id}/workflow/task"
        params = {"node_id": node_id}
        return self._request("GET", path, headers=self.headers, params=params)

    def get_create_meta(self, project_key, work_item_type_key="issue"):
        """获取创建工作项元数据"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/meta"
        return self._request("GET", path, headers=self.headers)


class ViewClient(BaseClient):
    def __init__(self, base_url: str, plugin_token: str, user_key: Optional[str] = None):
        super().__init__(base_url)
        self.headers = {"X-PLUGIN-TOKEN": plugin_token}
        if user_key:
            self.headers["X-USER-KEY"] = user_key

    def get_views(self, project_key: str, payload: Dict) -> Dict:
        """获取视图列表及配置信息"""
        path = f"/open_api/{project_key}/view_conf/list"
        return self._request("POST", path, headers=self.headers, json=payload)

    def get_view_items(self, project_key: str, view_id: str, payload: Dict) -> Dict:
        """获取视图下工作项列表（全景视图）"""
        path = f"/open_api/{project_key}/view/{view_id}"
        return self._request("POST", path, headers=self.headers, json=payload)


class CommentClient(BaseClient):
    def __init__(self, base_url: str, plugin_token: str, user_key: Optional[str] = None):
        super().__init__(base_url)
        self.headers = {"X-PLUGIN-TOKEN": plugin_token}
        if user_key:
            self.headers["X-USER-KEY"] = user_key

    def create_comment(self, project_key: str, work_item_id: int, content, work_item_type_key: str = "issue") -> Dict:
        """添加评论"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/{work_item_id}/comment/create"
        if isinstance(content, str):
            payload = {"content": content}
        elif isinstance(content, list):
            payload = {"rich_text": content}
        else:
            raise ValueError("content must be str or list")
        return self._request("POST", path, headers=self.headers, json=payload)

    def get_comments(
        self, project_key: str, work_item_type_key: str, work_item_id: int, page_num: int = 1, page_size: int = 10
    ) -> Dict:
        """查询评论"""
        path = f"/open_api/{project_key}/work_item/{work_item_type_key}/{work_item_id}/comments"
        params = {"page_num": page_num, "page_size": page_size}
        return self._request("GET", path, headers=self.headers, params=params)


class FeishuProjectApiUtils:
    def __init__(
        self,
        base_url=None,
        project_key=None,
        plugin_id=None,
        plugin_secret=None,
        user_key=None,
        plugin_token=None,
    ):
        self.base_url = base_url or FEISHU_PROJECT_URL
        self.project_key = project_key or PROJECT_KEY
        self.plugin_id = plugin_id or PLUGIN_ID
        self.plugin_secret = plugin_secret or PLUGIN_SECRET
        self.user_key = user_key or USER_KEY
        self.auth = AuthClient(self.base_url)
        self.plugin_token = plugin_token or self.set_plugin_token()

        self._init_sub_clients()
        self.pcc = None

    def _init_sub_clients(self):
        self.file = FileClient(self.base_url, self.plugin_token, self.user_key)
        self.space = SpaceClient(self.base_url, self.plugin_token, self.user_key)
        self.config = ConfigClient(self.base_url, self.plugin_token, self.user_key)
        self.user = UserClient(self.base_url, self.plugin_token, self.user_key)
        self.work_item = WorkItemClient(self.base_url, self.plugin_token, self.user_key)
        self.view = ViewClient(self.base_url, self.plugin_token, self.user_key)
        self.comment = CommentClient(self.base_url, self.plugin_token, self.user_key)

    def set_user_key(self, user_key: str):
        """Update the user_key for all initialized sub-clients"""
        self.user_key = user_key
        if self.plugin_token:
            self._init_sub_clients()

    def set_plugin_token(self):
        """Update the plugin_token for all initialized sub-clients"""
        return self.auth.get_plugin_token(self.plugin_id, self.plugin_secret).get("data", {}).get("token")


class PingCodeToFeishuUtils(FeishuProjectApiUtils):
    """
    PingCode 缺陷转飞书项目缺陷
    """

    def set_ping_code_client(self, **kwargs):
        self.pcc = PingCodeClient(**kwargs)
        return self.pcc

    @staticmethod
    def format_rich_paragraph(_text="", _type="text", attrs=None, is_line_attrs=False):
        """格式化paragraph"""

        content_dict: Dict[str, Any] = {"type": _type}
        if _text:
            content_dict["text"] = _text
        if attrs:
            content_dict["attrs"] = attrs
        if is_line_attrs:
            content_dict["lineAttrs"] = {"blockquote": "true", "indent": "1"}

        return {"type": "paragraph", "content": [content_dict]}

    @staticmethod
    def extract_text_from_children(children):
        """从children中提取纯文本内容"""
        text_parts = []
        for child in children:
            if "text" in child:
                text_parts.append(child["text"])
            elif child.get("type") == "mention":
                # 对于mention类型，提取用户名
                name = child.get("data", {}).get("name", "")
                if name:
                    text_parts.append(f"@{name}")
        return "".join(text_parts)

    def html_to_feishu_rich_text(
        self, html_str, assignee=None, created_by=None, created_at=None, updated_by=None, update_at=None, bug_url=None
    ):
        """
        HTML 转为飞书富文本
        """
        from bs4 import BeautifulSoup

        result = []

        if assignee:
            result.append(self.format_rich_paragraph(f"由 {assignee} 处理。"))
        if created_at:
            result.append(self.format_rich_paragraph(f"由 {created_by} 在 {datetime.fromtimestamp(created_at)} 创建。"))
            result.append(self.format_rich_paragraph(f"由 {updated_by} 在 {datetime.fromtimestamp(update_at)} 更新。"))
        if bug_url:
            result.append(
                self.format_rich_paragraph(_type="hyperlink", attrs={"title": "PingCode链接", "url": bug_url})
            )
        if html_str:
            soup = BeautifulSoup(html_str, "html.parser")

            for elem in soup.find_all(True):
                if elem.name == "p":
                    text = elem.get_text(strip=True)
                    if text:
                        result.append(self.format_rich_paragraph(text))
                elif elem.name == "img":
                    token = self.pcc.get_public_image_token()
                    src = elem.get("src", "").strip()
                    if not src:
                        continue
                    img_res = self.pcc.request_client.get(src + "?token=" + token)

                    feishu_img_url = self.file.upload_file(self.project_key, file_bytes=img_res.content).get("data", [])

                    if not feishu_img_url:
                        continue
                    result.append(self.format_rich_paragraph(_type="img", attrs={"src": feishu_img_url[0]}))

        return result

    def convert_content_item(self, item, is_line_attrs=False):
        """转换单个content项"""
        item_type = item.get("type", "paragraph")

        if item_type == "paragraph":
            # 提取段落文本
            children = item.get("children", [])
            text = self.extract_text_from_children(children)
            return self.format_rich_paragraph(_text=text, _type="text", is_line_attrs=is_line_attrs)

        elif item_type == "code":
            # 处理代码块 - 转换为引用格式
            code_content = item.get("content", "")
            if code_content:
                return self.format_rich_paragraph(code_content, is_line_attrs=True)
            return None

        elif item_type == "numbered-list":
            # 处理有序列表
            list_items = item.get("children", [])
            converted_items = []
            for idx, list_item in enumerate(list_items, 1):
                if list_item.get("type") == "list-item":
                    # 列表项可能包含段落
                    for child in list_item.get("children", []):
                        if child.get("type") == "paragraph":
                            text = self.extract_text_from_children(child.get("children", []))
                            # 为列表项添加序号
                            numbered_text = f"{idx}. {text}"
                            converted_items.append(
                                self.format_rich_paragraph(
                                    _text=numbered_text, _type="text", is_line_attrs=is_line_attrs
                                )
                            )
            return converted_items

        else:
            # 其他类型，尝试提取文本
            children = item.get("children", [])
            text = self.extract_text_from_children(children)
            return self.format_rich_paragraph(_text=text, _type="text", is_line_attrs=is_line_attrs)

    def add_ping_code_comment(self, comment_info):
        """添加PingCode的评论"""
        if comment_info.get("is_deleted") or comment_info.get("content") is None:
            logger.info("PingCode的评论已删除,返回 None")
            return None

        created_by = comment_info.get("created_by")
        created_at = comment_info.get("created_at")
        content_list = comment_info.get("content", [])
        reply_comment = comment_info.get("reply_comment", {})
        attachments = comment_info.get("attachments")

        rich_text = [
            self.format_rich_paragraph(f"由 {created_by} 在 {datetime.fromtimestamp(created_at)} 创建。"),
            self.format_rich_paragraph("-" * 50),
        ]

        for content in content_list:
            feishu_content = self.convert_content_item(content)
            if isinstance(feishu_content, list):
                rich_text.extend(feishu_content)
            else:
                rich_text.append(feishu_content)

        if reply_comment:
            rich_text.append(self.format_rich_paragraph("-" * 50))
            rich_text.append(
                self.format_rich_paragraph(f"回复{reply_comment.get('reply_user',{}).get('display_name')}:")
            )
            content_list = reply_comment.get("content", [])
            for content in content_list:
                feishu_reply_content = self.convert_content_item(content, is_line_attrs=True)
                if isinstance(feishu_reply_content, list):
                    rich_text.extend(feishu_reply_content)
                else:
                    rich_text.append(feishu_reply_content)

        for attachment in attachments:
            file_token = attachment.get("token")
            file_title = attachment.get("title")
            file_ext = attachment.get("addition", {}).get("ext", "")
            file_size = attachment.get("addition", {}).get("size", 0)
            if file_size > 1024 * 1024 * 100:
                logger.error(f"文件超过100MB，请自行上传: {file_title}")
                logger.error(f"评论内容: {comment_info}")
                continue
            if file_ext not in ["png", "jpg", "jpeg", "gif", "bmp"]:
                logger.error(f"文件格式不支持: {file_title}")
                logger.error(f"评论内容: {comment_info}")
                continue
            file_res = self.pcc.download_attachment(file_token)
            file_bytes = file_res.content
            feishu_img_url = self.file.upload_file(self.project_key, file_bytes=file_bytes, file_name=file_title).get(
                "data", []
            )
            if not feishu_img_url:
                continue
            rich_text.append(self.format_rich_paragraph(_type="img", attrs={"src": feishu_img_url[0]}))

        return rich_text

    def import_ping_code_bugs(self, pc_search_data):
        """
        导入PingCode的Bug
        """
        pc_bugs = self.pcc.format_bug_info_for_feishu(pc_search_data)
        if not pc_bugs:
            return 0

        create_meta = self.work_item.get_create_meta(self.project_key).get("data", [])
        priority_options = Utils.search_list_json(create_meta, "field_key", "priority").get("options", [])
        severity_options = Utils.search_list_json(create_meta, "field_key", "severity").get("options", [])
        ping_code_url_field_key = Utils.search_list_json(create_meta, "field_name", "PingCode_URL").get("field_key")
        ping_code_id_field_key = Utils.search_list_json(create_meta, "field_name", "PingCode编号").get("field_key")
        env_type_field_key = Utils.search_list_json(create_meta, "field_name", "环境类型").get("field_key")
        env_type_options = Utils.search_list_json(create_meta, "field_name", "环境类型").get("options", [])

        for pc_bug in pc_bugs:
            # 缺陷名称、优先级、严重级别
            priority_value = Utils.search_list_json(priority_options, "label", pc_bug.get("priority")).get("value")
            severity_value = Utils.search_list_json(severity_options, "label", pc_bug.get("severity")).get("value")
            env_type_value = [
                {"value": Utils.search_list_json(env_type_options, "label", env_type).get("value")}
                for env_type in pc_bug.get("test_env", [])
            ]
            identifier = pc_bug.get("identifier")
            bug_name = pc_bug.get("title")
            create_work_item_data = {
                "work_item_type_key": "issue",
                "name": bug_name,
                "field_value_pairs": [
                    {"field_key": "priority", "field_value": {"value": priority_value}},
                    {"field_key": "severity", "field_value": {"value": severity_value}},
                    {"field_key": ping_code_url_field_key, "field_value": pc_bug.get("bug_url")},
                    {"field_key": ping_code_id_field_key, "field_value": f"MINIS-{identifier}"},
                    {"field_key": env_type_field_key, "field_value": env_type_value},
                ],
            }

            # 缺陷描述、创建信息、更新信息、链接、负责人
            description = self.html_to_feishu_rich_text(
                pc_bug.get("description"),
                pc_bug.get("assignee"),
                pc_bug.get("created_by"),
                pc_bug.get("created_at"),
                pc_bug.get("updated_by"),
                pc_bug.get("updated_at"),
                pc_bug.get("bug_url"),
            )
            create_work_item_data["field_value_pairs"].append({"field_key": "description", "field_value": description})

            create_res = self.work_item.create(self.project_key, create_work_item_data)
            if create_res.get("err_code") != 0:
                logger.error(f"创建缺陷失败: {create_res}")
                logger.error(f"创建缺陷数据: {identifier} {create_work_item_data}")
                continue

            create_id = create_res.get("data")
            # create_id = 6670340307

            logger.info(f"创建缺陷成功: {bug_name} {create_id}")

            # multi_attachment 附件
            attachments = pc_bug.get("attachments", [])
            for attachment in attachments:
                file_token = attachment.get("token")
                file_title = attachment.get("title")
                # file_ext = attachment.get("addition", {}).get("ext", "png")
                file_size = attachment.get("addition", {}).get("size", 0)
                # file_origin_size = attachment.get("addition", {}).get("origin_size", {})
                if file_size > 1024 * 1024 * 100:
                    logger.error(f"文件超过100MB，请自行上传: {file_title}")
                    logger.error(f"缺陷信息: {identifier} {create_work_item_data}")
                    continue
                file_res = self.pcc.download_attachment(file_token)
                file_bytes = file_res.content
                self.file.add_attachment(self.project_key, create_id, file_bytes=file_bytes, file_name=file_title)

            logger.info(f"上传附件成功: {bug_name} {create_id}")

            # 评论
            comments = pc_bug.get("comments", [])

            for comment in comments:
                rich_text = self.add_ping_code_comment(comment)
                if not rich_text:
                    continue
                self.comment.create_comment(self.project_key, create_id, rich_text)
                time.sleep(1)

            # 状态
            ping_code_state_name = pc_bug.get("state_name", "新提交")
            feishu_state_name = STATUS_PING_CODE_TO_FEISHU.get(ping_code_state_name, "新增")

            if feishu_state_name != "新增":
                transition_id = self.work_item.get_transition_id(
                    self.project_key, "issue", create_id, target_state_name=feishu_state_name
                )
                if transition_id:
                    state_change_data = {"transition_id": transition_id}
                    self.work_item.state_change(self.project_key, "issue", create_id, state_change_data)
                    logger.info(f"状态转换成功: {feishu_state_name}")
                else:
                    logger.error(f"状态转换失败: {ping_code_state_name} {feishu_state_name}")

            logger.info(f"bug创建成功: {bug_name} {create_id}")

        return len(pc_bugs)
