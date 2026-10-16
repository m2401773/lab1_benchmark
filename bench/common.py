import os
import re
import shutil
import statistics
import subprocess
import time
from pathlib import Path

import boto3
import trino

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
RESULTS_DIR = ROOT / "results"

TRINO_HOST = os.getenv("TRINO_HOST", "localhost")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:8333")
BUCKET = "warehouse"

FORMATS = ["PARQUET", "ORC"]
CODECS = ["NONE", "SNAPPY", "LZ4", "ZSTD", "GZIP"]
# parquet writer в trino не поддерживает lz4
UNSUPPORTED = {("PARQUET", "LZ4")}


def variants():
    return [(f, c) for f in FORMATS for c in CODECS if (f, c) not in UNSUPPORTED]


def schema_name(sf, fmt, codec):
    return f"{sf}_{fmt}_{codec}".lower()


def connect(catalog="iceberg", codec=None):
    props = {"iceberg.compression_codec": codec} if codec else {}
    return trino.dbapi.connect(
        host=TRINO_HOST, port=TRINO_PORT, user="lab",
        catalog=catalog, schema="default", session_properties=props,
    )


def run(conn, sql):
    cur = conn.cursor()
    t0 = time.perf_counter()
    cur.execute(sql)
    rows = cur.fetchall()
    wall = time.perf_counter() - t0
    s = cur.stats
    return rows, {
        "query_id": cur.query_id,
        "wall_s": round(wall, 3),
        "elapsed_ms": s.get("elapsedTimeMillis"),
        "cpu_ms": s.get("cpuTimeMillis"),
        "planning_ms": s.get("planningTimeMillis"),
        "analysis_ms": s.get("analysisTimeMillis"),
        "physical_input_bytes": s.get("physicalInputBytes"),
        "processed_rows": s.get("processedRows"),
        "peak_memory_bytes": s.get("peakMemoryBytes"),
    }


def render(text, **params):
    for k, v in params.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def statements(path, **params):
    text = render(Path(path).read_text(), **params)
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def named_queries(**params):
    text = render((SQL_DIR / "04_bench_queries.sql").read_text(), **params)
    out = {}
    for block in text.split("-- name: ")[1:]:
        name, sql = block.split("\n", 1)
        sql = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
        out[name.strip()] = sql.strip().rstrip(";")
    return out


def s3():
    return boto3.client(
        "s3", endpoint_url=S3_ENDPOINT, region_name="us-east-1",
        aws_access_key_id="lab", aws_secret_access_key="labsecret",
    )


def prefix_usage(prefix):
    total, count = 0, 0
    for page in s3().get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            total += obj["Size"]
            count += 1
    return total, count


def table_location(conn, fq_table):
    ddl = run(conn, f"SHOW CREATE TABLE {fq_table}")[0][0][0]
    loc = re.search(r"location = '([^']+)'", ddl).group(1)
    return loc.replace(f"s3://{BUCKET}/", "").rstrip("/")


def table_storage(conn, fq_table):
    # данные и метаданные iceberg лежат в соседних префиксах таблицы
    loc = table_location(conn, fq_table)
    data_b, data_n = prefix_usage(loc + "/data/")
    meta_b, meta_n = prefix_usage(loc + "/metadata/")
    rows = run(conn, f"SELECT count(*) FROM {fq_table}")[0][0][0]
    return {"rows": rows, "data_bytes": data_b, "data_files": data_n,
            "metadata_bytes": meta_b, "metadata_files": meta_n}


def median(xs):
    return statistics.median(xs) if xs else None


def docker_bin():
    found = shutil.which("docker")
    return found or "/Applications/Docker.app/Contents/Resources/bin/docker"


def compose(*args):
    subprocess.run([docker_bin(), "compose", *args], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def restart_trino(clear_fs_cache=True):
    # холодный старт: пустые jvm кэши метаданных и пустой файловый кэш
    if clear_fs_cache:
        compose("exec", "-T", "trino", "rm", "-rf", "/tmp/trino-fs-cache")
    compose("restart", "trino")
    for _ in range(90):
        try:
            conn = connect()
            run(conn, "SELECT count(*) FROM tpch.tiny.nation")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("trino не поднялся после рестарта")


def fs_cache_bytes():
    out = subprocess.run(
        [docker_bin(), "compose", "exec", "-T", "trino", "du", "-sb", "/tmp/trino-fs-cache"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout.split()
    return int(out[0]) if out else 0
