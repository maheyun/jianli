-- 第 22 题 ★★★  窗口函数
-- 查询用户相邻两笔订单的间隔天数
-- 考点: LEAD() 取同一分区下一行的值
--      LAG() 取上一行，DATEDIFF() 计算日期差

SELECT user_id, order_id, create_time,
       LEAD(create_time) OVER (
           PARTITION BY user_id ORDER BY create_time
       ) AS next_order_time,
       DATEDIFF(
           LEAD(create_time) OVER (
               PARTITION BY user_id ORDER BY create_time
           ),
           create_time
       ) AS days_till_next
FROM orders
ORDER BY user_id, create_time;
