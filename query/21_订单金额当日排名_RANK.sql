-- 第 21 题 ★★  窗口函数
-- 每个订单金额在当天的降序排名
-- 考点: PARTITION BY + ORDER BY 组合使用 RANK()

SELECT order_id, user_id, amount, DATE(create_time) AS dt,
       RANK() OVER (
           PARTITION BY DATE(create_time)
           ORDER BY amount DESC
       ) AS day_rank
FROM orders
ORDER BY dt, day_rank;
