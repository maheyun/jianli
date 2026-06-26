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

### 0.3 可视化搭建教程：从度量值到图表

> 以下覆盖四个项目用到的全部图表类型。每个图表都按「点击哪里 → 拖什么到哪」的步骤写，照做即可。

#### 0.3.1 界面速览

```
┌──────────────────────────────────────────────────────────┐
│  Power BI 主界面                                         │
│                                                          │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │          │  │                  │  │ 可视化面板     │  │
│  │ 左侧：   │  │   中间：画布      │  │               │  │
│  │ 报表/数据 │  │                  │  │ 📊 图标列表   │  │
│  │ /模型    │  │   空白的这块      │  │ (点一下选中)  │  │
│  │          │  │   就是画布区域    │  │               │  │
│  ├──────────┤  │                  │  ├───────────────┤  │
│  │ 数据面板  │  │                  │  │ 格式面板      │  │
│  │ (右侧)   │  │                  │  │ (点🎨画笔切)  │  │
│  │          │  │                  │  │               │  │
│  │ 📁 表1   │  │                  │  │ X轴/Y轴/图例  │  │
│  │  📄 列1  │  │                  │  │ 值/工具提示   │  │
│  │  📄 列2  │  │                  │  │               │  │
│  │  📊 度量 │  │                  │  │               │  │
│  └──────────┘  └──────────────────┘  └───────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**核心操作**：左侧数据面板**勾选字段**（或拖到右侧字段区）→ 图表自动出现在画布上。

---

#### 0.3.2 卡片（Card）— 显示单个数字

**用途**：展示 PV、UV、GMV、ROI 等核心 KPI。

```
操作步骤：
1. 先点一下画布空白处（确保没选中任何图表）
2. 右侧「可视化」面板 → 点击 📊「卡片」图标
3. 左侧「数据」面板 → 把度量值（如 [PV]）拖到右侧「字段」框
4. 画布上出现卡片 → 拖四角调整大小

格式美化（可选）：
  - 选中卡片 → 右侧点 🎨「设置视觉对象格式」
  - 视觉对象 → 标注：打开「类别标签」，填 "日均 PV"
  - 视觉对象 → 边框：打开边框，颜色浅灰
```

> 一次只能显示一个值。想并排显示多个 KPI，就重复建多个卡片。

---

#### 0.3.3 折线图（Line Chart）— 看趋势

**用途**：PV/UV 日趋势、付费率趋势、GMV 月度走势。

```
操作步骤：
1. 右侧「可视化」面板 → 点击 📈「折线图」
2. 左侧数据面板：
   - 拖 create_time（日期列）→ 右侧「X 轴」
   - 拖 [PV] → 右侧「Y 轴」
   - 拖 [UV] → 右侧「Y 轴」（会和 PV 同框显示）
3. 完成

双 Y 轴设置（PV 和 GMV 数值差距大时用）：
  - 选中折线图 → 🎨 格式 → Y 轴 → 打开「次轴」
  - 把 GMV 拖到「次轴值」
```

---

#### 0.3.4 柱形图 / 簇状柱形图（Clustered Column Chart）— 分类对比

**用途**：各平台 ROI 对比、产品销量排行。

```
操作步骤：
1. 右侧「可视化」面板 → 点击 ▊「簇状柱形图」
2. 拖字段：
   - 拖 platform（分类字段）→ 「X 轴」
   - 拖 [ROI]（度量值）→ 「Y 轴」
3. 完成

添加参考线（如 ROI=1 盈亏线）：
  - 🎨 格式 → Y 轴 → 参考线 → 添加 → 值填 1 → 颜色红色虚线
```

---

#### 0.3.5 堆积柱形图（Stacked Column Chart）— 看组成

**用途**：各平台花费月度趋势（看每个平台占多少）。

```
操作步骤：
1. 右侧「可视化」面板 → 点击 ▊▊「堆积柱形图」
2. 拖字段：
   - 拖 日期列 → 「X 轴」
   - 拖 [Total_Spend] → 「Y 轴」
   - 拖 platform → 「图例」（这样每个平台一种颜色堆叠）
```

---

#### 0.3.6 漏斗图（Funnel）— 转化分析

**用途**：浏览 → 加购 → 下单 → 支付，看各环节流失。

```
操作步骤：
1. 右侧「可视化」面板 → 点击 ▽「漏斗图」
2. 拖字段：
   - 拖 action 或 环节名称列 → 「类别」
   - 拖 [用户数度量值] → 「值」
3. 如果数据是四个独立的度量值（View_Users, Cart_Users…），
   更简单的做法：用条形图模拟漏斗（拖四个度量值到「值」）
```

> Power BI 原生漏斗图要求一个列作为类别。如果度量值是分开建的，建议用「簇状条形图」——把四个度量值拖到「值」区域，效果一样。

---

#### 0.3.7 饼图 / 环形图（Pie / Donut Chart）— 占比分布

**用途**：客户分层占比、产品分级占比。

```
操作步骤：
1. 右侧「可视化」面板 → 点击 ◉「饼图」或 ◉「环形图」
2. 拖字段：
   - 拖 segment（分类字段）→ 「图例」
   - 拖 [user_count 度量值] → 「值」
3. 调标签格式：
   - 🎨 格式 → 详细信息标签 → 打开 → 选「类别, 百分比」
```

---

#### 0.3.8 散点图 / 气泡图（Scatter Chart）— 四象限分析

**用途**：CPC × ROI 平台定位、售罄率 × 毛利率 产品健康度。

```
操作步骤（以项目三"平台四象限"为例）：
1. 右侧「可视化」面板 → 点击 ●●●「散点图」
2. 拖字段：
   - 拖 [CPC] → 「X 轴」
   - 拖 [ROI] → 「Y 轴」
   - 拖 platform → 「详细信息」（每个点会自动标文字）
   - 拖 [Total_Spend] → 「大小」（气泡图，花费越多点越大）
   - 拖 platform → 「图例」（不同平台不同颜色）

添加四象限参考线：
  1. 🎨 格式 → X 轴 → 参考线 → 添加 → 值 = CPC平均值
  2. 🎨 格式 → Y 轴 → 参考线 → 添加 → 值 = ROI平均值
  3. 两条线交叉，画面自动分成四个象限
```

---

#### 0.3.9 表格（Table）— 明细数据

**用途**：日报明细、补货清单、分层画像。

```
操作步骤：
1. 右侧「可视化」面板 → 点击 ▦「表」
2. 左侧数据面板，逐一拖入指标：
   - 拖 日期列、[PV]、[UV]、[GMV]、[Payment_Rate] → 「列」
3. 调样式：
   - 🎨 格式 → 视觉对象 → 网格：打开水平/垂直网格线
   - 🎨 格式 → 视觉对象 → 值 → 字体大小调小

条件格式（如 GMV 环比红色标跌）：
  - 🎨 格式 → 单元格元素 → 字体颜色 → 条件格式
  - 规则：值 < 0 → 红色
```

---

#### 0.3.10 环形图 vs 饼图

| 场景 | 推荐 |
| :-- | :-- |
| 类别 ≤ 5 个 | 环形图（中间是空的，更美观） |
| 类别 > 5 个 | 柱形图（饼图太拥挤分不清） |
| 需要强调占比 | 饼图 + 标签显示百分比 |
| 分两层（大类+小类） | 两个环形图并排 |

---

#### 0.3.11 常用快捷键 & 技巧

| 操作 | 方法 |
| :-- | :-- |
| 复制一个图表 | 选中 → Ctrl+C → Ctrl+V |
| 对齐多个图表 | Ctrl 多选 → 顶部「格式」→ 对齐 → 顶端对齐/均分 |
| 图表间距一致 | Ctrl 多选 → 格式 → 分布 → 水平分布 |
| 锁定图表位置 | 选中 → 视图 → 锁定对象（防止误拖） |
| 统一调颜色 | 🎨 格式 → 视觉对象 → 颜色 → 选自定义色板 |

---

#### 0.3.12 快速排错

| 症状 | 检查 |
| :-- | :-- |
| 图表空白 | 度量值有没有拖到正确区域？X 轴和 Y 轴不要搞反 |
| 数字不对 | 表关系建好了吗？dim_users 两条 1:N 线都连了？ |
| 折线断了/日期乱序 | 日期字段可能被自动汇总了 → 右键日期列 → 改为「日期层级」或去掉时间部分 |
| 度量值找不到 | 右侧「数据」面板刷新一下，或者切到「模型」看看字段在不在 |
| 表名报错 | DAX 里表名要加单引号 `'ecommerce_analysis user_behavior'` |

---

### 1.1 看板目标
每天早上 9 点运营部早会，刘总监站在大屏幕前过数据。需要一张图看清昨日 + 近 7 天的核心指标。

### 1.2 数据模型

> ⚠️ **关键说明**：`user_behavior` 和 `orders` 的 `user_id` 都不是唯一的——一个用户有多条行为记录、多个订单，两表之间是**多对多**关系，不能直接建关系线！

正确做法是用 `dim_users` 做维度表，构成**星型模型**：

```
       dim_users (维度表)
       ┌──────────────┐
       │ user_id (主键)│  ← 唯一，16,155 个用户
       └───┬──────────┘
           │
     1:N ──┼── 1:N
           │
    ┌──────┴──────┐    ┌──────────────┐
    │ user_behavior│    │    orders     │
    │ (事实表)     │    │   (事实表)    │
    ├──────────────┤    ├──────────────┤
    │ id           │    │ order_id     │
    │ user_id (FK) │    │ user_id (FK) │
    │ action       │    │ amount       │
    │ product_id   │    │ order_status │
    │ create_time  │    │ create_time  │
    └──────────────┘    └──────────────┘
```

> 两表互不直连，所有度量值通过 `dim_users` 间接桥接。

在 Power BI 模型视图中建立两条关系：

- `dim_users[user_id]` ──1:N──→ `user_behavior[user_id]`
- `dim_users[user_id]` ──1:N──→ `orders[user_id]`

建表 SQL（已在 MySQL 中执行）：

```sql
CREATE TABLE dim_users AS
SELECT DISTINCT user_id FROM user_behavior
UNION
SELECT DISTINCT user_id FROM orders;
ALTER TABLE dim_users ADD PRIMARY KEY (user_id);
```

### 1.3 DAX 度量值

> **关于表名**：Power BI 从 MySQL 导入时会自动在表名前加数据库前缀，如 `user_behavior` 变成 `ecommerce_analysis user_behavior`。DAX 中带空格/下划线的表名必须用单引号包起来：`'ecommerce_analysis user_behavior'[id]`。
>
> 确认你实际的表名：在 Power BI 右侧 **数据** 面板查看表名，替换下面代码中的表名部分。
>
> **关于创建位置**：度量值不绑定表，放在哪个表下都行。建议放在对应的数据表下方便查找——每个度量值开头注释了建议存放的表。

```dax
// ═══════════════════════════════════════════════════════
// 以下度量值建议在「ecommerce_analysis user_behavior」表下创建
// ═══════════════════════════════════════════════════════

// ── 流量指标 ──
PV = COUNT('ecommerce_analysis user_behavior'[id])

UV = DISTINCTCOUNT('ecommerce_analysis user_behavior'[user_id])

PV_UV_Ratio = DIVIDE([PV], [UV])    // 人均浏览页面数

// ── 漏斗各环节人数 ──
View_Users = 
    CALCULATE(
        DISTINCTCOUNT('ecommerce_analysis user_behavior'[user_id]), 
        'ecommerce_analysis user_behavior'[action] = "view"
    )

Cart_Users = 
    CALCULATE(
        DISTINCTCOUNT('ecommerce_analysis user_behavior'[user_id]), 
        'ecommerce_analysis user_behavior'[action] = "add_to_cart"
    )

Order_Users = 
    CALCULATE(
        DISTINCTCOUNT('ecommerce_analysis user_behavior'[user_id]), 
        'ecommerce_analysis user_behavior'[action] = "place_order"
    )

Pay_Users = 
    CALCULATE(
        DISTINCTCOUNT('ecommerce_analysis user_behavior'[user_id]), 
        'ecommerce_analysis user_behavior'[action] = "pay"
    )

// 环节转化率
View_to_Cart = DIVIDE([Cart_Users], [View_Users])
Cart_to_Order = DIVIDE([Order_Users], [Cart_Users])
Order_to_Pay = DIVIDE([Pay_Users], [Order_Users])

// ═══════════════════════════════════════════════════════
// 以下度量值建议在「ecommerce_analysis orders」表下创建
// ═══════════════════════════════════════════════════════

// ── 付费指标 ──
Total_Orders = COUNT('ecommerce_analysis orders'[order_id])

Paid_Users = 
    CALCULATE(
        DISTINCTCOUNT('ecommerce_analysis orders'[user_id]),
        'ecommerce_analysis orders'[order_status] IN {"paid", "shipped", "completed"}
    )

// 付费率 = 付费用户 / 活跃用户（引用另一个表的度量值，跨表引用直接用 [度量值名]）
Payment_Rate = 
    DIVIDE(
        [Paid_Users],
        [UV]
    )

// ── 收入指标 ──
GMV = SUM('ecommerce_analysis orders'[amount])

Avg_Order_Value = 
    DIVIDE(
        SUM('ecommerce_analysis orders'[amount]),
        COUNT('ecommerce_analysis orders'[order_id])
    )

// ── 复购率 ──
Repeat_Buyers = 
    CALCULATE(
        DISTINCTCOUNT('ecommerce_analysis orders'[user_id]),
        FILTER(
            VALUES('ecommerce_analysis orders'[user_id]),
            CALCULATE(DISTINCTCOUNT('ecommerce_analysis orders'[order_id])) >= 2
        )
    )

Repurchase_Rate = DIVIDE([Repeat_Buyers], DISTINCTCOUNT('ecommerce_analysis orders'[user_id]))
```

> **Payment_Rate 的改动说明**：原来写的是 `DIVIDE([Paid_Users], DISTINCTCOUNT(user_behavior[user_id]))`，改为直接引用已有度量值 `[UV]`——两者计算结果完全一样，且跨表引用度量值比跨表写聚合函数更清晰、更不容易出错。

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

> 表名规则同项目一：Power BI 导入 MySQL 后表名变为 `ecommerce_analysis 表名`，需用单引号包裹。确认你实际的表名后替换。

```dax
// ═══════════════════════════════════════════════════════
// 建议在「ecommerce_analysis users_p2」表下创建
// ═══════════════════════════════════════════════════════

// ── 用户分层相关 ──
Total_Old_Users = COUNT('ecommerce_analysis users_p2'[user_id])

// ═══════════════════════════════════════════════════════
// 建议在「ecommerce_analysis orders_p2」表下创建
// ═══════════════════════════════════════════════════════

// 品类拓展率（需要 models 中 products_p2 和 orders_p2 通过 order_items_p2 桥接）
Expansion_Rate = 
    DIVIDE(
        CALCULATE(
            DISTINCTCOUNT('ecommerce_analysis orders_p2'[user_id]),
            RELATED('ecommerce_analysis products_p2'[category_id]) = 2
        ),
        DISTINCTCOUNT('ecommerce_analysis orders_p2'[user_id])
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

> 表名规则同项目一。项目三的表：`ecommerce_analysis ad_campaigns`、`ecommerce_analysis attribution_data`。

```dax
// ═══════════════════════════════════════════════════════
// 建议在「ecommerce_analysis ad_campaigns」表下创建
// ═══════════════════════════════════════════════════════

// ── 投放效能指标 ──
Total_Spend = SUM('ecommerce_analysis ad_campaigns'[spend])
Total_Revenue = SUM('ecommerce_analysis ad_campaigns'[revenue])

ROI = DIVIDE([Total_Revenue], [Total_Spend])

CTR = DIVIDE(
    SUM('ecommerce_analysis ad_campaigns'[clicks]), 
    SUM('ecommerce_analysis ad_campaigns'[impressions])
)
CVR = DIVIDE(
    SUM('ecommerce_analysis ad_campaigns'[conversions]), 
    SUM('ecommerce_analysis ad_campaigns'[clicks])
)
CPC = DIVIDE([Total_Spend], SUM('ecommerce_analysis ad_campaigns'[clicks]))
CPA = DIVIDE([Total_Spend], SUM('ecommerce_analysis ad_campaigns'[conversions]))

// ── 预算占比 ──
Spend_Share = 
    DIVIDE(
        [Total_Spend],
        CALCULATE([Total_Spend], ALL('ecommerce_analysis ad_campaigns'[platform]))
    )

// ── 四象限角色 ──
Platform_Role = 
    SWITCH(
        TRUE(),
        [CPC] < AVERAGEX(ALL('ecommerce_analysis ad_campaigns'[platform]), [CPC]) && 
        [ROI] > AVERAGEX(ALL('ecommerce_analysis ad_campaigns'[platform]), [ROI]), "高效拉新场",
        [CPC] < AVERAGEX(ALL('ecommerce_analysis ad_campaigns'[platform]), [CPC]), "低成本引流",
        [ROI] > AVERAGEX(ALL('ecommerce_analysis ad_campaigns'[platform]), [ROI]), "高价值种草地",
        "需优化"
    )

// ═══════════════════════════════════════════════════════
// 建议在「ecommerce_analysis attribution_data」表下创建
// ═══════════════════════════════════════════════════════

// ── 归因相关 ──
Last_Click_Conversions = 
    CALCULATE(
        COUNT('ecommerce_analysis attribution_data'[user_id]),
        NOT(ISBLANK('ecommerce_analysis attribution_data'[conversion_time]))
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

> 表名规则同前。项目四的表：`ecommerce_analysis products_p4`、`ecommerce_analysis sales_data`、`ecommerce_analysis inventory_data`。

```dax
// ═══════════════════════════════════════════════════════
// 建议在「ecommerce_analysis sales_data」表下创建
// ═══════════════════════════════════════════════════════

// ── 产品指标 ──
Total_Sales_Volume = SUM('ecommerce_analysis sales_data'[sales_volume])
Total_Sales_Amount = SUM('ecommerce_analysis sales_data'[sales_amount])

// 售罄率（需要从 inventory_data 表取 current_stock，两表必须通过 product_id 关联）
Sell_Through_Rate = 
    DIVIDE(
        [Total_Sales_Volume],
        [Total_Sales_Volume] + SUM('ecommerce_analysis inventory_data'[current_stock])
    )

// 毛利率（需要 products_p4 和 sales_data 通过 product_id 关联）
Gross_Margin = 
    DIVIDE(
        SUM('ecommerce_analysis sales_data'[sales_amount]) 
            - SUM('ecommerce_analysis products_p4'[cost]) * SUM('ecommerce_analysis sales_data'[sales_volume]),
        SUM('ecommerce_analysis sales_data'[sales_amount])
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

// ═══════════════════════════════════════════════════════
// 建议在「ecommerce_analysis inventory_data」表下创建
// ═══════════════════════════════════════════════════════

// 需要补货标记
Needs_Replenishment = 
    IF(
        SUM('ecommerce_analysis inventory_data'[current_stock]) < 
        DIVIDE([Total_Sales_Volume], 30) * SUM('ecommerce_analysis inventory_data'[lead_time_days]) + 
        SUM('ecommerce_analysis inventory_data'[safety_stock]),
        "需要补货",
        "库存充足"
    )

// 库存资金占用
Inventory_Value = SUMX(
    'ecommerce_analysis products_p4', 
    'ecommerce_analysis products_p4'[cost] * RELATED('ecommerce_analysis inventory_data'[current_stock])
)
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
