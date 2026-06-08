-- 第 6 题 ★  基础查询
-- 查询有库存且品类为 1 或 2 的产品
-- 考点: IN 多值匹配（比多个 OR 更简洁高效）

SELECT p.product_id, p.product_name, i.current_stock
FROM products p
JOIN inventory_data i ON p.product_id = i.product_id
WHERE i.current_stock > 0
  AND p.category_id IN (1, 2);
