import streamlit as st
from openai import OpenAI
import pandas as pd

client = OpenAI(
    api_key="sk-76c7bd4997134f4d9962cfa2de3d76f9", 
    base_url="https://api.deepseek.com"
)

st.set_page_config(page_title="服装趋势分析 Agent v4", layout="centered")
st.title("🧥 服装趋势分析 Agent v4.0")
st.write("上传你的销售数据，AI 结合市场趋势给出完整分析")

# 读取市场趋势
with open('市场趋势数据.txt', 'r', encoding='utf-8') as f:
    市场趋势 = f.read()

上传的文件 = st.file_uploader("上传你的 CSV 或 Excel 文件", type=["csv", "xlsx"])

if 上传的文件:
    if 上传的文件.name.endswith('.csv'):
        df = pd.read_csv(上传的文件)
    else:
        df = pd.read_excel(上传的文件)

    st.success(f"已读取 {len(df)} 条数据")
    with st.expander("查看原始数据"):
        st.dataframe(df)

    # 菜单选择
    分析模式 = st.radio("分析模式", [
        "📊 按品类分析",
        "🔍 自由提问",
        "📈 数据+趋势综合分析"
    ])

    if 分析模式 == "📊 按品类分析":
        品类列表 = df['品类'].unique() if '品类' in df.columns else []
        if len(品类列表) > 0:
            品类 = st.selectbox("选择品类", 品类列表)
            if st.button("分析"):
                with st.spinner("分析中..."):
                    品类数据 = df[df['品类'] == 品类]
                    res = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "你是一名服装数据分析师。"},
                            {"role": "user", "content": f"数据：{品类数据.to_string()}\n\n分析销售趋势并给出建议"}
                        ]
                    )
                    st.write(res.choices[0].message.content)

    elif 分析模式 == "🔍 自由提问":
        question = st.text_input("向 AI 提问你的数据")
        if question:
            with st.spinner("思考中..."):
                res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一名数据专家。"},
                        {"role": "user", "content": f"数据：{df.to_string()}\n\n问题：{question}"}
                    ]
                )
                st.write(res.choices[0].message.content)

    elif 分析模式 == "📈 数据+趋势综合分析":
        品类列表 = df['品类'].unique() if '品类' in df.columns else []
        if len(品类列表) > 0 and st.button("生成全品类综合分析"):
            with st.spinner("正在整合数据与市场趋势..."):
                for 品类 in 品类列表:
                    品类数据 = df[df['品类'] == 品类]
                    总销售额 = 品类数据['销售额'].sum()

                    res = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "你是一名服装行业资深顾问。"},
                            {"role": "user", "content": f"""
【内部销售数据】
品类：{品类}
总销售额：¥{总销售额:,}
明细：{品类数据.to_string()}

【外部市场趋势】
{市场趋势}

请结合销售数据和市场趋势，给出：
1. 该品类当前表现如何？
2. 市场趋势对该品类意味着什么机会或风险？
3. 具体行动建议
"""}
                    ]
                    )
                    st.subheader(f"📌 {品类}")
                    st.write(res.choices[0].message.content)
