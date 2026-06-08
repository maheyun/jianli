-- 第 18 题 ★★  多表 JOIN
-- 查询产品库存+销量+销售额+售罄率
-- 考点: 三表 LEFT JOIN + NULLIF 防除零 + 子查询聚合

SELECT p.product_id,
       p.product_name,
       COALESCE(i.current_stock, 0)            AS current_stock,
       COALESCE(s.total_volume, 0)             AS total_sold,
       COALESCE(s.total_amount, 0)             AS total_revenue,
       ROUND(
           COALESCE(s.total_volume, 0)
           / NULLIF(COALESCE(s.total_volume, 0)
               + COALESCE(i.current_stock, 0), 0),
           4
       ) AS sell_through_rate
FROM products p
LEFT JOIN inventory_data i ON p.product_id = i.product_id
LEFT JOIN (
    SELECT product_id,
           SUM(sales_volume) AS total_volume,
           SUM(sales_amount) AS total_amount
    FROM sales_data
    GROUP BY product_id
) s ON p.product_id = s.product_id
ORDER BY sell_through_rate DESC;
