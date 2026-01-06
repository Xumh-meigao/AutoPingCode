# --*-- coding:utf-8 --*--
# @Time : 2024/08/13 15:37
# @Author : Xumh
# 修改 thread_utils.py
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from utils.log_utils import logger


class AsyncTask:
    def __init__(self, task_id, func, *args, **kwargs):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = "pending"
        self.progress = 0  # 添加进度字段
        self.result = None
        self.error = None
        self.created_time = datetime.now()
        self.start_time = None
        self.end_time = None


class ThreadUtils:
    def __init__(self, max_workers=1):
        self._lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}  # 存储所有任务

    def _task_wrapper(self, async_task):
        try:
            async_task.status = "running"
            async_task.start_time = datetime.now()

            # 创建更完善的进度回调函数
            def progress_callback(percentage=0, current=None, total=None, message=""):
                with self._lock:
                    # if percentage:
                    async_task.progress = max(0, min(100, percentage))
                    if current is not None and total > 0:
                        async_task.progress = int(max(0, min(100, (current / total) * 100)))
                    # logger.info(f"任务 {async_task.task_id} 进度更新: {async_task.progress}%, 消息: {message}")

            # 检查函数是否接受 progress_callback 参数
            import inspect

            func_signature = inspect.signature(async_task.func)

            if "progress_callback" in func_signature.parameters:
                # 执行任务并传递进度回调
                result = async_task.func(*async_task.args, **async_task.kwargs, progress_callback=progress_callback)
            else:
                # 执行任务（不传递进度回调）
                result = async_task.func(*async_task.args, **async_task.kwargs)

            async_task.status = "completed"
            async_task.result = result
            async_task.progress = 100
            logger.info(f"任务 {async_task.task_id} 完成，最终进度: {async_task.progress}%")
        except Exception as e:
            async_task.status = "failed"
            async_task.error = str(e)
            async_task.progress = 0
            logger.error(f"任务 {async_task.task_id} 失败，进度: {async_task.progress}%, 错误: {str(e)}")
        finally:
            async_task.end_time = datetime.now()

    def submit_task(self, func, *args, **kwargs):
        """提交异步任务"""
        task_id = str(uuid.uuid4())
        async_task = AsyncTask(task_id, func, *args, **kwargs)

        with self._lock:
            self.tasks[task_id] = async_task

        # 提交任务给执行器
        self.executor.submit(self._task_wrapper, async_task)
        return task_id

    def get_task_status(self, task_id):
        """获取任务状态"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                # 将 datetime 对象转换为字符串
                logger.info(f"任务进度: {task.progress}%")
                result = {
                    "task_id": task.task_id,
                    "status": task.status,
                    "progress": task.progress,  # 添加进度信息
                    "created_time": task.created_time.isoformat() if task.created_time else None,
                    "start_time": task.start_time.isoformat() if task.start_time else None,
                    "end_time": task.end_time.isoformat() if task.end_time else None,
                }
                return result
            return None

    def get_task_result(self, task_id):
        """获取任务结果"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {"task_id": task.task_id, "status": task.status, "result": task.result, "error": task.error}
            return None

    def shutdown(self, wait=True):
        """关闭线程池"""
        self.executor.shutdown(wait=wait)
