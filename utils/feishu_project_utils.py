from pathlib import Path

from conf.feishu_conf import FEISHU_PROJECT_URL, PROJECT_KEY, PLUGIN_ID, PLUGIN_SECRET, USER_KEY
from utils.log_utils import logger
from utils.ping_code_utils import PingCodeClient
from utils.request_utils import RetryableRequest
from utils.utils import Utils


class FeiShuProjectUtils:
    """
    飞书项目 API Utils
    """

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
        self.client = RetryableRequest(retries=3, backoff_factor=2)
        self.plugin_token = plugin_token or self.get_project_token()
        self.headers = {
            # "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token,
            "X-USER-KEY": self.user_key,
        }

    @classmethod
    def _get_response_data(cls, response, _key="data"):
        """
        获取 API Response data
        :param response:
        :return:
        """
        if response.status_code == 200:
            if _key:
                return response.json().get(_key)
            else:
                return response.json()
        else:
            return response.text

    def get_project_token(self):
        """
        /open_api/authen/plugin_token
        :return:
        """
        url = self.base_url + "/open_api/authen/plugin_token"
        data = {
            "plugin_id": self.plugin_id,
            "plugin_secret": self.plugin_secret,
            "type": 1,
        }
        res = self.client.post(url=url, json=data)
        if res.status_code == 200:
            token = res.json().get("data").get("token")
            self.plugin_token = token
        else:
            token = None
        return token

    def get_work_item_all_types(self):
        """
        /open_api/:project_key/work_item/all-types
        :return:
        """
        url = self.base_url + f"/open_api/{self.project_key}/work_item/all-types"
        res = self.client.get(url=url, headers=self.headers)
        return self._get_response_data(res)

    def get_project_field(self, work_item_type_key):
        """
        获取字段信息
        :param work_item_type_key:
        :return:
        """
        url = self.base_url + f"/open_api/{self.project_key}/field/all"
        data = {"work_item_type_key": work_item_type_key}
        res = self.client.post(url=url, headers=self.headers, json=data)
        return self._get_response_data(res)

    def upload_file(self, file_path):
        """
        上传文件 或 富文本图片
        :param file_path:
        :return:
        """
        url = self.base_url + f"/open_api/{self.project_key}/file/upload"
        if isinstance(file_path, str):
            file_path = Path(file_path)

        with file_path.open("rb") as f:
            files = {"file": f}
            res = self.client.post(url=url, files=files, headers=self.headers)

        return self._get_response_data(res)

    def create_work_item(self, _data):
        """
        创建工作项
        :return:
        """
        url = self.base_url + f"/open_api/{self.project_key}/work_item/create"
        res = self.client.post(url=url, headers=self.headers, json=_data)
        return self._get_response_data(res)

    def update_work_item(self, work_item_type_key, work_item_id, request_data):
        """
        更新工作项
        :param work_item_type_key:
        :param work_item_id:
        :param request_data: {"update_fields": [{"field_key": "field_9d59f3","field_value": "asdf1222211a"}]}
        :return:
        """
        url = self.base_url + f"/open_api/{self.project_key}/work_item/{work_item_type_key}/{work_item_id}"
        res = self.client.post(url=url, headers=self.headers, json=request_data)
        # logger.info(f"更新数据：{request_data}")
        return self._get_response_data(res, _key="")

    def search_work_item_filter(self, work_item_type_keys, work_item_name=None, request_data=None):
        """
        获取指定的工作项列表（单空间-过滤条件）
        :param work_item_name:
        :param request_data:
        :param work_item_type_keys:
        :return:
        """
        url = self.base_url + f"/open_api/{self.project_key}/work_item/filter"
        request_data = request_data or {"work_item_type_keys": work_item_type_keys, "work_item_name": work_item_name}
        res = self.client.post(url=url, headers=self.headers, json=request_data)
        return self._get_response_data(res, _key="")

    def search_work_item_all(self, work_item_type_key, request_data):
        """
        获取指定的工作项列表（单空间-复杂传参）
        :param request_data:
        :param work_item_type_key:
        :return:
        """
        url = self.base_url + f"/open_api/{self.project_key}/work_item/{work_item_type_key}/search/params"
        # if not request_data:
        #     request_data = {
        #         "search_group": {
        #             "search_params": [
        #                 {
        #                     "param_key": "work_item_status",
        #                     "value": ["systemEnded", "ps1lrq6tg", "oz8xmdsl_"],
        #                     "operator": "HAS NONE OF"
        #                 },
        #                 {
        #                     "param_key": "field_e2c852",
        #                     "value": "",
        #                     "operator": "IS NOT NULL"
        #                 }
        #             ],
        #             "conjunction": "AND"
        #         },
        #         "page_num": 1,
        #         "page_size": 50,
        #         "fields": [
        #             "field_e2c852"
        #         ],
        #         "expand": {
        #             "need_workflow": False,
        #             "relation_fields_detail": False,
        #             "need_multi_text": False,
        #             "need_user_detail": False,
        #             "need_sub_task_parent": False
        #         }
        #     }
        res = self.client.post(url=url, headers=self.headers, json=request_data)
        total = res.json().get("pagination", {}).get("total", 0)
        page_size = res.json().get("pagination", {}).get("page_size", 50)
        res_data_list = res.json().get("data", [])
        page_num = 1
        while (page_size * page_num) <= total:
            page_num += 1
            request_data["page_num"] = page_num
            res = self.client.post(url=url, headers=self.headers, json=request_data)
            res_data_list = res_data_list + res.json().get("data", [])
        return res_data_list

    def update_bug_info_from_ping_code(self, _bugs=None, progress_callback=None):
        """
        获取 PingCode 数据更新 bug 信息
        :param _bugs: 可选的bug列表
        :param progress_callback: 进度回调函数，接收0-100的进度值
        :return: 处理结果
        """
        # 初始化进度
        if progress_callback:
            progress_callback(0, message="开始更新Bug信息，初始进度: 0%")

        feishu_search_params = {
            "search_group": {
                "search_params": [{"param_key": "field_e2c852", "value": "", "operator": "IS NOT NULL"}],
                "conjunction": "AND",
            },
            "fields": ["field_e2c852", "field_9d59f3", "field_7f6e66", "field_f18a13"],
        }
        _bugs = _bugs or self.search_work_item_all(work_item_type_key="issue", request_data=feishu_search_params)
        bug_count = len(_bugs)
        result_set = {"count": bug_count, "success": [], "error": []}

        if not _bugs:
            if progress_callback:
                progress_callback(100, message="没有bug需要更新")
            return result_set

        pcc = PingCodeClient()

        for index, bug in enumerate(_bugs):
            try:
                pc_bug_id = (
                    Utils.search_list_json(bug.get("fields", []), "field_alias", "pingcode_id")
                    .get("field_value")
                    .strip()
                )
                fs_bug_comments = (
                    Utils.search_list_json(bug.get("fields", []), "field_alias", "pingcode_comments")
                    .get("field_value", "")
                    .replace("\\n", "\n")
                    .strip()
                )
                fs_bug_status = Utils.search_list_json(bug.get("fields", []), "field_alias", "pingcode_status").get(
                    "field_value"
                )
                fs_bug_url = Utils.search_list_json(bug.get("fields", []), "field_alias", "pingcode_url").get(
                    "field_value"
                )

                if pc_bug_id:
                    pc_bug_info = pcc.search_bug_by_id(pc_bug_id[6:]).get("data")
                    if pc_bug_info:
                        update_request_data = {"update_fields": []}
                        # 处理PingCode Bug状态
                        pc_bug_state_id = pc_bug_info.get("value")[0].get("state_id")
                        pc_bug_short_id = pc_bug_info.get("value")[0].get("short_id")

                        if not fs_bug_url:
                            update_request_data["update_fields"].append(
                                {"field_key": "field_f18a13", "field_value": pcc.get_bug_url(pc_bug_short_id)}
                            )
                        pc_bug_state_name = pcc.get_bug_status_name(pc_bug_state_id)
                        if pc_bug_state_name != fs_bug_status:
                            update_request_data["update_fields"].append(
                                {"field_key": "field_9d59f3", "field_value": pc_bug_state_name}
                            )

                        # 处理PingCode Bug 评论
                        pc_bug_comment_id = pc_bug_info.get("value")[0].get("_id")
                        pc_comment_request_list = pcc.format_comments(pc_bug_comment_id, fs_bug_comments)
                        if pc_comment_request_list:
                            update_request_data["update_fields"].append(
                                {"field_key": "field_7f6e66", "field_value": pc_comment_request_list}
                            )

                        if update_request_data.get("update_fields"):
                            res = self.update_work_item("issue", bug.get("id"), update_request_data)
                            if res.get("err_code"):
                                logger.error(f"修改缺陷失败：{res}")
                                logger.error(f"PingCode_编号: {pc_bug_id}，PingCode_状态: {pc_bug_state_name}")
                                result_set["error"].append({pc_bug_id: res})
                            else:
                                logger.info(f"PingCode_编号：{pc_bug_id} 数据已更新: {update_request_data}")
                                result_set["success"].append({pc_bug_id: update_request_data})
                        else:
                            logger.debug(f"BUG({pc_bug_id})状态和评论未变更！")
                    else:
                        error_msg = f"BUG({pc_bug_id})信息获取失败！\n已运行的结果：{result_set}"
                        result_set["error"].append({pc_bug_id: f"信息获取失败{pc_bug_info}"})
                        logger.error(error_msg)
                        raise Exception(error_msg)
                else:
                    result_set["error"].append({f"飞书BUG（{bug.get('name')}）": "缺少PingCode编号"})
                    logger.error(f"缺少PingCode编号: {pc_bug_id}")

            except Exception as e:
                # 错误处理
                error_msg = f"处理BUG时发生错误: {str(e)}"
                result_set["error"].append({f"飞书BUG（{bug.get('name')}）": error_msg})
                logger.error(error_msg)

            # 更新进度
            if progress_callback:
                progress_callback(current=index+1, total=bug_count, message="")

        # 完成进度
        if progress_callback:
            progress_callback(100, message="更新完成")

        return result_set

    def update_ping_code_sprint_bug(self, sprint_name, progress_callback=None):
        """
        更新 sprint 下的 bug 列表
        :param sprint_name: Sprint名称
        :param progress_callback: 进度回调函数，接收0-100的进度值
        :return: 处理结果
        """
        # 初始化进度
        if progress_callback:
            progress_callback(0, message="开始同步sprint bug信息")

        pcc = PingCodeClient()

        fs_sprint_info = self.search_work_item_filter(work_item_type_keys=["sprint"], work_item_name=sprint_name)
        fs_sprint_id = fs_sprint_info.get("data")[0].get("id")
        pc_sprint_id = pcc.get_sprints_info(sprint_name).get("data").get("value")[0].get("_id")
        request_data = {
            "search_group": {
                "search_params": [{"param_key": "planning_sprint", "value": [fs_sprint_id], "operator": "HAS ANY OF"}],
                "conjunction": "AND",
            },
            "fields": ["field_e2c852", "field_9d59f3", "field_7f6e66", "field_f18a13", "planning_sprint"],
        }

        fs_bugs = self.search_work_item_all(work_item_type_key="issue", request_data=request_data)
        bug_count = len(fs_bugs)

        result_set = {"count": bug_count, "success": [], "error": []}

        for index, bug in enumerate(fs_bugs):
            try:
                pc_bug_id = (
                    Utils.search_list_json(bug.get("fields", []), "field_alias", "pingcode_id")
                    .get("field_value")
                    .strip()
                )
                if pc_bug_id:
                    pc_bug_info = pcc.search_bug_by_id(pc_bug_id[6:]).get("data")
                    if pc_bug_info:
                        temp_pc_bug_id = pc_bug_info.get("value")[0].get("_id")
                        res = pcc.put_work_item_info(temp_pc_bug_id, {"sprint_id": pc_sprint_id})
                        if res.get("data").get("value"):
                            result_set["success"].append({pc_bug_id: res})
                            logger.info(f"PingCode_编号：{pc_bug_id} 数据已更新: {res}")
                        else:
                            result_set["error"].append({pc_bug_id: res})
                    else:
                        result_set["error"].append({pc_bug_id: f"信息获取失败{pc_bug_info}"})
                        logger.error(f"BUG({pc_bug_id})信息获取失败！")
                else:
                    result_set["error"].append({f"飞书BUG（{bug.get('name')}）": "缺少PingCode编号"})
                    logger.error(f"缺少PingCode编号: {pc_bug_id}")

            except Exception as e:
                # 错误处理
                error_msg = f"处理BUG时发生错误: {str(e)}"
                result_set["error"].append({f"飞书BUG（{bug.get('name')}）": error_msg})
                logger.error(error_msg)

            # 更新进度
            if progress_callback:
                progress_callback(current=index + 1, total=bug_count, message="")

        # 完成进度
        if progress_callback:
            progress_callback(100)

        return result_set


#
#     print(feishu_client.get_project_token())
