-- 第 19 题 ★★  窗口函数
-- 给每笔订单标上用户的第几次下单
-- 考点: ROW_NUMBER() OVER(PARTITION BY ... ORDER BY ...)
-- 追问: ROW_NUMBER vs RANK vs DENSE_RANK 区别
--   ROW_NUMBER:  1,2,3,4   严格递增不重号不跳号
--   RANK:        1,2,2,4   重号后跳号
--   DENSE_RANK:  1,2,2,3   重号不跳号

SELECT user_id, order_id, amount, create_time,
       ROW_NUMBER() OVER (
           PARTITION BY user_id ORDER BY create_time
       ) AS order_seq
FROM orders
ORDER BY user_id, create_time;
