-- 第 5 题 ★  基础查询
-- 查询 product_name 包含"袜子"的所有产品
-- 考点: LIKE 模糊匹配，% 匹配任意字符
-- 追问: LIKE '%袜子%' 能否用索引？答: 不能，前缀模糊才能走索引

SELECT product_id, product_name, category_id
FROM products
WHERE product_name LIKE '%袜子%';
