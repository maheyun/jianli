"""
跃动体育 · 静态 HTML 看板生成器
==============================
将四个项目的交互式图表导出为单个静态 HTML 文件，
可直接部署到 GitHub Pages，无需 Python 服务器。

运行: python 可视化/build_static_site.py
输出: 可视化/index.html（自包含，可直接打开）
"""

import sys, os

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ============================================================
# 0. 配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
NOW = pd.Timestamp.now()

BG = "#1a1a2e"
CARD_BG = "#16213e"
BORDER = "#0f3460"
ACCENT = "#e94560"
PRIMARY = "#3498db"
SUCCESS = "#2ecc71"
WARNING = "#f39c12"
DANGER = "#e74c3c"
TEXT = "#ecf0f1"
MUTED = "#95a5a6"
PALETTE = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6",
            "#1abc9c", "#e67e22", "#2980b9", "#c0392b", "#27ae60"]

LAYOUT = {
    "paper_bgcolor": CARD_BG,
    "plot_bgcolor": "rgba(0,0,0,0.1)",
    "font": {"color": TEXT},
    "margin": {"l": 40, "r": 20, "t": 50, "b": 40},
    "legend": {"font": {"color": MUTED}},
    "xaxis": {"gridcolor": "rgba(255,255,255,0.05)", "color": MUTED},
    "yaxis": {"gridcolor": "rgba(255,255,255,0.05)", "color": MUTED},
}

print("=" * 60)
print("  跃动体育 · 静态 HTML 看板生成器")
print("=" * 60)


def safe_qcut(s, q, labels):
    aq = min(q, len(s.unique()))
    if aq < 2:
        return pd.Series([labels[-1]] * len(s), index=s.index)
    try:
        return pd.qcut(s, aq, labels=labels[-aq:], duplicates="drop")
    except ValueError:
        return pd.cut(s, bins=aq, labels=labels[-aq:])


def kpi_html(title, value, prefix="", suffix="", color=PRIMARY):
    display = f"{prefix}{value:,.0f}{suffix}" if isinstance(value, (int, float)) else f"{prefix}{value}{suffix}"
    return f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value" style="color:{color}">{display}</div>
    </div>"""


def chart_html(title, fig):
    fig.update_layout(**LAYOUT)
    fig.update_layout(title=dict(text=title, font=dict(color=TEXT, size=15)))
    return f"""
    <div class="chart-card">
        {fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": True, "displaylogo": False, "responsive": True})}
    </div>"""


def table_html(title, df, columns):
    header = "".join(f"<th>{c}</th>" for c in columns)
    rows = ""
    for _, row in df.iterrows():
        rows += "<tr>" + "".join(f"<td>{row[c]}</td>" for c in columns) + "</tr>"
    return f"""
    <div class="chart-card">
        <h4>{title}</h4>
        <div class="table-wrap">
            <table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>
        </div>
    </div>"""


# ============================================================
# 1. 加载 & 计算数据
# ============================================================

# ---------- 项目一 ----------
print("  [1/4] 项目一：日常运营...")
conn = sqlite3.connect(os.path.join(ROOT_DIR, "项目一：公司日常运营指标分析", "ecommerce_ops.db"))
ub = pd.read_sql("SELECT * FROM user_behavior", conn)
orders1 = pd.read_sql("SELECT * FROM orders", conn)
conn.close()
ub["create_time"] = pd.to_datetime(ub["create_time"])
orders1["create_time"] = pd.to_datetime(orders1["create_time"])

paid1 = orders1[orders1["order_status"].isin(["paid", "shipped", "completed"])]

P1_KPI = {
    "pv": len(ub), "uv": ub["user_id"].nunique(),
    "paid_users": paid1["user_id"].nunique(), "gmv": paid1["amount"].sum(),
}
P1_KPI["payment_rate"] = P1_KPI["paid_users"] / P1_KPI["uv"] if P1_KPI["uv"] > 0 else 0
P1_KPI["avg_order_value"] = P1_KPI["gmv"] / len(paid1) if len(paid1) > 0 else 0

# 日报
daily = ub.groupby(ub["create_time"].dt.date).agg(pv=("id", "count"), uv=("user_id", "nunique")).reset_index()
daily.columns = ["date", "pv", "uv"]
daily["date"] = pd.to_datetime(daily["date"])
dp = paid1.groupby(paid1["create_time"].dt.date).agg(
    paid_users=("user_id", "nunique"), gmv=("amount", "sum"), orders=("order_id", "count")).reset_index()
dp.columns = ["date", "paid_users", "gmv", "orders"]
dp["date"] = pd.to_datetime(dp["date"])
daily = daily.merge(dp, on="date", how="left").fillna(0)
daily["payment_rate"] = daily["paid_users"] / daily["uv"]
daily["avg_order_value"] = daily["gmv"] / daily["orders"].replace(0, np.nan)

# 近30天趋势
recent30 = daily.nlargest(30, "date").sort_values("date")
fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
fig_trend.add_trace(go.Scatter(x=recent30["date"], y=recent30["pv"], name="PV",
    mode="lines+markers", line=dict(color=PRIMARY, width=2)), secondary_y=False)
fig_trend.add_trace(go.Scatter(x=recent30["date"], y=recent30["uv"], name="UV",
    mode="lines+markers", line=dict(color=SUCCESS, width=2)), secondary_y=False)
fig_trend.add_trace(go.Scatter(x=recent30["date"], y=recent30["gmv"], name="GMV (元)",
    mode="lines+markers", line=dict(color=ACCENT, width=2)), secondary_y=True)
fig_trend.update_yaxes(title_text="用户数", secondary_y=False)
fig_trend.update_yaxes(title_text="GMV (元)", secondary_y=True)

# 漏斗
funnel_users = [ub[ub["action"] == a]["user_id"].nunique() for a in ["view", "add_to_cart", "place_order", "pay"]]
fig_funnel = go.Figure(go.Funnel(
    y=["浏览", "加购", "下单", "支付"], x=funnel_users,
    text=[f"{u:,}" for u in funnel_users],
    textposition="inside", textinfo="text+percent initial",
    marker=dict(color=[PRIMARY, WARNING, ACCENT, SUCCESS])))

# 转化率
rates = []
cn = ["浏览", "加购", "下单", "支付"]
for i in range(3):
    r = funnel_users[i + 1] / funnel_users[i] * 100 if funnel_users[i] > 0 else 0
    rates.append(f"{cn[i]}->{cn[i+1]}: {r:.1f}%")

# RFM
rfm = paid1.groupby("user_id").agg(last_purchase=("create_time", "max"),
    frequency=("order_id", "nunique"), monetary=("amount", "sum")).reset_index()
rfm["recency"] = (NOW - rfm["last_purchase"]).dt.days
rfm["r_score"] = safe_qcut(rfm["recency"], 5, [5, 4, 3, 2, 1])
rfm["f_score"] = safe_qcut(rfm["frequency"], 5, [1, 2, 3, 4, 5])
rfm["m_score"] = safe_qcut(rfm["monetary"], 5, [1, 2, 3, 4, 5])
score = rfm["r_score"].astype(int) + rfm["f_score"].astype(int) + rfm["m_score"].astype(int)
rfm["segment"] = np.select([score >= 12, score >= 9, score >= 6],
    ["高价值客户", "中高价值客户", "中价值客户"], default="低价值客户")
seg = rfm["segment"].value_counts().reset_index()
seg.columns = ["segment", "count"]
fig_pie = px.pie(seg, values="count", names="segment", hole=0.5, color_discrete_sequence=PALETTE)

# 近7天日报
recent7 = daily.nlargest(7, "date").sort_values("date", ascending=False).copy()
recent7["date"] = recent7["date"].dt.strftime("%Y-%m-%d")
recent7["payment_rate"] = (recent7["payment_rate"] * 100).round(1).astype(str) + "%"
recent7["gmv"] = recent7["gmv"].round(0).astype(int)
recent7["avg_order_value"] = recent7["avg_order_value"].round(1)

del ub, orders1, paid1, rfm
print("    [OK]")

# ---------- 项目二 ----------
print("  [2/4] 项目二：老用户健康...")
conn = sqlite3.connect(os.path.join(ROOT_DIR, "项目二：老用户激活与价值提升", "user_activation.db"))
users2 = pd.read_sql("SELECT * FROM users", conn)
orders2 = pd.read_sql("SELECT * FROM orders", conn)
items2 = pd.read_sql("SELECT * FROM order_items", conn)
prods2 = pd.read_sql("SELECT * FROM products", conn)
conn.close()
orders2["create_time"] = pd.to_datetime(orders2["create_time"])

valid2 = orders2[orders2["order_status"].isin(["paid", "shipped", "completed"])]
df2 = valid2.merge(items2, on="order_id", how="left").merge(prods2, on="product_id", how="left")
rfm2 = df2.dropna(subset=["order_id"]).groupby("user_id").agg(
    last_purchase=("create_time", "max"), frequency=("order_id", "nunique"),
    monetary=("amount", "sum"), category_diversity=("category_id", "nunique")).reset_index()
rfm2["recency"] = (NOW - rfm2["last_purchase"]).dt.days
rfm2["growth"] = rfm2["category_diversity"] * rfm2["frequency"]
rfm2["r_score"] = safe_qcut(rfm2["recency"], 5, [5, 4, 3, 2, 1])
rfm2["f_score"] = safe_qcut(rfm2["frequency"], 5, [1, 2, 3, 4, 5])
rfm2["m_score"] = safe_qcut(rfm2["monetary"], 5, [1, 2, 3, 4, 5])
rfm2["g_score"] = safe_qcut(rfm2["growth"], 5, [1, 2, 3, 4, 5])
score2 = (rfm2["r_score"].astype(int) + rfm2["f_score"].astype(int) +
          rfm2["m_score"].astype(int) + rfm2["g_score"].astype(int))
rfm2["segment"] = np.select([score2 >= 16, score2 >= 12, score2 >= 8],
    ["高价值深耕用户", "高潜唤醒用户", "成长型用户"], default="流失风险用户")

seg2 = rfm2.groupby("segment").agg(count=("user_id", "nunique"),
    avg_recency=("recency", "mean"), avg_frequency=("frequency", "mean"),
    avg_monetary=("monetary", "mean")).reset_index()

fig_donut = px.pie(seg2, values="count", names="segment", hole=0.6, color_discrete_sequence=PALETTE)

sgmv = rfm2.groupby("segment")["monetary"].sum().reset_index()
sgmv.columns = ["segment", "gmv"]
sgmv["pct"] = (sgmv["gmv"] / sgmv["gmv"].sum() * 100).round(1)
fig_bar = px.bar(sgmv, x="segment", y="gmv", text="pct", color="segment", color_discrete_sequence=PALETTE)
fig_bar.update_traces(texttemplate="%{text}%", textposition="outside")

# 月度趋势
user_seg = rfm2[["user_id", "segment"]]
oseg = valid2.merge(user_seg, on="user_id", how="inner")
oseg["month"] = oseg["create_time"].dt.strftime("%Y-%m")
monthly_seg = oseg.groupby(["month", "segment"])["amount"].sum().reset_index()
monthly_seg["month"] = pd.to_datetime(monthly_seg["month"] + "-01")
mt = monthly_seg.groupby("month")["amount"].sum().reset_index(name="total")
monthly_seg = monthly_seg.merge(mt, on="month")
monthly_seg["pct"] = monthly_seg["amount"] / monthly_seg["total"] * 100
fig_monthly = px.line(monthly_seg.sort_values("month"), x="month", y="pct", color="segment",
    color_discrete_sequence=PALETTE)
fig_monthly.update_traces(mode="lines+markers")

# 品类散点
ucats = df2.dropna(subset=["order_id"]).groupby("user_id").agg(
    cat_1_orders=("category_id", lambda x: (x == 1).sum()),
    cat_2_orders=("category_id", lambda x: (x == 2).sum()),
    total_orders=("order_id", "nunique")).reset_index()
ucats = ucats.merge(user_seg, on="user_id", how="left")
fig_scatter = px.scatter(ucats, x="cat_1_orders", y="cat_2_orders", color="segment",
    size="total_orders", color_discrete_sequence=PALETTE)

profile = seg2.round(1).copy()
profile.columns = ["分层", "人数", "平均Recency(天)", "平均购买频次", "平均消费金额"]

P2_KPI = {
    "total": len(rfm2),
    "high": len(rfm2[rfm2["segment"] == "高价值深耕用户"]),
    "grow": len(rfm2[rfm2["segment"] == "高潜唤醒用户"]),
    "churn": len(rfm2[rfm2["segment"] == "流失风险用户"]),
}
del users2, orders2, items2, prods2, valid2, df2, rfm2, oseg
print("    [OK]")

# ---------- 项目三 ----------
print("  [3/4] 项目三：投放 ROI...")
conn = sqlite3.connect(os.path.join(ROOT_DIR, "项目三：各平台ROI预算重新分配", "roi_allocation.db"))
camps = pd.read_sql("SELECT * FROM ad_campaigns", conn)
attr_data = pd.read_sql("SELECT * FROM attribution_data", conn)
conn.close()
camps["campaign_date"] = pd.to_datetime(camps["campaign_date"])

ps = camps.groupby("platform").agg(spend=("spend", "sum"), revenue=("revenue", "sum"),
    impressions=("impressions", "sum"), clicks=("clicks", "sum"),
    conversions=("conversions", "sum")).reset_index()
ps["ROI"] = ps["revenue"] / ps["spend"]
ps["CPC"] = ps["spend"] / ps["clicks"]
ps["CPA"] = ps["spend"] / ps["conversions"]

P3_KPI = {"spend": ps["spend"].sum(), "revenue": ps["revenue"].sum()}
P3_KPI["roi"] = P3_KPI["revenue"] / P3_KPI["spend"] if P3_KPI["spend"] > 0 else 0
P3_KPI["cpa"] = P3_KPI["spend"] / ps["conversions"].sum() if ps["conversions"].sum() > 0 else 0
P3_KPI["cpc"] = P3_KPI["spend"] / ps["clicks"].sum() if ps["clicks"].sum() > 0 else 0

fig_roi_bar = px.bar(ps.sort_values("ROI", ascending=False), x="platform", y="ROI",
    color="platform", text=ps["ROI"].round(2), color_discrete_sequence=PALETTE)
fig_roi_bar.update_traces(texttemplate="%{text}", textposition="outside")
fig_roi_bar.add_hline(y=1, line_dash="dash", line_color=DANGER,
    annotation_text="盈亏线 ROI=1", annotation_position="right")

avg_cpc = ps["CPC"].mean()
avg_roi = ps["ROI"].mean()
fig_quad = px.scatter(ps, x="CPC", y="ROI", size="spend", color="platform", text="platform",
    size_max=55, color_discrete_sequence=PALETTE)
fig_quad.add_hline(y=avg_roi, line_dash="dash", line_color=WARNING,
    annotation_text=f"平均 ROI={avg_roi:.2f}")
fig_quad.add_vline(x=avg_cpc, line_dash="dash", line_color=WARNING,
    annotation_text=f"平均 CPC=Y{avg_cpc:.2f}")

# 月度堆叠
camps["month"] = camps["campaign_date"].dt.strftime("%Y-%m")
mspend = camps.groupby(["month", "platform"])["spend"].sum().reset_index()
mspend["month"] = pd.to_datetime(mspend["month"] + "-01")
fig_stacked = px.bar(mspend.sort_values("month"), x="month", y="spend", color="platform",
    color_discrete_sequence=PALETTE)

# 归因
ac = attr_data.groupby("platform").agg(
    total_attributions=("user_id", "nunique"),
    last_click=("days_to_conversion", lambda x: (x <= 1).sum())).reset_index()
fig_attr = go.Figure()
fig_attr.add_trace(go.Bar(x=ac["platform"], y=ac["total_attributions"], name="归因转化", marker_color=PRIMARY))
fig_attr.add_trace(go.Bar(x=ac["platform"], y=ac["last_click"], name="末次点击", marker_color=ACCENT))

ps["spend_pct"] = (ps["spend"] / P3_KPI["spend"] * 100).round(1)
budget_table = ps[["platform", "spend", "revenue", "ROI", "CPC", "CPA", "spend_pct"]].round(2).copy()
budget_table.columns = ["平台", "花费", "收入", "ROI", "CPC", "CPA", "花费占比%"]

del camps, attr_data
print("    [OK]")

# ---------- 项目四 ----------
print("  [4/4] 项目四：产品健康度...")
conn = sqlite3.connect(os.path.join(ROOT_DIR, "项目四：产品组合分析", "product_portfolio.db"))
prods4 = pd.read_sql("SELECT * FROM products", conn)
sales4 = pd.read_sql("SELECT * FROM sales_data", conn)
inv4 = pd.read_sql("SELECT * FROM inventory_data", conn)
conn.close()
sales4["sale_date"] = pd.to_datetime(sales4["sale_date"])

ps4 = sales4.groupby("product_id").agg(total_volume=("sales_volume", "sum"),
    total_amount=("sales_amount", "sum")).reset_index()
pm = prods4.merge(ps4, on="product_id", how="left").fillna(0)
pm = pm.merge(inv4, on="product_id", how="left")
pm["gross_profit"] = pm["total_amount"] - pm["cost"] * pm["total_volume"]
pm["gross_margin"] = (pm["gross_profit"] / pm["total_amount"].replace(0, np.nan)).fillna(0)
pm["sell_through_rate"] = (pm["total_volume"] / (pm["total_volume"] + pm["current_stock"])).clip(0, 1)
pm["segment"] = np.select(
    [(pm["sell_through_rate"] > 0.55) & (pm["gross_margin"] > 0.35),
     (pm["sell_through_rate"] > 0.35) & (pm["gross_margin"] > 0.25),
     pm["sell_through_rate"] > 0.15],
    ["爆款", "畅销款", "一般款"], default="滞销款")
pm["inventory_value"] = pm["cost"] * pm["current_stock"]
pm["avg_daily"] = pm["total_volume"] / 30
pm["reorder_point"] = pm["avg_daily"] * pm["lead_time_days"] + pm["safety_stock"]
pm["suggested_reorder"] = np.ceil(pm["avg_daily"] * (pm["lead_time_days"] + 7) - pm["current_stock"]).clip(0)
pm["needs_replenishment"] = pm["current_stock"] < pm["reorder_point"]

P4_KPI = {
    "total": len(pm), "hit": len(pm[pm["segment"] == "爆款"]),
    "dead": len(pm[pm["segment"] == "滞销款"]),
    "stock_value": pm["inventory_value"].sum(), "replen": pm["needs_replenishment"].sum(),
}

color_map = {"爆款": SUCCESS, "畅销款": PRIMARY, "一般款": WARNING, "滞销款": DANGER}
fig_bubble = px.scatter(pm, x="sell_through_rate", y="gross_margin",
    size="total_amount", color="segment", text=pm["product_name"].str[:6], size_max=45,
    color_discrete_map=color_map)
fig_bubble.add_hline(y=0.3, line_dash="dash", line_color=MUTED, annotation_text="毛利率=30%")
fig_bubble.add_vline(x=0.4, line_dash="dash", line_color=MUTED, annotation_text="售罄率=40%")

sc4 = pm["segment"].value_counts().reset_index()
sc4.columns = ["segment", "count"]
fig_donut4 = px.pie(sc4, values="count", names="segment", hole=0.6, color="segment", color_discrete_map=color_map)

plat_sales = sales4.groupby("platform")["sales_amount"].sum().reset_index()
fig_platform_bar = px.bar(plat_sales.sort_values("sales_amount", ascending=False),
    x="platform", y="sales_amount", color="platform", text=plat_sales["sales_amount"].round(0),
    color_discrete_sequence=PALETTE)
fig_platform_bar.update_traces(texttemplate="Y%{text:,.0f}", textposition="outside")

# Top5 爆款
top5 = pm[pm["segment"] == "爆款"].nlargest(5, "total_amount")["product_id"]
ts = sales4[sales4["product_id"].isin(top5)].merge(pm[["product_id", "product_name"]], on="product_id")
tsd = ts.groupby(["sale_date", "product_name"])["sales_volume"].sum().reset_index()
tsd["sale_date"] = pd.to_datetime(tsd["sale_date"])
tsd = tsd.sort_values(["product_name", "sale_date"])
tsd["ma7"] = tsd.groupby("product_name")["sales_volume"].transform(lambda x: x.rolling(7, min_periods=1).mean())
fig_top5 = px.line(tsd, x="sale_date", y="ma7", color="product_name", color_discrete_sequence=PALETTE)

repl = pm[pm["needs_replenishment"]][
    ["product_name", "current_stock", "reorder_point", "suggested_reorder", "lead_time_days", "sell_through_rate", "segment"]
].copy()
repl.columns = ["产品名", "当前库存", "补货点", "建议补货量", "提前期(天)", "售罄率", "分级"]
repl = repl.sort_values("建议补货量", ascending=False)

del prods4, sales4, inv4, pm
print("    [OK]")

print("\n  生成静态 HTML...")


# ============================================================
# 2. 组装 HTML
# ============================================================

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>跃动体育 · 数据看板</title>
<script src="https://cdn.plot.ly/plotly-3.2.4.min.js"></script>
<style>
:root {{
    --bg: #1a1a2e; --card: #16213e; --border: #0f3460;
    --text: #ecf0f1; --muted: #95a5a6; --accent: #e94560;
    --primary: #3498db;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: var(--bg); font-family: "Microsoft YaHei","PingFang SC",sans-serif;
    color: var(--text); min-height: 100vh;
}}

/* 顶部栏 */
.header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 24px; background: var(--card);
    border-bottom: 2px solid var(--accent); flex-wrap: wrap; gap: 8px;
}}
.header h1 {{ font-size: clamp(16px, 2vw, 24px); }}
.header span {{ color: var(--muted); font-size: 13px; }}

/* 标签切换 */
.tabs {{
    display: flex; flex-wrap: wrap; gap: 2px;
    padding: 0 24px; background: var(--bg);
}}
.tab-btn {{
    background: var(--card); color: var(--muted); border: none;
    padding: 12px 20px; cursor: pointer; font-size: clamp(12px, 1vw, 14px);
    font-weight: bold; transition: all 0.2s;
}}
.tab-btn:hover {{ color: var(--text); }}
.tab-btn.active {{ background: var(--accent); color: #fff; }}

/* 内容区 */
.tab-content {{ display: none; padding: 16px 24px; }}
.tab-content.active {{ display: block; }}

/* KPI 行 */
.kpi-row {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }}
.kpi-card {{
    background: var(--card); border-radius: 8px; padding: 12px 16px;
    border: 1px solid var(--border); text-align: center;
    flex: 1 1 130px; min-width: 110px;
}}
.kpi-title {{ color: var(--muted); font-size: 12px; margin-bottom: 6px; }}
.kpi-value {{ font-size: clamp(18px, 2.5vw, 26px); font-weight: bold; }}

/* 图表容器 */
.chart-grid-2 {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 480px), 1fr));
    gap: 16px; margin-bottom: 16px;
}}
.chart-full {{ margin-bottom: 16px; }}
.chart-card {{
    background: var(--card); border-radius: 8px;
    border: 1px solid var(--border); padding: 12px;
}}
.chart-card h4 {{ font-size: 14px; margin-bottom: 8px; }}

/* 转化率条 */
.rate-bar {{
    background: var(--card); padding: 12px 16px; border-radius: 8px;
    font-size: clamp(12px, 1vw, 14px); margin-bottom: 16px;
}}

/* 表格 */
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: clamp(10px, 0.85vw, 12px); }}
th, td {{ padding: 8px 10px; border: 1px solid rgba(255,255,255,0.05); text-align: center; }}
th {{ background: var(--border); color: var(--text); font-weight: bold; }}
td {{ color: var(--text); }}

/* 响应式 */
@media (max-width: 768px) {{
    .chart-grid-2 {{ grid-template-columns: 1fr; }}
    .kpi-card {{ flex: 1 1 45% !important; }}
}}
@media (max-width: 480px) {{
    .kpi-card {{ flex: 1 1 100% !important; }}
}}
</style>
</head>
<body>

<div class="header">
    <h1>跃动体育 · 数据看板</h1>
    <span>数据生成: {NOW.strftime('%Y-%m-%d %H:%M')} | 200,000 用户 · 100 人规模 DTC 品牌</span>
</div>

<div class="tabs">
    <button class="tab-btn active" onclick="switchTab('tab1')">项目一：日常运营</button>
    <button class="tab-btn" onclick="switchTab('tab2')">项目二：老用户健康</button>
    <button class="tab-btn" onclick="switchTab('tab3')">项目三：投放 ROI</button>
    <button class="tab-btn" onclick="switchTab('tab4')">项目四：产品健康度</button>
</div>

<!-- ====== 项目一 ====== -->
<div id="tab1" class="tab-content active">
    <div class="kpi-row">
        {kpi_html("PV", P1_KPI["pv"], color=PRIMARY)}
        {kpi_html("UV", P1_KPI["uv"], color=SUCCESS)}
        {kpi_html("付费用户", P1_KPI["paid_users"], color=WARNING)}
        {kpi_html("GMV", P1_KPI["gmv"], prefix="Y", color=ACCENT)}
        {kpi_html("付费率", P1_KPI["payment_rate"]*100, suffix="%", color=PALETTE[4])}
        {kpi_html("客单价", P1_KPI["avg_order_value"], prefix="Y", color=PALETTE[5])}
    </div>
    <div class="chart-full">{chart_html("近 30 天 PV / UV / GMV 趋势", fig_trend)}</div>
    <div class="chart-grid-2">
        {chart_html("转化漏斗", fig_funnel)}
        {chart_html("RFM 客户分层占比", fig_pie)}
    </div>
    <div class="rate-bar">
        <strong>环节转化率：</strong> {" | ".join(rates)}
    </div>
    {table_html("近 7 天日报明细", recent7, ["date", "pv", "uv", "gmv", "payment_rate", "avg_order_value"])}
</div>

<!-- ====== 项目二 ====== -->
<div id="tab2" class="tab-content">
    <div class="kpi-row">
        {kpi_html("老用户总数", P2_KPI["total"], color=PRIMARY)}
        {kpi_html("高价值深耕", P2_KPI["high"], color=SUCCESS)}
        {kpi_html("高潜唤醒", P2_KPI["grow"], color=WARNING)}
        {kpi_html("流失风险", P2_KPI["churn"], color=DANGER)}
    </div>
    <div class="chart-grid-2">
        {chart_html("RFM-G 用户分层占比", fig_donut)}
        {chart_html("各分层 GMV 贡献", fig_bar)}
    </div>
    <div class="chart-full">{chart_html("各分层月度 GMV 占比趋势", fig_monthly)}</div>
    <div class="chart-grid-2">
        {chart_html("用户品类拓展分布", fig_scatter)}
        {table_html("分层画像", profile, ["分层", "人数", "平均Recency(天)", "平均购买频次", "平均消费金额"])}
    </div>
</div>

<!-- ====== 项目三 ====== -->
<div id="tab3" class="tab-content">
    <div class="kpi-row">
        {kpi_html("总花费", P3_KPI["spend"], prefix="Y", color=ACCENT)}
        {kpi_html("总收入", P3_KPI["revenue"], prefix="Y", color=SUCCESS)}
        {kpi_html("全域 ROI", P3_KPI["roi"], color=PRIMARY)}
        {kpi_html("平均 CPA", P3_KPI["cpa"], prefix="Y", color=WARNING)}
        {kpi_html("平均 CPC", P3_KPI["cpc"], prefix="Y", color=PALETTE[4])}
    </div>
    <div class="chart-grid-2">
        {chart_html("各平台 ROI 对比", fig_roi_bar)}
        {chart_html("四象限分析：CPC x ROI", fig_quad)}
    </div>
    <div class="chart-full">{chart_html("各平台月度花费趋势", fig_stacked)}</div>
    <div class="chart-grid-2">
        {chart_html("归因分析", fig_attr)}
        {table_html("预算分配明细", budget_table, ["平台", "花费", "收入", "ROI", "CPC", "CPA", "花费占比%"])}
    </div>
</div>

<!-- ====== 项目四 ====== -->
<div id="tab4" class="tab-content">
    <div class="kpi-row">
        {kpi_html("产品总数", P4_KPI["total"], color=PRIMARY)}
        {kpi_html("爆款数", P4_KPI["hit"], color=SUCCESS)}
        {kpi_html("滞销品数", P4_KPI["dead"], color=DANGER)}
        {kpi_html("库存总价值", P4_KPI["stock_value"], prefix="Y", color=ACCENT)}
        {kpi_html("需补货", P4_KPI["replen"], color=WARNING)}
    </div>
    <div class="chart-full">{chart_html("产品健康度气泡图", fig_bubble)}</div>
    <div class="chart-grid-2">
        {chart_html("产品分级占比", fig_donut4)}
        {chart_html("各平台销售金额", fig_platform_bar)}
    </div>
    <div class="chart-full">{chart_html("Top 5 爆款 7日移动平均趋势", fig_top5)}</div>
    {table_html("需补货产品清单 (Top 20)", repl.head(20), ["产品名", "当前库存", "补货点", "建议补货量", "提前期(天)", "售罄率", "分级"])}
</div>

<script>
function switchTab(tabId) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');
}}
</script>

</body>
</html>"""

# ============================================================
# 3. 写入文件
# ============================================================
output_path = os.path.join(BASE_DIR, "index.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = os.path.getsize(output_path) / 1024
print(f"\n  输出: {output_path}")
print(f"  大小: {size_kb:.0f} KB")
print()
print("  部署方式：")
print("    1. 直接双击 index.html 在浏览器中打开")
print("    2. 上传到 GitHub Pages 即可在线访问")
print("    3. 放到任何静态服务器（Nginx/Apache/OSS）都能用")
