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
st.title("🧥 服装趋势分析 Agent")
st.write("输入品类名称，AI 自动分析销售数据并预测趋势")

品类 = st.text_input("请输入要分析的品类（如：外套、T恤、裤子、衬衫）")

if 品类 and st.button("开始分析"):
    with st.spinner("正在分析中..."):
        # 读数据
        df = pd.read_csv('店铺销售数据.csv')
        品类数据 = df[df['品类'] == 品类]
        if len(品类数据) == 0:
            st.error(f"未找到品类: {品类}")
            st.stop()

        总销售额 = 品类数据['销售额'].sum()

        # 画图
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(品类数据['日期'], 品类数据['销售额'], marker='o', linewidth=2, color='#FF6B6B')
        ax.set_title(f'{品类} 销售额趋势', fontweight='bold')
        ax.tick_params(axis='x', rotation=30)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)

        # AI 分析
        res = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一名服装数据分析师。"},
                {"role": "user", "content": f"分析：{品类数据.to_string()}\n\n总销售额:¥{总销售额}\n给出趋势判断和1条建议"}
            ]
        )
        st.subheader("📈 AI 分析报告")
        st.write(res.choices[0].message.content)
