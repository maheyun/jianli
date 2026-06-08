-- 第 15 题 ★★★  多表 JOIN
-- 四表关联: users → orders → order_items → products
-- 考点: 多表 JOIN 链式关联，每步明确 ON 条件
--      JOIN 顺序影响性能 — 小表驱动大表

SELECT u.user_id, u.gender,
       o.order_id, o.amount,
       oi.product_id, p.product_name,
       oi.quantity, oi.price,
       (oi.quantity * oi.price) AS line_total
FROM users u
JOIN orders o      ON u.user_id = o.user_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p    ON oi.product_id = p.product_id
WHERE o.order_status IN ('paid', 'shipped', 'completed')
ORDER BY u.user_id, o.create_time
LIMIT 50;
