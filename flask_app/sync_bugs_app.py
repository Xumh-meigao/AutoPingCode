# sync_bugs_app.py
import sqlite3

from flask import Flask
from flask_cors import CORS
from flask_restx import Api, Resource, fields

from utils.feishu_project_utils import FeiShuProjectUtils
from utils.thread_utils import ThreadUtils

# 创建 Flask 应用
app = Flask(__name__, static_folder="static")

# 启用 CORS 支持
CORS(app)


# 添加静态文件服务路由
@app.route("/")
def index():
    """提供前端页面"""
    return app.send_static_file("index.html")


# 添加一个路由来提供静态HTML页面
@app.route("/smart-monitor")
def smart_monitor():
    """提供SMART监控页面"""
    return app.send_static_file("smart_report.html")


# 创建 RESTX API 实例
api = Api(
    app,
    version="1.0",
    title="FeiShu Project API",
    description="飞书项目与 PingCode 集成 API",
    doc="/doc/",
    prefix="/api/v1",
)

# 定义统一的飞书项目命名空间
feishu_ns = api.namespace("feishu_pingcode", description="飞书项目相关操作")
device_info_ns = api.namespace("device_info", description="设备信息 数据相关操作")

# 创建线程工具实例
thread_utils = ThreadUtils(max_workers=2)

# 定义响应码常量
SUCCESS_CODE = 0  # 全部成功
PARTIAL_SUCCESS_CODE = 1  # 部分成功
ERROR_CODE = 2  # 全部失败
PARAM_ERROR_CODE = 3  # 参数错误

# 定义数据模型
response_model = api.model(
    "ResponseModel",
    {
        "code": fields.Integer(description="响应码: 0-全部成功, 1-部分成功, 2-全部失败, 3-参数错误", example=0),
        "message": fields.String(description="响应消息", example="操作成功"),
        "data": fields.Raw(description="返回数据"),
    },
)

sprint_request_model = api.model(
    "SprintRequest", {"sprint_name": fields.String(required=True, description="Sprint 名称", example="Sprint 1")}
)

smart_request_model = api.model(
    "SmartRequest",
    {
        "nas_ip": fields.String(required=True, description="NAS IP地址", example="192.168.1.100"),
        "nas_user": fields.String(required=True, description="NAS用户名", example="admin"),
        "nas_password": fields.String(required=False, description="NAS密码", example="password123"),
    },
)


def process_result(result):
    """处理方法调用结果，生成统一响应格式"""
    error_count = len(result.get("error", []))
    success_count = len(result.get("success", []))
    total_count = result.get("count", 0)

    # 构造统一格式的返回数据
    response_data = {"count": total_count, "success": result.get("success", []), "error": result.get("error", [])}

    # 判断响应码
    if error_count == 0:
        return {"code": SUCCESS_CODE, "message": "全部操作成功", "data": response_data}, 200
    elif success_count > 0:
        return {"code": PARTIAL_SUCCESS_CODE, "message": "部分操作成功", "data": response_data}, 200
    else:
        return {"code": ERROR_CODE, "message": "操作失败", "data": response_data}, 200


def handle_exception(e):
    """统一异常处理"""
    return {"code": ERROR_CODE, "message": "服务器内部错误", "data": {"error": str(e)}}, 500


@feishu_ns.route("/bugs/update")
class UpdateBugInfo(Resource):
    @api.doc("update_bug_info")
    @api.response(200, "操作完成", response_model)
    @api.response(500, "服务器内部错误", response_model)
    def post(self):
        """
        从 PingCode 获取 bug 数据并更新飞书项目中的 bug 信息
        """
        try:
            # 初始化飞书项目工具类
            feishu_client = FeiShuProjectUtils()

            # 调用更新函数
            result = feishu_client.update_bug_info_from_ping_code()

            # 处理结果
            return process_result(result)

        except Exception as e:
            return handle_exception(e)


@feishu_ns.route("/sprints/<string:sprint_name>/sync-bugs")
@api.param("sprint_name", "Sprint 名称")
class UpdateSprintBugs(Resource):
    @api.doc("sync_sprint_bugs_to_pingcode")
    @api.response(200, "操作完成", response_model)
    @api.response(400, "请求参数错误", response_model)
    @api.response(500, "服务器内部错误", response_model)
    def post(self, sprint_name):
        """
        将飞书项目中指定 sprint 下的 bug 同步到 PingCode 相同 sprint 中
        """
        try:
            if not sprint_name:
                return {"code": PARAM_ERROR_CODE, "message": "缺少必要参数: sprint_name", "data": {}}, 400

            # 初始化飞书项目工具类
            feishu_client = FeiShuProjectUtils()

            # 调用更新函数
            result = feishu_client.update_ping_code_sprint_bug(sprint_name)

            # 处理结果
            return process_result(result)

        except Exception as e:
            return handle_exception(e)


@feishu_ns.route("/bugs/update/async")
class AsyncUpdateBugInfo(Resource):
    @api.doc("async_update_bug_info")
    @api.response(202, "任务已提交")
    @api.response(500, "服务器内部错误", response_model)
    def post(self):
        """
        异步从 PingCode 获取 bug 数据并更新飞书项目中的 bug 信息
        """
        try:

            def update_task(progress_callback=None):
                feishu_client = FeiShuProjectUtils()
                return feishu_client.update_bug_info_from_ping_code(progress_callback=progress_callback)

            # 提交异步任务
            task_id = thread_utils.submit_task(update_task)

            return {
                "code": SUCCESS_CODE,
                "message": "任务已提交",
                "data": {"task_id": task_id, "message": "Bug信息更新任务已提交，请稍后查询任务状态"},
            }, 202

        except Exception as e:
            return handle_exception(e)


@feishu_ns.route("/sprints/<string:sprint_name>/sync-bugs/async")
@api.param("sprint_name", "Sprint 名称")
class AsyncUpdateSprintBugs(Resource):
    @api.doc("async_sync_sprint_bugs_to_pingcode")
    @api.response(202, "任务已提交")
    @api.response(400, "请求参数错误", response_model)
    @api.response(500, "服务器内部错误", response_model)
    def post(self, sprint_name):
        """
        异步将飞书项目中指定 sprint 下的 bug 同步到 PingCode 相同 sprint 中
        """
        try:
            if not sprint_name:
                return {"code": PARAM_ERROR_CODE, "message": "缺少必要参数: sprint_name", "data": {}}, 400

            def sync_task(sprint_name, progress_callback=None):
                feishu_client = FeiShuProjectUtils()
                return feishu_client.update_ping_code_sprint_bug(sprint_name, progress_callback=progress_callback)

            # 提交异步任务
            task_id = thread_utils.submit_task(sync_task, sprint_name)

            return {
                "code": SUCCESS_CODE,
                "message": "任务已提交",
                "data": {
                    "task_id": task_id,
                    "sprint_name": sprint_name,
                    "message": f"Sprint '{sprint_name}' 的Bugs同步任务已提交，请稍后查询任务状态",
                },
            }, 202

        except Exception as e:
            return handle_exception(e)


@feishu_ns.route("/tasks/<string:task_id>")
@api.param("task_id", "任务ID")
class TaskStatus(Resource):
    @api.doc("get_task_status")
    @api.response(200, "获取任务状态成功", response_model)
    @api.response(404, "任务不存在", response_model)
    def get(self, task_id):
        """
        查询异步任务执行状态
        """
        try:
            task_info = thread_utils.get_task_status(task_id)

            if task_info is None:
                return {"code": ERROR_CODE, "message": "任务不存在", "data": {}}, 404

            return {"code": SUCCESS_CODE, "message": "任务状态查询成功", "data": task_info}, 200

        except Exception as e:
            return handle_exception(e)


@feishu_ns.route("/tasks/<string:task_id>/result")
@api.param("task_id", "任务ID")
class TaskResult(Resource):
    @api.doc("get_task_result")
    @api.response(200, "获取任务结果成功", response_model)
    @api.response(404, "任务不存在", response_model)
    @api.response(400, "任务未完成", response_model)
    def get(self, task_id):
        """
        查询异步任务执行结果
        """
        try:
            task_result = thread_utils.get_task_result(task_id)

            if task_result is None:
                return {"code": ERROR_CODE, "message": "任务不存在", "data": {}}, 404

            if task_result["status"] == "completed":
                # 处理任务结果
                processed_result = process_result(task_result["result"])
                return processed_result
            elif task_result["status"] == "failed":
                return {"code": ERROR_CODE, "message": "任务执行失败", "data": {"error": task_result["error"]}}, 200
            else:
                return {
                    "code": PARAM_ERROR_CODE,
                    "message": "任务尚未完成",
                    "data": {"status": task_result["status"]},
                }, 400

        except Exception as e:
            return handle_exception(e)


@device_info_ns.route("/smart-data")
class SmartData(Resource):
    @api.doc("get_smart_data")
    @api.response(200, "获取数据成功")
    def get(self):
        """获取所有SMART数据记录"""
        try:
            # Using pathlib and PROJECT_PATH global variable
            from conf.global_conf import PROJECT_PATH
            from datetime import datetime, timedelta

            db_path = PROJECT_PATH / "data" / "nas_smart.db"

            if not db_path.exists():
                return {"code": ERROR_CODE, "message": f"数据库文件未找到: {db_path}", "data": []}, 404

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Query all records, ordered by timestamp descending
            cursor.execute(
                """
                SELECT id, nas_ip, device, timestamp, data_units_read_gb, data_units_written_gb 
                FROM smart_records 
                ORDER BY timestamp DESC
                """
            )

            rows = cursor.fetchall()
            conn.close()

            # Convert to dictionary list with formatted timestamps
            columns = ["id", "nas_ip", "device", "timestamp", "data_units_read_gb", "data_units_written_gb"]
            smart_data = []

            for row in rows:
                # Format timestamp to a more readable format with timezone adjustment
                raw_timestamp = row[3]
                if raw_timestamp:
                    try:
                        # Parse the ISO timestamp and add 8 hours for China timezone
                        dt = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
                        # Add 8 hours for China timezone (UTC+8)
                        china_time = dt + timedelta(hours=8)
                        formatted_timestamp = china_time.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        formatted_timestamp = raw_timestamp
                else:
                    formatted_timestamp = "N/A"

                row_data = list(row)
                row_data[3] = formatted_timestamp
                smart_data.append(dict(zip(columns, row_data)))

            return {"code": SUCCESS_CODE, "message": "数据获取成功", "data": smart_data}, 200

        except Exception as e:
            return handle_exception(e)



@device_info_ns.route("/fetch-smart")
class FetchSmart(Resource):
    @api.doc("fetch_smart_data")
    @api.expect(smart_request_model)
    @api.response(200, "获取成功", response_model)
    @api.response(400, "请求参数错误", response_model)
    @api.response(500, "服务器内部错误", response_model)
    def post(self):
        """获取NAS SMART信息并存储到数据库"""
        try:
            # 获取请求数据
            data = api.payload
            nas_ip = data.get("nas_ip")
            nas_user = data.get("nas_user")
            nas_password = data.get("nas_password")

            # 验证必需参数
            if not nas_ip or not nas_user:
                return {"code": PARAM_ERROR_CODE, "message": "缺少必要参数: nas_ip 或 nas_user", "data": {}}, 400

            # 调用获取和存储SMART信息的函数
            from utils.nas_utils import fetch_and_store_smart_json

            record_id = fetch_and_store_smart_json(nas_ip, nas_user, nas_password)

            if record_id:
                return {
                    "code": SUCCESS_CODE,
                    "message": "成功获取并存储SMART信息",
                    "data": {"record_id": record_id},
                }, 200
            else:
                return {"code": ERROR_CODE, "message": "获取SMART信息失败", "data": {}}, 200

        except Exception as e:
            return handle_exception(e)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5432, debug=True)
