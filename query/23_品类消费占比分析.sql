-- 第 23 题 ★★★  窗口函数
-- 每个用户在各品类(category_id)的消费金额占比
-- 考点: CTE + 窗口函数 SUM OVER(PARTITION BY) + 多表 JOIN

WITH user_category AS (
    SELECT u.user_id,
           p.category_id,
           SUM(oi.quantity * oi.price) AS category_amount
    FROM users_p2 u
    JOIN orders_p2 o      ON u.user_id = o.user_id
    JOIN order_items_p2 oi ON o.order_id = oi.order_id
    JOIN products_p2 p    ON oi.product_id = p.product_id
    WHERE o.order_status IN ('paid', 'shipped', 'completed')
    GROUP BY u.user_id, p.category_id
)
SELECT user_id,
       category_id,
       category_amount,
       ROUND(
           category_amount * 100.0
           / SUM(category_amount) OVER (PARTITION BY user_id),
           1
       ) AS category_pct
FROM user_category
ORDER BY user_id, category_amount DESC;
