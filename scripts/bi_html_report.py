import os
from datetime import UTC, datetime
from html import escape
from typing import Any

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Аналитика репозиториев Kotlin Multiplatform (CDM) — BI Preview</title>
    <style>
        :root { --bg-color: #0f172a; --card-bg: #1e293b; --border-color: #334155; --text-primary: #f8fafc; --text-secondary: #94a3b8; --accent-blue: #38bdf8; --accent-purple: #c084fc; --accent-green: #4ade80; --accent-amber: #fbbf24; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg-color); color: var(--text-primary); line-height: 1.5; padding: 24px; }
        header { margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
        h1 { font-size: 24px; font-weight: 700; color: #fff; } .meta { font-size: 13px; color: var(--text-secondary); }
        .grid-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .kpi-title { font-size: 13px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
        .kpi-value { font-size: 28px; font-weight: 700; color: #fff; } .kpi-sub { font-size: 12px; color: var(--accent-blue); margin-top: 4px; }
        .charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
        @media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }
        .card-header { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #fff; display: flex; justify-content: space-between; align-items: center; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
        th { background: #0b1120; color: var(--text-secondary); font-weight: 600; padding: 10px 12px; border-bottom: 1px solid var(--border-color); }
        td { padding: 10px 12px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
        tr:hover td { background: rgba(255,255,255,0.03); }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; }
        .badge-open { background: rgba(251,191,36,0.15); color: var(--accent-amber); } .badge-closed { background: rgba(74,222,128,0.15); color: var(--accent-green); }
        .badge-pr { background: rgba(192,132,252,0.15); color: var(--accent-purple); } .badge-issue { background: rgba(56,189,248,0.15); color: var(--accent-blue); }
        .chart-container { width: 100%; min-height: 220px; display: flex; align-items: flex-end; gap: 12px; padding-top: 16px; }
        .bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; }
        .bar-rect { width: 100%; border-radius: 4px 4px 0 0; transition: height 0.3s ease; }
        .bar-label { font-size: 11px; color: var(--text-secondary); margin-top: 6px; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 100%; }
        .bar-val { font-size: 11px; font-weight: 600; color: #fff; margin-bottom: 4px; }
    </style>
</head>
<body>
    <header>
        <div><h1>Аналитика репозиториев Kotlin Multiplatform (CDM)</h1><div class="meta">ППАД Лабораторная 3 • Витрина данных CDM • Источник: PostgreSQL dds → cdm</div></div>
        <div class="meta">Сгенерировано: <strong>__RENDER_TIME__</strong></div>
    </header>
    <div class="grid-kpis">
        <div class="card"><div class="kpi-title">Всего репозиториев</div><div class="kpi-value">__TOTAL_REPOS__</div><div class="kpi-sub">__TOTAL_VERSIONS__ версий в SCD2</div></div>
        <div class="card"><div class="kpi-title">Всего сущностей (Issues + PR)</div><div class="kpi-value">__TOTAL_ITEMS__</div><div class="kpi-sub">__TOTAL_ISSUES__ Issues • __TOTAL_PRS__ PRs</div></div>
        <div class="card"><div class="kpi-title">Close Rate Issues / PR</div><div class="kpi-value">__AVG_CLOSE_RATE__%</div><div class="kpi-sub">__CLOSED_ITEMS__ закрыто из __TOTAL_ITEMS__</div></div>
        <div class="card"><div class="kpi-title">Медиана решения (SLA)</div><div class="kpi-value">__MEDIAN_RESOLUTION__ ч.</div><div class="kpi-sub">Среднее: __AVG_RESOLUTION__ ч.</div></div>
        <div class="card"><div class="kpi-title">Уникальных авторов</div><div class="kpi-value">__TOTAL_AUTHORS__</div><div class="kpi-sub">Активных контрибьюторов</div></div>
    </div>
    <div class="charts-row">
        <div class="card"><div class="card-header"><span>1. Сводка активности репозиториев</span><span class="meta">cdm.repository_summary</span></div>
            <table><thead><tr><th>Репозиторий</th><th>Звезды</th><th>Forks</th><th>Issues / PR</th><th>Close Rate</th><th>Медиана SLA</th></tr></thead><tbody>__REPO_SUMMARY_ROWS__</tbody></table></div>
        <div class="card"><div class="card-header"><span>2. Соотношение категорий и динамика по месяцам</span><span class="meta">cdm.activity_monthly</span></div><div class="chart-container">__MONTHLY_BARS__</div></div>
    </div>
    <div class="charts-row">
        <div class="card"><div class="card-header"><span>3. Топ контрибьюторов</span><span class="meta">cdm.contributor_activity</span></div>
            <table><thead><tr><th>Автор</th><th>Репозиторий</th><th>Всего</th><th>Issues</th><th>PRs</th><th>Ср. SLA</th></tr></thead><tbody>__CONTRIBUTOR_ROWS__</tbody></table></div>
        <div class="card"><div class="card-header"><span>4. Аналитика меток (Labels)</span><span class="meta">cdm.label_analytics</span></div>
            <table><thead><tr><th>Метка</th><th>Репозиторий</th><th>Всего</th><th>Закрыто</th><th>Close Rate</th></tr></thead><tbody>__LABEL_ROWS__</tbody></table></div>
    </div>
    <div class="charts-row">
        <div class="card"><div class="card-header"><span>5. История изменений репозиториев (SCD2 дельты)</span><span class="meta">cdm.repository_version_history</span></div>
            <table><thead><tr><th>Репозиторий</th><th>Версия</th><th>Звезды (Δ)</th><th>Forks (Δ)</th><th>Open Issues (Δ)</th><th>valid_from</th></tr></thead><tbody>__HISTORY_ROWS__</tbody></table></div>
        <div class="card"><div class="card-header"><span>6. Детализация жизненного цикла (Последние 10 сущностей)</span><span class="meta">cdm.issue_lifecycle_current</span></div>
            <table><thead><tr><th>#</th><th>Тип</th><th>Заголовок</th><th>Статус</th><th>Возраст / SLA</th></tr></thead><tbody>__LIFECYCLE_ROWS__</tbody></table></div>
    </div>
</body>
</html>"""


def render_html_report(cursor: Any, output_path: str):
    cursor.execute("SELECT * FROM cdm.repository_summary ORDER BY full_name")
    repos = cursor.fetchall()
    cursor.execute("SELECT * FROM cdm.activity_monthly ORDER BY period_month, item_type")
    monthly = cursor.fetchall()
    cursor.execute("SELECT * FROM cdm.contributor_activity ORDER BY total_items_count DESC LIMIT 10")
    contributors = cursor.fetchall()
    cursor.execute("SELECT * FROM cdm.label_analytics ORDER BY total_items_count DESC LIMIT 10")
    labels = cursor.fetchall()
    cursor.execute("SELECT * FROM cdm.repository_version_history ORDER BY github_repository_id, version_number")
    history = cursor.fetchall()
    cursor.execute("SELECT * FROM cdm.issue_lifecycle_current ORDER BY source_created_at DESC LIMIT 10")
    lifecycle = cursor.fetchall()

    total_repos = len(repos)
    total_versions = len(history)
    total_items = sum(r["total_items_count"] for r in repos)
    total_issues = sum(r["issues_total_count"] for r in repos)
    total_prs = sum(r["prs_total_count"] for r in repos)
    closed_items = sum(r["closed_issues_count"] + r["closed_prs_count"] for r in repos)
    avg_close_rate = round(closed_items * 100 / total_items, 2) if total_items else 0.0

    medians = [r["median_issue_resolution_hours"] for r in repos if r["median_issue_resolution_hours"] is not None]
    median_res = round(float(sum(medians) / len(medians)), 2) if medians else 0.0

    avgs = [r["avg_issue_resolution_hours"] for r in repos if r["avg_issue_resolution_hours"] is not None]
    avg_res = round(float(sum(avgs) / len(avgs)), 2) if avgs else 0.0

    total_authors = sum(r["unique_authors_count"] for r in repos)

    repo_rows = [
        f"<tr><td><strong>{escape(str(r['full_name']))}</strong></td><td>★ {r['stars_count']}</td><td>⑂ {r['forks_count']}</td>"
        f"<td>{r['issues_total_count']} / {r['prs_total_count']}</td><td>{r['issue_close_rate_pct']}%</td>"
        f"<td>{r['median_issue_resolution_hours'] or '-'} ч.</td></tr>"
        for r in repos
    ]

    max_c = max([m["created_count"] for m in monthly], default=1) or 1
    monthly_bars = []
    for m in monthly:
        h_pct = max(10, int((m["created_count"] / max_c) * 160))
        col = "var(--accent-blue)" if m["item_type"] == "issue" else "var(--accent-purple)"
        tag = "ISS" if m["item_type"] == "issue" else "PR"
        monthly_bars.append(
            f'<div class="bar-col"><span class="bar-val">{m["created_count"]}</span>'
            f'<div class="bar-rect" style="height: {h_pct}px; background-color: {col};"></div>'
            f'<div class="bar-label">{m["period_month"].strftime("%b %y")} ({tag})</div></div>'
        )

    contrib_rows = [
        f"<tr><td><strong>{escape(str(c['author_login']))}</strong></td><td>{escape(str(c['full_name']))}</td><td><strong>{c['total_items_count']}</strong></td>"
        f"<td>{c['issues_created_count']}</td><td>{c['prs_created_count']}</td><td>{c['avg_resolution_hours'] or '-'} ч.</td></tr>"
        for c in contributors
    ]

    label_rows = [
        f"<tr><td><span class=\"badge badge-issue\">{escape(str(l['label_name']))}</span></td><td>{escape(str(l['full_name']))}</td>"
        f"<td><strong>{l['total_items_count']}</strong></td><td>{l['closed_items_count']}</td><td>{l['close_rate_pct']}%</td></tr>"
        for l in labels
    ]

    history_rows = []
    for h in history:
        s_d = f"+{h['stars_delta']}" if h['stars_delta'] > 0 else str(h['stars_delta'])
        f_d = f"+{h['forks_delta']}" if h['forks_delta'] > 0 else str(h['forks_delta'])
        i_d = f"+{h['open_issues_delta']}" if h['open_issues_delta'] > 0 else str(h['open_issues_delta'])
        cur = " (текущая)" if h["is_current"] else ""
        history_rows.append(
            f"<tr><td>{escape(str(h['full_name']))}</td><td>v{h['version_number']}{cur}</td><td>{h['stars_count']} ({s_d})</td>"
            f"<td>{h['forks_count']} ({f_d})</td><td>{h['open_issues_count']} ({i_d})</td>"
            f"<td>{h['valid_from'].strftime('%Y-%m-%d %H:%M')}</td></tr>"
        )

    lifecycle_rows = []
    for item in lifecycle:
        b_type = '<span class="badge badge-pr">PR</span>' if item["is_pull_request"] else '<span class="badge badge-issue">Issue</span>'
        b_state = '<span class="badge badge-closed">closed</span>' if item["state"] == "closed" else '<span class="badge badge-open">open</span>'
        t_info = f"{item['resolution_hours']} ч." if item["resolution_hours"] is not None else f"{item['age_days']} дн. (открыт)"
        lifecycle_rows.append(
            f"<tr><td>#{item['issue_number']}</td><td>{b_type}</td><td>{escape(str(item['title'][:40]))}</td><td>{b_state}</td><td>{t_info}</td></tr>"
        )

    replacements = {
        "__RENDER_TIME__": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "__TOTAL_REPOS__": str(total_repos), "__TOTAL_VERSIONS__": str(total_versions),
        "__TOTAL_ITEMS__": str(total_items), "__TOTAL_ISSUES__": str(total_issues),
        "__TOTAL_PRS__": str(total_prs), "__CLOSED_ITEMS__": str(closed_items),
        "__AVG_CLOSE_RATE__": str(avg_close_rate), "__MEDIAN_RESOLUTION__": str(median_res),
        "__AVG_RESOLUTION__": str(avg_res), "__TOTAL_AUTHORS__": str(total_authors),
        "__REPO_SUMMARY_ROWS__": "\n".join(repo_rows), "__MONTHLY_BARS__": "\n".join(monthly_bars),
        "__CONTRIBUTOR_ROWS__": "\n".join(contrib_rows), "__LABEL_ROWS__": "\n".join(label_rows),
        "__HISTORY_ROWS__": "\n".join(history_rows), "__LIFECYCLE_ROWS__": "\n".join(lifecycle_rows),
    }

    html = HTML_TEMPLATE
    for k, v in replacements.items():
        html = html.replace(k, v)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"BI dashboard HTML preview generated at: {output_path}")
