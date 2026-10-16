-- справочник поставщиков с флагом жалоб вместо сырого комментария
CREATE TABLE {schema}.silver_supplier WITH (format = '{fmt}') AS
SELECT
  suppkey,
  trim(name)                                  AS supplier_name,
  nationkey,
  comment LIKE '%Customer%Complaints%'        AS has_complaints
FROM {schema}.bronze_supplier
WHERE suppkey IS NOT NULL;

-- основная silver таблица: поставка + деталь, без поставщиков с жалобами
CREATE TABLE {schema}.silver_part_supplier WITH (format = '{fmt}') AS
SELECT
  ps.partkey,
  ps.suppkey,
  trim(p.brand)                               AS brand,
  upper(trim(p.type))                         AS type,
  split_part(upper(trim(p.type)), ' ', 1)     AS type_grade,
  split_part(upper(trim(p.type)), ' ', 2)     AS type_finish,
  split_part(upper(trim(p.type)), ' ', 3)     AS type_material,
  p.size,
  p.container,
  p.retailprice,
  ps.availqty,
  ps.supplycost,
  ps.availqty * ps.supplycost                 AS stock_value
FROM {schema}.bronze_partsupp AS ps
JOIN {schema}.bronze_part AS p ON p.partkey = ps.partkey
WHERE ps.partkey IS NOT NULL
  AND ps.suppkey NOT IN (
    SELECT suppkey FROM {schema}.silver_supplier WHERE has_complaints
  );
