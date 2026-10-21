import os
from datetime import UTC, datetime
from html import escape
from typing import Any

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Аналитика репозиториев Kotlin Multiplatform (CDM) — Neo-Brutalism BI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700;800&family=Space+Grotesk:wght@700;900&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #F4F0EA; --ink: #111111; --card: #FFFFFF; --lime: #B8FF01; --yellow: #FFE600; --coral: #FF6B6B; --cyan: #00E5FF; --violet: #C084FC; }
        * { box-sizing: border-box; margin: 0; padding: 0; border-radius: 0 !important; }
        body { background-color: var(--bg); background-image: radial-gradient(var(--ink) 1px, transparent 1px); background-size: 20px 20px; color: var(--ink); font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.4; padding: 24px; }
        .ticker { background: var(--ink); color: var(--yellow); font-family: 'JetBrains Mono', monospace; font-weight: 800; padding: 10px 16px; border: 3px solid var(--ink); box-shadow: 6px 6px 0 var(--ink); margin-bottom: 20px; font-size: 13px; letter-spacing: 0.05em; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
        header { background: var(--card); border: 3px solid var(--ink); box-shadow: 6px 6px 0 var(--ink); padding: 20px 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
        h1 { font-size: 26px; font-weight: 900; text-transform: uppercase; letter-spacing: -0.02em; color: var(--ink); }
        .meta-sub { font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: #444; margin-top: 4px; }
        .stamp { background: var(--yellow); color: var(--ink); border: 2px solid var(--ink); box-shadow: 3px 3px 0 var(--ink); padding: 6px 12px; font-family: 'JetBrains Mono', monospace; font-weight: 900; font-size: 12px; text-transform: uppercase; }
        .grid-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .kpi-card { background: var(--card); border: 3px solid var(--ink); box-shadow: 6px 6px 0 var(--ink); display: flex; flex-direction: column; transition: transform 0.15s ease, box-shadow 0.15s ease; }
        .kpi-card:hover { transform: translate(-2px, -2px); box-shadow: 8px 8px 0 var(--ink); }
        .kpi-strip { padding: 6px 12px; border-bottom: 3px solid var(--ink); font-family: 'JetBrains Mono', monospace; font-weight: 900; font-size: 12px; text-transform: uppercase; display: flex; justify-content: space-between; }
        .kpi-body { padding: 16px; flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .kpi-title { font-size: 13px; font-weight: 800; text-transform: uppercase; color: #333; margin-bottom: 6px; }
        .kpi-value { font-size: 32px; font-weight: 900; color: var(--ink); font-family: 'JetBrains Mono', monospace; line-height: 1.1; margin: 4px 0 8px; }
        .kpi-sub { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: #555; }
        .charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
        @media (max-width: 960px) { .charts-row { grid-template-columns: 1fr; } }
        .card { background: var(--card); border: 3px solid var(--ink); box-shadow: 6px 6px 0 var(--ink); padding: 20px; transition: transform 0.15s ease, box-shadow 0.15s ease; overflow-x: auto; }
        .card:hover { transform: translate(-2px, -2px); box-shadow: 8px 8px 0 var(--ink); }
        .card-header { font-size: 16px; font-weight: 900; text-transform: uppercase; margin-bottom: 16px; color: var(--ink); display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid var(--ink); padding-bottom: 10px; }
        .meta-tag { background: var(--ink); color: var(--yellow); padding: 3px 8px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 800; border: 2px solid var(--ink); box-shadow: 2px 2px 0 var(--ink); }
        table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }
        th { background: var(--ink); color: #fff; font-family: 'JetBrains Mono', monospace; font-weight: 800; text-transform: uppercase; font-size: 11px; padding: 10px 12px; border: 2px solid var(--ink); }
        td { border: 2px solid var(--ink); padding: 10px 12px; background: var(--card); font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--ink); }
        tr:hover td { background: #FFFDE6; }
        .badge { display: inline-block; padding: 3px 8px; border: 2px solid var(--ink); box-shadow: 2px 2px 0 var(--ink); font-size: 11px; font-weight: 900; text-transform: uppercase; font-family: 'JetBrains Mono', monospace; }
        .badge-open { background: var(--yellow); color: var(--ink); } .badge-closed { background: var(--lime); color: var(--ink); }
        .badge-pr { background: var(--violet); color: var(--ink); } .badge-issue { background: var(--cyan); color: var(--ink); }
        .chart-container { width: 100%; min-height: 220px; display: flex; align-items: flex-end; gap: 8px; padding-top: 16px; overflow-x: auto; }
        .bar-col { flex: 1; min-width: 28px; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; }
        .bar-rect { width: 100%; border: 2px solid var(--ink); box-shadow: 3px 3px 0 var(--ink); transition: height 0.3s ease; }
        .bar-label { font-size: 10px; font-family: 'JetBrains Mono', monospace; font-weight: 800; color: var(--ink); margin-top: 8px; text-align: center; }
        .bar-val { font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 900; color: var(--ink); margin-bottom: 4px; }
    </style>
</head>
<body>
    <div class="ticker">
        <span>ППАД ЛАБ 3 // СЛОЙ CDM // KOTLIN MULTIPLATFORM // POSTGRESQL DDS → CDM</span>
        <span>ROLE: PPAD_BI_READER</span>
    </div>
    <header>
        <div>
            <h1>Аналитика репозиториев Kotlin Multiplatform (CDM)</h1>
            <div class="meta-sub">ППАД ЛАБОРАТОРНАЯ 3 • АНАЛИТИЧЕСКИЕ ВИТРИНЫ CDM • НЕОБРУТАЛИЗМ BI DASHBOARD</div>
        </div>
        <div class="stamp">СГЕНЕРИРОВАНО: __RENDER_TIME__</div>
    </header>
    <div class="grid-kpis">
        <div class="kpi-card">
            <div class="kpi-strip" style="background: var(--lime);"><span>[KPI-01] РЕПОЗИТОРИИ</span><span>★</span></div>
            <div class="kpi-body">
                <div class="kpi-title">Всего репозиториев</div><div class="kpi-value">__TOTAL_REPOS__</div><div class="kpi-sub">__TOTAL_VERSIONS__ версий в SCD2</div>
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-strip" style="background: var(--yellow);"><span>[KPI-02] СУЩНОСТИ</span><span>#</span></div>
            <div class="kpi-body">
                <div class="kpi-title">Всего сущностей (Issues + PR)</div><div class="kpi-value">__TOTAL_ITEMS__</div><div class="kpi-sub">__TOTAL_ISSUES__ Issues • __TOTAL_PRS__ PRs</div>
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-strip" style="background: var(--coral);"><span>[KPI-03] CLOSE RATE</span><span>%</span></div>
            <div class="kpi-body">
                <div class="kpi-title">Close Rate Issues / PR</div><div class="kpi-value">__AVG_CLOSE_RATE__%</div><div class="kpi-sub">__CLOSED_ITEMS__ закрыто из __TOTAL_ITEMS__</div>
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-strip" style="background: var(--cyan);"><span>[KPI-04] SLA РЕШЕНИЯ</span><span>⏱</span></div>
            <div class="kpi-body">
                <div class="kpi-title">Медиана решения (SLA)</div><div class="kpi-value">__MEDIAN_RESOLUTION__ ч.</div><div class="kpi-sub">Среднее: __AVG_RESOLUTION__ ч.</div>
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-strip" style="background: var(--violet);"><span>[KPI-05] АВТОРЫ</span><span>👤</span></div>
            <div class="kpi-body">
                <div class="kpi-title">Уникальных авторов</div><div class="kpi-value">__TOTAL_AUTHORS__</div><div class="kpi-sub">Активных контрибьюторов</div>
            </div>
        </div>
    </div>
    <div class="charts-row">
        <div class="card"><div class="card-header"><span>1. Сводка активности репозиториев</span><span class="meta-tag">cdm.repository_summary</span></div>
            <table><thead><tr><th>Репозиторий</th><th>Звезды</th><th>Forks</th><th>Issues / PR</th><th>Close Rate</th><th>Медиана SLA</th></tr></thead><tbody>__REPO_SUMMARY_ROWS__</tbody></table></div>
        <div class="card"><div class="card-header"><span>2. Динамика активности по месяцам</span><span class="meta-tag">cdm.activity_monthly</span></div><div class="chart-container">__MONTHLY_BARS__</div></div>
    </div>
    <div class="charts-row">
        <div class="card"><div class="card-header"><span>3. Топ контрибьюторов</span><span class="meta-tag">cdm.contributor_activity</span></div>
            <table><thead><tr><th>Автор</th><th>Репозиторий</th><th>Всего</th><th>Issues</th><th>PRs</th><th>Ср. SLA</th></tr></thead><tbody>__CONTRIBUTOR_ROWS__</tbody></table></div>
        <div class="card"><div class="card-header"><span>4. Аналитика меток (Labels)</span><span class="meta-tag">cdm.label_analytics</span></div>
            <table><thead><tr><th>Метка</th><th>Репозиторий</th><th>Всего</th><th>Закрыто</th><th>Close Rate</th></tr></thead><tbody>__LABEL_ROWS__</tbody></table></div>
    </div>
    <div class="charts-row">
        <div class="card"><div class="card-header"><span>5. История изменений репозиториев (SCD2 дельты)</span><span class="meta-tag">cdm.repository_version_history</span></div>
            <table><thead><tr><th>Репозиторий</th><th>Версия</th><th>Звезды (Δ)</th><th>Forks (Δ)</th><th>Open Issues (Δ)</th><th>valid_from</th></tr></thead><tbody>__HISTORY_ROWS__</tbody></table></div>
        <div class="card"><div class="card-header"><span>6. Детализация жизненного цикла (Последние 10 сущностей)</span><span class="meta-tag">cdm.issue_lifecycle_current</span></div>
            <table><thead><tr><th>#</th><th>Тип</th><th>Заголовок</th><th>Статус</th><th>Возраст / SLA</th></tr></thead><tbody>__LIFECYCLE_ROWS__</tbody></table></div>
    </div>
</body>
</html>"""


def render_html_report(cursor: Any, output_path: str):
    cursor.execute("SELECT * FROM cdm.repository_summary ORDER BY full_name")
    repos = cursor.fetchall()
    cursor.execute("""
        SELECT period_month, item_type, sum(created_count)::int AS created_count
        FROM cdm.activity_monthly
        GROUP BY period_month, item_type
        ORDER BY period_month DESC, item_type DESC
        LIMIT 16
    """)
    monthly = list(reversed(cursor.fetchall()))
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
        f"<td>{r['issues_total_count']} / {r['prs_total_count']}</td><td><span class=\"badge badge-closed\">{r['issue_close_rate_pct']}%</span></td>"
        f"<td>{r['median_issue_resolution_hours'] or '-'} ч.</td></tr>"
        for r in repos
    ]

    max_c = max([m["created_count"] for m in monthly], default=1) or 1
    monthly_bars = []
    for m in monthly:
        h_pct = max(10, int((m["created_count"] / max_c) * 160))
        col = "var(--cyan)" if m["item_type"] == "issue" else "var(--violet)"
        tag = "ISS" if m["item_type"] == "issue" else "PR"
        monthly_bars.append(
            f'<div class="bar-col"><span class="bar-val">{m["created_count"]}</span>'
            f'<div class="bar-rect" style="height: {h_pct}px; background-color: {col};"></div>'
            f'<div class="bar-label">{m["period_month"].strftime("%b %y")}<br>({tag})</div></div>'
        )

    contrib_rows = [
        f"<tr><td><strong>{escape(str(c['author_login']))}</strong></td><td>{escape(str(c['full_name']))}</td><td><span class=\"badge\" style=\"background: var(--lime);\">{c['total_items_count']}</span></td>"
        f"<td>{c['issues_created_count']}</td><td>{c['prs_created_count']}</td><td>{c['avg_resolution_hours'] or '-'} ч.</td></tr>"
        for c in contributors
    ]

    label_rows = [
        f"<tr><td><span class=\"badge badge-issue\">{escape(str(l['label_name']))}</span></td><td>{escape(str(l['full_name']))}</td>"
        f"<td><strong>{l['total_items_count']}</strong></td><td>{l['closed_items_count']}</td><td><span class=\"badge badge-closed\">{l['close_rate_pct']}%</span></td></tr>"
        for l in labels
    ]

    history_rows = []
    for h in history:
        s_d = f"+{h['stars_delta']}" if h['stars_delta'] > 0 else str(h['stars_delta'])
        f_d = f"+{h['forks_delta']}" if h['forks_delta'] > 0 else str(h['forks_delta'])
        i_d = f"+{h['open_issues_delta']}" if h['open_issues_delta'] > 0 else str(h['open_issues_delta'])
        cur = ' <span class="badge" style="background: var(--lime);">текущая</span>' if h["is_current"] else ""
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
