# fashion-agent 容器化（Dockerfile）
# 用途：客户/服务器一条命令启动，无需手动装环境
# 构建：docker build -t fashion-agent .
# 运行：docker run -p 8501:8501 --env-file .env fashion-agent

FROM python:3.11-slim

WORKDIR /app

# 先装依赖（利用缓存层，改代码不用重装依赖）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 再复制代码
COPY . .

# 数据目录可挂载（客户数据 + 知识库 + 向量库持久化）
VOLUME ["/app/data", "/app/charts"]

# 端口：Streamlit 默认 8501
EXPOSE 8501

# 容器内要监听 0.0.0.0，否则外部访问不到
CMD ["streamlit", "run", "src/web/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
