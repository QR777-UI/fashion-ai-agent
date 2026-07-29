from openai import OpenAI
import pandas as pd
from datetime import datetime

client = OpenAI(
    api_key="sk-76c7bd4997134f4d9962cfa2de3d76f9",
    base_url="https://api.deepseek.com"
)

print("=" * 40)
print("  服装趋势预测 Agent v1.0")
print("=" * 40)

品类 = input("\n请输入要分析的品类: ")

# 1. 先算数据
df = pd.read_csv('店铺销售数据.csv')
品类数据 = df[df['品类'] == 品类]

if len(品类数据) == 0:
    print(f"未找到品类: {品类}")
    exit()

总销售额 = 品类数据['销售额'].sum()
总销量 = 品类数据['销量'].sum()
平均单价 = 品类数据['单价'].mean()

data_summary = f"品类:{品类}, 总销售额:¥{总销售额}, 总销量:{总销量}件, 平均单价:¥{平均单价}"

# 2. 让 AI 做两份分析
print("\n🔄 AI 正在分析销售数据...")
res1 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一名服装数据分析师，严格依据数据回答。"},
        {"role": "user", "content": f"分析数据：{品类数据.to_string()}\n\n回答：\n1. 销售趋势（上升/下降）？\n2. 最高最低分别是哪天？\n3. 一条经营建议"}
    ]
)

print("🔄 AI 正在预测未来趋势...")
res2 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一名男装潮流预测专家。"},
        {"role": "user", "content": f"针对{品类}品类，2026年秋季的流行趋势是什么？给出3个关键方向。"}
    ]
)

# 3. 生成完整报告
报告 = f"""
================================
服装趋势预测报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
品类: {品类}
================================

📊 数据概览
━━━━━━━━━━━━━━━━━━━━━━━━━━━
总销售额: ¥{总销售额:,}
总销量: {总销量} 件
平均单价: ¥{平均单价:.0f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 销售数据分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━
{res1.choices[0].message.content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔮 未来趋势预测
━━━━━━━━━━━━━━━━━━━━━━━━━━━
{res2.choices[0].message.content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

print(报告)

filename = f"趋势报告_{品类}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
with open(filename, 'w', encoding='utf-8') as f:
    f.write(报告)
print(f"📄 报告已保存: {filename}")
