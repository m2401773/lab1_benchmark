-- bronze: сырые таблицы как есть, добавляем только служебные поля загрузки
CREATE TABLE {schema}.bronze_part WITH (format = '{fmt}') AS
SELECT p.*, current_timestamp(3) AS _ingested_at, 'tpch.{sf}.part' AS _source
FROM tpch.{sf}.part AS p;

CREATE TABLE {schema}.bronze_partsupp WITH (format = '{fmt}') AS
SELECT ps.*, current_timestamp(3) AS _ingested_at, 'tpch.{sf}.partsupp' AS _source
FROM tpch.{sf}.partsupp AS ps;

CREATE TABLE {schema}.bronze_supplier WITH (format = '{fmt}') AS
SELECT s.*, current_timestamp(3) AS _ingested_at, 'tpch.{sf}.supplier' AS _source
FROM tpch.{sf}.supplier AS s;
