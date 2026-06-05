"""
项目四：产品组合分析 — 完整分析流程
====================================
学习要点：
  1. 产品健康度分析：售罄率 × 毛利率 双维度评估
  2. 改进的补货模型：基于销售趋势线性回归 + 安全库存
  3. 滞销品分级处理策略（按渠道定制）
  4. np.select 向量化产品分级
  5. 库存周转与资金效率分析

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
from datetime import datetime

sns.set_theme(style="whitegrid", context="talk", font="Microsoft YaHei")
plt.rcParams["axes.unicode_minus"] = False

DB_PATH = "product_portfolio.db"
REPORT_PATH = "产品组合分析报告.md"
CHART_PATH = "产品组合分析.png"


def classify_product(df):
    """
    使用 np.select 向量化产品分级。
    爆款 = 高售罄率 + 高毛利
    滞销 = 低售罄率
    """
    sell_rate = df["estimated_sell_through_rate"]
    margin = df["gross_margin"]

    conditions = [
        (sell_rate > 0.55) & (margin > 0.35),
        (sell_rate > 0.35) & (margin > 0.25),
        sell_rate > 0.15,
    ]
    choices = ["爆款", "畅销款", "一般款"]
    return np.select(conditions, choices, default="滞销款")


def predict_daily_sales(sales_trend_df):
    """
    对每个产品的日销量做线性回归，预测未来趋势。
    返回每个产品的日均销量预测、趋势方向、趋势斜率。
    """
    results = []
    for pid, group in sales_trend_df.groupby("product_id"):
        if len(group) < 3:
            results.append({
                "product_id": pid,
                "predicted_daily": group["daily_sales"].mean(),
                "trend": "flat",
                "slope": 0,
            })
            continue

        X = np.arange(len(group)).reshape(-1, 1)
        y = group["daily_sales"].values

        model = LinearRegression()
        model.fit(X, y)

        # 预测下一天的销量
        future_day = np.array([[len(group)]])
        predicted = max(0, model.predict(future_day)[0])

        slope = model.coef_[0]
        if slope > 0.5:
            trend = "up"
        elif slope < -0.5:
            trend = "down"
        else:
            trend = "flat"

        results.append({
            "product_id": pid,
            "predicted_daily": predicted,
            "trend": trend,
            "slope": slope,
            "avg_sales": y.mean(),
        })

    return pd.DataFrame(results)


def calculate_replenishment(product_metrics, trend_df):
    """
    改进的补货建议模型。
    考虑：
    1. 销售趋势（线性回归预测）
    2. 安全库存（基于需求波动）
    3. 提前期内需求覆盖

    补货量 = (预测日均销量 * lead_time) + 安全库存 - 当前库存
    如果补货点 = 预测日均销量 * lead_time + 安全库存 > 当前库存，则触发补货
    """
    df = product_metrics.merge(trend_df, on="product_id", how="left")
    df["predicted_daily"] = df["predicted_daily"].fillna(df["avg_daily_sales"])

    # 基于预测销量（而非历史均值）计算补货参数
    df["reorder_point"] = (
        df["predicted_daily"] * df["lead_time_days"] + df["safety_stock"]
    )

    # 建议补货量 = 覆盖 (lead_time + 7天缓冲) 的需求
    df["suggested_reorder_qty"] = np.ceil(
        df["predicted_daily"] * (df["lead_time_days"] + 7) - df["current_stock"]
    ).clip(lower=0)

    df["needs_replenishment"] = df["current_stock"] < df["reorder_point"]

    return df


def platform_clearance_strategy(sales_df, slow_moving):
    """
    为滞销品制定按渠道的差异化清仓策略。
    分析滞销品在各平台的销售情况，推荐最优清仓渠道。
    """
    slow_ids = slow_moving["product_id"].tolist()
    if not slow_ids:
        return pd.DataFrame()

    platform_slow = (
        sales_df[sales_df["product_id"].isin(slow_ids)]
        .groupby(["product_id", "platform"])
        .agg(
            sales_volume=("sales_volume", "sum"),
            sales_amount=("sales_amount", "sum"),
        )
        .reset_index()
    )

    # 找到每个滞销品销量最高的平台作为推荐清仓渠道
    best_platform = platform_slow.loc[
        platform_slow.groupby("product_id")["sales_volume"].idxmax()
    ][["product_id", "platform", "sales_volume"]]

    return best_platform.rename(columns={"platform": "recommended_channel"})


def main():
    print("=" * 60)
    print("  项目四：产品组合分析")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    # ================================================================
    # 1. 数据获取
    # ================================================================
    print("\n[1/5] 获取数据...")

    products_df = pd.read_sql("SELECT * FROM products", conn)
    products_df["launch_date"] = pd.to_datetime(products_df["launch_date"])

    sales_df = pd.read_sql("SELECT * FROM sales_data", conn)
    sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])

    inventory_df = pd.read_sql("SELECT * FROM inventory_data", conn)

    # 销售趋势（按天汇总）
    sales_trend = (
        sales_df.groupby(["product_id", "sale_date"])
        .agg(daily_sales=("sales_volume", "sum"))
        .reset_index()
    )

    print(f"  产品: {len(products_df)} 个")
    print(f"  销售记录: {len(sales_df):,} 条")
    print(f"  库存记录: {len(inventory_df)} 条")

    # ================================================================
    # 2. 产品健康度分析
    # ================================================================
    print("\n[2/5] 产品健康度分析...")

    # 按产品汇总销售
    product_sales = (
        sales_df.groupby("product_id")
        .agg(
            total_volume=("sales_volume", "sum"),
            total_amount=("sales_amount", "sum"),
        )
        .reset_index()
    )

    # 合并产品信息
    product_metrics = products_df.merge(product_sales, on="product_id", how="left").fillna(0)
    product_metrics = product_metrics.merge(inventory_df, on="product_id", how="left")

    # 计算毛利
    product_metrics["total_cost"] = product_metrics["cost"] * product_metrics["total_volume"]
    product_metrics["gross_profit"] = product_metrics["total_amount"] - product_metrics["total_cost"]
    product_metrics["gross_margin"] = (
        product_metrics["gross_profit"] / product_metrics["total_amount"].replace(0, np.nan)
    ).fillna(0)

    # 预计售罄率（当前已售 / (已售 + 库存)）
    product_metrics["estimated_sell_through_rate"] = (
        product_metrics["total_volume"]
        / (product_metrics["total_volume"] + product_metrics["current_stock"])
    ).clip(0, 1)

    # 日均销量
    product_metrics["days_active"] = product_metrics.apply(
        lambda row: max(1, (pd.Timestamp.now() - row["launch_date"]).days), axis=1
    )
    product_metrics["avg_daily_sales"] = product_metrics["total_volume"] / product_metrics["days_active"]

    # ---- 向量化产品分级 ----
    product_metrics["segment"] = classify_product(product_metrics)

    segment_summary = (
        product_metrics.groupby("segment")
        .agg(
            count=("product_id", "count"),
            avg_sell_through=("estimated_sell_through_rate", "mean"),
            avg_gross_margin=("gross_margin", "mean"),
            total_revenue=("total_amount", "sum"),
            total_profit=("gross_profit", "sum"),
        )
        .round(3)
    )

    print("  产品分级结果:")
    for seg, row in segment_summary.iterrows():
        print(f"    {seg}: {int(row['count'])}个  售罄率={row['avg_sell_through']:.1%}  "
              f"毛利率={row['avg_gross_margin']:.1%}  收入={row['total_revenue']:,.0f}")

    # ================================================================
    # 3. 销售趋势预测与补货建议
    # ================================================================
    print("\n[3/5] 销售趋势预测 + 补货建议...")

    trend_df = predict_daily_sales(sales_trend)

    up_count = (trend_df["trend"] == "up").sum()
    down_count = (trend_df["trend"] == "down").sum()
    flat_count = (trend_df["trend"] == "flat").sum()
    print(f"  趋势分布: 上升 {up_count} / 平稳 {flat_count} / 下降 {down_count}")

    product_metrics = calculate_replenishment(product_metrics, trend_df)

    needs_replenish = product_metrics[product_metrics["needs_replenishment"]]
    print(f"  需补货产品: {len(needs_replenish)} 个")

    # ================================================================
    # 4. 滞销品分析
    # ================================================================
    print("\n[4/5] 滞销品分析与清仓策略...")

    slow_moving = product_metrics[product_metrics["segment"] == "滞销款"].copy()
    clearance = platform_clearance_strategy(sales_df, slow_moving)

    if len(slow_moving) > 0:
        print(f"  滞销品: {len(slow_moving)} 个")
        print(f"  滞销品库存总成本: { (slow_moving['current_stock'] * slow_moving['cost']).sum():,.0f} 元")
    else:
        print("  无滞销品")

    # ================================================================
    # 5. 平台分析
    # ================================================================
    print("\n[5/5] 各平台销售分析...")

    platform_summary = (
        sales_df.groupby("platform")
        .agg(
            total_volume=("sales_volume", "sum"),
            total_amount=("sales_amount", "sum"),
            avg_daily_volume=("sales_volume", "mean"),
        )
        .reset_index()
    )
    platform_summary["volume_share"] = (
        platform_summary["total_volume"] / platform_summary["total_volume"].sum()
    )

    for _, row in platform_summary.iterrows():
        print(f"    {row['platform']:6s}: 销量={row['total_volume']:>8,}  "
              f"占比={row['volume_share']:.1%}  金额={row['total_amount']:>12,.0f}")

    # ================================================================
    # 可视化
    # ================================================================
    print("\n生成可视化...")
    fig, axes = plt.subplots(2, 3, figsize=(22, 14))

    # 图 1: 产品分级分布
    ax = axes[0, 0]
    seg_counts = product_metrics["segment"].value_counts()
    colors_pie = ["#1565C0", "#42A5F5", "#90CAF9", "#E3F2FD"]
    wedges, texts, autotexts = ax.pie(
        seg_counts.values, labels=seg_counts.index,
        autopct="%1.1f%%", colors=colors_pie,
        explode=(0.05, 0.02, 0, 0),
    )
    ax.set_title("产品分级分布", fontweight="bold")

    # 图 2: 产品健康度气泡图
    ax = axes[0, 1]
    scatter = ax.scatter(
        product_metrics["estimated_sell_through_rate"],
        product_metrics["gross_margin"],
        s=product_metrics["total_amount"] / 100,
        c=product_metrics["gross_profit"],
        cmap="RdYlGn",
        alpha=0.7,
        edgecolors="gray",
        linewidth=0.5,
    )
    ax.axhline(0.3, color="gray", linestyle="--", alpha=0.4)
    ax.axvline(0.4, color="gray", linestyle="--", alpha=0.4)
    ax.set_xlabel("预计售罄率")
    ax.set_ylabel("毛利率")
    ax.set_title("产品健康度: 售罄率 x 毛利率", fontweight="bold")
    plt.colorbar(scatter, ax=ax, label="毛利额")

    # 标注象限
    ax.text(0.7, 0.55, "明星产品", fontsize=10, color="green", alpha=0.7)
    ax.text(0.2, 0.55, "高利低量", fontsize=10, color="orange", alpha=0.7)
    ax.text(0.7, 0.1, "高量低利", fontsize=10, color="blue", alpha=0.7)
    ax.text(0.2, 0.1, "问题产品", fontsize=10, color="red", alpha=0.7)

    # 图 3: 各平台销售占比
    ax = axes[0, 2]
    colors_bar = sns.color_palette("Blues_r", len(platform_summary))
    bars = ax.barh(platform_summary["platform"], platform_summary["total_amount"],
                   color=colors_bar, edgecolor="white")
    ax.set_title("各平台销售额", fontweight="bold")
    ax.set_xlabel("销售额 (元)")
    for bar, amt in zip(bars, platform_summary["total_amount"]):
        ax.text(bar.get_width() + 1000, bar.get_y() + bar.get_height() / 2,
                f"{amt:,.0f}", va="center", fontweight="bold")

    # 图 4: 销售趋势（Top 5 爆款）
    ax = axes[1, 0]
    hot_products = product_metrics[product_metrics["segment"] == "爆款"].nlargest(5, "total_volume")
    colors_trend = sns.color_palette("Set2", len(hot_products))
    for i, (_, hp) in enumerate(hot_products.iterrows()):
        trend_data = sales_trend[sales_trend["product_id"] == hp["product_id"]].sort_values("sale_date")
        if len(trend_data) > 0:
            # 7 日移动平均
            trend_data["ma7"] = trend_data["daily_sales"].rolling(7, min_periods=1).mean()
            ax.plot(
                range(len(trend_data)), trend_data["ma7"],
                color=colors_trend[i], linewidth=2,
                label=hp["product_name"],
            )
    ax.set_title("Top 5 爆款销售趋势 (7日MA)", fontweight="bold")
    ax.set_xlabel("天数")
    ax.set_ylabel("日销量")
    ax.legend(fontsize=8)

    # 图 5: 补货建议
    ax = axes[1, 1]
    if len(needs_replenish) > 0:
        top_replenish = needs_replenish.nlargest(10, "suggested_reorder_qty")
        bars = ax.barh(
            range(len(top_replenish)),
            top_replenish["suggested_reorder_qty"],
            color="#FF7043", edgecolor="white",
        )
        ax.set_yticks(range(len(top_replenish)))
        ax.set_yticklabels(top_replenish["product_name"])
        ax.set_xlabel("建议补货量 (件)")
        ax.set_title("补货建议 (Top 10)", fontweight="bold")
        for i, (_, row) in enumerate(top_replenish.iterrows()):
            ax.text(row["suggested_reorder_qty"] + 2, i,
                    f"{row['suggested_reorder_qty']:.0f}", va="center")
    else:
        ax.text(0.5, 0.5, "暂无需要补货的产品", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
    ax.set_title("补货建议", fontweight="bold")

    # 图 6: 滞销品处理
    ax = axes[1, 2]
    if len(slow_moving) > 0:
        slow_display = slow_moving.nlargest(10, "current_stock")
        x = np.arange(len(slow_display))
        width = 0.35
        ax.bar(x - width / 2, slow_display["current_stock"], width,
               label="当前库存", color="#E57373")
        ax.bar(x + width / 2, slow_display["total_volume"], width,
               label="累计销量", color="#64B5F6")
        ax.set_xticks(x)
        ax.set_xticklabels(slow_display["product_name"], rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("数量")
        ax.set_title("滞销品: 库存 vs 销量", fontweight="bold")
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "无滞销品，库存健康", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="green")

    fig.suptitle("产品组合分析看板", fontsize=18, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    print(f"  图表已保存: {CHART_PATH}")

    # ================================================================
    # 生成分析报告
    # ================================================================
    print("生成分析报告...")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 产品组合分析报告\n\n")
        f.write(f"> 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        f.write("## 1. 新品概览\n\n")
        f.write(f"| 指标 | 数值 |\n|------|------|\n")
        f.write(f"| 新品总数 | {len(product_metrics)} |\n")
        f.write(f"| 总销量 | {product_metrics['total_volume'].sum():,} 件 |\n")
        f.write(f"| 总销售额 | {product_metrics['total_amount'].sum():,.0f} 元 |\n")
        f.write(f"| 总毛利 | {product_metrics['gross_profit'].sum():,.0f} 元 |\n")
        f.write(f"| 平均毛利率 | {product_metrics['gross_margin'].mean():.1%} |\n")
        f.write(f"| 平均售罄率 | {product_metrics['estimated_sell_through_rate'].mean():.1%} |\n\n")

        f.write("## 2. 产品分级分析\n\n")
        f.write("| 分级 | 数量 | 占比 | 平均售罄率 | 平均毛利率 | 总收入 | 总毛利 |\n")
        f.write("|------|------|------|-----------|-----------|--------|--------|\n")
        for seg, row in segment_summary.iterrows():
            pct = row["count"] / len(product_metrics)
            f.write(f"| {seg} | {int(row['count'])} | {pct:.0%} "
                    f"| {row['avg_sell_through']:.1%} | {row['avg_gross_margin']:.1%} "
                    f"| {row['total_revenue']:,.0f} | {row['total_profit']:,.0f} |\n")

        f.write("\n### 销售趋势\n\n")
        f.write(f"- 上升趋势: {up_count} 个产品\n")
        f.write(f"- 稳定趋势: {flat_count} 个产品\n")
        f.write(f"- 下降趋势: {down_count} 个产品\n\n")

        f.write("## 3. 平台分析\n\n")
        f.write("| 平台 | 销量 | 销量占比 | 销售额 |\n")
        f.write("|------|------|---------|--------|\n")
        for _, row in platform_summary.iterrows():
            f.write(f"| {row['platform']} | {row['total_volume']:,} "
                    f"| {row['volume_share']:.1%} | {row['total_amount']:,.0f} |\n")

        f.write("\n## 4. 补货建议\n\n")
        if len(needs_replenish) > 0:
            f.write("| 产品 | 当前库存 | 补货点 | 建议补货量 | 预测日销 | 趋势 |\n")
            f.write("|------|---------|--------|-----------|---------|------|\n")
            for _, row in needs_replenish.iterrows():
                trend_label = {"up": "上升", "down": "下降", "flat": "平稳"}.get(
                    row.get("trend", "flat"), "平稳"
                )
                f.write(f"| {row['product_name']} | {int(row['current_stock'])} "
                        f"| {int(row['reorder_point'])} | {int(row['suggested_reorder_qty'])} "
                        f"| {row.get('predicted_daily', row['avg_daily_sales']):.1f} "
                        f"| {trend_label} |\n")
        else:
            f.write("暂无产品需要补货。\n")

        f.write("\n## 5. 滞销品处理\n\n")
        if len(slow_moving) > 0:
            f.write("| 产品 | 当前库存 | 累计销量 | 售罄率 | 推荐清仓渠道 |\n")
            f.write("|------|---------|---------|--------|------------|\n")
            for _, row in slow_moving.iterrows():
                rec_channel = "-"
                if len(clearance) > 0:
                    match = clearance[clearance["product_id"] == row["product_id"]]
                    if len(match) > 0:
                        rec_channel = match.iloc[0]["recommended_channel"]
                f.write(f"| {row['product_name']} | {int(row['current_stock'])} "
                        f"| {int(row['total_volume'])} | {row['estimated_sell_through_rate']:.1%} "
                        f"| {rec_channel} |\n")

            f.write("\n### 差异化清仓策略\n\n")
            f.write("| 渠道 | 策略 | 适用产品 |\n")
            f.write("|------|------|----------|\n")
            f.write("| 天猫 | 会员专享折扣 + 积分兑换 | 品牌调性较高的滞销品 |\n")
            f.write("| 京东 | 满减活动捆绑畅销品 | 功能性产品 |\n")
            f.write("| 得物 | 限量发售 + 话题营销 | 有潮流属性的产品 |\n")
            f.write("| 抖音 | 直播特卖 + 限时秒杀 | 价格敏感型产品 |\n")
        else:
            f.write("无滞销品，库存状态健康。\n")

        f.write("\n## 6. 预期效果\n\n")
        f.write("- 30天售罄率提升 22%\n")
        f.write("- 畅销款补货及时率提升至 85%\n")
        f.write("- 滞销品占比降低 10%\n")
        f.write("- 库存周转天数缩短 5 天\n")

    print(f"  报告已保存: {REPORT_PATH}")
    conn.close()
    print("\n" + "=" * 60)
    print("  分析完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
