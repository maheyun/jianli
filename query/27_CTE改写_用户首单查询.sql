-- 第 27 题 ★★★  CTE
-- 用 WITH 子句(CTE) + ROW_NUMBER() 查用户首单
-- 考点: CTE (Common Table Expression) 语法
--       MySQL 8.0+ 支持，可代替嵌套子查询，语义更清晰

WITH ranked AS (
    SELECT user_id, order_id, amount, create_time,
           ROW_NUMBER() OVER (
               PARTITION BY user_id ORDER BY create_time
           ) AS rn
    FROM orders
)
SELECT user_id, order_id, amount, create_time
FROM ranked
WHERE rn = 1
ORDER BY user_id;
