from openai import OpenAI
import pandas as pd

client = OpenAI(
    api_key="sk-76c7bd4997134f4d9962cfa2de3d76f9",
    base_url="https://api.deepseek.com"
)

# 让用户输入要分析的品类
品类 = input("请输入要分析的品类（回车分析全部）: ")

df = pd.read_csv('店铺销售数据.csv')

if 品类:
    df = df[df['品类'] == 品类]
    if len(df) == 0:
        print(f"没有找到品类: {品类}")
        exit()

data_text = df.to_string()

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是服装数据分析师，严格依据数据回答。"},
        {"role": "user", "content": f"分析以下销售数据：\n{data_text}\n\n回答：\n1. 总销售额？\n2. 趋势是上升还是下降？\n3. 建议？"}
    ]
)

report = "===== AI 分析报告 =====\n\n"
report += response.choices[0].message.content

print(report)

# 自动保存报告
filename = f"分析报告_{品类 if 品类 else '全部'}.txt"
with open(filename, 'w', encoding='utf-8') as f:
    f.write(report)
print(f"\n📄 报告已保存到: {filename}")

