-- 第 12 题 ★★  聚合分组
-- 把 action 字段行转列为每个用户的四种行为计数
-- 考点: CASE WHEN + SUM() 条件聚合（面试必考）
--      等价于 pandas 的 pivot_table + clip

SELECT user_id,
       SUM(CASE WHEN action = 'view'        THEN 1 ELSE 0 END) AS view_cnt,
       SUM(CASE WHEN action = 'add_to_cart' THEN 1 ELSE 0 END) AS cart_cnt,
       SUM(CASE WHEN action = 'place_order' THEN 1 ELSE 0 END) AS order_cnt,
       SUM(CASE WHEN action = 'pay'         THEN 1 ELSE 0 END) AS pay_cnt
FROM user_behavior
GROUP BY user_id
ORDER BY view_cnt DESC;
