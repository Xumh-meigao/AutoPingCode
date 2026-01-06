FROM python:3.12.12-slim

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 设置默认环境变量
ENV PING_CODE_COOKIE="your_default_cookie_here"

# 暴露端口 5432
EXPOSE 5432

# 设置环境变量
ENV PYTHONPATH=/app

# 启动应用
CMD ["python", "app.py"]
