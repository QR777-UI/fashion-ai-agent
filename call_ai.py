from openai import OpenAI

# 把你的密钥贴到下面这行的 sk-xxx 位置
client = OpenAI(
    api_key="sk-76c7bd4997134f4d9962cfa2de3d76f9",
    base_url="https://api.deepseek.com"
)

# 让 AI 分析服装数据
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个专业的男装潮流分析师。"},
        {"role": "user", "content": "2026年夏季男装衬衫的流行趋势是什么？给出3个关键趋势。"}
    ]
)

print(response.choices[0].message.content)
