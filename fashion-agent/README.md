# Fashion Agent｜服装经营与趋势分析 Agent

一个面向服装零售与电商经营场景的可追溯 AI 分析 Agent。

它不是把销售表格直接交给大模型总结，而是先由 AI 将问题拆成可执行计划，再调用确定性的本地工具完成数据计算、趋势检索和图表生成，最后基于真实执行结果生成带引用的分析报告。

```text
用户任务
   ↓
Planner：拆解分析步骤
   ↓
Executor：调用数据、预测、RAG、联网搜索等工具
   ↓
Evidence：记录数据来源与每一步结果
   ↓
Reporter：生成带步骤引用的经营分析报告
   ↓
Evaluator：检查执行成功率、结构、引用和数字忠实度
```

## 为什么做这个项目

传统的“上传 Excel → 大模型生成结论”存在几个明显问题：数字可能被误读、分析过程不可见、外部趋势与企业数据混在一起，最终也很难判断报告是否可靠。

Fashion Agent 将工作拆成三层：

- **AI 负责理解与规划**：根据任务选择需要执行的分析工具。
- **程序负责事实计算**：销售额、退货率、渠道分布和趋势预测由代码计算。
- **AI 负责有依据地表达**：报告只能使用工具返回的事实，并用 `[步骤N]`、`[知识库资料N]` 标注来源。

因此，它更接近一个轻量的行业分析工作台，而不是普通聊天机器人。

## 核心能力

### 1. 企业数据接入与治理

- 支持上传 CSV、XLSX、XLS，也可直接使用仓库内的模拟数据。
- 自动识别常见中英文字段，例如 `销售额 / revenue / GMV`、`渠道 / channel / 平台`。
- 接入时检查空值、类型错误、负数、退货量大于销量和重复行。
- 不修改原始文件，并为每个数据源生成 SHA-256 指纹和唯一来源 ID。

### 2. Planner–Executor 多步 Agent

- Planner 使用结构化 JSON 将自然语言任务拆成步骤。
- Pydantic 校验工具名称、参数和计划结构，不合格时自动重试。
- Executor 按顺序执行工具；单步失败会记录原因，不会伪造结果。
- Reporter 只基于实际执行结果生成最终报告。

当前工具包括：

| 工具 | 作用 |
|---|---|
| `get_sales` | 计算指定品类总销售额 |
| `get_return_rate` | 计算销量、退货量及退货率 |
| `get_channel_compare` | 对比不同渠道的销售表现 |
| `make_chart` | 生成品类销量趋势图 |
| `predict_trend` | 使用历史销量进行短期基线外推 |
| `search_knowledge` | 检索本地服装行业知识库 |
| `search_web` | 搜索外部行业趋势与市场动态 |
| `save_report` | 保存最终分析报告 |

### 3. 行业知识库与 RAG

- 使用 Chroma 持久化本地向量库。
- 支持从界面增量上传 TXT、Markdown 行业资料。
- 知识块使用内容哈希同步，资料新增、修改和删除都能反映到向量库。
- 本地已缓存 `bge-small-zh` 时使用语义检索；模型不可用时自动退回离线字符检索。
- 主 Agent 直接引用检索到的原文片段，避免再调用一次模型造成信息漂移。

### 4. 可追溯分析与自动评测

每次运行都会生成独立的 `run_id`，并保存：

- 数据源名称、字段映射、质量检查结果和文件指纹。
- AI 生成的任务计划。
- 每一步的工具、参数、输出、状态和耗时。
- 最终报告及其 SHA-256 哈希。
- 错误信息和自动评测结果。

内置评测器无需再次调用外部模型，可重复检查：

- 执行成功率。
- 报告结构覆盖率。
- 步骤与知识库引用覆盖率。
- 报告数字能否在工具结果中找到依据。

### 5. 可视化工作台

- 上传企业数据并查看可用品类。
- 用自然语言下达分析任务。
- 在简洁模式查看最终报告，或在详细模式检查规划与执行过程。
- 管理本地知识库和常用任务。
- 查看运行 ID、证据链与评测明细。
- 下载当前报告并回看本次会话的历史结果。

## 示例任务

```text
分析外套和衬衫两个品类的销售表现，对比销售额、退货率和渠道分布，
结合本地知识库中的秋季趋势资料生成趋势图，并给出下一阶段备货建议。
```

Agent 会根据任务自动决定调用哪些工具，而不是依赖一套写死的展示流程。

## 数据格式

标准字段如下：

| 字段 | 含义 | 示例 |
|---|---|---|
| 日期 | 交易或统计日期 | `2026-08-01` |
| 品类 | 商品品类 | `外套` |
| 销售额 | 对应日期和品类的销售金额 | `12800` |
| 销量 | 销售件数 | `80` |
| 退货量 | 退货件数 | `6` |
| 渠道 | 销售渠道 | `抖音`、`淘宝`、`门店` |

系统也能自动映射 `date / category / revenue / quantity / returns / channel` 等常见字段。若企业导出表使用其他列名，可以在调用接入层时传入显式字段映射。

## 快速开始

当前工程化版本位于仓库的 `fashion-agent/` 子目录；仓库根目录中的其他脚本是项目早期的探索原型。建议从该子目录启动和二次开发。

### 环境要求

- Python 3.11 或更高版本。
- 一个兼容 OpenAI Chat Completions 的 DeepSeek API Key。
- 首次使用语义检索时，需要提前准备 `BAAI/bge-small-zh-v1.5` 模型缓存；没有缓存也可以使用离线兜底检索。

### 1. 安装

```bash
git clone https://github.com/QR777-UI/fashion-ai-agent.git
cd fashion-ai-agent/fashion-agent

python -m venv .venv
```

激活虚拟环境：

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

如需读取 Excel，请按文件类型安装对应引擎：

```bash
pip install openpyxl   # XLSX
pip install xlrd       # XLS
```

### 2. 配置模型

复制环境变量模板：

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

`.env` 已被 Git 忽略，请勿把真实密钥提交到仓库。

### 3. 启动

```bash
python main.py
```

也可以直接运行：

```bash
streamlit run src/web/app.py
```

浏览器访问 [http://localhost:8501](http://localhost:8501)。

## Docker 部署

```bash
cp .env.example .env
# 在 .env 中填写 API Key
docker compose up -d --build
```

启动后访问 [http://localhost:8501](http://localhost:8501)。`data/` 与 `charts/` 会挂载到宿主机，知识库、运行记录和图表不会随容器重建而丢失。

停止服务：

```bash
docker compose down
```

## 测试

测试默认 Mock 外部模型和联网调用，不消耗 API 额度：

```bash
python -m pytest tests -q
```

当前测试覆盖：

- 数据加载、字段映射和数据质量校验。
- Planner 结构校验、失败重试和异常退出。
- 本地分析工具与趋势预测。
- RAG 工具注册、检索调用和降级行为。
- 联网搜索失败时的容错。
- 任务调度、审计记录与自动评测。

## 项目结构

```text
fashion-ai-agent/fashion-agent/
├── main.py                       # Streamlit 一键启动入口
├── config.py                     # 模型、路径和运行参数配置
├── requirements.txt              # Python 依赖
├── Dockerfile
├── docker-compose.yml
├── data/
│   ├── 模拟企业数据.csv           # 开箱即用的演示数据
│   ├── 店铺销售数据.csv           # 销售数据示例
│   ├── 服装知识库.txt             # 本地行业知识库
│   ├── traces/                    # 运行证据链，执行时生成
│   └── evaluations/               # 自动评测结果，执行时生成
├── src/
│   ├── agent/planner.py           # Planner、Executor、Reporter 与工具注册
│   ├── data/ingestion.py          # 企业数据接入、映射、校验与指纹
│   ├── rag/vector_rag.py          # Chroma RAG 与离线检索降级
│   ├── observability/trace.py     # 运行追踪与报告哈希
│   ├── evaluation/evaluator.py    # 无模型自动评测
│   └── web/app.py                 # Streamlit 工作台
└── tests/                         # 离线自动化测试
```

## 技术栈

| 层级 | 技术 |
|---|---|
| AI 与结构化输出 | DeepSeek API、OpenAI Python SDK、Pydantic |
| 数据分析 | Pandas、NumPy、Matplotlib |
| 知识检索 | ChromaDB、FastEmbed、bge-small-zh |
| 外部信息 | DuckDuckGo Search (`ddgs`) |
| 产品界面 | Streamlit |
| 质量保障 | Pytest、自定义 Trace 与 Evaluator |
| 部署 | Docker、Docker Compose |

## 当前边界

- 当前趋势预测是线性外推或近三日均值的基线模型，适合演示分析流程，不应直接作为采购、库存或财务决策的唯一依据。
- 外部搜索结果可能存在误差，最终报告仍需结合来源页面与业务人员判断。
- 当前数据模型以品类级销售、销量、退货和渠道分析为主；SKU、库存、毛利、营销费用等指标尚未纳入标准字段。
- 项目目前是可本地运行的原型，尚未包含用户权限、多租户隔离、任务队列和生产级监控。

## 后续方向

- 扩展 SKU、库存、毛利和广告投放数据模型。
- 增加可配置指标与企业字段映射界面。
- 引入更可靠的时间序列预测和回测机制。
- 为外部趋势信息增加来源筛选、时间范围和引用快照。
- 增加多任务队列、权限体系和团队协作能力。

## 数据与安全说明

- 仓库内数据仅用于演示，请勿提交真实客户数据、个人信息或商业机密。
- API Key 仅保存在本地 `.env` 中。
- 使用企业数据前，请确认已获得相应的数据处理权限。
- AI 输出应由业务负责人复核后再用于实际经营决策。
