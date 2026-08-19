# 🧥 服装行业 AI 趋势分析 Agent

一个支持**数据上传、AI 自动分析、多步工作流**的服装行业智能助手。
AI 先规划 → 程序逐步执行 → AI 汇总报告，全程可视化。

## 功能

- 📊 **数据接入**：支持上传 CSV / Excel（客户自己的数据），也内置示例数据
- 🏢 **企业数据治理**：兼容常见中英文字段名，接入时校验类型、负数、退货异常和重复行
- 📋 **多步工作流**：AI 把大任务拆成步骤，程序逐步执行（Lv2 任务规划器）
- 📈 **趋势分析**：销售额 / 退货率 / 渠道对比 / 销量趋势图
- 🔍 **知识库问答**：向量检索 RAG（服装知识库，按语义匹配）
- 📝 **报告生成**：AI 汇总分析结果，一键下载
- 🔎 **结果可追溯**：每次运行保存数据指纹、规划、工具输入输出、耗时、报告哈希和运行 ID
- ✅ **AI 评测体系**：自动评估执行成功率、报告结构、引用覆盖率和数字忠实度

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key（复制模板，填入你自己的 key）
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 启动
python main.py
# 或：streamlit run src/web/app.py
```

## Docker 部署（给客户/服务器用，一条命令启动）

```bash
# 方式一：docker compose（推荐）
cp .env.example .env          # 填入客户自己的 key
docker compose up -d          # 一键启动
# 访问 http://localhost:8501

# 方式二：docker build + run
docker build -t fashion-agent .
docker run -p 8501:8501 --env-file .env fashion-agent
```

- `data/` 目录自动挂载：客户数据 + 知识库 + 向量库持久化，升级镜像不丢数据
- 要求：目标机器已装 Docker（Windows 装 Docker Desktop）

## 目录结构

```
fashion-agent/
├── main.py              # 一键启动入口
├── config.py            # 配置中心（密钥/路径/参数）
├── requirements.txt     # 依赖清单（锁版本）
├── .env                 # 密钥文件（已被 .gitignore 排除，勿提交）
├── .env.example         # 密钥模板（提交用）
├── src/
│   ├── agent/planner.py     # Agent 核心：多步工作流（规划/执行/汇总）
│   ├── rag/vector_rag.py    # RAG：知识库向量检索（Chroma + bge）
│   └── web/app.py           # Streamlit 界面
└── data/
    ├── 模拟企业数据.csv     # 示例数据
    ├── traces/              # 每次运行的 JSON 审计记录
    ├── evaluations/         # 评测数据集/结果预留目录
    └── 服装知识库.txt       # 知识库资料
```

## 企业数据字段

标准字段为：`日期、品类、销售额、销量、退货量、渠道`。接入层也会自动识别
`date/category/revenue/quantity/returns/channel`、`GMV`、`平台` 等常见别名。
每个已加载文件都会生成 SHA-256 指纹；任务完成后可在页面展开“证据链与评测明细”，
或直接查看 `data/traces/<run_id>.json`。

## 技术栈

Python · DeepSeek API · Streamlit · Pandas · Matplotlib · Chroma · bge-small-zh · Pydantic

## 免责声明

- 数据文件为演示数据，请替换为客户真实数据
- API Key 请放在 `.env`，不要提交到代码仓库
