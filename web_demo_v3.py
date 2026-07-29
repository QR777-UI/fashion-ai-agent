import streamlit as st
from openai import OpenAI
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']

client = OpenAI(
    api_key="sk-76c7bd4997134f4d9962cfa2de3d76f9",
    base_url="https://api.deepseek.com"
)

st.set_page_config(page_title="服装趋势分析 Agent", layout="centered")
st.title("🧥 服装趋势分析 Agent v3.0")
st.write("上传你的销售数据，自由提问 AI 分析")

# 上传数据
上传的文件 = st.file_uploader("上传你的 CSV 或 Excel 文件", type=["csv", "xlsx"])

if 上传的文件:
    if 上传的文件.name.endswith('.csv'):
        df = pd.read_csv(上传的文件)
    else:
        df = pd.read_excel(上传的文件)

    st.success(f"已读取 {len(df)} 条数据")
    with st.expander("查看原始数据"):
        st.dataframe(df)

    # 选择品类
    品类列表 = df['品类'].unique() if '品类' in df.columns else []
    if len(品类列表) > 0:
        品类 = st.selectbox("选择要分析的品类", 品类列表)
        品类数据 = df[df['品类'] == 品类]

        总销售额 = 品类数据['销售额'].sum()

        if st.button("📊 分析这个品类"):
            with st.spinner("AI 分析中..."):
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.plot(品类数据['日期'], 品类数据['销售额'] if '日期' in 品类数据.columns else range(len(品类数据)), 
                       marker='o', linewidth=2, color='#FF6B6B')
                ax.set_title(f'{品类} 趋势', fontweight='bold')
                ax.grid(axis='y', alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

                res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一名专业的服装数据分析师，基于数据给出客观分析。"},
                        {"role": "user", "content": f"分析数据：{品类数据.to_string()}\n总销售额：¥{总销售额}\n请给出趋势判断和1条建议"}
                    ]
                )
                st.subheader("📈 AI 分析")
                st.write(res.choices[0].message.content)

    # 自由提问
    st.markdown("---")
    st.subheader("💬 自由提问")
    question = st.text_input("向 AI 提问你的数据（比如：哪个品类利润最高？）")
    if question:
        with st.spinner("AI 思考中..."):
            res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一名服装数据专家，基于以下数据回答用户的问题。"},
                    {"role": "user", "content": f"数据表：\n{df.to_string()}\n\n问题：{question}"}
                ]
            )
            st.write(res.choices[0].message.content)
