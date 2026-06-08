-- 第 2 题 ★  基础查询
-- 查询已取消的订单，按金额降序取前 10
-- 考点: WHERE → ORDER BY → LIMIT 执行顺序

SELECT order_id, user_id, amount, create_time
FROM orders
WHERE order_status = 'cancelled'
ORDER BY amount DESC
LIMIT 10;
