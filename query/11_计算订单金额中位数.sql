-- 第 11 题 ★★★  聚合分组
-- 计算订单金额的五统计量: 总数/最小/最大/平均/中位数
-- 考点: MySQL 无 MEDIAN()，用 ROW_NUMBER() 窗口函数模拟中位数
--      偶数行取中间两数的平均，奇数行取中间值

SELECT COUNT(*)                        AS total_orders,
       MIN(amount)                     AS min_amount,
       MAX(amount)                     AS max_amount,
       ROUND(AVG(amount), 2)           AS avg_amount,
       ROUND(AVG(CASE
           WHEN rn IN (FLOOR((cnt+1)/2), CEIL((cnt+1)/2))
           THEN amount END), 2)        AS median_amount
FROM (
    SELECT amount,
           ROW_NUMBER() OVER (ORDER BY amount) AS rn,
           COUNT(*) OVER ()                    AS cnt
    FROM orders
) t;
