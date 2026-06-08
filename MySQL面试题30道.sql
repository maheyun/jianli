-- ═══════════════════════════════════════════════════════════════
--  MySQL 面试题 30 道（覆盖全部四个项目的所有表）
--  涵盖: user_behavior / orders / users / order_items / products
--        user_activities / ad_campaigns / attribution_data
--        sales_data / inventory_data
--
--  使用方式: 选中任意一道题的 SQL，在 MySQL 客户端中直接执行
--  难度标注: ★ 基础  ★★ 中等  ★★★ 进阶
-- ═══════════════════════════════════════════════════════════════


-- ============================================================
-- 一、基础查询与过滤（1-6 题）★
-- ============================================================

-- ── 第 1 题 ★  DISTINCT 去重
-- 查询 user_behavior 表中所有不重复的 action 类型。
SELECT DISTINCT action
FROM user_behavior;


-- ── 第 2 题 ★  WHERE → ORDER BY → LIMIT
-- 查询已取消的订单，按金额降序排列，取前 10 条。
SELECT order_id, user_id, amount, create_time
FROM orders
WHERE order_status = 'cancelled'
ORDER BY amount DESC
LIMIT 10;


-- ── 第 3 题 ★  GROUP BY + COUNT(*) + 排序
-- 统计 users 表中每种性别（gender）的用户数，按人数降序排列。
SELECT gender,
       COUNT(*) AS user_count
FROM users
GROUP BY gender
ORDER BY user_count DESC;


-- ── 第 4 题 ★  BETWEEN...AND... 闭区间
-- 查询 ad_campaigns 中，花费在 5000 到 20000 之间的投放记录数。
SELECT COUNT(*) AS campaign_count
FROM ad_campaigns
WHERE spend BETWEEN 5000 AND 20000;


-- ── 第 5 题 ★  LIKE 模糊匹配
-- 查询 products 表中 product_name 包含"袜子"的所有产品。
-- 追问: LIKE '%袜子%' 能否用到索引？答: 不能，前缀模糊才能走索引。
SELECT product_id, product_name, category_id
FROM products
WHERE product_name LIKE '%袜子%';


-- ── 第 6 题 ★  IN 多值匹配
-- 查询在有库存（current_stock > 0）且类型为"袜子"或"服装"的产品。
-- 考点: IN 比多个 OR 更简洁，MySQL 内部会对 IN 列表排序后二分查找。
SELECT product_id, product_name, current_stock
FROM inventory_data
JOIN products USING (product_id)
WHERE current_stock > 0
  AND category_id IN (1, 2);


-- ============================================================
-- 二、聚合函数与分组（7-12 题）★★
-- ============================================================

-- ── 第 7 题 ★★  COUNT(DISTINCT ...) 去重计数
-- 统计每天的 UV + PV。
-- 考点: DATE() 截取日期、COUNT(DISTINCT col) 去重。
SELECT DATE(create_time)                    AS dt,
       COUNT(DISTINCT user_id)              AS uv,
       COUNT(id)                            AS pv,
       ROUND(COUNT(id)*1.0/COUNT(DISTINCT user_id), 1) AS pv_per_uv
FROM user_behavior
GROUP BY DATE(create_time)
ORDER BY dt;


-- ── 第 8 题 ★★  WHERE vs HAVING
-- 查询 2025 年 10 月每天活跃 > 500 人的日期。
-- 执行顺序: FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT
SELECT DATE(create_time)                AS dt,
       COUNT(DISTINCT user_id)          AS active_users
FROM user_behavior
WHERE create_time >= '2025-10-01' AND create_time < '2025-11-01'
GROUP BY DATE(create_time)
HAVING active_users > 500
ORDER BY dt;


-- ── 第 9 题 ★★  窗口函数 SUM() OVER () 计算占比
-- 统计各平台广告花费及其占总花费的百分比。
SELECT platform,
       SUM(spend)                                      AS total_spend,
       CONCAT(ROUND(SUM(spend) * 100.0
            / SUM(SUM(spend)) OVER (), 2), '%')        AS spend_pct
FROM ad_campaigns
GROUP BY platform
ORDER BY total_spend DESC;


-- ── 第 10 题 ★★  GROUP BY + HAVING 复购筛选
-- 查询下单 ≥ 2 次的复购用户及消费数据。
SELECT user_id,
       COUNT(DISTINCT order_id)  AS order_count,
       SUM(amount)               AS total_amount,
       AVG(amount)               AS avg_amount
FROM orders
WHERE order_status IN ('paid', 'shipped', 'completed')
GROUP BY user_id
HAVING order_count >= 2
ORDER BY order_count DESC;


-- ── 第 11 题 ★★★  用窗口函数模拟中位数
-- 计算 orders 表金额的五个统计量: 总数/最小/最大/平均/中位数。
-- MySQL 没有 MEDIAN()，用 ROW_NUMBER() 模拟。
SELECT COUNT(*)                        AS total_orders,
       MIN(amount)                     AS min_amount,
       MAX(amount)                     AS max_amount,
       ROUND(AVG(amount), 2)           AS avg_amount,
       ROUND(AVG(CASE
           WHEN rn IN (FLOOR((cnt+1)/2), CEIL((cnt+1)/2))
           THEN amount END), 2)        AS median_amount
FROM (
    SELECT amount,
           ROW_NUMBER() OVER (ORDER BY amount) AS rn,
           COUNT(*) OVER ()                    AS cnt
    FROM orders
) t;


-- ── 第 12 题 ★★  CASE WHEN 条件聚合 → 行转列
-- 把 user_behavior 的 action 行转列: 每人一行，四列行为计数。
SELECT user_id,
       SUM(CASE WHEN action = 'view'        THEN 1 ELSE 0 END) AS view_cnt,
       SUM(CASE WHEN action = 'add_to_cart' THEN 1 ELSE 0 END) AS cart_cnt,
       SUM(CASE WHEN action = 'place_order' THEN 1 ELSE 0 END) AS order_cnt,
       SUM(CASE WHEN action = 'pay'         THEN 1 ELSE 0 END) AS pay_cnt
FROM user_behavior
GROUP BY user_id
ORDER BY view_cnt DESC;


-- ============================================================
-- 三、多表 JOIN（13-18 题）★★
-- ============================================================

-- ── 第 13 题 ★★  LEFT JOIN + CASE WHEN
-- 列出所有注册用户及其是否参与过活动。
SELECT u.user_id,
       u.registration_date,
       CASE WHEN a.user_id IS NOT NULL
            THEN '参与过活动' ELSE '未参与' END AS activity_status
FROM users u
LEFT JOIN (SELECT DISTINCT user_id FROM user_activities) a
    ON u.user_id = a.user_id
ORDER BY u.registration_date;


-- ── 第 14 题 ★★  子查询 + 自连接找首单
-- 查询每个用户的首次下单完整记录。
SELECT o.user_id, o.order_id, o.amount, o.create_time
FROM orders o
JOIN (
    SELECT user_id, MIN(create_time) AS first_time
    FROM orders
    GROUP BY user_id
) t ON o.user_id = t.user_id AND o.create_time = t.first_time;


-- ── 第 15 题 ★★★  三表 JOIN 查看订单明细
-- 用户 + 订单 + 订单项的完整明细。
SELECT u.user_id,
       u.gender,
       o.order_id,
       o.amount,
       oi.product_id,
       p.product_name,
       oi.quantity,
       oi.price,
       (oi.quantity * oi.price) AS line_total
FROM users u
JOIN orders o        ON u.user_id = o.user_id
JOIN order_items oi  ON o.order_id = oi.order_id
JOIN products p      ON oi.product_id = p.product_id
WHERE o.order_status IN ('paid', 'shipped', 'completed')
ORDER BY u.user_id, o.create_time
LIMIT 50;


-- ── 第 16 题 ★★  LEFT JOIN + WHERE IS NULL（反连接）
-- 查询"浏览过但从未下单"的用户。
SELECT DISTINCT ub.user_id
FROM user_behavior ub
LEFT JOIN orders o ON ub.user_id = o.user_id
WHERE o.user_id IS NULL;


-- ── 第 17 题 ★★  COALESCE 处理 NULL + 子查询先聚合再 JOIN
-- 统计每个用户的行为总数和订单总数，两边都可能缺失。
SELECT COALESCE(b.user_id, o.user_id) AS user_id,
       COALESCE(b.behavior_cnt, 0)    AS behavior_cnt,
       COALESCE(o.order_cnt, 0)       AS order_cnt
FROM (
    SELECT user_id, COUNT(*) AS behavior_cnt
    FROM user_behavior
    GROUP BY user_id
) b
LEFT JOIN (
    SELECT user_id, COUNT(*) AS order_cnt
    FROM orders
    GROUP BY user_id
) o ON b.user_id = o.user_id
ORDER BY order_cnt DESC;


-- ── 第 18 题 ★★  库存 + 销量 + 销售金额三表关联
-- 查询每个产品的库存、销量和销售额。
SELECT p.product_id,
       p.product_name,
       COALESCE(i.current_stock, 0)            AS current_stock,
       COALESCE(s.total_volume, 0)             AS total_sold,
       COALESCE(s.total_amount, 0)             AS total_revenue,
       ROUND(COALESCE(s.total_volume, 0)
        / NULLIF(COALESCE(s.total_volume, 0)
            + COALESCE(i.current_stock, 0), 0), 4) AS sell_through_rate
FROM products p
LEFT JOIN inventory_data i  ON p.product_id = i.product_id
LEFT JOIN (
    SELECT product_id,
           SUM(sales_volume) AS total_volume,
           SUM(sales_amount) AS total_amount
    FROM sales_data
    GROUP BY product_id
) s ON p.product_id = s.product_id
ORDER BY sell_through_rate DESC;


-- ============================================================
-- 四、窗口函数（19-24 题）★★～★★★
-- ============================================================

-- ── 第 19 题 ★★  ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)
-- 给每笔订单标上用户的第几次下单。
-- 追问 ROW_NUMBER vs RANK vs DENSE_RANK 区别见注释。
SELECT user_id, order_id, amount, create_time,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time) AS order_seq
FROM orders
ORDER BY user_id, create_time;


-- ── 第 20 题 ★★★  SUM(SUM()) OVER (ORDER BY ...) 滚动累计
-- 每天订单金额 + 截至当天的累计金额。
SELECT DATE(create_time)                                      AS dt,
       SUM(amount)                                            AS daily_amount,
       SUM(SUM(amount)) OVER (ORDER BY DATE(create_time))     AS cumulative_amount
FROM orders
GROUP BY DATE(create_time)
ORDER BY dt;


-- ── 第 21 题 ★★  RANK() 排名
-- 每个订单金额在当天的排名（按金额降序）。
SELECT order_id, user_id, amount, DATE(create_time) AS dt,
       RANK() OVER (PARTITION BY DATE(create_time) ORDER BY amount DESC) AS day_rank
FROM orders
ORDER BY dt, day_rank;


-- ── 第 22 题 ★★★  LEAD() 取下一条记录
-- 查询每个用户相邻订单的时间间隔。
SELECT user_id, order_id, create_time,
       LEAD(create_time) OVER (PARTITION BY user_id ORDER BY create_time) AS next_order_time,
       DATEDIFF(
           LEAD(create_time) OVER (PARTITION BY user_id ORDER BY create_time),
           create_time
       ) AS days_till_next
FROM orders
ORDER BY user_id, create_time;


-- ── 第 23 题 ★★★  窗口函数 + 条件聚合的品类分析
-- 每个用户的品类消费占比。
WITH user_category AS (
    SELECT u.user_id,
           p.category_id,
           SUM(oi.quantity * oi.price) AS category_amount
    FROM users u
    JOIN orders o         ON u.user_id = o.user_id
    JOIN order_items oi   ON o.order_id = oi.order_id
    JOIN products p       ON oi.product_id = p.product_id
    WHERE o.order_status IN ('paid', 'shipped', 'completed')
    GROUP BY u.user_id, p.category_id
)
SELECT user_id,
       category_id,
       category_amount,
       ROUND(category_amount * 100.0
           / SUM(category_amount) OVER (PARTITION BY user_id), 1) AS category_pct
FROM user_category
ORDER BY user_id, category_amount DESC;


-- ── 第 24 题 ★★  移动平均
-- 计算每个产品销量的 7 日移动平均。
SELECT product_id,
       sale_date,
       daily_sales,
       ROUND(AVG(daily_sales) OVER (
           PARTITION BY product_id
           ORDER BY sale_date
           ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
       ), 1) AS ma_7day
FROM (
    SELECT product_id, sale_date, SUM(sales_volume) AS daily_sales
    FROM sales_data
    GROUP BY product_id, sale_date
) t
ORDER BY product_id, sale_date;


-- ============================================================
-- 五、子查询与 CTE（25-28 题）★★～★★★
-- ============================================================

-- ── 第 25 题 ★  标量子查询
-- 查询金额高于平均值的订单。
SELECT order_id, user_id, amount, create_time
FROM orders
WHERE amount > (SELECT AVG(amount) FROM orders)
ORDER BY amount DESC;


-- ── 第 26 题 ★★  NOT EXISTS（比 NOT IN 更安全）
-- 查询有活动推送但从未参与的用户。
-- NOT EXISTS 不会因子查询 NULL 而返回空结果，比 NOT IN 安全。
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


-- ── 第 27 题 ★★★  CTE + ROW_NUMBER 找用户首单
-- 用 WITH 子句改写子查询版的首单查询。
WITH ranked AS (
    SELECT user_id, order_id, amount, create_time,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time) AS rn
    FROM orders
)
SELECT user_id, order_id, amount, create_time
FROM ranked
WHERE rn = 1
ORDER BY user_id;


-- ── 第 28 题 ★★★  CTE 多步骤 + 各平台效能汇总
-- 分三步：汇总 → 算指标 → 区分析，全部用 WITH。
WITH platform_summary AS (
    SELECT platform,
           SUM(spend)         AS total_spend,
           SUM(impressions)   AS total_impressions,
           SUM(clicks)        AS total_clicks,
           SUM(conversions)   AS total_conversions,
           SUM(revenue)       AS total_revenue
    FROM ad_campaigns
    GROUP BY platform
),
platform_kpi AS (
    SELECT platform, total_spend, total_revenue,
           ROUND(total_clicks * 1.0 / NULLIF(total_impressions, 0), 4) AS ctr,
           ROUND(total_conversions * 1.0 / NULLIF(total_clicks, 0), 4) AS cvr,
           ROUND(total_spend * 1.0 / NULLIF(total_conversions, 0), 2)  AS cpa,
           ROUND(total_revenue * 1.0 / NULLIF(total_spend, 0), 2)      AS roi
    FROM platform_summary
)
SELECT platform,
       total_spend,
       total_revenue,
       roi,
       ctr,
       cvr,
       cpa,
       CASE
           WHEN roi >= 3.0 AND cpa < 50 THEN '高效拉新场'
           WHEN roi >= 2.0 THEN '高价值种草地'
           WHEN ctr >= 0.02 THEN '低成本引流'
           ELSE '需优化'
       END AS role
FROM platform_kpi
ORDER BY roi DESC;


-- ============================================================
-- 六、索引与性能（第 29 题）★★★
-- ============================================================

-- ── 第 29 题 ★★★  索引设计
-- 场景: 需要频繁查询某用户在某时间段的下单记录
-- SELECT * FROM orders
-- WHERE user_id = 'U12345'
--   AND create_time >= '2025-10-01'
-- ORDER BY create_time DESC
-- LIMIT 20;
--
-- 问题 1: 应该在哪些列上建什么索引？
-- 答: 联合索引 (user_id, create_time)
--     user_id 等值过滤放前面，create_time 范围查询+排序放后面
--     最左前缀原则: WHERE user_id=? AND create_time>=? 能充分利用
--
-- 问题 2: 为什么不是 (create_time, user_id)？
-- 答: 如果 create_time 在前，范围查询后的列无法用索引排序
--     且 user_id 等值过滤的过滤性更强，应放前面
--
-- 问题 3: 这个查询能用覆盖索引吗？
-- 答: SELECT * 不能覆盖；改成 SELECT user_id, create_time 可以用
--     (user_id, create_time) 索引覆盖这两个字段，避免回表
--
-- 建索引语句:
-- CREATE INDEX idx_uid_ctime ON orders(user_id, create_time);


-- ============================================================
-- 七、综合实战题（第 30 题）★★★
-- ============================================================

-- ── 第 30 题 ★★★  RFM + G 五维用户分层
-- 综合 CTE + NTILE + CASE WHEN + 多表 JOIN，项目中最复杂的一道。
-- 考点: 窗口函数 NTILE() 等分打分、CTE 多步骤、CASE WHEN 分层。
WITH user_order_stats AS (
    SELECT u.user_id,
           u.registration_date,
           -- R: 最近购买距今天数
           DATEDIFF(NOW(), MAX(o.create_time))            AS recency,
           -- F: 订单数
           COUNT(DISTINCT o.order_id)                     AS frequency,
           -- M: 累计金额
           COALESCE(SUM(o.amount), 0)                     AS monetary,
           -- G: 品类多样性
           COUNT(DISTINCT p.category_id)                  AS category_diversity
    FROM users u
    LEFT JOIN orders o       ON u.user_id = o.user_id
        AND o.order_status IN ('paid', 'shipped', 'completed')
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    LEFT JOIN products p     ON oi.product_id = p.product_id
    GROUP BY u.user_id, u.registration_date
),
scored AS (
    SELECT user_id, recency, frequency, monetary, category_diversity,
           -- R: 越小越好 → 倒序 NTILE 打分
           COALESCE(6 - NTILE(5) OVER (ORDER BY recency DESC), 3) AS r_score,
           -- F: 越大越好
           COALESCE(NTILE(5) OVER (ORDER BY frequency), 3)       AS f_score,
           -- M: 越大越好
           COALESCE(NTILE(5) OVER (ORDER BY monetary), 3)        AS m_score,
           -- G: 品类多样性越大越好
           COALESCE(NTILE(5) OVER (ORDER BY category_diversity), 3) AS g_score
    FROM user_order_stats
),
segmented AS (
    SELECT *,
           r_score + f_score + m_score + g_score AS rfm_total,
           CASE
               WHEN r_score + f_score + m_score + g_score >= 16 THEN '高价值深耕用户'
               WHEN r_score + f_score + m_score + g_score >= 12 THEN '高潜唤醒用户'
               WHEN r_score + f_score + m_score + g_score >= 8  THEN '成长型用户'
               ELSE '流失风险用户'
           END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*)                                      AS user_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct,
       ROUND(AVG(recency), 0)                        AS avg_recency_days,
       ROUND(AVG(frequency), 1)                      AS avg_frequency,
       ROUND(AVG(monetary), 0)                       AS avg_monetary,
       ROUND(AVG(category_diversity), 1)             AS avg_diversity
FROM segmented
GROUP BY segment
ORDER BY AVG(rfm_total) DESC;


-- ═══════════════════════════════════════════════════════════════
--  每题涉及的表格速查
-- ═══════════════════════════════════════════════════════════════
--
--   题号    涉及表
--   ──────────────────────────────────────
--    1      user_behavior
--    2      orders（项目一）
--    3      users
--    4      ad_campaigns
--    5      products
--    6      inventory_data + products
--    7      user_behavior
--    8      user_behavior
--    9      ad_campaigns
--   10      orders
--   11      orders
--   12      user_behavior
--   13      users + user_activities
--   14      orders
--   15      users + orders + order_items + products（四表 JOIN）
--   16      user_behavior + orders
--   17      user_behavior + orders（聚合后关联）
--   18      products + inventory_data + sales_data（三表）
--   19      orders
--   20      orders
--   21      orders
--   22      orders
--   23      users + orders + order_items + products + 品类分析
--   24      sales_data（移动平均）
--   25      orders
--   26      users + user_activities（NOT EXISTS）
--   27      orders（CTE + ROW_NUMBER）
--   28      ad_campaigns（CTE + 平台效能）
--   29      口述题: orders 索引设计
--   30      users+orders+order_items+products（RFM+G 五表）
--
-- ═══════════════════════════════════════════════════════════════
--  高频 TOP 5（面试最常考）
-- ═══════════════════════════════════════════════════════════════
--
--   1. 第 8 题  WHERE vs HAVING 区别（执行顺序）
--   2. 第 12 题 CASE WHEN 行转列（条件聚合）
--   3. 第 19 题 ROW_NUMBER vs RANK vs DENSE_RANK
--   4. 第 15 题 多表 JOIN（四表联查）
--   5. 第 30 题 RFM+G 综合分层（CTE+NTILE+CASE WHEN）
-- ═══════════════════════════════════════════════════════════════
