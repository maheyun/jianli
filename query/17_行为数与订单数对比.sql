-- 第 17 题 ★★  多表 JOIN
-- 统计每个用户的行为总数和订单总数（两边都可能缺失）
-- 考点: COALESCE 处理 NULL + 子查询先聚合再 JOIN（避免笛卡尔积）

SELECT COALESCE(b.user_id, o.user_id) AS user_id,
       COALESCE(b.behavior_cnt, 0)    AS behavior_cnt,
       COALESCE(o.order_cnt, 0)       AS order_cnt
FROM (
    SELECT user_id, COUNT(*) AS behavior_cnt
    FROM user_behavior
    GROUP BY user_id
) b
LEFT JOIN (
    SELECT user_id, COUNT(*) AS order_cnt
    FROM orders
    GROUP BY user_id
) o ON b.user_id = o.user_id
ORDER BY order_cnt DESC;
