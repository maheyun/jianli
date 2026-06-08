-- 第 25 题 ★  子查询
-- 查询金额 > 所有订单平均金额的订单
-- 考点: 标量子查询返回单值，可放在 WHERE 中比较

SELECT order_id, user_id, amount, create_time
FROM orders
WHERE amount > (SELECT AVG(amount) FROM orders)
ORDER BY amount DESC;
