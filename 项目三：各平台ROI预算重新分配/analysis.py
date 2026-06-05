"""
项目三：各平台ROI预算重新分配 — 完整分析流程
============================================
学习要点：
  1. 多平台投放效能对比分析
  2. 四象限分析法（流量成本 × 转化效率）
  3. 改进的边际 ROI 计算：使用多项式回归替代逐点差分
  4. 跨平台归因分析：末次点击 / 时间衰减归因模型
  5. 考虑边际效益递减的预算优化模型

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
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from datetime import datetime

sns.set_theme(style="whitegrid", context="talk", font="Microsoft YaHei")
plt.rcParams["axes.unicode_minus"] = False

DB_PATH = "roi_allocation.db"
REPORT_PATH = "各平台ROI预算重新分配分析报告.md"
CHART_PATH = "各平台ROI预算重新分配分析.png"


def calculate_marginal_roi_regression(df):
    """
    使用多项式回归计算各平台的边际 ROI 曲线。
    比原始的逐点差分方法更稳定、更有经济学意义。

    原理: revenue = f(spend)，边际ROI = f'(spend)
    对 spend-revenue 散点做二次多项式拟合: revenue = a*spend^2 + b*spend + c
    则边际 revenue = 2*a*spend + b，边际 ROI = 边际 revenue / 边际 spend = 2*a*spend + b

    返回每个平台的回归系数和当前边际ROI估计值。
    """
    results = {}
    for platform in df["platform"].unique():
        pdata = df[df["platform"] == platform].sort_values("spend")
        if len(pdata) < 4:
            continue

        X = pdata[["spend"]].values
        y = pdata["revenue"].values

        # 二次多项式: revenue = a*spend^2 + b*spend + c
        poly = PolynomialFeatures(degree=2, include_bias=True)
        X_poly = poly.fit_transform(X)

        model = LinearRegression()
        model.fit(X_poly, y)

        a, b, c = model.coef_[2], model.coef_[1], model.intercept_

        # 在当前平均花费水平下的边际 ROI
        avg_spend = X.mean()
        marginal_revenue = 2 * a * avg_spend + b
        marginal_roi = max(0, marginal_revenue)

        # 计算 R^2
        y_pred = model.predict(X_poly)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / max(ss_tot, 1e-10)

        results[platform] = {
            "a": a, "b": b, "c": c,
            "marginal_roi": marginal_roi,
            "r2": r2,
            "model": model,
            "poly": poly,
            "avg_spend": avg_spend,
            "spend_range": (X.min(), X.max()),
        }

    return results


def attribution_analysis(attr_df):
    """
    跨平台归因分析。

    实现两种归因模型：
    1. 末次点击归因（Last Click）：转化功劳全归最后一个触点
    2. 时间衰减归因（Time Decay）：越接近转化的触点获得越大权重

    返回各平台在两种模型下的贡献占比。
    """
    # 只取有转化的记录
    converted = attr_df.dropna(subset=["conversion_time"]).copy()

    if len(converted) == 0:
        return pd.DataFrame(), pd.DataFrame()

    # --- 末次点击归因 ---
    # 每个用户取 conversion_time 最近的那个触点
    last_click = (
        converted.sort_values("conversion_time")
        .groupby("user_id")
        .last()
        .reset_index()
    )
    last_click_attribution = (
        last_click.groupby("platform")
        .agg(last_click_conversions=("user_id", "count"))
        .reset_index()
    )

    # --- 时间衰减归因 ---
    # 权重 = 2 ^ (-days_to_conversion / halflife), halflife = 3 天
    halflife = 3
    converted["decay_weight"] = 2.0 ** (-converted["days_to_conversion"].fillna(30) / halflife)
    # 按用户归一化
    user_weights = converted.groupby("user_id")["decay_weight"].sum().reset_index(name="total_weight")
    converted = converted.merge(user_weights, on="user_id")
    converted["normalized_weight"] = converted["decay_weight"] / converted["total_weight"]

    time_decay_attribution = (
        converted.groupby("platform")
        .agg(time_decay_conversions=("normalized_weight", "sum"))
        .reset_index()
    )

    attribution = last_click_attribution.merge(time_decay_attribution, on="platform", how="outer").fillna(0)

    return attribution, converted


def optimize_budget(platform_metrics, marginal_roi_results, total_budget):
    """
    在给定总预算下，基于边际 ROI 递减规律优化分配。

    优化策略（贪心）：
    1. 初始均匀分配
    2. 每次迭代：从边际ROI最低的平台转移预算到边际ROI最高的平台
    3. 直到边际ROI趋于均衡，或总预算分配完毕

    简化版：直接用各平台 ROI 和边际 ROI 综合计算建议分配。
    """
    platforms = platform_metrics["platform"].tolist()
    n = len(platforms)

    # 当前分配
    current = platform_metrics.set_index("platform")["total_spend"].to_dict()
    total_current = sum(current.values())

    # 综合评分：ROI 权重 0.6 + 边际ROI 权重 0.4（归一化）
    roi_values = platform_metrics.set_index("platform")["ROI"]
    marginal_values = pd.Series({
        p: marginal_roi_results.get(p, {}).get("marginal_roi", 1.0)
        for p in platforms
    })

    roi_norm = roi_values / roi_values.sum()
    marginal_norm = marginal_values / marginal_values.sum()

    combined_score = 0.6 * roi_norm + 0.4 * marginal_norm
    suggested_share = combined_score / combined_score.sum()

    result = pd.DataFrame({
        "platform": platforms,
        "current_spend": [current[p] for p in platforms],
        "current_share": [current[p] / total_current for p in platforms],
        "suggested_share": suggested_share.values,
        "suggested_spend": [total_budget * s for s in suggested_share.values],
        "roi": roi_values.values,
        "marginal_roi": marginal_values.values,
    })

    return result


def main():
    print("=" * 60)
    print("  项目三：各平台 ROI 预算重新分配")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    # ================================================================
    # 1. 数据获取
    # ================================================================
    print("\n[1/5] 获取数据...")
    campaigns_df = pd.read_sql("SELECT * FROM ad_campaigns", conn)
    campaigns_df["campaign_date"] = pd.to_datetime(campaigns_df["campaign_date"])

    attr_df = pd.read_sql("SELECT * FROM attribution_data", conn)
    attr_df["event_time"] = pd.to_datetime(attr_df["event_time"])
    attr_df["conversion_time"] = pd.to_datetime(attr_df["conversion_time"])

    print(f"  广告数据: {len(campaigns_df)} 条 campaign")
    print(f"  归因数据: {len(attr_df)} 条触点记录")

    # ================================================================
    # 2. 各平台效能指标汇总
    # ================================================================
    print("\n[2/5] 计算各平台效能指标...")
    platform_metrics = (
        campaigns_df.groupby("platform")
        .agg(
            total_spend=("spend", "sum"),
            total_impressions=("impressions", "sum"),
            total_clicks=("clicks", "sum"),
            total_conversions=("conversions", "sum"),
            total_revenue=("revenue", "sum"),
        )
        .reset_index()
    )

    platform_metrics["CTR"] = platform_metrics["total_clicks"] / platform_metrics["total_impressions"]
    platform_metrics["CVR"] = platform_metrics["total_conversions"] / platform_metrics["total_clicks"]
    platform_metrics["CPA"] = platform_metrics["total_spend"] / platform_metrics["total_conversions"]
    platform_metrics["ROI"] = platform_metrics["total_revenue"] / platform_metrics["total_spend"]
    platform_metrics["CPC"] = platform_metrics["total_spend"] / platform_metrics["total_clicks"]
    platform_metrics["ARPU"] = platform_metrics["total_revenue"] / platform_metrics["total_conversions"]

    print("  各平台核心指标:")
    for _, row in platform_metrics.iterrows():
        print(f"    {row['platform']:6s}  "
              f"花费={row['total_spend']:>10,.0f}  ROI={row['ROI']:.2f}  "
              f"CPA={row['CPA']:.0f}  CPC={row['CPC']:.2f}")

    # ================================================================
    # 3. 边际 ROI 回归分析
    # ================================================================
    print("\n[3/5] 边际 ROI 回归分析...")
    marginal_results = calculate_marginal_roi_regression(campaigns_df)

    for plat, res in marginal_results.items():
        print(f"    {plat}: 当前边际ROI={res['marginal_roi']:.2f}  R^2={res['r2']:.3f}")

    # ================================================================
    # 4. 归因分析
    # ================================================================
    print("\n[4/5] 跨平台归因分析...")
    attribution, converted = attribution_analysis(attr_df)

    if len(attribution) > 0:
        print("  各平台归因贡献:")
        for _, row in attribution.iterrows():
            print(f"    {row['platform']:6s}  "
                  f"末次点击: {row['last_click_conversions']:>6,.0f}  "
                  f"时间衰减: {row['time_decay_conversions']:>8.1f}")

    # ================================================================
    # 5. 预算优化
    # ================================================================
    print("\n[5/5] 预算优化...")
    total_budget = platform_metrics["total_spend"].sum()
    optimization = optimize_budget(platform_metrics, marginal_results, total_budget)

    print("  预算分配建议:")
    for _, row in optimization.iterrows():
        change = (row["suggested_share"] - row["current_share"]) * 100
        direction = "+" if change > 0 else ""
        print(f"    {row['platform']:6s}: {row['current_share']:.0%} -> {row['suggested_share']:.0%} "
              f"({direction}{change:.1f}pp)  ROI={row['roi']:.2f}  边际ROI={row['marginal_roi']:.2f}")

    # 预估优化后全域 ROI
    suggested_revenue = sum(
        row["suggested_spend"] * row["roi"] for _, row in optimization.iterrows()
    )
    # 考虑边际递减：实际提升打 8 折
    realistic_revenue = suggested_revenue * 0.8 + sum(
        row["current_spend"] * row["roi"] for _, row in optimization.iterrows()
    ) * 0.2
    new_roi = realistic_revenue / total_budget
    current_roi = platform_metrics["total_revenue"].sum() / total_budget
    print(f"\n  全域 ROI: {current_roi:.2f} -> {new_roi:.2f} (预估提升 {(new_roi/current_roi-1):.1%})")

    # ================================================================
    # 可视化
    # ================================================================
    print("\n生成可视化...")
    fig, axes = plt.subplots(2, 3, figsize=(22, 14))

    # 图 1: 各平台 ROI 对比
    ax = axes[0, 0]
    colors_bar = sns.color_palette("Blues_r", len(platform_metrics))
    bars = ax.bar(platform_metrics["platform"], platform_metrics["ROI"], color=colors_bar, edgecolor="white")
    ax.axhline(1.0, color="red", linestyle="--", alpha=0.5, label="盈亏线 (ROI=1)")
    ax.set_title("各平台 ROI 对比", fontweight="bold")
    ax.set_ylabel("ROI")
    ax.legend()
    for bar, roi in zip(bars, platform_metrics["ROI"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{roi:.2f}", ha="center", fontweight="bold")

    # 图 2: 四象限分析
    ax = axes[0, 1]
    cpc_mean = platform_metrics["CPC"].mean()
    # 用 ROI 作为转化效率的代理
    roi_mean = platform_metrics["ROI"].mean()
    for _, row in platform_metrics.iterrows():
        ax.scatter(row["CPC"], row["ROI"], s=row["total_spend"] / 5000, alpha=0.7)
        ax.annotate(row["platform"], (row["CPC"], row["ROI"]),
                    fontsize=12, fontweight="bold",
                    xytext=(8, 8), textcoords="offset points")
    ax.axhline(roi_mean, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(cpc_mean, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("CPC (点击成本)")
    ax.set_ylabel("ROI")
    ax.set_title("四象限分析: CPC vs ROI", fontweight="bold")

    # 标注象限
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.text(cpc_mean * 0.6, roi_mean * 1.1, "低成本高回报\n(高效拉新场)",
            ha="center", fontsize=9, color="green", alpha=0.8)
    ax.text(cpc_mean * 1.4, roi_mean * 1.1, "高成本高回报\n(高价值种草地)",
            ha="center", fontsize=9, color="blue", alpha=0.8)
    ax.text(cpc_mean * 0.6, roi_mean * 0.85, "低成本低回报\n(低成本引流)",
            ha="center", fontsize=9, color="orange", alpha=0.8)
    ax.text(cpc_mean * 1.4, roi_mean * 0.85, "高成本低回报\n(需优化)",
            ha="center", fontsize=9, color="red", alpha=0.8)

    # 图 3: 边际 ROI 分析
    ax = axes[0, 2]
    x_plot = np.linspace(0, 80000, 100)
    colors_line = {"天猫": "#E91E63", "京东": "#2196F3", "得物": "#4CAF50", "抖音": "#FF9800"}
    for plat, res in marginal_results.items():
        poly = res["poly"]
        model = res["model"]
        X_plot_poly = poly.transform(x_plot.reshape(-1, 1))
        y_plot = model.predict(X_plot_poly)
        y_plot = np.maximum(y_plot, 0)
        ax.plot(x_plot, y_plot, color=colors_line.get(plat, "gray"),
                linewidth=2, label=f"{plat} (R^2={res['r2']:.2f})")

        # 标注当前花费位置
        ax.scatter([res["avg_spend"]], [model.predict(poly.transform([[res["avg_spend"]]]))[0]],
                   color=colors_line.get(plat, "gray"), s=100, zorder=5)

    ax.set_xlabel("花费")
    ax.set_ylabel("预估收入")
    ax.set_title("投入-产出曲线（含边际递减）", fontweight="bold")
    ax.legend(fontsize=9)

    # 图 4: 预算分配对比
    ax = axes[1, 0]
    x = np.arange(len(platform_metrics))
    width = 0.35
    ax.bar(x - width / 2, optimization["current_share"], width, label="当前", color="#90CAF9")
    ax.bar(x + width / 2, optimization["suggested_share"], width, label="建议", color="#1565C0")
    ax.set_xticks(x)
    ax.set_xticklabels(optimization["platform"])
    ax.set_ylabel("预算占比")
    ax.set_title("预算分配对比", fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend()

    # 图 5: 归因分析
    ax = axes[1, 1]
    if len(attribution) > 0:
        attr_plot = attribution.set_index("platform")
        attr_plot[["last_click_conversions", "time_decay_conversions"]].plot(
            kind="bar", ax=ax, color=["#42A5F5", "#FF7043"], edgecolor="white"
        )
        ax.set_title("跨平台归因：末次点击 vs 时间衰减", fontweight="bold")
        ax.set_ylabel("转化贡献")
        ax.legend(["末次点击归因", "时间衰减归因"], fontsize=9)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)

    # 图 6: CPA 对比
    ax = axes[1, 2]
    bars = ax.bar(platform_metrics["platform"], platform_metrics["CPA"], color=colors_bar, edgecolor="white")
    ax.set_title("各平台 CPA 对比", fontweight="bold")
    ax.set_ylabel("CPA (元)")
    for bar, cpa in zip(bars, platform_metrics["CPA"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                f"{cpa:.0f}", ha="center", fontweight="bold")

    fig.suptitle("各平台 ROI 预算重新分配分析看板", fontsize=18, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    print(f"  图表已保存: {CHART_PATH}")

    # ================================================================
    # 生成分析报告
    # ================================================================
    print("生成分析报告...")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 各平台 ROI 预算重新分配分析报告\n\n")
        f.write(f"> 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        f.write("## 1. 投放现状\n\n")
        f.write(f"| 指标 | 数值 |\n|------|------|\n")
        f.write(f"| 总预算 | {total_budget:,.0f} 元 |\n")
        f.write(f"| 总销售额 | {platform_metrics['total_revenue'].sum():,.0f} 元 |\n")
        f.write(f"| 全域 ROI | 1:{current_roi:.2f} |\n\n")

        f.write("## 2. 各平台表现\n\n")
        f.write("| 平台 | 花费 | 收入 | ROI | CTR | CVR | CPA | CPC |\n")
        f.write("|------|------|------|-----|-----|-----|-----|-----|\n")
        for _, row in platform_metrics.iterrows():
            f.write(f"| {row['platform']} | {row['total_spend']:,.0f} | {row['total_revenue']:,.0f} "
                    f"| {row['ROI']:.2f} | {row['CTR']:.2%} | {row['CVR']:.2%} "
                    f"| {row['CPA']:.0f} | {row['CPC']:.2f} |\n")

        f.write("\n## 3. 边际 ROI 分析\n\n")
        f.write("使用二次多项式回归 `revenue = a*spend^2 + b*spend + c` 拟合各平台投入-产出曲线。\n\n")
        f.write("| 平台 | 当前边际ROI | 模型R^2 | 投入区间 |\n")
        f.write("|------|-----------|---------|----------|\n")
        for plat, res in marginal_results.items():
            f.write(f"| {plat} | {res['marginal_roi']:.2f} | {res['r2']:.3f} "
                    f"| {res['spend_range'][0]:,.0f} - {res['spend_range'][1]:,.0f} |\n")

        f.write("\n## 4. 归因分析\n\n")
        if len(attribution) > 0:
            f.write("| 平台 | 末次点击转化 | 时间衰减转化 |\n")
            f.write("|------|------------|------------|\n")
            for _, row in attribution.iterrows():
                f.write(f"| {row['platform']} | {row['last_click_conversions']:,.0f} "
                        f"| {row['time_decay_conversions']:.1f} |\n")

        f.write("\n## 5. 预算优化建议\n\n")
        f.write("| 平台 | 当前占比 | 建议占比 | 调整幅度 | 当前花费 | 建议花费 | ROI |\n")
        f.write("|------|---------|---------|---------|---------|---------|-----|\n")
        for _, row in optimization.iterrows():
            change = (row["suggested_share"] - row["current_share"]) * 100
            direction = "+" if change > 0 else ""
            f.write(f"| {row['platform']} | {row['current_share']:.0%} | {row['suggested_share']:.0%} "
                    f"| {direction}{change:.1f}pp | {row['current_spend']:,.0f} "
                    f"| {row['suggested_spend']:,.0f} | {row['roi']:.2f} |\n")

        f.write(f"\n### 预期全域 ROI: 1:{new_roi:.2f}（提升 {(new_roi/current_roi-1):.1%}）\n")

        f.write("\n## 6. 实施计划\n\n")
        f.write("### 第一阶段（第1-2周）：小范围测试\n")
        f.write("- 将预算从低效渠道转移 10% 到高效渠道\n")
        f.write("- 建立实时监控看板，按日追踪指标变化\n\n")
        f.write("### 第二阶段（第3-4周）：逐步扩大\n")
        f.write("- 根据测试结果调整转移比例\n")
        f.write("- 优化各平台内的投放模式配比\n\n")
        f.write("### 第三阶段（第2个月起）：动态优化\n")
        f.write("- 建立月度预算复盘机制\n")
        f.write("- 引入季节性因子，动态调整平台权重\n")

    print(f"  报告已保存: {REPORT_PATH}")
    conn.close()
    print("\n" + "=" * 60)
    print("  分析完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
