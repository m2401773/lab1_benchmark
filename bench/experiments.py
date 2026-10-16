"""эксперименты: влияние метаданных (мелкие файлы и снапшоты) и кэширования

пример: python bench/experiments.py --sf sf10 metadata
        python bench/experiments.py --sf sf10 cache
"""
import argparse

import pandas as pd

from common import (RESULTS_DIR, connect, fs_cache_bytes, median, named_queries,
                    restart_trino, run, schema_name, table_storage)

META_QUERIES = ["q16_on_silver", "scan_agg", "point_filter"]
CACHE_QUERIES = ["q16_on_bronze", "q16_on_silver", "scan_agg"]


def table_meta(conn, fq):
    t = fq.split(".")
    base = f'{t[0]}."{t[1]}'
    snaps = run(conn, f'SELECT count(*) FROM {base}$snapshots"')[0][0][0]
    manifests = run(conn, f'SELECT count(*) FROM {base}$manifests"')[0][0][0]
    return {"snapshots": snaps, "manifests": manifests, **table_storage(conn, fq)}


def time_queries(conn, schema, table, state, repeats):
    out = []
    queries = named_queries(schema=schema)
    for name in META_QUERIES:
        sql = queries[name].replace("silver_part_supplier", table)
        for i in range(repeats + 1):
            _, st = run(conn, sql)
            out.append({"state": state, "query": name, "run": i, **st})
    return out


def metadata_experiment(sf, fmt, codec, batches, repeats):
    src = f"{schema_name(sf, fmt, codec)}.silver_part_supplier"
    schema = f"{sf}_meta_{fmt}".lower()
    conn = connect(codec=codec)
    run(conn, f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    run(conn, f"CREATE SCHEMA {schema}")

    compact = f"{schema}.silver_compact"
    frag = f"{schema}.silver_fragmented"
    run(conn, f"CREATE TABLE {compact} WITH (format = '{fmt}') AS SELECT * FROM {src}")
    run(conn, f"CREATE TABLE {frag} WITH (format = '{fmt}') AS SELECT * FROM {src} WITH NO DATA")

    # имитируем потоковую загрузку: много мелких коммитов
    for i in range(batches):
        run(conn, f"INSERT INTO {frag} SELECT * FROM {src} WHERE partkey % {batches} = {i}")
        if i % 20 == 0:
            print(f"  insert {i}/{batches}")

    stats, timings = [], []
    states = [("compact", compact, None), ("fragmented", frag, None),
              ("after_optimize", frag, f"ALTER TABLE {frag} EXECUTE optimize"),
              ("after_expire", frag, f"ALTER TABLE {frag} EXECUTE expire_snapshots(retention_threshold => '0s')"),
              ("after_manifests", frag, f"ALTER TABLE {frag} EXECUTE optimize_manifests")]
    for state, table, action in states:
        if action:
            run(conn, action)
            if state == "after_expire":
                run(conn, f"ALTER TABLE {frag} EXECUTE remove_orphan_files(retention_threshold => '0s')")
        meta = table_meta(conn, table)
        stats.append({"sf": sf, "format": fmt, "codec": codec, "state": state, **meta})
        print(f"  {state:15} files={meta['data_files']:4} manifests={meta['manifests']:4} "
              f"snapshots={meta['snapshots']:4} meta={meta['metadata_bytes'] / 1024:8.1f} KiB")
        timings += time_queries(conn, schema, table.split(".")[1], state, repeats)

    t = pd.DataFrame(timings)
    t["sf"], t["format"], t["codec"] = sf, fmt, codec
    return pd.DataFrame(stats), t


def cache_experiment(sf, variant_list, repeats):
    rows = []
    for fmt, codec in variant_list:
        schema = schema_name(sf, fmt, codec)
        queries = named_queries(schema=schema)
        for catalog in ["iceberg", "iceberg_cached"]:
            restart_trino()
            conn = connect(catalog=catalog)
            # прогрев jit на другой схеме, чтобы холодный прогон мерил только io и метаданные
            for warm_fmt in ["PARQUET", "ORC"]:
                warm_q = named_queries(schema=schema_name(sf, warm_fmt, "SNAPPY"))
                for name in CACHE_QUERIES:
                    run(connect(), warm_q[name])
            for name in CACHE_QUERIES:
                for i in range(repeats + 1):
                    _, st = run(conn, queries[name])
                    rows.append({"sf": sf, "format": fmt, "codec": codec, "catalog": catalog,
                                 "query": name, "run": i, **st})
            cache = fs_cache_bytes() if catalog == "iceberg_cached" else 0
            for r in rows[-len(CACHE_QUERIES) * (repeats + 1):]:
                r["fs_cache_bytes"] = cache
            cold = [r["elapsed_ms"] for r in rows if r["catalog"] == catalog and r["run"] == 0
                    and r["format"] == fmt and r["codec"] == codec]
            print(f"  {fmt} {codec} {catalog:15} cold sum {sum(cold)} ms, cache {cache / 2**20:.0f} MiB")
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment", choices=["metadata", "cache"])
    ap.add_argument("--sf", default="sf10")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--batches", type=int, default=100)
    args = ap.parse_args()
    out_dir = RESULTS_DIR / args.sf
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.experiment == "metadata":
        frames = [metadata_experiment(args.sf, f, c, args.batches, args.repeats)
                  for f, c in [("PARQUET", "ZSTD"), ("ORC", "ZSTD")]]
        pd.concat([f[0] for f in frames]).to_csv(out_dir / "metadata_stats.csv", index=False)
        pd.concat([f[1] for f in frames]).to_csv(out_dir / "metadata_queries.csv", index=False)
    else:
        df = cache_experiment(args.sf, [("PARQUET", "ZSTD"), ("ORC", "ZSTD"), ("PARQUET", "NONE")],
                              args.repeats)
        df.to_csv(out_dir / "cache.csv", index=False)
        summary = df.groupby(["format", "codec", "catalog", "query"]).apply(
            lambda g: pd.Series({"cold_ms": g[g.run == 0].elapsed_ms.iloc[0],
                                 "warm_ms": median(list(g[g.run > 0].elapsed_ms))}))
        print(summary)


if __name__ == "__main__":
    main()
