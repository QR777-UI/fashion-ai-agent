from openai import OpenAI
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']

client = OpenAI(
    api_key="sk-76c7bd4997134f4d9962cfa2de3d76f9",
    base_url="https://api.deepseek.com"
)

print("=" * 40)
print("  服装趋势预测 Agent v2.0")
print("=" * 40)

品类 = input("\n请输入要分析的品类: ")

df = pd.read_csv('店铺销售数据.csv')
品类数据 = df[df['品类'] == 品类]

if len(品类数据) == 0:
    print(f"未找到品类: {品类}")
    exit()

总销售额 = 品类数据['销售额'].sum()
总销量 = 品类数据['销量'].sum()

# 画趋势图
plt.figure(figsize=(8, 4))
plt.plot(品类数据['日期'], 品类数据['销售额'], marker='o', linewidth=2, color='#FF6B6B')
plt.title(f'{品类} 销售额趋势', fontsize=13, fontweight='bold')
plt.xlabel('日期')
plt.ylabel('销售额(元)')
plt.xticks(rotation=30)
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
chart_file = f'{品类}_趋势图.png'
plt.savefig(chart_file, dpi=150)
plt.close()

print(f"\n📊 趋势图已生成: {chart_file}")

# AI 分析
print("🔄 AI 正在分析...")
res1 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一名服装数据分析师，严格依据数据回答。"},
        {"role": "user", "content": f"分析数据：{品类数据.to_string()}\n\n回答：\n1. 销售趋势？\n2. 最高最低点？\n3. 一条建议"}
    ]
)

res2 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一名男装潮流预测专家。"},
        {"role": "user", "content": f"针对{品类}品类，2026年秋季的流行趋势是什么？给出3个关键方向。"}
    ]
)

报告 = f"""
================================
服装趋势预测报告 v2.0
品类: {品类}    时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
================================

📊 数据概览
总销售额: ¥{总销售额:,}
总销量: {总销量} 件

📈 数据分析
{res1.choices[0].message.content}

🔮 趋势预测
{res2.choices[0].message.content}

📎 趋势图已保存: {品类}_趋势图.png
"""

print(报告)

report_file = f'趋势报告_{品类}.txt'
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(报告)
print(f"📄 报告已保存: {report_file}")
