-- 第 8 题 ★★  聚合分组
-- 查询 2025 年 10 月每天活跃 >500 的日期
-- 考点: WHERE vs HAVING（核心高频面试题）
--   WHERE:  GROUP BY 之前过滤行，不能用聚合函数
--   HAVING: GROUP BY 之后过滤分组，能用聚合函数
-- 执行顺序: FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT

SELECT DATE(create_time)                AS dt,
       COUNT(DISTINCT user_id)          AS active_users
FROM user_behavior
WHERE create_time >= '2025-10-01'
  AND create_time < '2025-11-01'
GROUP BY DATE(create_time)
HAVING active_users > 500
ORDER BY dt;
