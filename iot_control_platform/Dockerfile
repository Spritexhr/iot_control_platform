# 物联网控制平台 - Django 后端镜像
# 使用 Python 3.12 轻量级镜像
FROM docker.m.daocloud.io/library/python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（mysqlclient 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 包（使用国内镜像源）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt gunicorn

# 复制项目代码
COPY . .

# 暴露端口（Gunicorn 默认监听 8000）
EXPOSE 8000

# 使用 Gunicorn 启动 Django（生产级 WSGI 服务器）
# gthread + 多线程：避免 SSE 长连接占满 sync worker 导致其它 /api/* 请求排队/超时
# timeout 0：SSE 是无限长流，禁用 worker timeout 防止被 master 杀掉
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--worker-class", "gthread", \
     "--threads", "8", \
     "--timeout", "0"]
