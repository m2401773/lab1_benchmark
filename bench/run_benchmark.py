"""полный цикл bronze -> silver -> gold и бенчмарк форматов и кодеков

пример: python bench/run_benchmark.py --sf sf10 --repeats 5
"""
import argparse
import re

import pandas as pd

from common import (RESULTS_DIR, SQL_DIR, connect, median, named_queries, run,
                    schema_name, statements, table_storage, variants)

LAYER_FILES = [("bronze", "01_bronze.sql"), ("silver", "02_silver.sql"), ("gold", "03_gold.sql")]


def build_variant(sf, fmt, codec):
    schema = schema_name(sf, fmt, codec)
    conn = connect(codec=codec)
    run(conn, f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    run(conn, f"CREATE SCHEMA {schema}")

    writes = []
    for layer, fname in LAYER_FILES:
        for sql in statements(SQL_DIR / fname, sf=sf, schema=schema, fmt=fmt):
            table = re.search(r"CREATE TABLE \S+?\.(\w+)", sql).group(1)
            rows, st = run(conn, sql)
            writes.append({"sf": sf, "format": fmt, "codec": codec, "layer": layer,
                           "table": table, "rows_written": rows[0][0], **st})
            print(f"  {layer:6} {table:22} {st['elapsed_ms'] / 1000:7.2f} s")
    return schema, writes


def measure_sizes(sf, fmt, codec, schema, tables):
    conn = connect()
    out = []
    for layer, table in tables:
        info = table_storage(conn, f"{schema}.{table}")
        out.append({"sf": sf, "format": fmt, "codec": codec, "layer": layer, "table": table, **info})
    return out


def check_gold(sf, schema, reference):
    rows, _ = run(connect(), named_queries(schema=schema)["gold_read"])
    return [tuple(r) for r in rows] == reference


def bench_queries(sf, fmt, codec, schema, repeats):
    conn = connect()
    out = []
    for name, sql in named_queries(schema=schema).items():
        # нулевой прогон считаем первым после записи, остальные теплыми
        for i in range(repeats + 1):
            _, st = run(conn, sql)
            out.append({"sf": sf, "format": fmt, "codec": codec, "query": name, "run": i, **st})
        warm = [r["elapsed_ms"] for r in out if r["query"] == name and r["run"] > 0]
        print(f"  {name:14} first {out[-repeats - 1]['elapsed_ms']:6} ms  warm median {median(warm):8.1f} ms")
    return out


def bench_round_robin(sf, rounds):
    # раунды по кругу через все варианты, чтобы фоновый шум ложился на всех поровну
    conn = connect()
    plan = [(f, c, schema_name(sf, f, c)) for f, c in variants()]
    out = []
    for i in range(rounds + 1):
        for fmt, codec, schema in plan:
            for name, sql in named_queries(schema=schema).items():
                _, st = run(conn, sql)
                out.append({"sf": sf, "format": fmt, "codec": codec, "query": name, "run": i, **st})
        print(f"  раунд {i}/{rounds}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sf", default="sf10")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--only", help="например parquet_zstd")
    ap.add_argument("--queries-only", action="store_true", help="только перезамер запросов по кругу")
    args = ap.parse_args()

    out_dir = RESULTS_DIR / args.sf
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.queries_only:
        pd.DataFrame(bench_round_robin(args.sf, args.repeats)).to_csv(out_dir / "queries.csv", index=False)
        return

    ref_sql = statements(SQL_DIR / "00_reference_q16.sql", sf=args.sf)[0]
    ref_rows, ref_stats = run(connect(), ref_sql)
    reference = [tuple(r) for r in ref_rows]
    print(f"эталон q16 по tpch.{args.sf}: {len(reference)} строк, {ref_stats['elapsed_ms']} ms")

    writes, sizes, queries, checks = [], [], [], []
    for fmt, codec in variants():
        if args.only and args.only != f"{fmt}_{codec}".lower():
            continue
        print(f"== {fmt} + {codec}")
        schema, w = build_variant(args.sf, fmt, codec)
        writes += w
        sizes += measure_sizes(args.sf, fmt, codec, schema, [(x["layer"], x["table"]) for x in w])
        ok = check_gold(args.sf, schema, reference)
        checks.append({"sf": args.sf, "format": fmt, "codec": codec,
                       "gold_rows": len(reference), "matches_reference": ok})
        print(f"  gold совпадает с эталоном: {ok}")
        queries += bench_queries(args.sf, fmt, codec, schema, args.repeats)

    suffix = f"_{args.only}" if args.only else ""
    pd.DataFrame(writes).to_csv(out_dir / f"writes{suffix}.csv", index=False)
    pd.DataFrame(sizes).to_csv(out_dir / f"sizes{suffix}.csv", index=False)
    pd.DataFrame(queries).to_csv(out_dir / f"queries{suffix}.csv", index=False)
    pd.DataFrame(checks).to_csv(out_dir / f"checks{suffix}.csv", index=False)
    pd.DataFrame([{"sf": args.sf, "rows": len(reference), **ref_stats}]).to_csv(
        out_dir / f"reference{suffix}.csv", index=False)
    print(f"результаты в {out_dir}")


if __name__ == "__main__":
    main()
