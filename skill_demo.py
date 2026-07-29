from openai import OpenAI
import pandas as pd
import json

client = OpenAI(
    api_key="sk-76c7bd4997134f4d9962cfa2de3d76f9",
    base_url="https://api.deepseek.com"
)

df = pd.read_csv('模拟企业数据.csv')
可用品类 = df['品类'].unique().tolist()  # ['外套', 'T恤', '裤子', '衬衫']

def get_sales(category):
    if category not in 可用品类:
        return f"错误：没有'{category}'这个品类，可用品类有：{可用品类}"
    data = df[df['品类'] == category]
    return f"{category}总销售额: ¥{data['销售额'].sum():,}"

def get_return_rate(category):
    if category not in 可用品类:
        return f"错误：没有'{category}'这个品类，可用品类有：{可用品类}"
    data = df[df['品类'] == category]
    rate = data['退货量'].sum() / data['销量'].sum() * 100
    return f"{category}退货率: {rate:.1f}% (退货{data['退货量'].sum()}件/总销{data['销量'].sum()}件)"

def get_channel_compare(category):
    if category not in 可用品类:
        return f"错误：没有'{category}'这个品类，可用品类有：{可用品类}"
    data = df[df['品类'] == category]
    channels = data.groupby('渠道')['销售额'].sum()
    return f"{category}渠道分布:\n{channels.to_string()}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_sales",
            "description": f"查某个品类的总销售额。可用的品类：{可用品类}",
            "parameters": {"type": "object", "properties": {"category": {"type": "string", "description": f"品类名称，只能是以下几个之一：{可用品类}"}}, "required": ["category"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_return_rate",
            "description": f"查某个品类的退货率。可用的品类：{可用品类}",
            "parameters": {"type": "object", "properties": {"category": {"type": "string", "description": f"品类名称，只能是以下几个之一：{可用品类}"}}, "required": ["category"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_channel_compare",
            "description": f"查某个品类在不同渠道的销售对比。可用的品类：{可用品类}",
            "parameters": {"type": "object", "properties": {"category": {"type": "string", "description": f"品类名称，只能是以下几个之一：{可用品类}"}}, "required": ["category"]}
        }
    }
]

skills = {
    "get_sales": get_sales,
    "get_return_rate": get_return_rate,
    "get_channel_compare": get_channel_compare
}

print("=" * 40)
print("  Agent Skill Calling v2（带验证）")
print(f"  可用品类: {可用品类}")
print("=" * 40)

question = input("\n请输入问题\n> ")

messages = [
    {"role": "system", "content": f"你是服装数据分析助手。数据中有以下品类：{可用品类}。调用技能时category参数只能从这些里面选，不要编造品类名称。"},
    {"role": "user", "content": question}
]

print("\n🔄 AI 思考中...")
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,
    tool_choice="auto"
)

msg = response.choices[0].message

if msg.tool_calls:
    for tc in msg.tool_calls:
        name = tc.function.name
        args = json.loads(tc.function.arguments)
        print(f"🔧 AI 调用了: {name}(参数: {args})")
        result = skills[name](**args)
        print(f"✅ 返回: {result}")
        messages.append(msg)
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    final = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="none"
    )
    print(f"\n📝 AI 回答:\n{final.choices[0].message.content}")
else:
    print(f"\n📝 AI 回答:\n{msg.content}")
