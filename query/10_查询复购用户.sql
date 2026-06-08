-- 第 10 题 ★★  聚合分组
-- 查询有效订单 ≥2 的复购用户及消费数据
-- 考点: GROUP BY + HAVING 组合筛选

SELECT user_id,
       COUNT(DISTINCT order_id)  AS order_count,
       SUM(amount)               AS total_amount,
       AVG(amount)               AS avg_amount
FROM orders
WHERE order_status IN ('paid', 'shipped', 'completed')
GROUP BY user_id
HAVING order_count >= 2
ORDER BY order_count DESC;
