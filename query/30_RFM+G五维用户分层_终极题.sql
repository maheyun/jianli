-- 第 30 题 ★★★  综合实战（终极题）
-- RFM+G 五维用户分层: R(最近购买) F(频次) M(金额) G(品类拓展)
-- 考点: CTE三步 + NTILE(5)打分 + CASE WHEN分层 + 五表LEFT JOIN
--       + COALESCE/NULLIF + DATEDIFF + 窗口函数
--
-- 完整写出此题 = 具备中高级数据分析SQL能力

WITH user_order_stats AS (
    SELECT u.user_id,
           DATEDIFF(NOW(), MAX(o.create_time))  AS recency,
           COUNT(DISTINCT o.order_id)           AS frequency,
           COALESCE(SUM(o.amount), 0)           AS monetary,
           COUNT(DISTINCT p.category_id)        AS category_diversity
    FROM users_p2 u
    LEFT JOIN orders_p2 o ON u.user_id = o.user_id
        AND o.order_status IN ('paid', 'shipped', 'completed')
    LEFT JOIN order_items_p2 oi ON o.order_id = oi.order_id
    LEFT JOIN products_p2 p ON oi.product_id = p.product_id
    GROUP BY u.user_id
),
scored AS (
    SELECT user_id, recency, frequency, monetary, category_diversity,
           -- R: recency 越小越好 → NTILE 5 组后倒序，最近买的人得 5 分
           COALESCE(6 - NTILE(5) OVER (ORDER BY recency DESC), 3)    AS r_score,
           -- F: 越大越好 → 正序打分
           COALESCE(NTILE(5) OVER (ORDER BY frequency), 3)           AS f_score,
           -- M: 越大越好 → 正序打分
           COALESCE(NTILE(5) OVER (ORDER BY monetary), 3)            AS m_score,
           -- G: 品类越多越好 → 正序打分
           COALESCE(NTILE(5) OVER (ORDER BY category_diversity), 3)  AS g_score
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
       COUNT(*)                                   AS user_count,
       ROUND(AVG(recency), 0)                     AS avg_recency,
       ROUND(AVG(frequency), 1)                   AS avg_frequency,
       ROUND(AVG(monetary), 0)                    AS avg_monetary,
       ROUND(AVG(category_diversity), 1)          AS avg_diversity
FROM segmented
GROUP BY segment
ORDER BY AVG(rfm_total) DESC;
