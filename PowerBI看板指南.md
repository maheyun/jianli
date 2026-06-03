# Power BI 看板实战指南 — 跃动体育四个项目的仪表盘方案

> 本文档告诉你：四个分析项目分别应该搭建什么样的 Power BI 看板，
> 每个看板包含哪些图表、需要什么 DAX 公式、数据模型怎么设计。

---

## 0. 环境准备

### 0.1 Power BI 连接 SQLite

Power BI 不能直接连 SQLite。需要先安装 ODBC 驱动：

```bash
# 1. 下载安装: http://www.ch-werner.de/sqliteodbc/
# 2. 安装后在 Power BI 中:
#    获取数据 → ODBC → 选择 "SQLite3 ODBC Driver"
#    连接字符串: DRIVER=SQLite3 ODBC Driver;Database=D:\简历\项目一\ecommerce_ops.db
```

**推荐方案（更简单）：** 先用 Python 把 SQLite 数据导出为 CSV，Power BI 直接读 CSV：
```python
import sqlite3, pandas as pd
conn = sqlite3.connect('ecommerce_ops.db')
for table in ['user_behavior', 'orders']:
    pd.read_sql(f'SELECT * FROM {table}', conn).to_csv(f'{table}.csv', index=False)
```

或者直接用 MySQL 版数据（如果你已运行 `mysql_setup.py`），Power BI 原生支持 MySQL 连接：
```
获取数据 → MySQL 数据库 → localhost:3306 → ecommerce_analysis → 选择表
```

### 0.2 Python vs Power BI 对照表

| 你学过的 Python 写法 | Power BI 等价操作 | 用途 |
|---------------------|------------------|------|
| `df.groupby('date').agg(...)` | 拖日期到轴、拖指标到值 | 按日期汇总 |
| `df['ROI'] = revenue/spend` | `ROI = DIVIDE(SUM(revenue), SUM(spend))` | 计算派生指标 |
| `np.select(conditions, choices)` | `SWITCH(TRUE(), ...)` | 条件分层 |
| `pd.qcut(series, 5)` | `PERCENTILE.INC()` + `SWITCH()` | 分箱打分 |
| `stats.chi2_contingency()` | Power BI 做不了，需 Python 先算好 | 统计检验 |
| `sns.barplot()` | 堆积柱形图 / 簇状柱形图 | 分类对比 |
| `sns.lineplot()` | 折线图 | 趋势展示 |
| `plt.pie()` | 饼图 / 环形图 | 占比分布 |
| `ax.scatter()` | 散点图 | 四象限分析 |
| `sns.heatmap()` | 矩阵 | 相关性热力图 |

---

## 1. 项目一：日常运营看板（运营部大屏幕）

### 1.1 看板目标
每天早上 9 点运营部早会，刘总监站在大屏幕前过数据。需要一张图看清昨日 + 近 7 天的核心指标。

### 1.2 数据模型

```
user_behavior          orders
─────────────          ──────
id                     order_id
user_id ────────────── user_id   (一对多关系)
action                 amount
product_id             order_status
create_time            create_time
```

在 Power BI 中建立关系：`user_behavior[user_id] → orders[user_id]`

### 1.3 DAX 度量值（复制到 Power BI 的"新建度量值"）

```dax
// ── 流量指标 ──
PV = COUNT(user_behavior[id])

UV = DISTINCTCOUNT(user_behavior[user_id])

PV_UV_Ratio = DIVIDE([PV], [UV])    // 人均浏览页面数

// ── 付费指标 ──
Total_Orders = COUNT(orders[order_id])

Paid_Users = 
    CALCULATE(
        DISTINCTCOUNT(orders[user_id]),
        orders[order_status] IN {"paid", "shipped", "completed"}
    )

// 付费率 = 付费用户 / 活跃用户
Payment_Rate = 
    DIVIDE(
        [Paid_Users],
        DISTINCTCOUNT(user_behavior[user_id])
    )

// ── 漏斗各环节人数 ──
View_Users = 
    CALCULATE(DISTINCTCOUNT(user_behavior[user_id]), user_behavior[action] = "view")

Cart_Users = 
    CALCULATE(DISTINCTCOUNT(user_behavior[user_id]), user_behavior[action] = "add_to_cart")

Order_Users = 
    CALCULATE(DISTINCTCOUNT(user_behavior[user_id]), user_behavior[action] = "place_order")

Pay_Users = 
    CALCULATE(DISTINCTCOUNT(user_behavior[user_id]), user_behavior[action] = "pay")

// 环节转化率
View_to_Cart = DIVIDE([Cart_Users], [View_Users])
Cart_to_Order = DIVIDE([Order_Users], [Cart_Users])
Order_to_Pay = DIVIDE([Pay_Users], [Order_Users])

// ── 收入指标 ──
GMV = SUM(orders[amount])

Avg_Order_Value = 
    DIVIDE(
        SUM(orders[amount]),
        COUNT(orders[order_id])
    )

// ── 复购率 ──
Repeat_Buyers = 
    CALCULATE(
        DISTINCTCOUNT(orders[user_id]),
        FILTER(
            VALUES(orders[user_id]),
            CALCULATE(DISTINCTCOUNT(orders[order_id])) >= 2
        )
    )

Repurchase_Rate = DIVIDE([Repeat_Buyers], DISTINCTCOUNT(orders[user_id]))
```

### 1.4 看板布局（一页一张图）

```
┌────────────────────────────────────────────────────────────┐
│  跃动体育 · 日常运营看板                   昨日: 2026-01-14 │
├──────────────┬──────────────┬──────────────┬──────────────┤
│  卡片行       │  卡片行       │  卡片行       │  卡片行       │
│  📊 PV       │  📊 UV       │  💰 GMV      │  📈 付费率    │
│  45,230      │  8,120       │  ¥238,500    │  8.5%        │
├──────────────┴──────────────┴──────────────┴──────────────┤
│  折线图: 近 30 天 PV/UV/GMV 趋势（三线叠加，双 Y 轴）       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  🟦 PV  🟧 UV  🟩 GMV                          │ │
│  └──────────────────────────────────────────────────────┘ │
├─────────────────────────────┬────────────────────────────┤
│  漏斗图（条形）              │  饼图: 客户分层              │
│  浏览 ████████████ 15,200   │  高价值  中高价值            │
│  加购 ██████ 4,560          │   中价值   低价值            │
│  下单 ███ 1,368             │                             │
│  支付 ██ 984                │                             │
├─────────────────────────────┴────────────────────────────┤
│  表格: 近 7 天日报明细                                      │
│  日期 │ PV │ UV │ GMV │ 付费率 │ 环比变化 │                 │
└────────────────────────────────────────────────────────────┘
```

### 1.5 Python → Power BI 对照

| Python 代码 | Power BI 等价操作 |
|------------|------------------|
| `user_behavior_df.groupby(date).agg(pv=..., uv=...)` | 折线图：轴=date，值=[PV]和[UV] |
| `pay_rate_df['date']` 画折线 | 折线图：轴=date，值=[Payment_Rate] |
| `funnel_df` 画条形图 | 漏斗图（Bar Chart）：轴=漏斗环节，值=人数 |
| `rfm_df['segment'].value_counts()` 画饼图 | 饼图：图例=segment，值=user_count |
| `print(f'日均PV: {avg_pv:,}')` | 卡片（Card）视觉对象，绑定 [PV] 度量值 |

---

## 2. 项目二：老用户健康看板（CRM 组专用）

### 2.1 看板目标
黄晓明每周看一次，回答：各层用户的数量和趋势、哪层在流失、哪层在增长。

### 2.2 数据模型

```
users ──→ orders ──→ order_items ←── products
 1          N          N              1
```

### 2.3 DAX 度量值

```dax
// ── 用户分层相关 ──
Total_Old_Users = COUNT(users[user_id])

// 品类拓展率
Expansion_Rate = 
    DIVIDE(
        CALCULATE(
            DISTINCTCOUNT(orders[user_id]),
            RELATED(products[category_id]) = 2
        ),
        DISTINCTCOUNT(orders[user_id])
    )

// ── AB 测试看板 ──
// 注: AB 测试数据通常来自 CRM 系统，不在本数据库中
// 这里假设你有一个 ab_test_results 表，结构: group_name, sample_size, conversions
Conversion_Rate = DIVIDE(SUM(ab_test_results[conversions]), SUM(ab_test_results[sample_size]))

Lift_vs_Control = 
    DIVIDE(
        [Conversion_Rate] - CALCULATE([Conversion_Rate], ab_test_results[group_name] = "对照组"),
        CALCULATE([Conversion_Rate], ab_test_results[group_name] = "对照组")
    )
```

### 2.4 看板布局

```
┌────────────────────────────────────────────────────────┐
│  跃动体育 · 老用户健康看板             报告周期: 本周   │
├────────────────────┬───────────────────────────────────┤
│  环形图: 用户分层   │  柱形图: 各分层 GMV 贡献           │
│                    │  ████ 高价值深耕  → 45%            │
│                    │  ███ 高潜唤醒    → 28%             │
│                    │  ██ 成长型      → 18%              │
│                    │  █ 流失风险     →  9%              │
├────────────────────┴───────────────────────────────────┤
│  折线图: 各分层月度 GMV 占比趋势（12 个月）              │
├────────────────────┬───────────────────────────────────┤
│  散点图: 用户品类   │  表格: 分层画像                    │
│  拓展分布          │  分层 │ 人数 │ R均值 │ F均值 │ M均值│
│  (x=袜子订单,      │  ...  │ ...  │ ...   │ ...   │ ... │
│   y=服装订单)      │                                   │
└────────────────────┴───────────────────────────────────┘
```

---

## 3. 项目三：投放 ROI 看板（市场部专用）

### 3.1 看板目标
郑浩和吴佳妮每天看，回答：昨天各渠道花了多少钱、挣回来多少、ROI 在什么水平。

### 3.2 数据模型

```
ad_campaigns          attribution_data
───────────           ────────────────
campaign_id           id
platform              user_id
campaign_type         platform
campaign_date         conversion_time
spend
revenue
```

### 3.3 DAX 度量值

```dax
// ── 投放效能指标 ──
Total_Spend = SUM(ad_campaigns[spend])
Total_Revenue = SUM(ad_campaigns[revenue])

ROI = DIVIDE([Total_Revenue], [Total_Spend])

CTR = DIVIDE(SUM(ad_campaigns[clicks]), SUM(ad_campaigns[impressions]))
CVR = DIVIDE(SUM(ad_campaigns[conversions]), SUM(ad_campaigns[clicks]))
CPC = DIVIDE([Total_Spend], SUM(ad_campaigns[clicks]))
CPA = DIVIDE([Total_Spend], SUM(ad_campaigns[conversions]))

// ── 预算占比 ──
Spend_Share = 
    DIVIDE(
        [Total_Spend],
        CALCULATE([Total_Spend], ALL(ad_campaigns[platform]))
    )

// ── 四象限角色 ──
Platform_Role = 
    SWITCH(
        TRUE(),
        [CPC] < AVERAGEX(ALL(ad_campaigns[platform]), [CPC]) && 
        [ROI] > AVERAGEX(ALL(ad_campaigns[platform]), [ROI]), "高效拉新场",
        [CPC] < AVERAGEX(ALL(ad_campaigns[platform]), [CPC]), "低成本引流",
        [ROI] > AVERAGEX(ALL(ad_campaigns[platform]), [ROI]), "高价值种草地",
        "需优化"
    )

// ── 归因相关 ──
Last_Click_Conversions = 
    CALCULATE(
        COUNT(attribution_data[user_id]),
        NOT(ISBLANK(attribution_data[conversion_time]))
    )
```

### 3.4 看板布局

```
┌────────────────────────────────────────────────────────────┐
│  跃动体育 · 投放 ROI 看板                 本月预算: ¥530万  │
├──────────┬──────────┬──────────┬──────────┬───────────────┤
│  卡片     │  卡片     │  卡片     │  卡片     │  卡片          │
│  总花费   │  总收入   │  全域ROI  │  平均CPA  │  本月剩余预算   │
├──────────┴──────────┴──────────┴──────────┴───────────────┤
│  柱形图: 各平台 ROI 对比（带盈亏线 ROI=1）                  │
├─────────────────────────────┬─────────────────────────────┤
│  散点图: 四象限分析          │  堆积柱形图: 各平台花费月度    │
│  CPC × ROI                 │  趋势（12个月）              │
│  带平台标签                  │                             │
├─────────────────────────────┼─────────────────────────────┤
│  表格: 预算分配对比          │  柱形图: 归因分析              │
│  平台│当前占比│建议占比│调整  │  末次点击 vs 时间衰减          │
└─────────────────────────────┴─────────────────────────────┘
```

---

## 4. 项目四：产品健康度看板（商品部专用）

### 4.1 看板目标
钱莹和徐峰每周一早上看，回答：爆款够不够库存、滞销品压了多少资金、哪些该补货。

### 4.2 数据模型

```
products ──→ sales_data ←── inventory_data
   1            N              (一对一，用 product_id 关联)
```

### 4.3 DAX 度量值

```dax
// ── 产品指标 ──
Total_Sales_Volume = SUM(sales_data[sales_volume])
Total_Sales_Amount = SUM(sales_data[sales_amount])

// 售罄率（需要从 inventory_data 表取 current_stock）
Sell_Through_Rate = 
    DIVIDE(
        [Total_Sales_Volume],
        [Total_Sales_Volume] + SUM(inventory_data[current_stock])
    )

// 毛利率
Gross_Margin = 
    DIVIDE(
        SUM(sales_data[sales_amount]) - SUM(products[cost]) * SUM(sales_data[sales_volume]),
        SUM(sales_data[sales_amount])
    )

// ── 产品分级 ──
Product_Segment = 
    SWITCH(
        TRUE(),
        [Sell_Through_Rate] > 0.55 && [Gross_Margin] > 0.35, "爆款",
        [Sell_Through_Rate] > 0.35 && [Gross_Margin] > 0.25, "畅销款",
        [Sell_Through_Rate] > 0.15, "一般款",
        "滞销款"
    )

// ── 补货相关 ──
// 需要补货标记
Needs_Replenishment = 
    IF(
        SUM(inventory_data[current_stock]) < 
        DIVIDE([Total_Sales_Volume], 30) * SUM(inventory_data[lead_time_days]) + 
        SUM(inventory_data[safety_stock]),
        "需要补货",
        "库存充足"
    )

// 库存资金占用
Inventory_Value = SUMX(products, products[cost] * RELATED(inventory_data[current_stock]))
```

### 4.4 看板布局

```
┌─────────────────────────────────────────────────────────────┐
│  跃动体育 · 产品健康度看板               最后刷新: 今早 8:00  │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  卡片     │  卡片     │  卡片     │  卡片     │  卡片           │
│  产品总数  │  爆款数   │  滞销品数  │  总库存价值│  需补货产品数    │
├──────────┴──────────┴──────────┴──────────┴────────────────┤
│  散点图: 产品健康度气泡图                                   │
│  X=售罄率  Y=毛利率  气泡大小=销售额  颜色=毛利额            │
│  叠加四象限虚线（售罄率=0.4, 毛利率=0.3）                    │
├──────────────────────────────┬─────────────────────────────┤
│  环形图: 产品分级占比         │  柱形图: 各平台销售金额       │
│  爆款/畅销/一般/滞销          │  天猫 京东 得物 抖音           │
├──────────────────────────────┼─────────────────────────────┤
│  折线图: Top 5 爆款 7日       │  表格: 需要补货的产品清单      │
│  移动平均趋势                 │  产品名 │ 库存 │ 补货点 │ 建议量│
│                              │  ...   │ ... │ ...   │ ...  │
└──────────────────────────────┴─────────────────────────────┘
```

---

## 5. 快速开始清单

- [ ] 安装 Power BI Desktop（免费，微软官网下载）
- [ ] 用 Python 导出四个项目的数据库为 CSV（或直接连 MySQL）
- [ ] 在 Power BI 中导入数据 → 建立表关系
- [ ] 新建度量值，复制上面对应项目的 DAX 公式
- [ ] 按布局图拖拽视觉对象（折线图/柱形图/饼图/散点图/卡片/表格）
- [ ] 调颜色、加标题、设置数据刷新频率

**每个项目从零到完成一个看板，大约需要 2-3 小时。**
