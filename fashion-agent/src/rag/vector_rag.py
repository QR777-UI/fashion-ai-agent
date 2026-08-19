# -*- coding: utf-8 -*-
r"""
src/rag/vector_rag.py —— 向量数据库版 RAG（正式版模块）
=====================================================
向量数据库：Chroma（本地轻量，负责存向量 + 按相似度查）
嵌入模型：两种可选
  - 语义嵌入（推荐）：BAAI/bge-small-zh 中文模型，按"意思"找
  - 手写嵌入（兜底）  ：离线可用，按"字"找

工程化改造（2026-08-15）：
  知识库路径 / 向量库路径 / 密钥 全部走 config.py，不硬编码。
  对外暴露 检索知识(问题) 与 RAG回答(问题) 供界面/Agent 调用。

运行：cd fashion-agent && python -m src.rag.vector_rag（自由提问演示）
"""

import os, re, glob
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from openai import OpenAI

import config

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

# ============================================================
# ① 切块
# ============================================================
def 切块(知识库文件):
    with open(知识库文件, 'r', encoding='utf-8') as f:
        text = f.read()
    blocks = re.split(r'\n(?=【)', text)
    return [b.strip() for b in blocks if b.strip()]

知识块列表 = 切块(config.KNOWLEDGE_FILE)
print(f"知识库共 {len(知识块列表)} 块：{config.KNOWLEDGE_FILE}")

# ============================================================
# ② 两种嵌入函数
# ============================================================
def bigrams(text):
    text = text.lower()
    return [text[i:i+2] for i in range(len(text) - 1)]

class 手写嵌入(EmbeddingFunction):
    """兜底嵌入：离线可用，按"字"匹配"""
    def __init__(self, corpus):
        vocab = {}
        for doc in corpus:
            for bg in bigrams(doc):
                if bg not in vocab:
                    vocab[bg] = len(vocab)
        self._vocab, self._dim = vocab, len(vocab)

    def _vector(self, text):
        vec = [0.0] * self._dim
        for bg in bigrams(text):
            if bg in self._vocab:
                vec[self._vocab[bg]] += 1
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm for v in vec] if norm > 0 else vec

    def __call__(self, input: Documents) -> Embeddings:
        if isinstance(input, str):
            input = [input]
        return [self._vector(t) for t in input]

class 语义嵌入(EmbeddingFunction):
    """推荐嵌入：BAAI/bge-small-zh，按"意思"匹配"""
    def __init__(self):
        from fastembed import TextEmbedding
        self._model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")

    def __call__(self, input: Documents) -> Embeddings:
        if isinstance(input, str):
            input = [input]
        return [v.tolist() for v in self._model.embed(input)]

# 检测语义模型缓存是否完整
语义缓存 = os.path.expandvars(r"%LOCALAPPDATA%\Temp\fastembed_cache")
候选模式 = [
    os.path.join(语义缓存, "models--Qdrant--bge-small-zh-v1.5", "snapshots", "*", "model_optimized.onnx"),
    os.path.join(语义缓存, "fast-bge-small-zh-v1.5", "model_optimized.onnx"),
]
语义就绪 = any(
    os.path.exists(p) and os.path.getsize(p) > 1_000_000
    for 模式 in 候选模式 for p in glob.glob(模式)
)

if 语义就绪:
    print("使用语义嵌入 bge-small-zh（按意思找）")
    嵌入模型 = 语义嵌入()
    嵌入类型 = "semantic"
else:
    print("语义模型未下载，暂时用手写嵌入（按字找）；下载后自动切换语义嵌入")
    嵌入模型 = 手写嵌入(知识块列表)
    嵌入类型 = "lexical"

# ============================================================
# ③ 向量数据库（Chroma）
# ============================================================
print("连接向量数据库...")
db = chromadb.PersistentClient(path=os.path.join(config.BASE_DIR, "data", "向量库"))
集合 = db.get_or_create_collection(f"fashion_kb_{嵌入类型}", embedding_function=嵌入模型)

# ============================================================
# ④ 入库（可随时更新：按内容哈希同步，新增/修改/删除都会反映）
# ============================================================
import hashlib

def 块id(block: str) -> str:
    """用内容哈希当 id：内容变了 id 就变，天然支持"改了就刷新" """
    return hashlib.md5(block.encode("utf-8")).hexdigest()[:12]

def 同步知识库() -> dict:
    """把知识块列表和向量库对齐：
       - 新块 → 入库
       - 内容变了的块 → 旧 id 删除、新 id 写入（等价刷新）
       - 库里存在但已不在列表的块 → 删除
       返回 {新增, 删除}"""
    new_ids = [块id(b) for b in 知识块列表]
    existing = set(集合.get()["ids"])
    # 计算要写入的：列表里不在库中的（含内容已变的块）
    to_write = [(i, b) for i, b in zip(new_ids, 知识块列表) if i not in existing]
    if to_write:
        集合.upsert(ids=[i for i, _ in to_write], documents=[b for _, b in to_write])
    # 计算要删除的：库里有但列表里没有的
    to_remove = existing - set(new_ids)
    if to_remove:
        集合.delete(ids=list(to_remove))
    return {"新增": len(to_write), "删除": len(to_remove)}

def 添加文档(文本: str) -> int:
    """往知识库增量添加新资料（可随时调用，界面/脚本都行）：
       文本 → 切块 → 入库，返回新增块数"""
    blocks = 切块文本(文本)
    ids = [块id(b) for b in blocks]
    知识块列表.extend(blocks)
    集合.upsert(ids=ids, documents=blocks)
    return len(blocks)

def 切块文本(文本: str):
    """通用切块：优先按【标题】切；没有标题标记就按空行分段"""
    blocks = re.split(r'\n(?=【)', 文本)
    if len(blocks) <= 1:
        blocks = [p.strip() for p in 文本.split('\n\n') if p.strip()]
    return [b.strip() for b in blocks if b.strip()]

def 获取知识库概况() -> dict:
    """当前知识库统计（界面展示用）"""
    return {"块数": len(知识块列表), "库内条数": 集合.count()}

# 启动时同步一次（把 config.KNOWLEDGE_FILE 的最新内容对齐到向量库）
print("同步知识库...")
_同步结果 = 同步知识库()
print(f"同步完成：新增 {_同步结果['新增']} 块，删除 {_同步结果['删除']} 块，当前库内 {集合.count()} 条")

# ============================================================
# ⑤ 检索 + 回答（对外接口）
# ============================================================
def _检索文档(问题: str, top_k: int = 3) -> list[str]:
    """只做向量检索，不调用大模型。主 Agent 用它获取可追溯的原始知识。"""
    问题 = str(问题).strip()
    if not 问题:
        raise ValueError("检索问题不能为空")
    if top_k < 1:
        raise ValueError("top_k 必须大于等于 1")
    count = 集合.count()
    if count == 0:
        return []
    hits = 集合.query(query_texts=[问题], n_results=min(top_k, count))
    return hits.get("documents", [[]])[0]


def 检索知识(问题: str, top_k: int = 3) -> str:
    """返回知识库中最相关的原文片段，供 Agent 与销售数据一起汇总。"""
    docs = _检索文档(问题, top_k)
    if not docs:
        return f"知识库中未检索到与「{问题}」相关的资料"
    return "\n\n".join(f"[知识库资料{i}]\n{doc}" for i, doc in enumerate(docs, 1))


def RAG回答(问题, top_k=2):
    docs = _检索文档(问题, top_k)
    if not docs:
        return "知识库中没有可用于回答该问题的资料"
    参考材料 = "\n\n".join(f"[资料{i+1}]\n{d}" for i, d in enumerate(docs))
    res = client.chat.completions.create(
        model=config.MODEL_NAME,
        messages=[
            {"role": "system", "content": "你是服装顾问。只能根据【参考资料】回答用户问题，资料里没有的内容要明确说'资料里没有提到'，不要编造。"},
            {"role": "user", "content": f"【参考资料】\n{参考材料}\n\n【问题】{问题}"},
        ],
    )
    return res.choices[0].message.content

# ============================================================
# 主流程（自由提问演示）
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("自由提问环节（输入 exit 退出）")
    print("=" * 55)
    while True:
        q = input("\n你的问题 > ").strip()
        if q.lower() in ("exit", "quit", "退出"):
            print("再见！")
            break
        if not q:
            continue
        print("\n向量检索中...")
        print(RAG回答(q))
