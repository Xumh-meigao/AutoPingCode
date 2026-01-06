# --*-- conding:utf-8 --*--
# @Time : 2025/03/06 10:04
# @Author : Xumh
from types import TracebackType

import requests
from urllib3 import BaseHTTPResponse  # noqa
from urllib3.connectionpool import ConnectionPool
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

from conf.global_conf import REQUEST_TIMEOUT
from utils.log_utils import logger


class LoggingRetry(Retry):
    def increment(
        self,
        method: str | None = None,
        url: str | None = None,
        response: BaseHTTPResponse | None = None,
        error: Exception | None = None,
        _pool: ConnectionPool | None = None,
        _stacktrace: TracebackType | None = None,
    ) -> Retry:
        # 计算下次等待时间
        backoff = self.get_backoff_time()

        # 构造日志信息
        retry_log = f"Retry #{self.total} → "
        if response:
            retry_log += f"Status: {response.status} "
        if error:
            retry_log += f"Error: {error.__class__.__name__} "

        retry_log += f"| Method: {method} | URL: {url} | Next wait: {backoff:.2f}s"
        logger.warning(retry_log)

        return super().increment(method, url, response, error, _pool, _stacktrace)


class RetryableRequest:
    def __init__(self, retries=3, backoff_factor=1):
        self.session = requests.Session()

        # 配置重试策略
        retry_strategy = LoggingRetry(
            total=retries,
            backoff_factor=backoff_factor,  # 指数退避间隔
            status_forcelist=[500, 502, 503, 504],  # 需要重试的状态码
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
        )

        # 为HTTP和HTTPS请求添加适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)  # noqa
        self.session.mount("https://", adapter)

    def request(self, method, url, **kwargs):
        """
        增强的请求方法
        :param method: HTTP方法 (GET/POST/PUT/DELETE etc.)
        :param url: 请求地址
        :param kwargs: 其他requests参数
        """
        try:
            response = self.session.request(method=method, url=url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed after retries: {str(e)}")

    # 快捷方法
    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url, data=None, json=None, **kwargs):
        return self.request("PUT", url, data=data, json=json, **kwargs)

    def post_request_json(self, url: str, json=None, **kwargs):
        try:
            res = self.post(url, json=json, timeout=kwargs.pop("timeout", REQUEST_TIMEOUT), **kwargs)
            if res.status_code == 200:
                return res
            logger.warning(f"request failed with status code: {res.status_code}")
            logger.warning(f"request url: {url}")
            logger.warning(f"request data: {json}")
            logger.warning(res.text)
            return res
        except Exception as e:
            logger.warning(f"request failed: {e}")
            return None

# # 使用示例
# if __name__ == "__main__":
#     client = RetryableRequest(retries=3, backoff_factor=2)
#
#     # # 测试重试（模拟500错误）
#     # try:
#     #     response = client.get("https://httpbin.org/status/500")
#     #     print(response.status_code)
#     # except Exception as e:
#     #     print(f"最终请求失败: {e}")
#
#     # 测试连接超时（模拟不稳定网络）
#     client.get("https://httpbin.org/delay/5", timeout=3)
#
#     # 测试服务不可用（模拟维护场景）
#     # client.get("https://httpbin.org/status/503")
#
#     # 正常请求示例
#     response = client.post("https://httpbin.org/post", json={"key": "value"})
#     print(response.json())
