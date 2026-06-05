# 🏪 电商数据分析 portfolio

> **跃动体育** 电商运营数据分析项目集，涵盖流量分析、用户分层、ROI 优化、产品组合管理四大核心场景。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange.svg)](https://jupyter.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1.svg?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-blue.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

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
| 转化漏斗 | `pivot_table` 构建用户-行为矩阵 | 浏览→加购→下单→支付 |
| RFM 分层 | `pd.qcut` 五等分 + `np.select` 向量化 | 高/中高/中/低价值客户 |

📄 [查看 Notebook](项目一：公司日常运营指标分析/analysis.ipynb) · [分析报告](项目一：公司日常运营指标分析/日常运营指标分析报告.md)

---

### 项目二：老用户激活与价值提升

**核心问题：** 老用户 GMV 占比持续下滑，如何从"粗放拉新"转向"精细存量运营"？

| 分析模块 | 方法 | 亮点 |
|---------|------|------|
| RFM-G 特征工程 | 五表 JOIN 构建用户宽表，新增品类拓展维度 G | G = 品类多样性 × (1 + 服装金额占比) |
| 用户分层 | 四维评分（R/F/M/G）+ `np.select` 向量化 | 高价值深耕/高潜唤醒/成长型/流失风险 |
| AB 测试 | 卡方检验 + 双样本比例 z 检验 | 验证优惠策略的统计显著性 |
| 运营策略 | 按分层设计差异化方案 | 品类拓展券、阶梯优惠、召回机制 |

📄 [查看 Notebook](项目二：老用户激活与价值提升/analysis.ipynb) · [分析报告](项目二：老用户激活与价值提升/老用户激活与价值提升分析报告.md)

---

### 项目三：各平台 ROI 预算重新分配

**核心问题：** 天猫、京东、得物、抖音四个平台都在投，但预算分配最优吗？

| 分析模块 | 方法 | 亮点 |
|---------|------|------|
| 效能指标 | 六大指标：CTR / CVR / CPA / CPC / ROI / ARPU | 得物 ROI 44× vs 抖音 16× |
| 四象限定位 | CPC（成本）× ROI（回报）交叉分析 | 高效拉新场 / 高价值种草地 / 低成本引流 |
| 边际 ROI | 二次多项式回归拟合投入-产出曲线 | 量化边际收益递减拐点 |
| 归因分析 | 末次点击 + 时间衰减双模型 | 避免单一归因偏差 |
| 预算优化 | 综合 ROI(60%) + 边际 ROI(40%) 权重分配 | 全域 ROI 预估提升 15%+ |

📄 [查看 Notebook](项目三：各平台ROI预算重新分配/analysis.ipynb) · [分析报告](项目三：各平台ROI预算重新分配/各平台ROI预算重新分配分析报告.md)

---

### 项目四：产品组合分析

**核心问题：** 新品上市后如何实时监控健康度？滞销品何时清仓、走哪个渠道？

| 分析模块 | 方法 | 亮点 |
|---------|------|------|
| 健康度评分 | 售罄率 × 毛利率 双维度四象限 | 产品分级：爆款/畅销/一般/滞销 |
| 趋势预测 | 线性回归拟合日销量趋势 | 上升/平稳/下降三分类 |
| 智能补货 | 补货点 = 预测日销 × 提前期 + 安全库存 | 自动生成补货清单 |
| 清仓策略 | 按渠道（天猫/京东/得物/抖音）差异化推荐 | 滞销品 → 最优清仓渠道匹配 |

📄 [查看 Notebook](项目四：产品组合分析/analysis.ipynb) · [分析报告](项目四：产品组合分析/产品组合分析报告.md)

---

## 🛠 技术栈

| 层级 | 工具/库 | 用途 |
|------|--------|------|
| 数据处理 | `pandas`, `numpy` | 数据清洗、透视、聚合、向量化计算 |
| 统计分析 | `scipy.stats` | 卡方检验、双样本 z 检验 |
| 机器学习 | `scikit-learn` | 多项式回归（边际 ROI）、线性回归（趋势预测） |
| 可视化 | `matplotlib`, `seaborn` | 综合看板、漏斗图、热力图、四象限散点图 |
| 数据库 | `SQLite3` / `pymysql` | 本地轻量开发 / 生产环境 MySQL |
| 环境 | `Jupyter Notebook` | 交互式分析 + 图文并茂的报告输出 |
| BI 工具 | PowerBI | 数据导出模块，支持 PowerBI 看板 |

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/项目名.git
cd 项目名
```

### 2. 安装依赖

```bash
# 方式一：conda（推荐，自动处理 C 库依赖）
conda install -c conda-forge numpy pandas matplotlib seaborn scipy scikit-learn pymysql cryptography python-docx jupyter

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

### 4. （可选）切换到 MySQL

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
├── README.md                          # 本文件
├── requirements.txt                   # Python 依赖清单
├── 学习指南.md                         # 详细学习指南（数据思维 + 面试要点）
├── PowerBI看板指南.md                   # PowerBI 仪表板搭建指南
│
├── company_scale_setup.py             # 一键生成 4 个项目的 SQLite 数据
├── mysql_setup.py                     # 一键生成 4 个项目的 MySQL 数据
├── migrate_to_mysql.py                # SQLite → MySQL 数据迁移脚本
├── export_for_powerbi.py              # 导出数据供 PowerBI 使用
│
├── 项目一：公司日常运营指标分析/
│   ├── analysis.ipynb                 # Jupyter Notebook 分析（支持 SQLite/MySQL 双模式）
│   ├── analysis.py                    # 纯 Python 脚本版
│   ├── ecommerce_ops.db               # SQLite 数据
│   ├── 日常运营指标分析.png            # 综合可视化看板
│   └── 日常运营指标分析报告.md          # 自动生成的分析报告
│
├── 项目二：老用户激活与价值提升/
│   ├── analysis.ipynb
│   ├── analysis.py
│   ├── user_activation.db
│   ├── 老用户激活与价值提升分析.png
│   └── 老用户激活与价值提升分析报告.md
│
├── 项目三：各平台ROI预算重新分配/
│   ├── analysis.ipynb
│   ├── analysis.py
│   ├── roi_allocation.db
│   ├── 各平台ROI预算重新分配分析.png
│   └── 各平台ROI预算重新分配分析报告.md
│
├── 项目四：产品组合分析/
│   ├── analysis.ipynb
│   ├── analysis.py
│   ├── product_portfolio.db
│   ├── 产品组合分析.png
│   └── 产品组合分析报告.md
│
└── powerbi_data/                      # PowerBI 导出的 CSV 数据
```

---

## 📊 分析逻辑关系

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

## 📝 许可

MIT License — 仅供学习和展示使用。

---

> 💡 **提示：** 所有 Notebook 默认使用 SQLite（零配置、开箱即用）。如需连接 Navicat 或 MySQL 进行 SQL 练习，运行 `mysql_setup.py` 后将 `DB_TYPE` 改为 `'mysql'` 即可。
