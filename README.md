# 🏪 跃动体育 · 电商数据分析 Portfolio

> 模拟 100 人 DTC 运动品牌「跃动体育」的全链路数据分析实践，涵盖**流量运营、用户分层、ROI 优化、产品组合**四大核心场景。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange.svg)](https://jupyter.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1.svg?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-blue.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Dash](https://img.shields.io/badge/Dash-Plotly-3F4F75.svg?logo=plotly&logoColor=white)](https://dash.plotly.com/)
[![Power BI](https://img.shields.io/badge/Power_BI-Desktop-F2C811.svg?logo=powerbi&logoColor=black)](https://powerbi.microsoft.com/)

---

## 📋 项目全景

```
跃动体育 数据分析
├── 项目一：公司日常运营指标分析     ← 流量 × 转化 × 复购 × RFM 分层
├── 项目二：老用户激活与价值提升     ← RFM-G 模型 × AB 测试 × 分层运营
├── 项目三：各平台 ROI 预算重新分配   ← 边际效益 × 归因分析 × 预算优化
└── 项目四：产品组合分析             ← 健康度评分 × 趋势预测 × 智能补货
```

---

## 🎯 项目详情

### 项目一：公司日常运营指标分析

**核心问题：** 店铺流量进来了，但转化率卡在哪里？客户价值如何分布？

| 分析模块 | 方法 | 关键指标 |
|---------|------|---------|
| 流量分析 | 按日聚合 PV / UV，趋势可视化 | 日均 PV/UV 比 ≈ 1.9 |
| 付费率分析 | 付费用户 / 活跃用户（按日） | 各环节转化追踪 |
| 复购分析 | 下单 ≥ 2 次的用户画像 | 复购率 ≈ 46% |
| 转化漏斗 | `pivot_table` 构建用户-行为矩阵 | 浏览 → 加购 → 下单 → 支付 |
| RFM 分层 | `pd.qcut` 五等分 + `np.select` 向量化 | 高 / 中高 / 中 / 低价值客户 |

📄 [Notebook](项目一：公司日常运营指标分析/analysis.ipynb) · [分析报告](项目一：公司日常运营指标分析/日常运营指标分析报告.md) · [方案](项目一：公司日常运营指标分析/日常运营指标分析方案.md)

🖼️ [静态看板](可视化/charts/项目一_日常运营指标分析.png)

---

### 项目二：老用户激活与价值提升

**核心问题：** 老用户 GMV 占比持续下滑，如何从"粗放拉新"转向"精细存量运营"？

| 分析模块 | 方法 | 亮点 |
|---------|------|------|
| RFM-G 特征工程 | 五表 JOIN 构建用户宽表，新增品类拓展维度 G | G = 品类多样性 × (1 + 服装金额占比) |
| 用户分层 | 四维评分（R/F/M/G）+ `np.select` 向量化 | 高价值深耕 / 高潜唤醒 / 成长型 / 流失风险 |
| AB 测试 | 卡方检验 + 双样本比例 z 检验 | 验证优惠策略的统计显著性 |
| 运营策略 | 按分层设计差异化方案 | 品类拓展券、阶梯优惠、召回机制 |

📄 [Notebook](项目二：老用户激活与价值提升/analysis.ipynb) · [分析报告](项目二：老用户激活与价值提升/老用户激活与价值提升分析报告.md) · [方案](项目二：老用户激活与价值提升/老用户激活与价值提升方案.md)

🖼️ [静态看板](可视化/charts/项目二_老用户激活与价值提升分析.png)

---

### 项目三：各平台 ROI 预算重新分配

**核心问题：** 天猫、京东、得物、抖音四个平台都在投，但预算分配最优吗？

| 分析模块 | 方法 | 亮点 |
|---------|------|------|
| 效能指标 | CTR / CVR / CPA / CPC / ROI / ARPU 六大指标 | 得物 ROI 44× vs 抖音 16× |
| 四象限定位 | CPC（成本）× ROI（回报）交叉分析 | 高效拉新场 / 高价值种草地 / 低成本引流 |
| 边际 ROI | 二次多项式回归拟合投入-产出曲线 | 量化边际收益递减拐点 |
| 归因分析 | 末次点击 + 时间衰减双模型 | 避免单一归因偏差 |
| 预算优化 | 综合 ROI(60%) + 边际 ROI(40%) 权重分配 | 全域 ROI 预估提升 15%+ |

📄 [Notebook](项目三：各平台ROI预算重新分配/analysis.ipynb) · [分析报告](项目三：各平台ROI预算重新分配/各平台ROI预算重新分配分析报告.md) · [方案](项目三：各平台ROI预算重新分配/各平台ROI预算重新分配方案.md)

🖼️ [静态看板](可视化/charts/项目三_各平台ROI预算重新分配分析.png)

---

### 项目四：产品组合分析

**核心问题：** 新品上市后如何实时监控健康度？滞销品何时清仓、走哪个渠道？

| 分析模块 | 方法 | 亮点 |
|---------|------|------|
| 健康度评分 | 售罄率 × 毛利率 双维度四象限 | 产品分级：爆款 / 畅销 / 一般 / 滞销 |
| 趋势预测 | 线性回归拟合日销量趋势 | 上升 / 平稳 / 下降三分类 |
| 智能补货 | 补货点 = 预测日销 × 提前期 + 安全库存 | 自动生成补货清单 |
| 清仓策略 | 按渠道差异化推荐 | 滞销品 → 最优清仓渠道匹配 |

📄 [Notebook](项目四：产品组合分析/analysis.ipynb) · [分析报告](项目四：产品组合分析/产品组合分析报告.md) · [方案](项目四：产品组合分析/产品组合分析方案.md)

🖼️ [静态看板](可视化/charts/项目四_产品组合分析.png)

---

## 🛠 技术栈

| 层级 | 工具/库 | 用途 |
|------|--------|------|
| 数据处理 | `pandas`, `numpy` | 数据清洗、透视、聚合、向量化计算 |
| 统计分析 | `scipy.stats` | 卡方检验、双样本 z 检验 |
| 机器学习 | `scikit-learn` | 多项式回归（边际 ROI）、线性回归（趋势预测） |
| 静态可视化 | `matplotlib`, `seaborn` | 综合看板、漏斗图、热力图、四象限散点图 |
| 交互看板 | `Dash` + `Plotly` | Web 交互式数据看板（`可视化/dashboard.py`） |
| BI 工具 | Power BI Desktop | 企业级仪表板（`可视化/powerbi/项目可视化.pbix`） |
| 数据库 | `SQLite3` / `pymysql` | 本地轻量开发 / 生产环境 MySQL |
| 开发环境 | `Jupyter Notebook` | 交互式分析 + 图文并茂的报告输出 |

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/maheyun/dianwei_qingxi.git
cd dianwei_qingxi
```

### 2. 安装依赖

```bash
# 方式一：conda（推荐，自动处理 C 库依赖）
conda install -c conda-forge numpy pandas matplotlib seaborn scipy scikit-learn pymysql cryptography python-docx jupyter dash plotly

# 方式二：pip
pip install -r requirements.txt
```

### 3. 生成数据 & 启动分析

```bash
# 生成四个项目的模拟数据（SQLite，开箱即用）
python company_scale_setup.py

# 启动 Jupyter
jupyter notebook
```

### 4. 启动交互式 Web 看板

```bash
# 启动 Dash Web 看板（Plotly 交互图表）
python 可视化/dashboard.py
# 浏览器访问 http://127.0.0.1:8050
```

### 5. （可选）Power BI 看板

```bash
# 导出 Power BI 所需数据
python 可视化/export_for_powerbi.py
# 然后打开 可视化/powerbi/项目可视化.pbix（需 Power BI Desktop）
```

### 6. （可选）切换到 MySQL

```bash
# 方式一：一键生成 MySQL 数据（推荐）
python mysql_setup.py

# 方式二：从 SQLite 迁移已有数据
python migrate_to_mysql.py

# 然后在 Notebook 中将 DB_TYPE = 'sqlite' 改为 DB_TYPE = 'mysql'
# MySQL 连接：localhost / root / 123456 / ecommerce_analysis
```

---

## 📁 项目结构

```
.
├── README.md                           # 本文件
├── requirements.txt                    # Python 依赖清单
├── .gitignore
│
├── 📘 学习指南.md                       # 详细学习指南（数据思维 + 面试要点）
├── 📘 面试指标速查表.md                  # 面试指标速查手册
├── 📘 面试题全集.md                     # 22 道面试题及详细解答
├── 📘 PowerBI看板指南.md                # Power BI 仪表板搭建指南
├── 📘 PowerBI三层诊断看板搭建指南.md     # Power BI 三层下钻看板完整指南（含 DAX）
├── 📘 项目完整讲解稿.md                  # 面试项目陈述完整稿（含 Q&A 追问）
│
├── 🔧 company_scale_setup.py           # 一键生成 4 个项目的 SQLite 数据
├── 🔧 mysql_setup.py                   # 一键生成 4 个项目的 MySQL 数据
├── 🔧 migrate_to_mysql.py              # SQLite → MySQL 数据迁移脚本
│
├── 📊 可视化/                           # ★ 所有可视化资源集中管理
│   ├── dashboard_v4.py                 # Dash 三层诊断看板（驾驶舱→维度拆分→交叉归因）
│   ├── dashboard_v3.py                 # Dash 精简版看板（备用）
│   ├── dashboard.py                    # Dash Web 交互看板（原版四项目 Tab）
│   ├── export_for_powerbi.py           # Power BI 数据导出（含三层看板专用 CSV）
│   ├── charts/                         # 静态分析图表（PNG）
│   │   ├── 项目一_日常运营指标分析.png
│   │   ├── 项目二_老用户激活与价值提升分析.png
│   │   ├── 项目三_各平台ROI预算重新分配分析.png
│   │   └── 项目四_产品组合分析.png
│   ├── powerbi/                        # Power BI 资源
│   │   ├── 项目可视化.pbix              # Power BI 完整看板文件
│   │   └── data/                       # Power BI 源数据（CSV）
│   │       ├── 项目一_日常运营/
│   │       ├── 项目二_老用户激活/
│   │       ├── 项目三_ROI预算/
│   │       ├── 项目四_产品组合/
│   │       └── 统一驾驶舱/              # 三层诊断看板专用数据
│   └── 演示视频/                        # 预留：项目演示视频
│
├── 📁 项目一：公司日常运营指标分析/
│   ├── analysis.ipynb                  # Jupyter Notebook（SQLite/MySQL 双模式）
│   ├── analysis.py                     # 纯 Python 脚本版
│   ├── 复刻.ipynb                      # MySQL 连接复刻版
│   ├── ecommerce_ops.db                # SQLite 数据库（~2.5GB，10×规模）
│   ├── 日常运营指标分析方案.md           # 项目方案
│   └── 日常运营指标分析报告.md           # 分析报告
│
├── 📁 项目二：老用户激活与价值提升/
│   ├── analysis.ipynb
│   ├── analysis.py
│   ├── user_activation.db              # ~200MB
│   ├── 老用户激活与价值提升方案.md
│   └── 老用户激活与价值提升分析报告.md
│
├── 📁 项目三：各平台ROI预算重新分配/
│   ├── analysis.ipynb
│   ├── analysis.py
│   ├── roi_allocation.db               # ~4MB
│   ├── 各平台ROI预算重新分配方案.md
│   └── 各平台ROI预算重新分配分析报告.md
│
├── 📁 项目四：产品组合分析/
│   ├── analysis.ipynb
│   ├── analysis.py
│   ├── product_portfolio.db            # ~75MB
│   ├── 产品组合分析方案.md
│   └── 产品组合分析报告.md
│
├── 📝 MySQL面试题30道.sql              # 30 题合集（基础/聚合/JOIN/窗口/CTE/RFM-G）
├── 📝 query/                           # 30 道独立 SQL 文件
├── 📝 项目一sql数据查询.csv             # 项目一 PV/UV 示例数据导出
│
├── 📄 数据分析师-胡雅威-简历.docx        # 简历 Word 版
├── 📄 数据分析师-胡雅威-简历.pdf         # 简历 PDF 版
├── 📄 最新简历/                         # 简历最新版本
│   ├── 数据分析师-胡雅威-简历.docx
│   └── 数据分析师-胡雅威-简历.pdf
│
├── 🛠 extract_resume.py                # 简历文本提取工具
├── 🛠 resume_text.txt                  # 简历纯文本提取结果
├── 🛠 git更新指令                       # Git 常用指令速查
│
└── 📋 a.py / test_timestamp.db         # 测试/临时文件
```

---

## 📊 分析逻辑体系

```
┌──────────────────────────────────────────────────────────┐
│                    四项目分析体系                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│   项目一：运营指标分析（全局视角）                           │
│   ├─ 流量 → 转化 → 复购 → RFM 分层                        │
│   └─ 回答"店铺整体运营状况如何？"                           │
│         ↓                                                 │
│   项目二：老用户激活（用户视角）                             │
│   ├─ RFM-G 分层 → 行为画像 → AB 测试 → 运营策略            │
│   └─ 回答"存量用户如何精细化运营？"                         │
│         ↓                                                 │
│   项目三：ROI 优化（渠道视角）                              │
│   ├─ 效能指标 → 四象限定位 → 边际分析 → 预算调整           │
│   └─ 回答"投放预算怎样分配效率最高？"                       │
│         ↓                                                 │
│   项目四：产品组合（商品视角）                               │
│   ├─ 健康度评分 → 趋势预测 → 智能补货 → 清仓策略           │
│   └─ 回答"哪些产品该推、哪些该清、库存怎么管？"              │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 🖥️ 可视化体系

本项目提供 **三层可视化** 满足不同场景：

| 层级 | 工具 | 输出 | 适用场景 |
|------|------|------|---------|
| 静态图表 | `matplotlib` + `seaborn` | `可视化/charts/*.png` | 报告嵌入、快速预览 |
| 交互看板（三层下钻） | `Dash` + `Plotly` | `python 可视化/dashboard_v4.py` | 浏览器交互式三层诊断：驾驶舱 → 维度拆分 → 交叉归因 |
| 企业 BI | Power BI Desktop | `可视化/powerbi/项目可视化.pbix` | 正式汇报、大屏展示 |

### Dash 三层诊断看板（新增）

```bash
# 启动三层下钻诊断看板
python 可视化/dashboard_v4.py
# 浏览器访问 http://127.0.0.1:8054
```

**三层结构**：
- **第一层「CEO 驾驶舱」**：6 大核心 KPI + GMV 趋势 + 平台 ROI + 产品四象限，异常自动标红
- **第二层「维度拆分」**：点击任意 KPI → 按用户分层/渠道/品类拆分明细
- **第三层「交叉归因」**：点击异常维度 → 品类×渠道交叉分析 + 根因判断 + 策略建议

### Power BI 三层看板

```bash
# 导出 Power BI 所需数据（含三层诊断看板专用 CSV）
python 可视化/export_for_powerbi.py

# 然后打开 Power BI Desktop，按指南搭建
# 详细步骤和 DAX 公式参考：PowerBI三层诊断看板搭建指南.md
```

---

## 🗄️ SQL 面试题

**30 道 MySQL 面试题**涵盖 7 大模块：

| 模块 | 题量 | 考察点 |
|------|------|--------|
| 基础查询 | 6 | DISTINCT / WHERE / GROUP BY / BETWEEN / LIKE / IN |
| 聚合与分组 | 6 | COUNT DISTINCT / HAVING / 窗口百分比 / 中位数 / 透视 |
| 多表 JOIN | 6 | LEFT JOIN / 自连接 / 四表关联 / 反连接 / COALESCE |
| 窗口函数 | 6 | ROW_NUMBER / 累计求和 / RANK / LEAD / 移动平均 |
| 子查询与 CTE | 4 | 标量子查询 / NOT EXISTS / CTE 分层 / 多步 CTE |
| 索引设计 | 1 | 复合索引策略 |
| 综合实战 | 1 | RFM+G 五维用户分层（CTE + NTILE + CASE WHEN） |

📄 [合集文件](MySQL面试题30道.sql) · [分题目录](query/)

---

## 📝 许可

MIT License — 仅供学习和展示使用。

---

> 💡 **提示：** 所有 Notebook 默认使用 SQLite（零配置、开箱即用）。如需连接 Navicat 或 MySQL 进行 SQL 练习，运行 `mysql_setup.py` 后将 `DB_TYPE` 改为 `'mysql'` 即可。
