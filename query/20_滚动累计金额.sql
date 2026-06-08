-- 第 20 题 ★★★  窗口函数
-- 每天订单金额 + 截至当天的累计金额
-- 考点: SUM(SUM()) OVER (ORDER BY ...) 两层聚合 + 窗口滚动累计
--  GROUP BY 先聚到天 → 窗口函数外面做累计

SELECT DATE(create_time)                                  AS dt,
       SUM(amount)                                        AS daily_amount,
       SUM(SUM(amount)) OVER (ORDER BY DATE(create_time)) AS cumulative_amount
FROM orders
GROUP BY DATE(create_time)
ORDER BY dt;
