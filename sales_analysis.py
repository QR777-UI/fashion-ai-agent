import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# 解决中文显示问题
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']

# 读取 Excel 数据
df = pd.read_excel('店铺销售数据.xlsx')

# 看看数据长什么样
print("===== 数据概览 =====")
print(f"共 {len(df)} 条记录")
print(f"品类: {df['品类'].unique()}")
print()

# 每个品类的总销售额
print("===== 各品类总销售额(元) =====")
total = df.groupby('品类')['销售额'].sum().sort_values(ascending=False)
print(total)
print()

# 每个品类的总销量
print("===== 各品类总销量(件) =====")
count = df.groupby('品类')['销量'].sum().sort_values(ascending=False)
print(count)

# 画柱状图
plt.figure(figsize=(8, 5))
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
bars = plt.bar(total.index, total.values, color=colors)

# 在柱子上标数字
for bar, val in zip(bars, total.values):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1000,
             f'¥{val:,.0f}', ha='center', fontsize=11)

plt.title('各品类总销售额对比', fontsize=14, fontweight='bold')
plt.xlabel('品类')
plt.ylabel('销售额(元)')
plt.grid(axis='y', alpha=0.3)

# 保存图片
plt.savefig('品类销售额对比图.png', dpi=150, bbox_inches='tight')
print('\n✅ 分析完成，图表已保存为: 品类销售额对比图.png')
