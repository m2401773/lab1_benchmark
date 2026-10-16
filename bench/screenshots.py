"""скриншоты веб-интерфейсов стенда для отчета

используется установленный google chrome, отдельный браузер не скачивается
"""
import sys

from playwright.sync_api import sync_playwright

from common import ROOT, connect, named_queries, run, table_location

IMG = ROOT / "images"


def shot(page, url, name, wait="networkidle", delay=2500, full=False, click=None, search=None):
    page.goto(url, wait_until=wait)
    page.wait_for_timeout(delay)
    if click:
        page.get_by_text(click, exact=True).first.click()
        page.wait_for_timeout(1500)
    if search:
        page.locator("input[type=text]").first.click()
        page.keyboard.type(search, delay=40)
        page.wait_for_timeout(1500)
    page.screenshot(path=str(IMG / name), full_page=full)
    print("  ", IMG / name)


def main():
    sf = sys.argv[1] if len(sys.argv) > 1 else "sf10"
    # свежие запросы, чтобы в списке trino были именно они
    schema = f"{sf}_parquet_zstd"
    conn = connect()
    for name, sql in named_queries(schema=schema).items():
        _, st = run(conn, sql)
        if name == "q16_on_bronze":
            qid = st["query_id"]
    silver = table_location(conn, f"{schema}.silver_part_supplier")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        shot(page, "http://localhost:8080/ui/", "ui_trino_overview.png", search=schema, click="Finished")
        shot(page, f"http://localhost:8080/ui/query.html?{qid}", "ui_trino_query.png", full=False)
        shot(page, f"http://localhost:8080/ui/plan.html?{qid}", "ui_trino_plan.png", delay=6000)
        shot(page, "http://localhost:8888/buckets/warehouse/", "ui_seaweed_bucket.png")
        shot(page, f"http://localhost:8888/buckets/warehouse/{sf}_parquet_zstd/", "ui_seaweed_schema.png")
        shot(page, f"http://localhost:8888/buckets/warehouse/{silver}/data/", "ui_seaweed_data.png")
        shot(page, f"http://localhost:8888/buckets/warehouse/{silver}/metadata/", "ui_seaweed_metadata.png")
        browser.close()


if __name__ == "__main__":
    main()
