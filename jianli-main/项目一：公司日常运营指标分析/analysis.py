"""
项目一：公司日常运营指标分析 — 完整分析流程
============================================
学习要点：
  1. pandas + SQLite 的数据分析标准流程
  2. 用户行为漏斗分析的正确实现方式
  3. RFM 客户价值分层（含 pd.qcut 重复值处理）
  4. 使用 np.select 替代 .apply(axis=1) 进行向量化分层
  5. matplotlib + seaborn 可视化最佳实践

运行前提：先运行 setup_database.py 生成数据库
运行方式：python analysis.py
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 非交互式后端，适配无 GUI 环境
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from datetime import datetime

# ── 全局样式设置 ──────────────────────────────────────────
sns.set_theme(style="whitegrid", context="talk", font="Microsoft YaHei")
plt.rcParams["axes.unicode_minus"] = False

DB_PATH = "ecommerce_ops.db"
REPORT_PATH = "日常运营指标分析报告.md"
CHART_PATH = "日常运营指标分析.png"

# ── 辅助函数 ──────────────────────────────────────────────


def safe_qcut(series, q, labels):
    """
    安全分箱：处理 pd.qcut 重复边界值问题。
    当数据存在大量相同值时，pd.qcut 会报 ValueError。
    使用 duplicates='drop' 后，实际分箱数可能少于 q，
    此时自动调整 labels 数量。
    """
    try:
        result, bins = pd.qcut(series, q, labels=labels, retbins=True, duplicates="drop")
    except ValueError:
        # 如果分箱数太少，退化为等距分箱
        result, bins = pd.cut(series, bins=min(q, len(series.unique())),
                              labels=labels[:min(q, len(series.unique()))],
                              retbins=True, duplicates="drop")
    return result


def classify_rfm(df):
    """
    使用 np.select 向量化进行 RFM 客户分层。
    比 .apply(axis=1) 快 10-50 倍。
    """
    score = df["r_score"].astype(int) + df["f_score"].astype(int) + df["m_score"].astype(int)
    conditions = [
        score >= 12,
        score >= 9,
        score >= 6,
    ]
    choices = ["高价值客户", "中高价值客户", "中价值客户"]
    return np.select(conditions, choices, default="低价值客户")


# ── 主分析流程 ────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  项目一：公司日常运营指标分析")
    print("=" * 60)

    # ================================================================
    # 1. 数据获取
    # ================================================================
    print("\n[1/6] 连接数据库并读取数据...")
    conn = sqlite3.connect(DB_PATH)

    # 使用 pandas read_sql —— 和 MySQL + pymysql 的用法完全一致
    user_behavior_df = pd.read_sql("SELECT * FROM user_behavior", conn)
    orders_df = pd.read_sql("SELECT * FROM orders", conn)

    user_behavior_df["create_time"] = pd.to_datetime(user_behavior_df["create_time"])
    orders_df["create_time"] = pd.to_datetime(orders_df["create_time"])

    print(f"  用户行为数据: {len(user_behavior_df):,} 条")
    print(f"  订单数据:     {len(orders_df):,} 条")

    # ================================================================
    # 2. 日 PV 和 UV 分析
    # ================================================================
    print("\n[2/6] 日 PV / UV 分析...")
    pv_uv_df = (
        user_behavior_df
        .groupby(user_behavior_df["create_time"].dt.date)
        .agg(pv=("id", "count"), uv=("user_id", "nunique"))
        .reset_index()
        .rename(columns={"create_time": "date"})
    )
    avg_pv = pv_uv_df["pv"].mean()
    avg_uv = pv_uv_df["uv"].mean()
    print(f"  日均 PV: {avg_pv:,.0f}   日均 UV: {avg_uv:,.0f}")

    # ================================================================
    # 3. 付费率分析
    # ================================================================
    print("\n[3/6] 付费率分析...")
    daily_users = (
        user_behavior_df
        .groupby(user_behavior_df["create_time"].dt.date)["user_id"]
        .nunique()
        .reset_index(name="total_users")
        .rename(columns={"create_time": "date"})
    )
    paid = orders_df[orders_df["order_status"].isin(["paid", "shipped", "completed"])]
    daily_paid = (
        paid.groupby(paid["create_time"].dt.date)["user_id"]
        .nunique()
        .reset_index(name="paid_users")
        .rename(columns={"create_time": "date"})
    )
    pay_rate_df = daily_users.merge(daily_paid, on="date", how="left")
    pay_rate_df["paid_users"] = pay_rate_df["paid_users"].fillna(0).astype(int)
    pay_rate_df["payment_rate"] = pay_rate_df["paid_users"] / pay_rate_df["total_users"]
    avg_pay_rate = pay_rate_df["payment_rate"].mean()
    print(f"  平均付费率: {avg_pay_rate:.2%}")

    # ================================================================
    # 4. 复购行为分析
    # ================================================================
    print("\n[4/6] 复购行为分析...")
    valid_orders = orders_df[orders_df["order_status"].isin(["paid", "shipped", "completed"])]
    repurchase_df = (
        valid_orders
        .groupby("user_id")
        .agg(order_count=("order_id", "nunique"), total_amount=("amount", "sum"))
        .reset_index()
        .query("order_count >= 2")
    )
    repurchase_rate = len(repurchase_df) / orders_df["user_id"].nunique()
    print(f"  复购用户数: {len(repurchase_df)}  复购率: {repurchase_rate:.2%}")
    if len(repurchase_df) > 0:
        print(f"  复购用户人均订单数: {repurchase_df['order_count'].mean():.1f}")

    # ================================================================
    # 5. 漏斗流失分析
    # ================================================================
    print("\n[5/6] 漏斗流失分析...")
    # 使用 pivot_table 构建用户-行为矩阵（比多层 lambda 更清晰）
    user_action_matrix = (
        user_behavior_df
        .pivot_table(index="user_id", columns="action", aggfunc="size", fill_value=0)
        .clip(upper=1)  # 二值化：有该行为 = 1
    )
    funnel_steps = ["view", "add_to_cart", "place_order", "pay"]
    funnel_data = []
    for step in funnel_steps:
        if step in user_action_matrix.columns:
            count = int(user_action_matrix[step].sum())
        else:
            count = 0
        funnel_data.append({"step": step, "user_count": count})

    funnel_df = pd.DataFrame(funnel_data)
    funnel_df["overall_conversion_rate"] = (
        funnel_df["user_count"] / funnel_df.loc[0, "user_count"]
    )
    funnel_df["step_conversion_rate"] = (
        funnel_df["user_count"] / funnel_df["user_count"].shift(1)
    )

    print("  漏斗各环节:")
    for _, row in funnel_df.iterrows():
        print(f"    {row['step']:>20s}: {row['user_count']:>6,}  "
              f"(整体转化 {row['overall_conversion_rate']:.1%}, "
              f"环节转化 {row['step_conversion_rate']:.1%})")

    # ================================================================
    # 6. RFM 客户价值分层
    # ================================================================
    print("\n[6/6] RFM 客户价值分层...")
    rfm_df = (
        valid_orders
        .groupby("user_id")
        .agg(
            last_purchase=("create_time", "max"),
            frequency=("order_id", "nunique"),
            monetary=("amount", "sum"),
        )
        .reset_index()
    )

    now = pd.Timestamp.now()
    rfm_df["recency"] = (now - rfm_df["last_purchase"]).dt.days
    rfm_df["frequency"] = rfm_df["frequency"].astype(int)
    rfm_df["monetary"] = rfm_df["monetary"].astype(float)

    # ---- 关键改进：safe_qcut 处理重复值 ----
    rfm_df["r_score"] = safe_qcut(rfm_df["recency"], 5, labels=[5, 4, 3, 2, 1])
    rfm_df["f_score"] = safe_qcut(rfm_df["frequency"], 5, labels=[1, 2, 3, 4, 5])
    rfm_df["m_score"] = safe_qcut(rfm_df["monetary"], 5, labels=[1, 2, 3, 4, 5])

    # ---- 关键改进：np.select 向量化分层 ----
    rfm_df["segment"] = classify_rfm(rfm_df)

    segment_stats = (
        rfm_df.groupby("segment")
        .agg(
            user_count=("user_id", "count"),
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
        )
        .round(1)
    )
    print("  客户分层结果:")
    for seg, row in segment_stats.iterrows():
        print(f"    {seg}: {int(row['user_count'])}人  "
              f"R={row['avg_recency']:.0f}天  F={row['avg_frequency']:.1f}次  M={row['avg_monetary']:.0f}元")

    # ================================================================
    # 可视化（4 合 1 仪表盘布局）
    # ================================================================
    print("\n生成可视化图表...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 图 1: PV/UV 趋势
    ax = axes[0, 0]
    ax.plot(pv_uv_df["date"], pv_uv_df["pv"], color="#2196F3", linewidth=2, label="PV")
    ax.plot(pv_uv_df["date"], pv_uv_df["uv"], color="#FF5722", linewidth=2, label="UV")
    ax.set_title("日 PV / UV 趋势", fontweight="bold")
    ax.legend(loc="upper right")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xlabel("日期")
    ax.set_ylabel("数量")

    # 图 2: 付费率趋势
    ax = axes[0, 1]
    ax.plot(pay_rate_df["date"], pay_rate_df["payment_rate"],
            color="#4CAF50", linewidth=2, marker="o")
    ax.axhline(avg_pay_rate, color="red", linestyle="--", alpha=0.7,
               label=f"均值 ({avg_pay_rate:.1%})")
    ax.set_title("付费率趋势", fontweight="bold")
    ax.legend()
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.set_xlabel("日期")
    ax.set_ylabel("付费率")

    # 图 3: 漏斗分析
    ax = axes[1, 0]
    colors = sns.color_palette("Blues_r", len(funnel_df))
    bars = ax.bar(range(len(funnel_df)), funnel_df["user_count"], color=colors, edgecolor="white")
    ax.set_xticks(range(len(funnel_df)))
    ax.set_xticklabels(funnel_df["step"], rotation=15)
    ax.set_title("转化漏斗", fontweight="bold")
    ax.set_ylabel("用户数")
    # 在柱子上标注转化率
    for i, (_, row) in enumerate(funnel_df.iterrows()):
        ax.text(i, row["user_count"] + max(funnel_df["user_count"]) * 0.02,
                f"{row['overall_conversion_rate']:.1%}",
                ha="center", fontsize=12, fontweight="bold")

    # 图 4: 客户分层饼图
    ax = axes[1, 1]
    seg_counts = rfm_df["segment"].value_counts()
    colors_pie = ["#1565C0", "#42A5F5", "#90CAF9", "#E3F2FD"]
    wedges, texts, autotexts = ax.pie(
        seg_counts.values, labels=seg_counts.index,
        autopct="%1.1f%%", colors=colors_pie,
        explode=(0.05, 0.02, 0, 0),
        textprops={"fontsize": 12}
    )
    ax.set_title("客户分层分布", fontweight="bold")

    fig.suptitle("公司日常运营指标分析看板", fontsize=18, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    print(f"  图表已保存: {CHART_PATH}")

    # ================================================================
    # 生成分析报告
    # ================================================================
    print("\n生成分析报告...")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 日常运营指标分析报告\n\n")
        f.write(f"> 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        f.write("## 1. 流量分析\n\n")
        f.write(f"| 指标 | 数值 |\n|------|------|\n")
        f.write(f"| 日均 PV | {avg_pv:,.0f} |\n")
        f.write(f"| 日均 UV | {avg_uv:,.0f} |\n")
        f.write(f"| 日均 PV/UV 比 | {avg_pv / max(avg_uv, 1):.1f} |\n\n")

        f.write("## 2. 转化漏斗\n\n")
        f.write("| 环节 | 用户数 | 整体转化率 | 环节转化率 |\n")
        f.write("|------|--------|-----------|-----------|\n")
        for _, row in funnel_df.iterrows():
            f.write(f"| {row['step']} | {row['user_count']:,} "
                    f"| {row['overall_conversion_rate']:.1%} "
                    f"| {row['step_conversion_rate']:.1%} |\n")

        f.write(f"\n**最大流失环节**: ")
        max_drop_idx = funnel_df["step_conversion_rate"].iloc[1:].idxmin()
        f.write(f"{funnel_df.loc[max_drop_idx, 'step']} "
                f"(环节转化率仅 {funnel_df.loc[max_drop_idx, 'step_conversion_rate']:.1%})\n\n")

        f.write("## 3. 复购分析\n\n")
        f.write(f"- 复购用户数: {len(repurchase_df)}\n")
        f.write(f"- 复购率: {repurchase_rate:.2%}\n")
        if len(repurchase_df) > 0:
            f.write(f"- 复购用户人均订单数: {repurchase_df['order_count'].mean():.1f}\n")
            f.write(f"- 复购用户人均消费: {repurchase_df['total_amount'].mean():.0f} 元\n")

        f.write("\n## 4. RFM 客户分层\n\n")
        f.write("| 分层 | 人数 | 占比 | 平均R(天) | 平均F(次) | 平均M(元) |\n")
        f.write("|------|------|------|-----------|-----------|----------|\n")
        for seg, row in segment_stats.iterrows():
            pct = row["user_count"] / len(rfm_df)
            f.write(f"| {seg} | {int(row['user_count'])} | {pct:.1%} "
                    f"| {row['avg_recency']:.0f} | {row['avg_frequency']:.1f} "
                    f"| {row['avg_monetary']:.0f} |\n")

        f.write("\n## 5. 建议与行动计划\n\n")
        f.write("### 转化提升\n")
        max_drop_step = funnel_df.loc[max_drop_idx, "step"]

        suggestions = {
            "view→add_to_cart": [
                "优化商品详情页，增加用户评价和实物视频",
                "在关键页面增加「限时优惠」和「库存紧张」标签，制造紧迫感",
            ],
            "add_to_cart→place_order": [
                "优化购物车页面的推荐算法，提升连带率",
                "针对加购但未下单的用户，4 小时后推送优惠券提醒",
            ],
            "place_order→pay": [
                "增加支付方式（花呗分期、微信支付等）降低支付门槛",
                "针对未支付订单，1 小时后推送「库存即将释放」提醒",
            ],
        }
        if max_drop_step in suggestions:
            for s in suggestions[max_drop_step]:
                f.write(f"- {s}\n")

        f.write("\n### 用户运营\n")
        high_value_pct = len(rfm_df[rfm_df["segment"] == "高价值客户"]) / max(len(rfm_df), 1)
        if high_value_pct < 0.15:
            f.write("- 高价值客户占比偏低，建议分析其购买偏好，通过会员体系提升忠诚度\n")
        low_value_cnt = len(rfm_df[rfm_df["segment"] == "低价值客户"])
        if low_value_cnt > len(rfm_df) * 0.3:
            f.write("- 低价值客户占比较高，可设计首单优惠阶梯券激活沉睡用户\n")

        f.write("\n### 流量运营\n")
        f.write("- 周末流量偏低时加大促销活动力度，平衡周内流量波动\n")
        f.write("- 监控各渠道来源的 PV/UV 质量，区分自然流量与付费流量的转化效率\n")

    print(f"  报告已保存: {REPORT_PATH}")

    # ── 收尾 ──
    conn.close()
    print("\n" + "=" * 60)
    print("  分析完成！")
    print(f"  图表: {CHART_PATH}")
    print(f"  报告: {REPORT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
