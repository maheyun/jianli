-- 第 4 题 ★  基础查询
-- 查询 ad_campaigns 中花费在 5000~20000 之间的投放记录数
-- 考点: BETWEEN...AND... 是闭区间（含边界）

SELECT COUNT(*) AS campaign_count
FROM ad_campaigns
WHERE spend BETWEEN 5000 AND 20000;
