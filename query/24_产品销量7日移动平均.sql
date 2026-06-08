-- 第 24 题 ★★  窗口函数
-- 计算每个产品日销量的 7 日移动平均
-- 考点: AVG() OVER(...ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)

SELECT product_id,
       sale_date,
       daily_sales,
       ROUND(
           AVG(daily_sales) OVER (
               PARTITION BY product_id
               ORDER BY sale_date
               ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
           ), 1
       ) AS ma_7day
FROM (
    SELECT product_id, sale_date,
           SUM(sales_volume) AS daily_sales
    FROM sales_data
    GROUP BY product_id, sale_date
) t
ORDER BY product_id, sale_date;
