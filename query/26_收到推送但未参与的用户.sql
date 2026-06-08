-- 第 26 题 ★★  子查询
-- 查询有活动推送但从未参与的用户
-- 考点: NOT EXISTS 比 NOT IN 更安全（不受 NULL 影响）
--       EXISTS 找到第一条就停止扫描，效率高

SELECT u.user_id, u.registration_date
FROM users u
WHERE EXISTS (
    SELECT 1 FROM user_activities a
    WHERE a.user_id = u.user_id
)
AND NOT EXISTS (
    SELECT 1 FROM user_activities a
    WHERE a.user_id = u.user_id
      AND a.is_participated = 1
);
