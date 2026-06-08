-- 第 14 题 ★★  多表 JOIN
-- 查询每个用户历史首次下单的完整记录
-- 考点: 子查询先聚合 + 自连接回原表
-- 追问: 同时间多条订单怎么办？→ 用 ROW_NUMBER() 替代 MIN

SELECT o.user_id, o.order_id, o.amount, o.create_time
FROM orders o
JOIN (
    SELECT user_id, MIN(create_time) AS first_time
    FROM orders
    GROUP BY user_id
) t ON o.user_id = t.user_id AND o.create_time = t.first_time;
