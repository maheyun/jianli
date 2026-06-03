# 项目三：各平台ROI预算重新分配方案

## 1. 项目概述

本项目旨在通过分析各平台（天猫、京东、得物、抖音）的投放效果，运用归因分析与边际效益模型，重构预算分配策略，在总预算不变的情况下实现全域ROI的显著提升。

## 2. 数据获取

### 数据库结构

#### `ad_campaigns`表
| 字段名 | 数据类型 | 描述 |
|-------|---------|------|
| `campaign_id` | INT | 广告活动ID |
| `platform` | VARCHAR(50) | 平台名称 |
| `campaign_date` | DATE | 活动日期 |
| `spend` | DECIMAL(10,2) | 投放花费 |
| `impressions` | INT | 曝光量 |
| `clicks` | INT | 点击量 |
| `conversions` | INT | 转化量 |
| `revenue` | DECIMAL(10,2) |  revenue |

#### `user_behavior`表
| 字段名 | 数据类型 | 描述 |
|-------|---------|------|
| `id` | INT | 行为ID |
| `user_id` | INT | 用户ID |
| `platform` | VARCHAR(50) | 平台名称 |
| `session_id` | VARCHAR(100) | 会话ID |
| `action` | VARCHAR(50) | 行为类型 |
| `create_time` | DATETIME | 行为时间 |

#### `attribution_data`表
| 字段名 | 数据类型 | 描述 |
|-------|---------|------|
| `id` | INT | 归因ID |
| `user_id` | INT | 用户ID |
| `touchpoint` | VARCHAR(50) | 接触点 |
| `platform` | VARCHAR(50) | 平台名称 |
| `event_time` | DATETIME | 事件时间 |
| `conversion_time` | DATETIME | 转化时间 |

### MySQL查询语句

```sql
-- 1. 各平台广告投放数据
SELECT 
    platform,
    campaign_id,
    SUM(spend) as total_spend,
    SUM(impressions) as total_impressions,
    SUM(clicks) as total_clicks,
    SUM(conversions) as total_conversions,
    SUM(revenue) as total_revenue
FROM 
    ad_campaigns
WHERE 
    campaign_date BETWEEN DATE_SUB(NOW(), INTERVAL 6 MONTH) AND NOW()
GROUP BY 
    platform, campaign_id;

-- 2. 各平台用户行为数据
SELECT 
    platform,
    user_id,
    COUNT(DISTINCT session_id) as session_count,
    COUNT(DISTINCT CASE WHEN action = 'view' THEN session_id END) as view_count,
    COUNT(DISTINCT CASE WHEN action = 'add_to_cart' THEN session_id END) as add_to_cart_count,
    COUNT(DISTINCT CASE WHEN action = 'place_order' THEN session_id END) as place_order_count,
    COUNT(DISTINCT CASE WHEN action = 'pay' THEN session_id END) as pay_count
FROM 
    user_behavior
WHERE 
    create_time BETWEEN DATE_SUB(NOW(), INTERVAL 6 MONTH) AND NOW()
GROUP BY 
    platform, user_id;

-- 3. 跨平台归因数据
SELECT 
    user_id,
    touchpoint,
    platform,
    event_time,
    conversion_time,
    DATEDIFF(conversion_time, event_time) as days_to_conversion
FROM 
    attribution_data
WHERE 
    conversion_time BETWEEN DATE_SUB(NOW(), INTERVAL 6 MONTH) AND NOW();
```

## 3. 数据分析

### Python代码

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pymysql

# 连接数据库
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='password',
    database='ecommerce'
)

# 1. 各平台广告投放数据
ad_campaigns_query = """
SELECT 
    platform,
    campaign_id,
    SUM(spend) as total_spend,
    SUM(impressions) as total_impressions,
    SUM(clicks) as total_clicks,
    SUM(conversions) as total_conversions,
    SUM(revenue) as total_revenue
FROM 
    ad_campaigns
WHERE 
    campaign_date BETWEEN DATE_SUB(NOW(), INTERVAL 6 MONTH) AND NOW()
GROUP BY 
    platform, campaign_id;
"""
ad_campaigns_df = pd.read_sql(ad_campaigns_query, conn)

# 2. 各平台用户行为数据
user_behavior_query = """
SELECT 
    platform,
    user_id,
    COUNT(DISTINCT session_id) as session_count,
    COUNT(DISTINCT CASE WHEN action = 'view' THEN session_id END) as view_count,
    COUNT(DISTINCT CASE WHEN action = 'add_to_cart' THEN session_id END) as add_to_cart_count,
    COUNT(DISTINCT CASE WHEN action = 'place_order' THEN session_id END) as place_order_count,
    COUNT(DISTINCT CASE WHEN action = 'pay' THEN session_id END) as pay_count
FROM 
    user_behavior
WHERE 
    create_time BETWEEN DATE_SUB(NOW(), INTERVAL 6 MONTH) AND NOW()
GROUP BY 
    platform, user_id;
"""
user_behavior_df = pd.read_sql(user_behavior_query, conn)

# 3. 跨平台归因数据
attribution_query = """
SELECT 
    user_id,
    touchpoint,
    platform,
    event_time,
    conversion_time,
    DATEDIFF(conversion_time, event_time) as days_to_conversion
FROM 
    attribution_data
WHERE 
    conversion_time BETWEEN DATE_SUB(NOW(), INTERVAL 6 MONTH) AND NOW();
"""
attribution_df = pd.read_sql(attribution_query, conn)

# 计算各平台ROI和其他关键指标
platform_metrics = ad_campaigns_df.groupby('platform').agg({
    'total_spend': 'sum',
    'total_impressions': 'sum',
    'total_clicks': 'sum',
    'total_conversions': 'sum',
    'total_revenue': 'sum'
}).reset_index()

platform_metrics['CTR'] = platform_metrics['total_clicks'] / platform_metrics['total_impressions']
platform_metrics['CVR'] = platform_metrics['total_conversions'] / platform_metrics['total_clicks']
platform_metrics['CPA'] = platform_metrics['total_spend'] / platform_metrics['total_conversions']
platform_metrics['ROI'] = platform_metrics['total_revenue'] / platform_metrics['total_spend']

# 四象限分析：流量成本-转化效率
platform_metrics['cost_per_click'] = platform_metrics['total_spend'] / platform_metrics['total_clicks']
platform_metrics['conversion_efficiency'] = platform_metrics['CVR'] * platform_metrics['ROI']

# 边际效益分析
def calculate_marginal_roi(spend, revenue):
    # 简化的边际效益计算
    marginal_roi = []
    for i in range(1, len(spend)):
        marginal_spend = spend[i] - spend[i-1]
        marginal_revenue = revenue[i] - revenue[i-1]
        if marginal_spend > 0:
            marginal_roi.append(marginal_revenue / marginal_spend)
        else:
            marginal_roi.append(0)
    return marginal_roi

# 按平台计算边际ROI
marginal_roi_data = []
for platform in platform_metrics['platform'].unique():
    platform_data = ad_campaigns_df[ad_campaigns_df['platform'] == platform].sort_values('total_spend')
    if len(platform_data) > 1:
        marginal_rois = calculate_marginal_roi(platform_data['total_spend'].values, platform_data['total_revenue'].values)
        marginal_roi_data.extend([(platform, roi) for roi in marginal_rois])

marginal_roi_df = pd.DataFrame(marginal_roi_data, columns=['platform', 'marginal_roi'])
average_marginal_roi = marginal_roi_df.groupby('platform')['marginal_roi'].mean().reset_index()

# 数据可视化
plt.figure(figsize=(15, 12))

# 1. 各平台ROI对比
plt.subplot(3, 2, 1)
plt.bar(platform_metrics['platform'], platform_metrics['ROI'])
plt.title('各平台ROI对比')
plt.ylabel('ROI')

# 2. 四象限分析
plt.subplot(3, 2, 2)
plt.scatter(platform_metrics['cost_per_click'], platform_metrics['conversion_efficiency'], s=100)
for i, platform in enumerate(platform_metrics['platform']):
    plt.annotate(platform, (platform_metrics['cost_per_click'][i], platform_metrics['conversion_efficiency'][i]))
plt.axvline(platform_metrics['cost_per_click'].mean(), color='r', linestyle='--')
plt.axhline(platform_metrics['conversion_efficiency'].mean(), color='r', linestyle='--')
plt.title('四象限分析：流量成本 vs 转化效率')
plt.xlabel('点击成本')
plt.ylabel('转化效率')

# 3. 各平台CPA对比
plt.subplot(3, 2, 3)
plt.bar(platform_metrics['platform'], platform_metrics['CPA'])
plt.title('各平台CPA对比')
plt.ylabel('CPA')

# 4. 各平台CTR对比
plt.subplot(3, 2, 4)
plt.bar(platform_metrics['platform'], platform_metrics['CTR'])
plt.title('各平台CTR对比')
plt.ylabel('CTR')

# 5. 边际ROI分析
plt.subplot(3, 2, 5)
plt.bar(average_marginal_roi['platform'], average_marginal_roi['marginal_roi'])
plt.title('各平台平均边际ROI')
plt.ylabel('边际ROI')

# 6. 预算分配建议
current_budget = platform_metrics['total_spend'].sum()
platform_metrics['current_budget_share'] = platform_metrics['total_spend'] / current_budget
platform_metrics['suggested_budget_share'] = platform_metrics['ROI'] / platform_metrics['ROI'].sum()
plt.subplot(3, 2, 6)
budget_df = platform_metrics.melt(id_vars=['platform'], value_vars=['current_budget_share', 'suggested_budget_share'], 
                                  var_name='budget_type', value_name='share')
sns.barplot(x='platform', y='share', hue='budget_type', data=budget_df)
plt.title('预算分配对比')
plt.ylabel('预算占比')

plt.tight_layout()
plt.savefig('各平台ROI预算重新分配分析.png')

# 关闭数据库连接
conn.close()

# 生成分析报告
with open('各平台ROI预算重新分配分析报告.md', 'w', encoding='utf-8') as f:
    f.write('# 各平台ROI预算重新分配分析报告\n\n')
    f.write('## 1. 投放现状\n')
    f.write(f'### 总预算: {current_budget:.2f}\n')
    f.write(f'### 总销售额: {platform_metrics["total_revenue"].sum():.2f}\n')
    f.write(f'### 全域ROI: {platform_metrics["total_revenue"].sum() / current_budget:.2f}\n\n')
    
    f.write('## 2. 各平台表现\n')
    for index, row in platform_metrics.iterrows():
        f.write(f'### {row["platform"]}:\n')
        f.write(f'- 投放花费: {row["total_spend"]:.2f}\n')
        f.write(f'- 销售额: {row["total_revenue"]:.2f}\n')
        f.write(f'- ROI: {row["ROI"]:.2f}\n')
        f.write(f'- CTR: {row["CTR"]:.2%}\n')
        f.write(f'- CVR: {row["CVR"]:.2%}\n')
        f.write(f'- CPA: {row["CPA"]:.2f}\n\n')
    
    f.write('## 3. 四象限分析\n')
    f.write('### 平台角色定位:\n')
    for index, row in platform_metrics.iterrows():
        if row['cost_per_click'] < platform_metrics['cost_per_click'].mean() and row['conversion_efficiency'] > platform_metrics['conversion_efficiency'].mean():
            role = '高效拉新场'
        elif row['cost_per_click'] < platform_metrics['cost_per_click'].mean() and row['conversion_efficiency'] < platform_metrics['conversion_efficiency'].mean():
            role = '低成本引流'
        elif row['cost_per_click'] > platform_metrics['cost_per_click'].mean() and row['conversion_efficiency'] > platform_metrics['conversion_efficiency'].mean():
            role = '高价值种草地'
        else:
            role = '需优化'
        f.write(f'- {row["platform"]}: {role}\n')
    
    f.write('\n## 4. 预算分配建议\n')
    f.write('### 当前预算分配:\n')
    for index, row in platform_metrics.iterrows():
        f.write(f'- {row["platform"]}: {row["current_budget_share"]:.2%}\n')
    
    f.write('\n### 建议预算分配:\n')
    for index, row in platform_metrics.iterrows():
        f.write(f'- {row["platform"]}: {row["suggested_budget_share"]:.2%}\n')
    
    f.write('\n## 5. 实施计划\n')
    f.write('1. 第一阶段: 将预算从低效渠道向高效渠道转移\n')
    f.write('2. 第二阶段: 建立"平台-阶段-目标"的动态预算分配策略\n')
    f.write('3. 第三阶段: 建立按月回顾的闭环监控机制\n\n')
    
    f.write('## 6. 预期效果\n')
    f.write('1. 全域营销ROI提升至1:2.5以上\n')
    f.write('2. 整体加购成本(CPA)降低15%以上\n')
    f.write('3. 高效渠道预算占比提升15%\n')
