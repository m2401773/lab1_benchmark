-- name: q16_on_bronze
-- исходный q16 по сырому слою: join, анти-джойн и count distinct
SELECT p.brand, p.type, p.size, count(DISTINCT ps.suppkey) AS supplier_cnt
FROM {schema}.bronze_partsupp AS ps
JOIN {schema}.bronze_part AS p ON p.partkey = ps.partkey
WHERE p.brand <> 'Brand#45'
  AND p.type NOT LIKE 'MEDIUM POLISHED%'
  AND p.size IN (49, 14, 23, 45, 19, 3, 36, 9)
  AND ps.suppkey NOT IN (
    SELECT suppkey FROM {schema}.bronze_supplier
    WHERE comment LIKE '%Customer%Complaints%'
  )
GROUP BY p.brand, p.type, p.size
ORDER BY supplier_cnt DESC, p.brand, p.type, p.size;

-- name: q16_on_silver
-- тот же ответ, но по уже очищенному и соединенному слою
SELECT brand, type, size, count(DISTINCT suppkey) AS supplier_cnt
FROM {schema}.silver_part_supplier
WHERE brand <> 'Brand#45'
  AND type NOT LIKE 'MEDIUM POLISHED%'
  AND size IN (49, 14, 23, 45, 19, 3, 36, 9)
GROUP BY brand, type, size
ORDER BY supplier_cnt DESC, brand, type, size;

-- name: gold_read
-- чтение готовой витрины, так работает bi
SELECT brand, type, size, supplier_cnt
FROM {schema}.gold_supplier_cnt
ORDER BY supplier_cnt DESC, brand, type, size;

-- name: scan_agg
-- широкий скан числовых колонок с группировкой
SELECT type_grade, type_material,
       sum(stock_value) AS stock_value,
       avg(supplycost)  AS avg_cost,
       count(*)         AS rows_cnt
FROM {schema}.silver_part_supplier
GROUP BY type_grade, type_material;

-- name: point_filter
-- селективный фильтр, проверяем пропуск данных по статистикам
SELECT count(*), sum(availqty)
FROM {schema}.silver_part_supplier
WHERE brand = 'Brand#23' AND size = 15 AND type_finish = 'BRUSHED';
