"""графики для отчета из results/<sf>/*.csv

пример: python bench/plots.py --sf sf10
"""
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import CODECS, FORMATS, RESULTS_DIR, ROOT

IMG = ROOT / "images"
COLORS = {"PARQUET": "#2a78d6", "ORC": "#eb6834"}
LABELS = {"PARQUET": "Parquet", "ORC": "ORC"}
SECOND = {"cold": "#2a78d6", "warm": "#eb6834"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.titlecolor": INK, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False,
})


def grouped(ax, df, value, fmt_label="{:.0f}"):
    # кодеки по оси x, форматы соседними столбиками
    x = np.arange(len(CODECS))
    w = 0.38
    for i, fmt in enumerate(FORMATS):
        vals = [df[(df.format == fmt) & (df.codec == c)][value].sum() if
                ((df.format == fmt) & (df.codec == c)).any() else np.nan for c in CODECS]
        pos = x + (i - 0.5) * (w + 0.02)
        ax.bar(pos, vals, w, color=COLORS[fmt], label=LABELS[fmt], zorder=2)
        for p, v in zip(pos, vals):
            if np.isnan(v):
                ax.text(p, 0, "нет\nподдержки", ha="center", va="bottom", fontsize=7, color=MUTED)
            else:
                ax.text(p, v, fmt_label.format(v), ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(x, CODECS)
    ax.legend(loc="upper right")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / name, dpi=160)
    plt.close(fig)
    print("  ", IMG / name)


def fig_size(sf, sizes):
    total = sizes.groupby(["format", "codec"], as_index=False).data_bytes.sum()
    total["mib"] = total.data_bytes / 2**20
    fig, ax = plt.subplots(figsize=(8, 4))
    grouped(ax, total, "mib")
    ax.set_title(f"Размер данных bronze + silver + gold, МиБ ({sf})")
    ax.set_ylabel("МиБ")
    save(fig, f"{sf}_size.png")


def fig_write(sf, writes):
    total = writes.groupby(["format", "codec"], as_index=False).elapsed_ms.sum()
    total["s"] = total.elapsed_ms / 1000
    fig, ax = plt.subplots(figsize=(8, 4))
    grouped(ax, total, "s", "{:.1f}")
    ax.set_title(f"Время записи всех слоев, с ({sf})")
    ax.set_ylabel("секунды")
    save(fig, f"{sf}_write.png")


def warm(queries):
    q = queries[queries.run > 0]
    return q.groupby(["format", "codec", "query"], as_index=False).elapsed_ms.median()


def fig_queries(sf, queries):
    med = warm(queries)
    names = ["q16_on_bronze", "q16_on_silver", "scan_agg", "point_filter"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for ax, name in zip(axes.flat, names):
        grouped(ax, med[med["query"] == name], "elapsed_ms")
        ax.set_title(f"{name}, медиана, мс")
    save(fig, f"{sf}_queries.png")


def fig_tradeoff(sf, sizes, queries):
    size = sizes.groupby(["format", "codec"], as_index=False).data_bytes.sum()
    med = warm(queries)
    med = med[med["query"] == "q16_on_bronze"]
    df = size.merge(med, on=["format", "codec"])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.grid(axis="both")
    for fmt in FORMATS:
        d = df[df.format == fmt]
        ax.scatter(d.data_bytes / 2**20, d.elapsed_ms, s=70, color=COLORS[fmt],
                   edgecolor="white", linewidth=2, label=LABELS[fmt], zorder=3)
        for _, r in d.iterrows():
            ax.annotate(r.codec, (r.data_bytes / 2**20, r.elapsed_ms), xytext=(6, 4 if fmt == "PARQUET" else -12),
                        textcoords="offset points", fontsize=8, color=INK)
    ax.set_xlabel("размер всех слоев, МиБ")
    ax.set_ylabel("q16 по bronze, медиана, мс")
    ax.set_title(f"Компромисс размер / скорость ({sf})")
    ax.legend()
    save(fig, f"{sf}_tradeoff.png")


def fig_metadata(sf, stats, queries):
    order = ["compact", "fragmented", "after_optimize", "after_expire", "after_manifests"]
    labels = ["compact", "fragmented", "optimize", "expire", "manifests"]
    s = stats[stats.format == "PARQUET"].set_index("state").loc[order]
    q = queries[(queries.format == "PARQUET") & (queries.run > 0) & (queries["query"] == "q16_on_silver")]
    q = q.groupby("state")[["elapsed_ms", "planning_ms"]].median().loc[order]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    x = np.arange(len(order))
    for ax, col, title, scale in [
        (axes[0], s.data_files + s.metadata_files, "Объекты в S3 (данные + метаданные)", 1),
        (axes[1], s.metadata_bytes / 1024, "Объем метаданных, КиБ", 1),
        (axes[2], q.planning_ms, "Планирование q16_on_silver, мс", 1),
    ]:
        ax.bar(x, col.values, 0.6, color=COLORS["PARQUET"], zorder=2)
        for xi, v in zip(x, col.values):
            ax.text(xi, v, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_xticks(x, labels, rotation=20)
        ax.set_title(title)
    fig.suptitle(f"Влияние метаданных Iceberg, Parquet + ZSTD ({sf})", fontweight="bold")
    save(fig, f"{sf}_metadata.png")


def fig_cache(sf, cache):
    d = cache[(cache.format == "PARQUET") & (cache.codec == "ZSTD")]
    names = ["q16_on_bronze", "q16_on_silver", "scan_agg"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, catalog, title in [(axes[0], "iceberg", "Без файлового кэша"),
                               (axes[1], "iceberg_cached", "С файловым кэшем Trino")]:
        g = d[d.catalog == catalog]
        cold = [g[(g["query"] == n) & (g.run == 0)].elapsed_ms.iloc[0] for n in names]
        hot = [g[(g["query"] == n) & (g.run > 0)].elapsed_ms.median() for n in names]
        x = np.arange(len(names))
        for off, vals, key, lab in [(-0.2, cold, "cold", "первый запуск"), (0.2, hot, "warm", "повторные, медиана")]:
            ax.bar(x + off, vals, 0.38, color=SECOND[key], label=lab, zorder=2)
            for xi, v in zip(x + off, vals):
                ax.text(xi, v, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_xticks(x, names)
        ax.set_title(title)
        ax.legend()
    axes[0].set_ylabel("мс")
    fig.suptitle(f"Кэширование, Parquet + ZSTD ({sf})", fontweight="bold")
    save(fig, f"{sf}_cache.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sf", nargs="+", default=["sf1", "sf10"])
    args = ap.parse_args()
    IMG.mkdir(exist_ok=True)
    for sf in args.sf:
        d = RESULTS_DIR / sf
        print(sf)
        sizes, writes, queries = (pd.read_csv(d / f"{n}.csv") for n in ["sizes", "writes", "queries"])
        fig_size(sf, sizes)
        fig_write(sf, writes)
        fig_queries(sf, queries)
        fig_tradeoff(sf, sizes, queries)
        if (d / "metadata_stats.csv").exists():
            fig_metadata(sf, pd.read_csv(d / "metadata_stats.csv"), pd.read_csv(d / "metadata_queries.csv"))
        if (d / "cache.csv").exists():
            fig_cache(sf, pd.read_csv(d / "cache.csv"))


if __name__ == "__main__":
    main()
