-- gold: витрина ответа на q16
CREATE TABLE {schema}.gold_supplier_cnt WITH (format = '{fmt}') AS
SELECT
  brand,
  type,
  size,
  count(DISTINCT suppkey) AS supplier_cnt
FROM {schema}.silver_part_supplier
WHERE brand <> 'Brand#45'
  AND type NOT LIKE 'MEDIUM POLISHED%'
  AND size IN (49, 14, 23, 45, 19, 3, 36, 9)
GROUP BY brand, type, size;
