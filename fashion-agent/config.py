# -*- coding: utf-8 -*-
"""config.py —— 配置中心：密钥 / 路径 / 参数都在这里，改一处全局生效"""

import os
from dotenv import load_dotenv

# 读取 .env（项目根目录下的密钥文件，已被 .gitignore 排除）
load_dotenv()

# ============ 模型配置 ============
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")          # 从 .env 读取，不留任何硬编码
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

# ============ 路径配置 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "模拟企业数据.csv")   # 默认数据（可被界面上传替换）
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "data", "服装知识库.txt") # RAG 知识书
CHART_DIR = os.path.join(BASE_DIR, "charts")                      # 趋势图输出目录
REPORT_FILE = os.path.join(BASE_DIR, "data", "分析报告_任务.txt") # 报告保存位置
TRACE_DIR = os.path.join(BASE_DIR, "data", "traces")              # 每次任务的审计记录
EVAL_DIR = os.path.join(BASE_DIR, "data", "evaluations")          # AI 评测结果

# ============ 运行参数 ============
MAX_RETRY = 3        # 规划器最多重试次数
TEMPERATURE = 0.3    # 规划温度（低=稳定）

# 启动时确保输出目录存在
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(TRACE_DIR, exist_ok=True)
os.makedirs(EVAL_DIR, exist_ok=True)
