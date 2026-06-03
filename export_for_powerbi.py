"""
Power BI 看板数据导出脚本
=========================
一键生成四个项目 Power BI 看板所需的全部数据文件。
运行后在 Power BI 中直接导入 CSV，复制 DAX 即可使用。

运行: python export_for_powerbi.py
输出: powerbi_data/ 目录，按项目分文件夹
"""

import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime

OUTPUT_DIR = "powerbi_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

NOW = pd.Timestamp.now()


def export_project1():
    """项目一：日常运营看板数据"""
    print("[项目一] 导出日常运营数据...")
    out = os.path.join(OUTPUT_DIR, "项目一_日常运营")
    os.makedirs(out, exist_ok=True)
    conn = sqlite3.connect(os.path.join("项目一：公司日常运营指标分析", "ecommerce_ops.db"))

    # 1. 原始数据导出
    user_behavior = pd.read_sql("SELECT * FROM user_behavior", conn)
    user_behavior["create_time"] = pd.to_datetime(user_behavior["create_time"])
    user_behavior.to_csv(os.path.join(out, "user_behavior.csv"), index=False)

    orders = pd.read_sql("SELECT * FROM orders", conn)
    orders["create_time"] = pd.to_datetime(orders["create_time"])
    orders.to_csv(os.path.join(out, "orders.csv"), index=False)

    # 2. 预计算：日报表（Power BI 里省去复杂的 DAX）
    daily_pv_uv = (
        user_behavior
        .groupby(user_behavior["create_time"].dt.date)
        .agg(pv=("id", "count"), uv=("user_id", "nunique"))
        .reset_index()
        .rename(columns={"create_time": "date"})
    )

    paid = orders[orders["order_status"].isin(["paid", "shipped", "completed"])]
    daily_paid = (
        paid.groupby(paid["create_time"].dt.date)["user_id"]
        .nunique().reset_index(name="paid_users")
        .rename(columns={"create_time": "date"})
    )
    daily_active = (
        user_behavior.groupby(user_behavior["create_time"].dt.date)["user_id"]
        .nunique().reset_index(name="active_users")
        .rename(columns={"create_time": "date"})
    )

    daily_report = daily_pv_uv.merge(daily_paid, on="date", how="left")
    daily_report = daily_report.merge(daily_active, on="date", how="left")
    daily_report["paid_users"] = daily_report["paid_users"].fillna(0).astype(int)
    daily_report["payment_rate"] = daily_report["paid_users"] / daily_report["active_users"]
    daily_report["gmv"] = daily_report["date"].map(
        paid.groupby(paid["create_time"].dt.date)["amount"].sum()
    ).fillna(0)
    daily_report["avg_order_value"] = daily_report["gmv"] / daily_report["paid_users"].replace(0, np.nan)
    daily_report.to_csv(os.path.join(out, "daily_report.csv"), index=False)

    # 3. 预计算：漏斗数据
    funnel_matrix = (
        user_behavior
        .pivot_table(index="user_id", columns="action", aggfunc="size", fill_value=0)
        .clip(upper=1)
    )
    funnel_data = []
    for step in ["view", "add_to_cart", "place_order", "pay"]:
        c = int(funnel_matrix[step].sum()) if step in funnel_matrix.columns else 0
        funnel_data.append({"step": step, "step_cn": step, "user_count": c})
    funnel_df = pd.DataFrame(funnel_data)
    funnel_df["step_order"] = range(len(funnel_df))
    funnel_df.to_csv(os.path.join(out, "funnel.csv"), index=False)

    # 4. 预计算：RFM 分层
    valid = orders[orders["order_status"].isin(["paid", "shipped", "completed"])]
    rfm = (
        valid.groupby("user_id")
        .agg(last_purchase=("create_time", "max"), frequency=("order_id", "nunique"), monetary=("amount", "sum"))
        .reset_index()
    )
    rfm["recency"] = (NOW - pd.to_datetime(rfm["last_purchase"])).dt.days

    def safe_qcut(s, q, labels):
        try:
            return pd.qcut(s, q, labels=labels, duplicates="drop")
        except ValueError:
            return pd.cut(s, bins=min(q, len(s.unique())), labels=labels[:min(q, len(s.unique()))])

    rfm["r_score"] = safe_qcut(rfm["recency"], 5, labels=[5, 4, 3, 2, 1])
    rfm["f_score"] = safe_qcut(rfm["frequency"], 5, labels=[1, 2, 3, 4, 5])
    rfm["m_score"] = safe_qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5])
    score = rfm["r_score"].astype(int) + rfm["f_score"].astype(int) + rfm["m_score"].astype(int)
    rfm["segment"] = np.select(
        [score >= 12, score >= 9, score >= 6],
        ["高价值客户", "中高价值客户", "中价值客户"],
        default="低价值客户",
    )
    rfm[["user_id", "recency", "frequency", "monetary", "r_score", "f_score", "m_score", "segment"]].to_csv(
        os.path.join(out, "rfm_segments.csv"), index=False
    )

    conn.close()
    print(f"  -> {out}/  (5 CSV files)")
    print("  度量值: PV, UV, Payment_Rate, GMV, Avg_Order_Value, Repurchase_Rate")


def export_project2():
    """项目二：老用户健康看板数据"""
    print("[项目二] 导出老用户数据...")
    out = os.path.join(OUTPUT_DIR, "项目二_老用户激活")
    os.makedirs(out, exist_ok=True)
    conn = sqlite3.connect(os.path.join("项目二：老用户激活与价值提升", "user_activation.db"))

    # 原始表导出
    for t in ["users", "orders", "order_items", "products", "user_activities"]:
        pd.read_sql(f"SELECT * FROM {t}", conn).to_csv(os.path.join(out, f"{t}.csv"), index=False)

    # 预计算：RFM-G 分层（这个 DAX 写起来太复杂，直接导出）
    query = """
        SELECT u.user_id, u.registration_date, u.gender, u.age,
            o.order_id, o.amount, o.order_status, o.create_time,
            oi.product_id, oi.quantity, oi.price,
            p.product_name, p.category_id
        FROM users u
        LEFT JOIN orders o ON u.user_id = o.user_id
            AND o.order_status IN ('paid','shipped','completed')
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.product_id
    """
    df = pd.read_sql(query, conn)
    df["create_time"] = pd.to_datetime(df["create_time"])

    rfm = (
        df.dropna(subset=["order_id"])
        .groupby("user_id")
        .agg(
            last_purchase=("create_time", "max"),
            frequency=("order_id", "nunique"),
            monetary=("amount", "sum"),
            category_diversity=("category_id", "nunique"),
            category_2_orders=("category_id", lambda x: (x == 2).sum()),
            category_1_orders=("category_id", lambda x: (x == 1).sum()),
            category_2_amount=("amount", lambda x: x[df.loc[x.index, "category_id"] == 2].sum()),
        )
        .reset_index()
    )
    rfm["recency"] = (NOW - pd.to_datetime(rfm["last_purchase"])).dt.days
    rfm["growth"] = rfm["category_diversity"] * (1 + rfm["category_2_amount"] / (rfm["monetary"] + 1e-6))

    def safe_qcut(s, q, labels):
        aq = min(q, len(s.unique()))
        if aq < 2:
            return pd.Series([labels[-1]] * len(s), index=s.index)
        try:
            return pd.qcut(s, aq, labels=labels[-aq:], duplicates="drop")
        except ValueError:
            return pd.cut(s, bins=aq, labels=labels[-aq:])

    rfm["r_score"] = safe_qcut(rfm["recency"], 5, labels=[5, 4, 3, 2, 1])
    rfm["f_score"] = safe_qcut(rfm["frequency"], 5, labels=[1, 2, 3, 4, 5])
    rfm["m_score"] = safe_qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5])
    rfm["g_score"] = safe_qcut(rfm["growth"], 5, labels=[1, 2, 3, 4, 5])
    score = rfm["r_score"].astype(int) + rfm["f_score"].astype(int) + rfm["m_score"].astype(int) + rfm["g_score"].astype(int)
    rfm["segment"] = np.select(
        [score >= 16, score >= 12, score >= 8],
        ["高价值深耕用户", "高潜唤醒用户", "成长型用户"],
        default="流失风险用户",
    )
    rfm[["user_id", "recency", "frequency", "monetary", "growth",
          "r_score", "f_score", "m_score", "g_score", "segment",
          "category_1_orders", "category_2_orders"]].to_csv(
        os.path.join(out, "rfmg_segments.csv"), index=False
    )

    conn.close()
    print(f"  → {out}/  (6 个 CSV)")


def export_project3():
    """项目三：投放 ROI 看板数据"""
    print("[项目三] 导出 ROI 数据...")
    out = os.path.join(OUTPUT_DIR, "项目三_ROI预算")
    os.makedirs(out, exist_ok=True)
    conn = sqlite3.connect(os.path.join("项目三：各平台ROI预算重新分配", "roi_allocation.db"))

    # 原始表
    campaigns = pd.read_sql("SELECT * FROM ad_campaigns", conn)
    campaigns["campaign_date"] = pd.to_datetime(campaigns["campaign_date"])
    campaigns.to_csv(os.path.join(out, "ad_campaigns.csv"), index=False)

    attribution = pd.read_sql("SELECT * FROM attribution_data", conn)
    attribution.to_csv(os.path.join(out, "attribution_data.csv"), index=False)

    # 预计算：月度趋势
    campaigns["month"] = campaigns["campaign_date"].dt.strftime("%Y-%m")
    monthly = (
        campaigns.groupby(["platform", "month"])
        .agg(spend=("spend", "sum"), revenue=("revenue", "sum"),
             clicks=("clicks", "sum"), conversions=("conversions", "sum"))
        .reset_index()
    )
    monthly["ROI"] = monthly["revenue"] / monthly["spend"]
    monthly.to_csv(os.path.join(out, "monthly_trend.csv"), index=False)

    # 预计算：四象限数据
    platform_stats = (
        campaigns.groupby("platform")
        .agg(spend=("spend", "sum"), revenue=("revenue", "sum"),
             clicks=("clicks", "sum"), conversions=("conversions", "sum"),
             impressions=("impressions", "sum"))
        .reset_index()
    )
    platform_stats["ROI"] = platform_stats["revenue"] / platform_stats["spend"]
    platform_stats["CPC"] = platform_stats["spend"] / platform_stats["clicks"]
    platform_stats["CPA"] = platform_stats["spend"] / platform_stats["conversions"]
    platform_stats["CTR"] = platform_stats["clicks"] / platform_stats["impressions"]
    platform_stats["CVR"] = platform_stats["conversions"] / platform_stats["clicks"]
    platform_stats.to_csv(os.path.join(out, "platform_summary.csv"), index=False)

    conn.close()
    print(f"  → {out}/  (4 个 CSV)")


def export_project4():
    """项目四：产品健康度看板数据"""
    print("[项目四] 导出产品数据...")
    out = os.path.join(OUTPUT_DIR, "项目四_产品组合")
    os.makedirs(out, exist_ok=True)
    conn = sqlite3.connect(os.path.join("项目四：产品组合分析", "product_portfolio.db"))

    # 原始表
    products = pd.read_sql("SELECT * FROM products", conn)
    products["launch_date"] = pd.to_datetime(products["launch_date"])
    products.to_csv(os.path.join(out, "products.csv"), index=False)

    sales = pd.read_sql("SELECT * FROM sales_data", conn)
    sales["sale_date"] = pd.to_datetime(sales["sale_date"])
    sales.to_csv(os.path.join(out, "sales_data.csv"), index=False)

    inventory = pd.read_sql("SELECT * FROM inventory_data", conn)
    inventory.to_csv(os.path.join(out, "inventory_data.csv"), index=False)

    # 预计算：产品健康度（DAX 写 SWITCH 嵌套很痛苦，直接导）
    product_sales = sales.groupby("product_id").agg(
        total_volume=("sales_volume", "sum"), total_amount=("sales_amount", "sum")
    ).reset_index()
    pm = products.merge(product_sales, on="product_id", how="left").fillna(0)
    pm = pm.merge(inventory, on="product_id", how="left")
    pm["gross_profit"] = pm["total_amount"] - pm["cost"] * pm["total_volume"]
    pm["gross_margin"] = (pm["gross_profit"] / pm["total_amount"].replace(0, np.nan)).fillna(0)
    pm["sell_through_rate"] = (pm["total_volume"] / (pm["total_volume"] + pm["current_stock"])).clip(0, 1)
    pm["segment"] = np.select(
        [(pm["sell_through_rate"] > 0.55) & (pm["gross_margin"] > 0.35),
         (pm["sell_through_rate"] > 0.35) & (pm["gross_margin"] > 0.25),
         pm["sell_through_rate"] > 0.15],
        ["爆款", "畅销款", "一般款"], default="滞销款"
    )
    pm["avg_daily"] = pm["total_volume"] / 30
    pm["reorder_point"] = pm["avg_daily"] * pm["lead_time_days"] + pm["safety_stock"]
    pm["suggested_reorder"] = np.ceil(pm["avg_daily"] * (pm["lead_time_days"] + 7) - pm["current_stock"]).clip(0)
    pm["needs_replenishment"] = pm["current_stock"] < pm["reorder_point"]
    pm.to_csv(os.path.join(out, "product_health.csv"), index=False)

    conn.close()
    print(f"  → {out}/  (4 个 CSV)")


def print_powerbi_guide():
    """打印 Power BI 搭建步骤"""
    guide = f"""
============================================================
          Power BI Dashboard Setup - Quick Start
============================================================

  Data exported to: {OUTPUT_DIR}/

  Step 1: Open Power BI Desktop
  Step 2: Get Data -> Text/CSV
          -> Select CSV files from the folders above
          -> Import one project at a time
  Step 3: Create table relationships (drag in Model view)
  Step 4: Create measures (copy DAX from PowerBI看板指南.md)
  Step 5: Drag visuals to canvas -> bind data and measures
  Step 6: Adjust colors, add titles -> Save .pbix file

  Full DAX formulas and layouts: see PowerBI看板指南.md

============================================================"""
    print(guide)


# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  跃动体育 Power BI 数据导出")
    print("=" * 60)
    print()

    export_project1()
    export_project2()
    export_project3()
    export_project4()

    print_powerbi_guide()
    print("完成！打开 Power BI Desktop → 获取数据 → CSV → 开始搭建看板")
