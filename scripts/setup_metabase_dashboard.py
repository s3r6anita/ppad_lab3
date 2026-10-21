import argparse
import getpass
import json
import os
import urllib.error
import urllib.request
from typing import Any

import psycopg
from bi_html_report import render_html_report
from psycopg.rows import dict_row


def load_metabase_queries(sql_path: str | None = None) -> list[str]:
    if sql_path is None:
        sql_path = os.path.join(os.path.dirname(__file__), "..", "sql", "18_metabase_bi_queries.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        text = f.read()
    queries, current = [], []
    for line in text.splitlines():
        if line.strip().startswith("--") or (not line.strip() and not current):
            continue
        current.append(line)
        if line.strip().endswith(";"):
            q = "\n".join(current).strip()
            if q.upper().startswith("SELECT"):
                queries.append(q)
            current = []
    return queries


SQL_QUERIES = load_metabase_queries()

METABASE_CARD_METAS = [
    ("01. Ключевые показатели экосистемы (KPI Summary)", "Сводные агрегаты по репозиториям, закрытым задачам, SLA и авторам", "table", 24, 3),
    ("02. Сводка по репозиториям (Overview Table)", "Звезды, форки, открытые/закрытые задачи, SLA и версии SCD2", "table", 12, 7),
    ("03. Помесячная динамика активности (Monthly Activity)", "Динамика создания и закрытия задач и PR по календарным месяцам", "bar", 12, 7),
    ("04. Соотношение Issues и Pull Requests", "Сравнение общего числа и открытых/закрытых issues и PR по проектам", "table", 12, 6),
    ("05. Распределение SLA и возраста сущностей (Percentiles)", "Медиана (p50), 90-й перцентиль (p90) SLA решения и средний возраст открытых задач", "table", 12, 6),
    ("06. Топ контрибьюторов (Top Contributors)", "Рейтинг авторов по числу созданных issues, PR и среднему времени решения", "table", 12, 7),
    ("07. Аналитика меток (Label Analytics)", "Частота использования тегов и процент закрытия связанных задач", "table", 12, 7),
    ("08. История версий репозиториев (SCD2 Version History)", "Хронология срезов SCD2, изменения звезд, форков и открытых issues", "table", 24, 6),
]

METABASE_CARDS: list[dict[str, Any]] = [
    {
        "name": m[0], "description": m[1], "display": m[2], "size_x": m[3], "size_y": m[4],
        "query": SQL_QUERIES[idx] if idx < len(SQL_QUERIES) else "",
    }
    for idx, m in enumerate(METABASE_CARD_METAS)
]


def setup_metabase_api(metabase_url: str, user: str, password: str, db_config: dict[str, Any]) -> dict[str, Any]:
    print(f"Connecting to Metabase API at {metabase_url}...")
    req = urllib.request.Request(
        f"{metabase_url.rstrip('/')}/api/session",
        data=json.dumps({"username": user, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            session_id = json.load(response)["id"]
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"Failed to authenticate with Metabase API: {e}")
        return {"error": str(e)}

    headers = {"Content-Type": "application/json", "X-Metabase-Session": session_id}

    db_id = None
    req_dbs = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/database", headers=headers)
    with urllib.request.urlopen(req_dbs) as resp:
        for d in json.load(resp):
            if d.get("name") == "ppad_dwh":
                db_id = d.get("id")
                break

    if db_id is None:
        db_payload = json.dumps({
            "name": "ppad_dwh", "engine": "postgres",
            "details": {
                "host": db_config["host"], "port": db_config["port"],
                "dbname": db_config["database"], "user": db_config["user"],
                "password": db_config["password"], "ssl": False,
            },
        }).encode("utf-8")
        req_add_db = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/database", data=db_payload, headers=headers)
        with urllib.request.urlopen(req_add_db) as resp:
            db_id = json.load(resp)["id"]

    dash_id = None
    req_get_dash = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/dashboard", headers=headers)
    try:
        with urllib.request.urlopen(req_get_dash) as resp:
            for d in json.load(resp):
                if d.get("name") == "Аналитика репозиториев Kotlin Multiplatform (CDM)":
                    dash_id = d.get("id")
                    break
    except (urllib.error.URLError, json.JSONDecodeError):
        pass

    if dash_id is None:
        dash_payload = json.dumps({
            "name": "Аналитика репозиториев Kotlin Multiplatform (CDM)",
            "description": "Витрины данных CDM: активность, динамика, SLA, метки и SCD2 история",
        }).encode("utf-8")
        req_dash = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/dashboard", data=dash_payload, headers=headers)
        with urllib.request.urlopen(req_dash) as resp:
            dash_id = json.load(resp)["id"]

    existing_cards, attached_card_ids = {}, set()
    req_cards = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/card", headers=headers)
    try:
        with urllib.request.urlopen(req_cards) as resp:
            for c in json.load(resp):
                existing_cards[c.get("name")] = c.get("id")
    except (urllib.error.URLError, json.JSONDecodeError):
        pass

    req_dash_details = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/dashboard/{dash_id}", headers=headers)
    try:
        with urllib.request.urlopen(req_dash_details) as resp:
            dash_info = json.load(resp)
            for item in dash_info.get("ordered_cards", []) or dash_info.get("dashcards", []):
                if cid := (item.get("card_id") or (item.get("card") or {}).get("id")):
                    attached_card_ids.add(cid)
    except (urllib.error.URLError, json.JSONDecodeError):
        pass

    card_results, col, row = [], 0, 0
    for card_def in METABASE_CARDS:
        card_name = card_def["name"]
        card_id = existing_cards.get(card_name)
        if card_id is None:
            card_payload = json.dumps({
                "name": card_name, "description": card_def["description"],
                "dataset_query": {"type": "native", "native": {"query": card_def["query"]}, "database": db_id},
                "display": card_def.get("display", "table"), "visualization_settings": {},
            }).encode("utf-8")
            req_create = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/card", data=card_payload, headers=headers)
            try:
                with urllib.request.urlopen(req_create) as resp:
                    card_id = json.load(resp)["id"]
            except (urllib.error.URLError, json.JSONDecodeError):
                continue

        sx, sy = card_def.get("size_x", 12), card_def.get("size_y", 6)
        if col + sx > 24: col, row = 0, row + 6

        if card_id not in attached_card_ids:
            attach_payload = json.dumps({"cardId": card_id, "row": row, "col": col, "size_x": sx, "size_y": sy}).encode("utf-8")
            req_attach = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/dashboard/{dash_id}/cards", data=attach_payload, headers=headers)
            try:
                with urllib.request.urlopen(req_attach): pass
            except urllib.error.URLError:
                try:
                    fallback = urllib.request.Request(f"{metabase_url.rstrip('/')}/api/dashboard/{dash_id}/cards", data=json.dumps({"cardId": card_id}).encode("utf-8"), headers=headers)
                    with urllib.request.urlopen(fallback): pass
                except urllib.error.URLError: pass

        card_results.append({"name": card_name, "id": card_id})
        col += sx
        if col >= 24: col, row = 0, row + sy

    print(f"Metabase setup complete: database_id={db_id}, dashboard_id={dash_id}, cards={len(card_results)}")
    return {"database_id": db_id, "dashboard_id": dash_id, "cards_count": len(card_results), "cards": card_results}


def main():
    parser = argparse.ArgumentParser(description="Setup Metabase analytical cards or render standalone HTML BI preview.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15432)
    parser.add_argument("--database", default="ppad_dwh")
    parser.add_argument("--user", default="ppad_bi_reader")
    parser.add_argument("--render-html", default=None)
    parser.add_argument("--metabase-url", default=None)
    parser.add_argument("--metabase-user", default="admin@example.local")
    parser.add_argument("--metabase-password", default=None)
    args = parser.parse_args()

    password = os.environ["PGPASSWORD"] if "PGPASSWORD" in os.environ else os.environ.get("BI_READER_PASSWORD")
    if password is None and not args.metabase_url:
        password = getpass.getpass("PostgreSQL BI reader password: ")

    if args.render_html:
        with psycopg.connect(
            host=args.host, port=args.port, dbname=args.database, user=args.user,
            password=password, connect_timeout=10, application_name="ppad_bi_html_render",
            options="-c timezone=UTC", row_factory=dict_row,
        ) as connection, connection.cursor() as cursor:
            render_html_report(cursor, args.render_html)

    if args.metabase_url:
        setup_metabase_api(
            args.metabase_url, args.metabase_user, args.metabase_password or "admin_password",
            {"host": args.host, "port": args.port, "database": args.database, "user": args.user, "password": password or ""},
        )

    if not args.render_html and not args.metabase_url:
        print("Specify --render-html <path> or --metabase-url <url>")


if __name__ == "__main__":
    main()
