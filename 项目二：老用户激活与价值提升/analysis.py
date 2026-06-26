"""
项目二：老用户激活与价值提升 — 完整分析流程
============================================
学习要点：
  1. 多表 JOIN 的数据获取（pandas merge 替代 SQL JOIN 的两种方式）
  2. RFM-G 模型的构建：传统 RFM + 品类拓展成长性（G）维度
  3. np.select 向量化用户分层
  4. AB 测试的统计显著性检验（卡方检验 + 效应量）
  5. 分层运营策略的制定框架

运行前提：先运行 setup_database.py 生成数据库
运行方式：python analysis.py
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
from datetime import datetime

sns.set_theme(style="whitegrid", context="talk", font="Microsoft YaHei")
plt.rcParams["axes.unicode_minus"] = False

DB_PATH = "user_activation.db"
REPORT_PATH = "老用户激活与价值提升分析报告.md"
CHART_PATH = "../可视化/charts/项目二_老用户激活与价值提升分析.png"


def safe_qcut(series, q, labels):
    """安全分箱：处理 pd.qcut 重复边界值"""
    actual_q = min(q, len(series.unique()))
    if actual_q < 2:
        return pd.Series([labels[-1]] * len(series), index=series.index)
    actual_labels = labels[-actual_q:] if len(labels) >= actual_q else labels
    try:
        result = pd.qcut(series, actual_q, labels=actual_labels, duplicates="drop")
    except ValueError:
        result = pd.cut(series, bins=actual_q, labels=actual_labels)
    return result


def classify_rfmg(df):
    """
    使用 np.select 进行 RFM-G 用户分层（向量化，快 10-50 倍）
    """
    score = (
        df["r_score"].astype(int)
        + df["f_score"].astype(int)
        + df["m_score"].astype(int)
        + df["g_score"].astype(int)
    )
    conditions = [score >= 16, score >= 12, score >= 8]
    choices = ["高价值深耕用户", "高潜唤醒用户", "成长型用户"]
    return np.select(conditions, choices, default="流失风险用户")


def ab_test_analysis(conn):
    """
    AB 测试模拟分析：比较四种优惠策略的转化效果。

    实际工作中，这部分数据来自 CRM 系统的实验打点。
    这里模拟生成来展示分析方法。
    """
    np.random.seed(123)
    n_each = 200
    groups = {
        "对照组 (无优惠)": np.random.binomial(1, 0.08, n_each),
        "A组 (10%折扣券)": np.random.binomial(1, 0.14, n_each),
        "B组 (满199减30)": np.random.binomial(1, 0.18, n_each),
        "C组 (买一送一)": np.random.binomial(1, 0.22, n_each),
    }

    ab_results = []
    for name, conversions in groups.items():
        n = len(conversions)
        c = conversions.sum()
        ab_results.append({
            "group": name,
            "sample_size": n,
            "conversions": c,
            "conversion_rate": c / n,
        })

    ab_df = pd.DataFrame(ab_results)

    # 卡方检验：各组间转化率是否有显著差异
    observed = [[r["conversions"], r["sample_size"] - r["conversions"]] for r in ab_results]
    chi2, p_value, dof, _ = stats.chi2_contingency(observed)

    # 与对照组两两比较
    ctrl_rate = ab_results[0]["conversion_rate"]
    pairwise = []
    for r in ab_results[1:]:
        n1, c1 = ab_results[0]["sample_size"], ab_results[0]["conversions"]
        n2, c2 = r["sample_size"], r["conversions"]
        # 双样本比例 z 检验
        p_pool = (c1 + c2) / (n1 + n2)
        se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
        z = (r["conversion_rate"] - ctrl_rate) / max(se, 1e-10)
        p_val = 2 * (1 - stats.norm.cdf(abs(z)))
        lift = (r["conversion_rate"] - ctrl_rate) / ctrl_rate
        pairwise.append({
            "comparison": f"对照组 vs {r['group']}",
            "lift": lift,
            "p_value": p_val,
            "significant": p_val < 0.05,
        })

    return ab_df, chi2, p_value, pairwise


def main():
    print("=" * 60)
    print("  项目二：老用户激活与价值提升")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    # ================================================================
    # 1. 数据获取（多表关联）
    # ================================================================
    print("\n[1/5] 获取数据...")

    # 方式一：SQL JOIN 一次性获取宽表
    query = """
        SELECT
            u.user_id,
            u.registration_date,
            u.gender,
            u.age,
            o.order_id,
            o.amount,
            o.order_status,
            o.create_time,
            oi.product_id,
            oi.quantity,
            oi.price,
            p.product_name,
            p.category_id
        FROM users u
        LEFT JOIN orders o ON u.user_id = o.user_id AND o.order_status IN ('paid','shipped','completed')
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.product_id
        ORDER BY u.user_id, o.create_time
    """
    df_full = pd.read_sql(query, conn)
    df_full["registration_date"] = pd.to_datetime(df_full["registration_date"])
    df_full["create_time"] = pd.to_datetime(df_full["create_time"])

    # 活动数据
    activity_df = pd.read_sql("SELECT * FROM user_activities", conn)
    activity_df["activity_date"] = pd.to_datetime(activity_df["activity_date"])

    print(f"  宽表数据: {len(df_full):,} 行")
    print(f"  活动数据: {len(activity_df):,} 行")

    # ================================================================
    # 2. 特征工程：计算 RFM-G 指标
    # ================================================================
    print("\n[2/5] 计算 RFM-G 指标...")

    now = pd.Timestamp.now()

    # 按用户聚合 RFM 指标
    rfm = (
        df_full.dropna(subset=["order_id"])
        .groupby("user_id")
        .agg(
            last_purchase=("create_time", "max"),
            frequency=("order_id", "nunique"),
            monetary=("amount", "sum"),
            # G 维度：跨品类购买指标
            category_diversity=("category_id", "nunique"),
            category_2_orders=("category_id", lambda x: (x == 2).sum()),
            category_1_orders=("category_id", lambda x: (x == 1).sum()),
            category_2_amount=("amount", lambda x: x[df_full.loc[x.index, "category_id"] == 2].sum()),
        )
        .reset_index()
    )

    rfm["recency"] = (now - rfm["last_purchase"]).dt.days

    # 改进的 G 计算：不只考虑品类数量比，还考虑金额结构
    rfm["total_amount"] = rfm["monetary"]
    rfm["growth_ratio"] = rfm["category_2_orders"] / (rfm["category_1_orders"] + rfm["category_2_orders"] + 1e-6)
    rfm["growth_amount_pct"] = rfm["category_2_amount"] / (rfm["monetary"] + 1e-6)
    # 综合成长性 = 品类多样性 × (1 + 服装金额占比)
    rfm["growth"] = rfm["category_diversity"] * (1 + rfm["growth_amount_pct"])

    # 合并活动参与数据
    activity_summary = (
        activity_df.groupby("user_id")
        .agg(
            activity_count=("activity_id", "nunique"),
            participation_count=("is_participated", "sum"),
            participation_rate=("is_participated", "mean"),
        )
        .reset_index()
    )

    rfm = rfm.merge(activity_summary, on="user_id", how="left").fillna(0)

    print(f"  有效用户数: {len(rfm)}")
    print(f"  品类拓展用户占比: {(rfm['category_2_orders'] > 0).mean():.1%}")

    # ================================================================
    # 3. RFM-G 评分与分层
    # ================================================================
    print("\n[3/5] RFM-G 评分与用户分层...")

    rfm["r_score"] = safe_qcut(rfm["recency"], 5, labels=[5, 4, 3, 2, 1])
    rfm["f_score"] = safe_qcut(rfm["frequency"], 5, labels=[1, 2, 3, 4, 5])
    rfm["m_score"] = safe_qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5])
    rfm["g_score"] = safe_qcut(rfm["growth"], 5, labels=[1, 2, 3, 4, 5])

    rfm["segment"] = classify_rfmg(rfm)

    segment_profile = (
        rfm.groupby("segment")
        .agg(
            user_count=("user_id", "count"),
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            avg_growth=("growth", "mean"),
            avg_participation_rate=("participation_rate", "mean"),
            avg_cat2_orders=("category_2_orders", "mean"),
        )
        .round(2)
    )
    print("  分层结果:")
    for seg, row in segment_profile.iterrows():
        print(f"    {seg}: {int(row['user_count'])}人  "
              f"R={row['avg_recency']:.0f}d  F={row['avg_frequency']:.1f}  "
              f"M={row['avg_monetary']:.0f}  G={row['avg_growth']:.2f}")

    # ================================================================
    # 4. AB 测试分析
    # ================================================================
    print("\n[4/5] AB 测试分析...")
    ab_df, chi2, p_value, pairwise = ab_test_analysis(conn)

    print(f"  卡方检验: chi2={chi2:.2f}, p={p_value:.4f} {'***显著***' if p_value < 0.05 else '(不显著)'}")
    for pw in pairwise:
        sig_mark = "[显著]" if pw["significant"] else "[不显著]"
        print(f"    {pw['comparison']}: lift={pw['lift']:.1%}  p={pw['p_value']:.4f}  {sig_mark}")

    # ================================================================
    # 5. 可视化
    # ================================================================
    print("\n[5/5] 生成可视化...")
    fig, axes = plt.subplots(2, 3, figsize=(20, 14))

    # 图 1: 用户分层分布
    ax = axes[0, 0]
    seg_counts = rfm["segment"].value_counts()
    colors = ["#1565C0", "#42A5F5", "#90CAF9", "#E3F2FD"]
    ax.pie(seg_counts.values, labels=seg_counts.index, autopct="%1.1f%%",
           colors=colors, explode=(0.05, 0.02, 0, 0))
    ax.set_title("用户分层分布", fontweight="bold")

    # 图 2: 各分层 RFM-G 均值对比（雷达数据用柱状替代）
    ax = axes[0, 1]
    metrics = ["avg_frequency", "avg_monetary", "avg_growth", "avg_participation_rate"]
    labels_cn = ["购买频次", "消费金额", "品类成长性", "活动参与率"]
    x = np.arange(len(metrics))
    width = 0.2
    segments_ordered = ["高价值深耕用户", "高潜唤醒用户", "成长型用户", "流失风险用户"]
    for i, seg in enumerate(segments_ordered):
        if seg in segment_profile.index:
            vals = [segment_profile.loc[seg, m] for m in metrics]
            # 归一化以便比较
            max_vals = segment_profile[metrics].max()
            vals_norm = [v / max(max_vals.iloc[j], 1) for j, v in enumerate(vals)]
            ax.bar(x + i * width, vals_norm, width, label=seg, alpha=0.85)
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(labels_cn)
    ax.set_title("各分层特征对比（归一化）", fontweight="bold")
    ax.legend(fontsize=8)

    # 图 3: 品类拓展行为分析
    ax = axes[0, 2]
    for seg in segments_ordered:
        if seg in segment_profile.index:
            seg_data = rfm[rfm["segment"] == seg]
            ax.scatter(
                seg_data["category_1_orders"] + 0.5,
                seg_data["category_2_orders"] + 0.5,
                label=seg, alpha=0.6, s=40,
            )
    ax.set_xlabel("袜子品类订单数")
    ax.set_ylabel("服装品类订单数")
    ax.set_title("品类拓展散点图", fontweight="bold")
    ax.legend(fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")

    # 图 4: Recency 分布
    ax = axes[1, 0]
    for seg in segments_ordered:
        seg_data = rfm[rfm["segment"] == seg]
        ax.hist(seg_data["recency"], bins=30, alpha=0.5, label=seg)
    ax.set_xlabel("距上次购买天数")
    ax.set_ylabel("用户数")
    ax.set_title("Recency 分布 by 分层", fontweight="bold")
    ax.legend(fontsize=8)

    # 图 5: AB 测试结果
    ax = axes[1, 1]
    bar_colors = ["#90CAF9", "#42A5F5", "#1E88E5", "#1565C0"]
    bars = ax.bar(ab_df["group"], ab_df["conversion_rate"], color=bar_colors, edgecolor="white")
    ax.set_ylabel("转化率")
    ax.set_title("AB 测试：各实验组转化率", fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    for bar, rate in zip(bars, ab_df["conversion_rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{rate:.1%}", ha="center", fontweight="bold")
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")

    # 图 6: GMV 恢复模拟
    ax = axes[1, 2]
    months = ["7月", "8月", "9月", "10月", "11月(双十一)", "12月"]
    gmv_share_before = [32, 30, 28, 26, 24, 23]  # 老用户 GMV 占比下滑
    gmv_share_after = [28, 29, 30, 31, 33, 34]    # 干预后回升
    ax.plot(months, gmv_share_before, "o-", color="red", linewidth=2, label="干预前（下滑趋势）")
    ax.plot(months, gmv_share_after, "o-", color="green", linewidth=2, label="干预后（回升趋势）")
    ax.axvline(3.5, color="gray", linestyle="--", alpha=0.7, label="策略上线")
    ax.set_ylabel("老用户 GMV 占比 (%)")
    ax.set_title("老用户 GMV 占比趋势", fontweight="bold")
    ax.legend(fontsize=8)

    fig.suptitle("老用户激活与价值提升分析看板", fontsize=18, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    print(f"  图表已保存: {CHART_PATH}")

    # ================================================================
    # 生成分析报告
    # ================================================================
    print("生成分析报告...")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 老用户激活与价值提升分析报告\n\n")
        f.write(f"> 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        f.write("## 1. 老用户概况\n\n")
        f.write(f"- 老用户总数: {len(rfm)}\n")
        f.write(f"- 平均购买频次: {rfm['frequency'].mean():.1f} 次\n")
        f.write(f"- 平均消费金额: {rfm['monetary'].mean():.0f} 元\n")
        f.write(f"- 平均 Recency: {rfm['recency'].mean():.0f} 天\n")
        f.write(f"- 已拓展到服装品类用户: {(rfm['category_2_orders'] > 0).sum()} 人 ({(rfm['category_2_orders'] > 0).mean():.1%})\n\n")

        f.write("## 2. RFM-G 用户分层\n\n")
        f.write("| 分层 | 人数 | 占比 | 平均R(天) | 平均F(次) | 平均M(元) | 成长性G | 活动参与率 |\n")
        f.write("|------|------|------|-----------|-----------|----------|---------|----------|\n")
        for seg in ["高价值深耕用户", "高潜唤醒用户", "成长型用户", "流失风险用户"]:
            if seg in segment_profile.index:
                row = segment_profile.loc[seg]
                pct = row["user_count"] / len(rfm)
                f.write(f"| {seg} | {int(row['user_count'])} | {pct:.1%} "
                        f"| {row['avg_recency']:.0f} | {row['avg_frequency']:.1f} "
                        f"| {row['avg_monetary']:.0f} | {row['avg_growth']:.2f} "
                        f"| {row['avg_participation_rate']:.1%} |\n")

        f.write("\n## 3. AB 测试分析\n\n")
        f.write(f"### 整体显著性检验\n")
        f.write(f"- 卡方检验: chi2 = {chi2:.2f}, p = {p_value:.4f}\n")
        f.write(f"- 结论: 各组转化率{'存在' if p_value < 0.05 else '无'}显著差异\n\n")

        f.write("### 两两比较 (vs 对照组)\n")
        f.write("| 比较 | 提升幅度 | p值 | 显著性 |\n")
        f.write("|------|---------|-----|--------|\n")
        for pw in pairwise:
            sig = "Y" if pw["significant"] else "-"
            f.write(f"| {pw['comparison']} | {pw['lift']:+.1%} | {pw['p_value']:.4f} | {sig} |\n")

        f.write("\n## 4. 分层运营策略\n\n")
        f.write("### 高价值深耕用户\n")
        f.write("- 专属 VIP 权益 + 新品优先体验权\n")
        f.write("- 高端服装线定向推荐\n\n")

        f.write("### 高潜唤醒用户（核心目标群）\n")
        f.write("- 品类拓展券（袜子→服装跨品类优惠）\n")
        f.write("- 搭配购推荐：袜+服装组合套装\n")
        f.write("- 限时阶梯优惠：首单服装 8 折，第二单 7 折\n\n")

        f.write("### 成长型用户\n")
        f.write("- 品类教育内容（面料知识、穿搭指南）\n")
        f.write("- 低门槛试用：19.9 元体验装\n\n")

        f.write("### 流失风险用户\n")
        f.write("- 大力度召回券（满 99 减 25）\n")
        f.write("- 社交裂变：邀请好友得优惠\n")
        f.write("- 简化购买流程，减少下单摩擦\n\n")

        f.write("## 5. 预期效果\n\n")
        f.write("- 老用户复购率提升 6%\n")
        f.write("- 客单价提升 12%\n")
        f.write("- 老用户 GMV 占比回升 4-5 个百分点\n")

    print(f"  报告已保存: {REPORT_PATH}")

    conn.close()
    print("\n" + "=" * 60)
    print("  分析完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
