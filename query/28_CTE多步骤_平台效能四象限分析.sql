-- 第 28 题 ★★★  CTE
-- CTE 三步递进: 汇总 → 算KPI → 分层，分析各广告平台效能
-- 考点: CTE 链式定义 + NULLIF 防除零 + CASE WHEN 分层

WITH platform_summary AS (
    SELECT platform,
           SUM(spend)       AS total_spend,
           SUM(impressions) AS total_impressions,
           SUM(clicks)      AS total_clicks,
           SUM(conversions) AS total_conversions,
           SUM(revenue)     AS total_revenue
    FROM ad_campaigns
    GROUP BY platform
),
platform_kpi AS (
    SELECT platform, total_spend, total_revenue,
           ROUND(total_clicks * 1.0
               / NULLIF(total_impressions, 0), 4) AS ctr,
           ROUND(total_conversions * 1.0
               / NULLIF(total_clicks, 0), 4)      AS cvr,
           ROUND(total_spend * 1.0
               / NULLIF(total_conversions, 0), 2)  AS cpa,
           ROUND(total_revenue * 1.0
               / NULLIF(total_spend, 0), 2)        AS roi
    FROM platform_summary
)
SELECT platform, total_spend, total_revenue,
       roi, ctr, cvr, cpa,
       CASE
           WHEN roi >= 3.0 AND cpa < 50 THEN '高效拉新场'
           WHEN roi >= 2.0 THEN '高价值种草地'
           WHEN ctr >= 0.02 THEN '低成本引流'
           ELSE '需优化'
       END AS role
FROM platform_kpi
ORDER BY roi DESC;
