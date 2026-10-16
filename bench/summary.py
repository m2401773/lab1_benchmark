"""сводные таблицы в markdown из results/<sf>/*.csv

пример: python bench/summary.py sf10 > results/summary_sf10.md
"""
import sys

import pandas as pd

from common import RESULTS_DIR, variants

MIB = 2**20
# ориентировочные цены для оценки стоимости
S3_USD_PER_GB_MONTH = 0.023
VCPU_USD_PER_HOUR = 0.04


def md(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def order(df):
    keys = [f"{f}+{c}" for f, c in variants()]
    df["variant"] = df.format + "+" + df.codec
    df["variant"] = pd.Categorical(df.variant, keys, ordered=True)
    return df.sort_values("variant")


def main(sf):
    d = RESULTS_DIR / sf
    sizes = pd.read_csv(d / "sizes.csv")
    writes = pd.read_csv(d / "writes.csv")
    queries = pd.read_csv(d / "queries.csv")
    checks = pd.read_csv(d / "checks.csv")

    print(f"## {sf}\n\nПроверка gold против эталона: "
          f"{int(checks.matches_reference.sum())} из {len(checks)} вариантов совпали, "
          f"{checks.gold_rows.iloc[0]} строк\n")

    p = sizes.pivot_table(index=["format", "codec"], columns="layer", values="data_bytes", aggfunc="sum").reset_index()
    p["total"] = p.bronze + p.silver + p.gold
    base = p[p.codec == "NONE"].set_index("format").total
    p["ratio"] = (p.format.map(base) / p.total).round(2)
    meta = sizes.groupby(["format", "codec"]).metadata_bytes.sum().reset_index()
    p = order(p.merge(meta, on=["format", "codec"]))
    out = pd.DataFrame({
        "Формат": p.format, "Кодек": p.codec,
        "Bronze, МиБ": (p.bronze / MIB).round(1), "Silver, МиБ": (p.silver / MIB).round(1),
        "Gold, КиБ": (p.gold / 1024).round(1), "Всего, МиБ": (p.total / MIB).round(1),
        "Сжатие к NONE": p.ratio, "Метаданные, КиБ": (p.metadata_bytes / 1024).round(0).astype(int),
    })
    print("### Размер\n\n" + md(out) + "\n")

    w = writes.pivot_table(index=["format", "codec"], columns="layer", values="elapsed_ms", aggfunc="sum").reset_index()
    cpu = writes.groupby(["format", "codec"]).cpu_ms.sum().reset_index()
    w = order(w.merge(cpu, on=["format", "codec"]))
    out = pd.DataFrame({
        "Формат": w.format, "Кодек": w.codec,
        "Bronze, с": (w.bronze / 1000).round(2), "Silver, с": (w.silver / 1000).round(2),
        "Gold, с": (w.gold / 1000).round(2), "Всего, с": ((w.bronze + w.silver + w.gold) / 1000).round(2),
        "CPU, с": (w.cpu_ms / 1000).round(1),
    })
    print("### Запись\n\n" + md(out) + "\n")

    warm = queries[queries.run > 0]
    q = warm.pivot_table(index=["format", "codec"], columns="query", values="elapsed_ms", aggfunc="median").reset_index()
    inp = warm[warm["query"] == "q16_on_bronze"].groupby(["format", "codec"]).physical_input_bytes.median().reset_index()
    cpuq = warm[warm["query"] == "q16_on_bronze"].groupby(["format", "codec"]).cpu_ms.median().reset_index()
    q = order(q.merge(inp, on=["format", "codec"]).merge(cpuq, on=["format", "codec"]))
    out = pd.DataFrame({
        "Формат": q.format, "Кодек": q.codec,
        "q16_on_bronze": q.q16_on_bronze.astype(int), "q16_on_silver": q.q16_on_silver.astype(int),
        "gold_read": q.gold_read.astype(int), "scan_agg": q.scan_agg.astype(int),
        "point_filter": q.point_filter.astype(int),
        "Прочитано q16_on_bronze, МиБ": (q.physical_input_bytes / MIB).round(1),
    })
    print("### Агрегации, медиана повторных запусков, мс\n\n" + md(out) + "\n")

    # грубая модель стоимости: хранение всех слоев и 1000 запусков q16 по bronze в день
    size_gb = p.set_index(["format", "codec"]).total / 1e9
    cpu_h = q.set_index(["format", "codec"]).cpu_ms / 1000 / 3600
    cost = pd.DataFrame({"storage": size_gb * S3_USD_PER_GB_MONTH, "compute": cpu_h * 1000 * 30 * VCPU_USD_PER_HOUR}).reset_index()
    cost = order(cost)
    out = pd.DataFrame({
        "Формат": cost.format, "Кодек": cost.codec,
        "Хранение, $/мес": cost.storage.round(4), "Вычисления, $/мес": cost.compute.round(4),
        "Итого, $/мес": (cost.storage + cost.compute).round(4),
    })
    print("### Оценка стоимости\n\n" + md(out) + "\n")

    if (d / "metadata_stats.csv").exists():
        ms = pd.read_csv(d / "metadata_stats.csv")
        mq = pd.read_csv(d / "metadata_queries.csv")
        mq = mq[mq.run > 0].groupby(["format", "state", "query"])[["elapsed_ms", "planning_ms"]].median().reset_index()
        piv = mq.pivot_table(index=["format", "state"], columns="query", values="elapsed_ms").reset_index()
        plan = mq[mq["query"] == "q16_on_silver"][["format", "state", "planning_ms"]]
        m = ms.merge(piv, on=["format", "state"]).merge(plan, on=["format", "state"])
        states = ["compact", "fragmented", "after_optimize", "after_expire", "after_manifests"]
        m["state"] = pd.Categorical(m.state, states, ordered=True)
        m = m.sort_values(["format", "state"], ascending=[False, True])
        out = pd.DataFrame({
            "Формат": m.format, "Состояние": m.state, "Снапшоты": m.snapshots,
            "Файлы данных": m.data_files, "Файлы метаданных": m.metadata_files,
            "Метаданные, КиБ": (m.metadata_bytes / 1024).round(0).astype(int),
            "Данные, МиБ": (m.data_bytes / MIB).round(1),
            "Планирование, мс": m.planning_ms.astype(int),
            "q16_on_silver, мс": m.q16_on_silver.astype(int), "scan_agg, мс": m.scan_agg.astype(int),
            "point_filter, мс": m.point_filter.astype(int),
        })
        print("### Метаданные\n\n" + md(out) + "\n")

    if (d / "cache.csv").exists():
        c = pd.read_csv(d / "cache.csv")
        rows = []
        for (f, cd, cat, qn), g in c.groupby(["format", "codec", "catalog", "query"], sort=False):
            rows.append({"Формат": f, "Кодек": cd, "Каталог": cat, "Запрос": qn,
                         "Первый, мс": int(g[g.run == 0].elapsed_ms.iloc[0]),
                         "Повторные, мс": int(g[g.run > 0].elapsed_ms.median()),
                         "Планирование первый, мс": int(g[g.run == 0].planning_ms.iloc[0]),
                         "Планирование повторные, мс": int(g[g.run > 0].planning_ms.median()),
                         "Кэш, МиБ": round(g.fs_cache_bytes.iloc[0] / MIB, 1)})
        print("### Кэширование\n\n" + md(pd.DataFrame(rows)) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sf10")
