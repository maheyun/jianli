-- ═══════════════════════════════════════════════════════════════
-- MySQL 面试题 30 道（基于 user_behavior + orders 表）
-- 使用方式：选中任意一道题的 SQL，在 MySQL 客户端中直接执行
-- ═══════════════════════════════════════════════════════════════
--
-- 表结构说明:
--   user_behavior (id, user_id, action, create_time)
--     action 取值: view / add_to_cart / place_order / pay
--   orders        (order_id, user_id, order_status, amount, create_time)
--     order_status 取值: unpaid / paid / shipped / completed / cancelled
--
-- 难度标注: ★ 基础  ★★ 中等  ★★★ 进阶
-- ═══════════════════════════════════════════════════════════════


-- ============================================================
-- 一、基础查询与过滤（1-6 题）
-- ============================================================

-- ── 第 1 题 ★
-- 查询 user_behavior 表中所有不重复的 action 类型。
-- 考点: DISTINCT 去重
SELECT DISTINCT action
FROM user_behavior;


-- ── 第 2 题 ★
-- 查询已取消（cancelled）的订单，按金额降序排列，取前 10 条。
-- 考点: WHERE → ORDER BY → LIMIT 的执行顺序
SELECT *
FROM orders
WHERE order_status = 'cancelled'
ORDER BY amount DESC
LIMIT 10;


-- ── 第 3 题 ★
-- 统计每种行为类型（action）各有多少条记录，按数量从高到低排列。
-- 考点: GROUP BY + COUNT(*) + ORDER BY 聚合值
SELECT action,
       COUNT(*) AS cnt
FROM user_behavior
GROUP BY action
ORDER BY cnt DESC;


-- ── 第 4 题 ★
-- 查询订单金额在 100 到 500 之间（含边界）的订单数量。
-- 考点: BETWEEN...AND... 是闭区间，等价于 >= AND <=
SELECT COUNT(*) AS order_count
FROM orders
WHERE amount BETWEEN 100 AND 500;


-- ── 第 5 题 ★
-- 查询 user_behavior 表中 user_id 包含 "VIP" 的所有记录。
-- 考点: LIKE 模糊匹配，% 匹配任意长度字符
-- 追问: LIKE '%VIP%' 能否用到索引？答：不能，前缀模糊才能用索引
SELECT *
FROM user_behavior
WHERE user_id LIKE '%VIP%';


-- ── 第 6 题 ★
-- 查询订单状态为 paid、shipped、completed 的订单。
-- 考点: IN 用于多值匹配，比多个 OR 更简洁
SELECT *
FROM orders
WHERE order_status IN ('paid', 'shipped', 'completed');


-- ============================================================
-- 二、聚合函数与分组（7-12 题）
-- ============================================================

-- ── 第 7 题 ★★
-- 统计每天的独立访客数（UV）和页面浏览量（PV）。
-- 考点: DATE() 截取日期、COUNT(DISTINCT ...) 去重计数
-- 追问: COUNT(DISTINCT col) 性能问题及优化方案
SELECT DATE(create_time) AS dt,
       COUNT(DISTINCT user_id) AS uv,
       COUNT(id) AS pv
FROM user_behavior
GROUP BY DATE(create_time)
ORDER BY dt;


-- ── 第 8 题 ★★
-- 查询 2025 年 10 月每一天的活跃用户数，只显示活跃用户 > 500 的日期。
-- 考点: WHERE vs HAVING 区别
--   WHERE: GROUP BY 之前过滤行（不能用聚合函数）
--   HAVING: GROUP BY 之后过滤分组（能用聚合函数）
-- 执行顺序: FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT
SELECT DATE(create_time) AS dt,
       COUNT(DISTINCT user_id) AS active_users
FROM user_behavior
WHERE create_time >= '2025-10-01'
  AND create_time < '2025-11-01'
GROUP BY DATE(create_time)
HAVING active_users > 500
ORDER BY dt;


-- ── 第 9 题 ★★
-- 统计每种订单状态的数量及其占总订单的百分比。
-- 考点: 窗口函数 SUM() OVER () 计算全局总计
SELECT order_status,
       COUNT(*) AS order_count,
       CONCAT(ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2), '%') AS pct
FROM orders
GROUP BY order_status
ORDER BY order_count DESC;


-- ── 第 10 题 ★★
-- 查询每个用户的下单次数，只显示复购用户（下单次数 ≥ 2）。
-- 考点: GROUP BY + HAVING 组合筛选
SELECT user_id,
       COUNT(DISTINCT order_id) AS order_count,
       SUM(amount) AS total_amount
FROM orders
WHERE order_status IN ('paid', 'shipped', 'completed')
GROUP BY user_id
HAVING order_count >= 2
ORDER BY order_count DESC;


-- ── 第 11 题 ★★★
-- 计算订单金额的五个统计指标：总数、最小值、最大值、平均值、中位数。
-- 考点: MySQL 没有 MEDIAN() 函数，需要用 ROW_NUMBER() 窗口函数模拟
--      偶数行取中间两数的平均值，奇数行取中间值
SELECT COUNT(*)                        AS total_orders,
       MIN(amount)                     AS min_amount,
       MAX(amount)                     AS max_amount,
       ROUND(AVG(amount), 2)           AS avg_amount,
       ROUND(AVG(
           CASE
               WHEN rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2))
               THEN amount
           END
       ), 2)                           AS median_amount
FROM (
    SELECT amount,
           ROW_NUMBER() OVER (ORDER BY amount) AS rn,
           COUNT(*) OVER () AS cnt
    FROM orders
) t;


-- ── 第 12 题 ★★
-- 用行转列展示每个用户在不同 action 类型上的行为次数。
-- 考点: CASE WHEN + SUM() 条件聚合实现行转列（与 pandas pivot_table 同样效果）
SELECT user_id,
       SUM(CASE WHEN action = 'view'        THEN 1 ELSE 0 END) AS view_cnt,
       SUM(CASE WHEN action = 'add_to_cart' THEN 1 ELSE 0 END) AS cart_cnt,
       SUM(CASE WHEN action = 'place_order' THEN 1 ELSE 0 END) AS order_cnt,
       SUM(CASE WHEN action = 'pay'         THEN 1 ELSE 0 END) AS pay_cnt
FROM user_behavior
GROUP BY user_id
ORDER BY view_cnt DESC;


-- ============================================================
-- 三、多表 JOIN（13-17 题）
-- ============================================================

-- ── 第 13 题 ★★
-- 列出所有活跃用户及其是否有下单记录。
-- 考点: LEFT JOIN + CASE WHEN 判断匹配、子查询去重避免笛卡尔积
SELECT u.user_id,
       CASE WHEN o.user_id IS NOT NULL THEN '有下单' ELSE '未下单' END AS has_order
FROM (SELECT DISTINCT user_id FROM user_behavior) u
LEFT JOIN (SELECT DISTINCT user_id FROM orders) o
    ON u.user_id = o.user_id;


-- ── 第 14 题 ★★
-- 查询每个用户的首次下单完整记录。
-- 考点: 子查询 + 自连接。追问：同一时间多条订单怎么办？→ 用 ROW_NUMBER()
SELECT o.user_id,
       o.order_id,
       o.amount,
       o.create_time
FROM orders o
JOIN (
    SELECT user_id, MIN(create_time) AS first_time
    FROM orders
    GROUP BY user_id
) t ON o.user_id = t.user_id AND o.create_time = t.first_time;


-- ── 第 15 题 ★★
-- 统计每个用户的行为总数和订单总数（用户可能只在一边有数据）。
-- 考点: COALESCE() 处理 NULL、子查询先聚合再 JOIN 避免笛卡尔积
SELECT COALESCE(u.user_id, o.user_id) AS user_id,
       COALESCE(u.behavior_cnt, 0)    AS behavior_cnt,
       COALESCE(o.order_cnt, 0)       AS order_cnt
FROM (
    SELECT user_id, COUNT(*) AS behavior_cnt
    FROM user_behavior
    GROUP BY user_id
) u
LEFT JOIN (
    SELECT user_id, COUNT(*) AS order_cnt
    FROM orders
    GROUP BY user_id
) o ON u.user_id = o.user_id
ORDER BY order_cnt DESC;


-- ── 第 16 题 ★★
-- 面试口述题：INNER / LEFT / RIGHT JOIN 的区别，以 user_behavior 和 orders 为例说明。
-- 答案（作为注释记录）:
--   INNER JOIN: 两边都有的用户（有行为且下过单的用户）
--   LEFT JOIN:  所有有行为的用户 + 匹配的订单信息
--   RIGHT JOIN: 所有下过单的用户 + 匹配的行为信息
--   FULL OUTER JOIN: 所有出现在任意一边的用户（每个用户只要有过行为或下过单就算）
--   ⚠ MySQL 不直接支持 FULL OUTER JOIN，需用 LEFT JOIN UNION RIGHT JOIN 模拟。


-- ── 第 17 题 ★★
-- 查询"浏览过但从未下单"的用户列表（反连接）。
-- 考点: LEFT JOIN + WHERE IS NULL 找"左表有、右表没有"的记录
SELECT DISTINCT u.user_id
FROM user_behavior u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE o.user_id IS NULL;


-- ============================================================
-- 四、窗口函数（18-22 题）
-- ============================================================

-- ── 第 18 题 ★★
-- 给每笔订单标上该用户的第几次下单（累计编号）。
-- 考点: ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)
-- 追问: ROW_NUMBER vs RANK vs DENSE_RANK 区别
--   ROW_NUMBER:  1,2,3,4...    严格递增不重号不跳号
--   RANK:        1,2,2,4...    重号后跳号
--   DENSE_RANK:  1,2,2,3...    重号不跳号
SELECT user_id,
       order_id,
       amount,
       create_time,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time) AS order_seq
FROM orders
ORDER BY user_id, create_time;


-- ── 第 19 题 ★★★
-- 计算每天的订单金额，以及截至当天的累计金额（滚动合计）。
-- 考点: SUM(SUM()) OVER (ORDER BY dt) 两层聚合
--   GROUP BY 先聚到天级别 → 窗口函数外面做累计
SELECT DATE(create_time) AS dt,
       SUM(amount)        AS daily_amount,
       SUM(SUM(amount)) OVER (ORDER BY DATE(create_time)) AS cumulative_amount
FROM orders
GROUP BY DATE(create_time)
ORDER BY dt;


-- ── 第 20 题 ★★
-- 计算每个订单金额在当天所有订单中的排名（按金额降序）。
-- 考点: PARTITION BY + ORDER BY 组合使用 RANK()
SELECT order_id,
       user_id,
       amount,
       DATE(create_time) AS dt,
       RANK() OVER (PARTITION BY DATE(create_time) ORDER BY amount DESC) AS day_rank
FROM orders
ORDER BY dt, day_rank;


-- ── 第 21 题 ★★★
-- 查询每个用户的"下次购买时间"和"距下次购买间隔天数"。
-- 考点: LEAD() 窗口函数取同一分区内的下一行值
--       LAG() 取上一行，对应的项目里用的是 .shift(1)
--       DATEDIFF() 计算两个日期的天数差
SELECT user_id,
       order_id,
       create_time,
       LEAD(create_time) OVER (PARTITION BY user_id ORDER BY create_time) AS next_order_time,
       DATEDIFF(
           LEAD(create_time) OVER (PARTITION BY user_id ORDER BY create_time),
           create_time
       ) AS days_till_next
FROM orders
ORDER BY user_id, create_time;


-- ── 第 22 题 ★
-- 统计每天第一次下单和最后一次下单的时间差。
-- 考点: TIMEDIFF() 计算两个时间的差值
SELECT DATE(create_time) AS dt,
       MIN(create_time)  AS first_order,
       MAX(create_time)  AS last_order,
       TIMEDIFF(MAX(create_time), MIN(create_time)) AS time_span
FROM orders
GROUP BY DATE(create_time)
ORDER BY dt;


-- ============================================================
-- 五、子查询与 CTE（23-26 题）
-- ============================================================

-- ── 第 23 题 ★
-- 查询订单金额高于所有订单平均金额的订单。
-- 考点: 标量子查询（子查询返回单个值）
SELECT order_id, user_id, amount, create_time
FROM orders
WHERE amount > (SELECT AVG(amount) FROM orders)
ORDER BY amount DESC;


-- ── 第 24 题 ★★
-- 查询在 10 月 1 日到 10 月 15 日之间每天都下单的用户（全勤用户）。
-- 考点: HAVING COUNT(DISTINCT DATE) = 天数
SELECT user_id,
       COUNT(DISTINCT DATE(create_time)) AS days_with_order
FROM orders
WHERE DATE(create_time) BETWEEN '2025-10-01' AND '2025-10-15'
  AND order_status IN ('paid', 'shipped', 'completed')
GROUP BY user_id
HAVING COUNT(DISTINCT DATE(create_time)) = 15;


-- ── 第 25 题 ★★★
-- 使用 CTE（WITH 子句）+ ROW_NUMBER 查询每个用户的首次下单。
-- 考点: CTE（Common Table Expression）使 SQL 更可读
--       MySQL 8.0+ 支持；CTE 也可以做递归查询
WITH ranked_orders AS (
    SELECT user_id,
           order_id,
           amount,
           create_time,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time) AS rn
    FROM orders
)
SELECT user_id, order_id, amount, create_time
FROM ranked_orders
WHERE rn = 1
ORDER BY user_id;


-- ── 第 26 题 ★★
-- 查询有过浏览行为但从未有过加购行为的用户。
-- 考点: NOT IN 子查询
-- 追问: NOT IN vs NOT EXISTS 哪个更好？
--   答: NOT EXISTS 更安全，因为 NOT IN 子查询结果包含 NULL 时会返回空
--   NOT EXISTS 写法:
--     SELECT DISTINCT u1.user_id
--     FROM user_behavior u1
--     WHERE u1.action = 'view'
--       AND NOT EXISTS (
--           SELECT 1 FROM user_behavior u2
--           WHERE u2.user_id = u1.user_id AND u2.action = 'add_to_cart'
--       );
SELECT DISTINCT user_id
FROM user_behavior
WHERE action = 'view'
  AND user_id NOT IN (
      SELECT DISTINCT user_id
      FROM user_behavior
      WHERE action = 'add_to_cart'
  );

-- NOT EXISTS 版本（更安全，推荐）:
SELECT DISTINCT u1.user_id
FROM user_behavior u1
WHERE u1.action = 'view'
  AND NOT EXISTS (
      SELECT 1
      FROM user_behavior u2
      WHERE u2.user_id = u1.user_id
        AND u2.action = 'add_to_cart'
  );


-- ============================================================
-- 六、索引与性能（27-28 题）
-- ============================================================

-- ── 第 27 题 ★★★
-- 以下查询应该在哪些列上建立索引？为什么？
--
-- SELECT *
-- FROM orders
-- WHERE user_id = 'U12345'
--   AND create_time >= '2025-10-01'
-- ORDER BY create_time DESC
-- LIMIT 20;
--
-- 答案: 建议建联合索引 (user_id, create_time)
--   1. user_id 放前面做等值过滤（= 过滤效果最强）
--   2. create_time 放后面做范围过滤和排序
--   3. 最左前缀原则: WHERE user_id = ? AND create_time >= ? 能充分利用索引
--      但 WHERE create_time >= ? 单独查则用不到这个联合索引
--
-- 建索引语句:
-- CREATE INDEX idx_user_create ON orders(user_id, create_time);


-- ── 第 28 题 ★★
-- 下面两条 SQL 的区别是什么？
--
-- SELECT user_id, COUNT(*) FROM orders GROUP BY user_id;   -- 每个用户的订单数，多行
-- SELECT COUNT(DISTINCT user_id) FROM orders;              -- 总付费用户数，一行一个数
--
-- 区别:
--   第一条: 按 user_id 分组统计每组行数 → 返回多行（每个用户一行）
--   第二条: 统计不重复 user_id 总数 → 返回一行一个数字
--   它们是不同的业务需求，不是同一条 SQL 的两种写法！
--
-- 性能:
--   COUNT(DISTINCT user_id) 在 MySQL 8.0 之前较慢（全表扫描+文件排序），8.0+ 优化后有所改善
--   有 user_id 索引时两者差别不大


-- ============================================================
-- 七、综合实战题（29-30 题）
-- ============================================================

-- ── 第 29 题 ★★★  漏斗分析
-- 计算"浏览 → 加购 → 下单 → 支付"四步转化漏斗的用户数。
-- 考点: COUNT(DISTINCT CASE WHEN ...) 条件去重聚合
SELECT COUNT(DISTINCT CASE WHEN action = 'view'        THEN user_id END) AS view_users,
       COUNT(DISTINCT CASE WHEN action = 'add_to_cart' THEN user_id END) AS cart_users,
       COUNT(DISTINCT CASE WHEN action = 'place_order' THEN user_id END) AS order_users,
       COUNT(DISTINCT CASE WHEN action = 'pay'         THEN user_id END) AS pay_users
FROM user_behavior;

-- 带转化率的版本:
WITH funnel AS (
    SELECT COUNT(DISTINCT CASE WHEN action = 'view'        THEN user_id END) AS view_users,
           COUNT(DISTINCT CASE WHEN action = 'add_to_cart' THEN user_id END) AS cart_users,
           COUNT(DISTINCT CASE WHEN action = 'place_order' THEN user_id END) AS order_users,
           COUNT(DISTINCT CASE WHEN action = 'pay'         THEN user_id END) AS pay_users
    FROM user_behavior
)
SELECT '浏览' AS step, view_users  AS user_count, '100.00%' AS overall_rate, '' AS step_rate FROM funnel
UNION ALL
SELECT '加购', cart_users,  CONCAT(ROUND(cart_users  * 100.0 / view_users, 2), '%'),
                          CONCAT(ROUND(cart_users  * 100.0 / view_users, 2), '%') FROM funnel
UNION ALL
SELECT '下单', order_users, CONCAT(ROUND(order_users * 100.0 / view_users, 2), '%'),
                          CONCAT(ROUND(order_users * 100.0 / cart_users, 2), '%') FROM funnel
UNION ALL
SELECT '支付', pay_users,   CONCAT(ROUND(pay_users   * 100.0 / view_users, 2), '%'),
                          CONCAT(ROUND(pay_users   * 100.0 / order_users, 2), '%') FROM funnel;


-- ── 第 30 题 ★★★   RFM 客户价值分层
-- 为每个付费用户计算 R（最近购买距今天数）、F（购买频次）、M（累计金额），
-- 用 NTILE 五等分打分后求和，分四层：高价值 / 中高 / 中 / 低价值。
-- 考点: CTE + NTILE() 等分分组 + CASE WHEN 分层 + DATEDIFF() + NOW()
WITH rfm AS (
    SELECT user_id,
           DATEDIFF(NOW(), MAX(create_time)) AS recency,
           COUNT(DISTINCT order_id)          AS frequency,
           SUM(amount)                       AS monetary
    FROM orders
    WHERE order_status IN ('paid', 'shipped', 'completed')
    GROUP BY user_id
),
scored AS (
    SELECT user_id, recency, frequency, monetary,
           -- R: recency 越小越好 → NTILE 5 组后倒序，让最近购买的人得 5 分
           (6 - NTILE(5) OVER (ORDER BY recency DESC)) AS r_score,
           -- F: frequency 越大越好 → 正序打分
           NTILE(5) OVER (ORDER BY frequency)          AS f_score,
           -- M: monetary 越大越好 → 正序打分
           NTILE(5) OVER (ORDER BY monetary)           AS m_score
    FROM rfm
)
SELECT user_id,
       recency,
       frequency,
       monetary,
       r_score + f_score + m_score AS rfm_total,
       CASE
           WHEN r_score + f_score + m_score >= 12 THEN '高价值客户'
           WHEN r_score + f_score + m_score >= 9  THEN '中高价值客户'
           WHEN r_score + f_score + m_score >= 6  THEN '中价值客户'
           ELSE '低价值客户'
       END AS segment
FROM scored
ORDER BY rfm_total DESC;


-- ============================================================
-- 附录：各分层人数统计
-- ============================================================
WITH rfm AS (
    SELECT user_id,
           DATEDIFF(NOW(), MAX(create_time)) AS recency,
           COUNT(DISTINCT order_id)          AS frequency,
           SUM(amount)                       AS monetary
    FROM orders
    WHERE order_status IN ('paid', 'shipped', 'completed')
    GROUP BY user_id
),
scored AS (
    SELECT user_id, recency, frequency, monetary,
           (6 - NTILE(5) OVER (ORDER BY recency DESC)) AS r_score,
           NTILE(5) OVER (ORDER BY frequency)          AS f_score,
           NTILE(5) OVER (ORDER BY monetary)           AS m_score
    FROM rfm
),
segmented AS (
    SELECT user_id, recency, frequency, monetary,
           r_score + f_score + m_score AS rfm_total,
           CASE
               WHEN r_score + f_score + m_score >= 12 THEN '高价值客户'
               WHEN r_score + f_score + m_score >= 9  THEN '中高价值客户'
               WHEN r_score + f_score + m_score >= 6  THEN '中价值客户'
               ELSE '低价值客户'
           END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*)                                       AS user_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct,
       ROUND(AVG(recency), 0)                         AS avg_recency,
       ROUND(AVG(frequency), 1)                       AS avg_frequency,
       ROUND(AVG(monetary), 0)                        AS avg_monetary
FROM segmented
GROUP BY segment
ORDER BY user_count DESC;


-- ═══════════════════════════════════════════════════════════════
-- 每题快速定位:
--
--   ★ 基础 (1-6):    你已掌握 —— 直接跳过
--   ★★ 中等 (7-10,12-15,17,18,20,22-24,26,28):  核心发力区
--   ★★★ 进阶 (11,19,21,25,27,29,30):  冲刺加分项
--
-- 最常考的 TOP 5:
--   1. 第 8 题  WHERE vs HAVING
--   2. 第 12 题 CASE WHEN 行转列
--   3. 第 18 题 ROW_NUMBER vs RANK vs DENSE_RANK
--   4. 第 21 题 LEAD / LAG 窗口函数
--   5. 第 30 题 RFM 分层（CTE + NTILE + CASE WHEN 综合）
-- ═══════════════════════════════════════════════════════════════
