-- 第 13 题 ★★  多表 JOIN
-- 列出所有注册用户及其是否参与过活动
-- 考点: LEFT JOIN + CASE WHEN + 子查询 DISTINCT 去重

SELECT u.user_id,
       u.registration_date,
       CASE WHEN a.user_id IS NOT NULL
            THEN '参与过活动' ELSE '未参与' END AS activity_status
FROM users_p2 u
LEFT JOIN (SELECT DISTINCT user_id FROM user_activities) a
    ON u.user_id = a.user_id
ORDER BY u.registration_date;
