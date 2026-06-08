-- 第 7 题 ★★  聚合分组
-- 统计每天的 UV + PV + PV/UV 比
-- 考点: DATE() 截取日期、COUNT(DISTINCT) 去重计数

SELECT DATE(create_time)                    AS dt,
       COUNT(DISTINCT user_id)              AS uv,
       COUNT(id)                            AS pv,
       ROUND(COUNT(id)*1.0/COUNT(DISTINCT user_id), 1) AS pv_per_uv
FROM user_behavior
GROUP BY DATE(create_time)
ORDER BY dt;
