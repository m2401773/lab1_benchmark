## sf1

Проверка gold против эталона: 9 из 9 вариантов совпали, 18314 строк

### Размер

| Формат | Кодек | Bronze, МиБ | Silver, МиБ | Gold, КиБ | Всего, МиБ | Сжатие к NONE | Метаданные, КиБ |
|---|---|---|---|---|---|---|---|
| PARQUET | NONE | 121.5 | 20.6 | 49.0 | 142.1 | 1.0 | 845 |
| PARQUET | SNAPPY | 46.1 | 15.6 | 44.8 | 61.7 | 2.3 | 844 |
| PARQUET | ZSTD | 33.3 | 13.0 | 40.1 | 46.3 | 3.07 | 845 |
| PARQUET | GZIP | 29.7 | 11.9 | 40.1 | 41.7 | 3.41 | 844 |
| ORC | NONE | 123.9 | 24.8 | 74.5 | 148.7 | 1.0 | 844 |
| ORC | SNAPPY | 43.9 | 15.5 | 61.3 | 59.5 | 2.5 | 845 |
| ORC | LZ4 | 49.0 | 15.6 | 62.9 | 64.7 | 2.3 | 844 |
| ORC | ZSTD | 30.9 | 10.7 | 42.8 | 41.7 | 3.57 | 844 |
| ORC | GZIP | 29.8 | 10.9 | 43.7 | 40.7 | 3.66 | 844 |

### Запись

| Формат | Кодек | Bronze, с | Silver, с | Gold, с | Всего, с | CPU, с |
|---|---|---|---|---|---|---|
| PARQUET | NONE | 3.38 | 2.26 | 0.35 | 5.99 | 6.2 |
| PARQUET | SNAPPY | 3.66 | 2.39 | 0.32 | 6.37 | 8.0 |
| PARQUET | ZSTD | 2.14 | 1.72 | 0.21 | 4.08 | 4.8 |
| PARQUET | GZIP | 4.3 | 2.41 | 0.25 | 6.96 | 7.8 |
| ORC | NONE | 2.57 | 1.71 | 0.23 | 4.51 | 4.5 |
| ORC | SNAPPY | 2.5 | 2.09 | 0.25 | 4.84 | 5.3 |
| ORC | LZ4 | 2.03 | 1.61 | 0.2 | 3.83 | 3.9 |
| ORC | ZSTD | 2.23 | 1.9 | 0.22 | 4.35 | 4.8 |
| ORC | GZIP | 3.96 | 2.46 | 0.24 | 6.66 | 8.2 |

### Агрегации, медиана повторных запусков, мс

| Формат | Кодек | q16_on_bronze | q16_on_silver | gold_read | scan_agg | point_filter | Прочитано q16_on_bronze, МиБ |
|---|---|---|---|---|---|---|---|
| PARQUET | NONE | 329 | 325 | 89 | 89 | 164 | 9.1 |
| PARQUET | SNAPPY | 287 | 191 | 81 | 61 | 43 | 5.5 |
| PARQUET | ZSTD | 322 | 248 | 92 | 82 | 61 | 3.7 |
| PARQUET | GZIP | 336 | 243 | 93 | 122 | 67 | 3.8 |
| ORC | NONE | 398 | 258 | 96 | 99 | 55 | 5.7 |
| ORC | SNAPPY | 352 | 211 | 100 | 83 | 62 | 12.8 |
| ORC | LZ4 | 350 | 204 | 93 | 75 | 53 | 14.2 |
| ORC | ZSTD | 349 | 237 | 85 | 86 | 53 | 9.2 |
| ORC | GZIP | 423 | 237 | 89 | 106 | 62 | 9.3 |

### Оценка стоимости

| Формат | Кодек | Хранение, $/мес | Вычисления, $/мес | Итого, $/мес |
|---|---|---|---|---|
| PARQUET | NONE | 0.0034 | 0.0777 | 0.0811 |
| PARQUET | SNAPPY | 0.0015 | 0.069 | 0.0705 |
| PARQUET | ZSTD | 0.0011 | 0.0917 | 0.0928 |
| PARQUET | GZIP | 0.001 | 0.0927 | 0.0937 |
| ORC | NONE | 0.0036 | 0.098 | 0.1016 |
| ORC | SNAPPY | 0.0014 | 0.0953 | 0.0968 |
| ORC | LZ4 | 0.0016 | 0.0903 | 0.0919 |
| ORC | ZSTD | 0.001 | 0.101 | 0.102 |
| ORC | GZIP | 0.001 | 0.119 | 0.12 |

### Метаданные

| Формат | Состояние | Снапшоты | Файлы данных | Файлы метаданных | Метаданные, КиБ | Данные, МиБ | Планирование, мс | q16_on_silver, мс | scan_agg, мс | point_filter, мс |
|---|---|---|---|---|---|---|---|---|---|---|
| PARQUET | compact | 1 | 1 | 5 | 212 | 13.0 | 11 | 150 | 49 | 36 |
| PARQUET | fragmented | 101 | 100 | 502 | 52864 | 14.7 | 12 | 143 | 91 | 49 |
| PARQUET | after_optimize | 102 | 101 | 508 | 53711 | 27.5 | 22 | 163 | 77 | 52 |
| PARQUET | after_expire | 1 | 1 | 105 | 24273 | 12.8 | 20 | 149 | 83 | 47 |
| PARQUET | after_manifests | 2 | 1 | 108 | 24310 | 12.8 | 9 | 127 | 51 | 33 |
| ORC | compact | 1 | 1 | 5 | 212 | 10.8 | 9 | 142 | 55 | 34 |
| ORC | fragmented | 101 | 100 | 502 | 52736 | 11.8 | 10 | 157 | 47 | 59 |
| ORC | after_optimize | 102 | 101 | 508 | 53577 | 22.9 | 20 | 183 | 77 | 56 |
| ORC | after_expire | 1 | 1 | 105 | 24182 | 11.1 | 22 | 200 | 79 | 46 |
| ORC | after_manifests | 2 | 1 | 108 | 24219 | 11.1 | 14 | 189 | 76 | 40 |

### Кэширование

| Формат | Кодек | Каталог | Запрос | Первый, мс | Повторные, мс | Планирование первый, мс | Планирование повторные, мс | Кэш, МиБ |
|---|---|---|---|---|---|---|---|---|
| PARQUET | ZSTD | iceberg | q16_on_bronze | 351 | 335 | 65 | 40 | 0.0 |
| PARQUET | ZSTD | iceberg | q16_on_silver | 192 | 194 | 20 | 16 | 0.0 |
| PARQUET | ZSTD | iceberg | scan_agg | 79 | 71 | 10 | 7 | 0.0 |
| PARQUET | ZSTD | iceberg_cached | q16_on_bronze | 448 | 346 | 76 | 51 | 18.5 |
| PARQUET | ZSTD | iceberg_cached | q16_on_silver | 227 | 196 | 31 | 18 | 18.5 |
| PARQUET | ZSTD | iceberg_cached | scan_agg | 71 | 59 | 9 | 9 | 18.5 |
| ORC | ZSTD | iceberg | q16_on_bronze | 395 | 321 | 64 | 40 | 0.0 |
| ORC | ZSTD | iceberg | q16_on_silver | 226 | 169 | 20 | 15 | 0.0 |
| ORC | ZSTD | iceberg | scan_agg | 74 | 74 | 8 | 7 | 0.0 |
| ORC | ZSTD | iceberg_cached | q16_on_bronze | 574 | 350 | 150 | 49 | 20.8 |
| ORC | ZSTD | iceberg_cached | q16_on_silver | 203 | 196 | 23 | 18 | 20.8 |
| ORC | ZSTD | iceberg_cached | scan_agg | 81 | 72 | 11 | 9 | 20.8 |
| PARQUET | NONE | iceberg | q16_on_bronze | 452 | 419 | 63 | 50 | 0.0 |
| PARQUET | NONE | iceberg | q16_on_silver | 254 | 232 | 23 | 15 | 0.0 |
| PARQUET | NONE | iceberg | scan_agg | 76 | 77 | 8 | 7 | 0.0 |
| PARQUET | NONE | iceberg_cached | q16_on_bronze | 408 | 360 | 80 | 55 | 29.0 |
| PARQUET | NONE | iceberg_cached | q16_on_silver | 268 | 181 | 32 | 18 | 29.0 |
| PARQUET | NONE | iceberg_cached | scan_agg | 81 | 58 | 10 | 10 | 29.0 |

