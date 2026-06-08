-- 第 16 题 ★★  多表 JOIN
-- 查询在 user_behavior 中有行为但从未在 orders 下单的用户
-- 考点: LEFT JOIN + WHERE IS NULL（反连接）
--      NOT EXISTS 和 LEFT JOIN+IS NULL 优于 NOT IN

SELECT DISTINCT ub.user_id
FROM user_behavior ub
LEFT JOIN orders o ON ub.user_id = o.user_id
WHERE o.user_id IS NULL;
