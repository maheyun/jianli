-- 第 3 题 ★  基础查询
-- 统计 users 表中每种 gender 的用户数，按人数降序
-- 考点: GROUP BY + COUNT + ORDER BY 聚合结果

SELECT gender, COUNT(*) AS user_count
FROM users_p2
GROUP BY gender
ORDER BY user_count DESC;
