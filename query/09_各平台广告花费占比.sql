-- 第 9 题 ★★  聚合分组
-- 统计各平台广告花费及占比
-- 考点: 窗口函数 SUM() OVER () 计算全局总计

SELECT platform,
       SUM(spend)                                              AS total_spend,
       CONCAT(ROUND(SUM(spend) * 100.0
            / SUM(SUM(spend)) OVER (), 2), '%')                AS spend_pct
FROM ad_campaigns
GROUP BY platform
ORDER BY total_spend DESC;
