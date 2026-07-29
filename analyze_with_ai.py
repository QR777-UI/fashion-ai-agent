from openai import OpenAI
import pandas as pd

client = OpenAI(
    api_key="sk-76c7bd4997134f4d9962cfa2de3d76f9",
    base_url="https://api.deepseek.com"
)

# 读销售数据
df = pd.read_csv('店铺销售数据.csv')
data_text = df.to_string()

# 把数据发给 AI 分析
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个服装行业的数据分析师。"},
        {"role": "user", "content": f"以下是某服装品牌的销售数据，请分析：\n1. 哪个品类表现最好？\n2. 有什么异常？\n3. 给3条经营建议\n\n{data_text}"}
    ]
)

print(response.choices[0].message.content)
