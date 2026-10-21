from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

QUANT_TWO = Decimal("0.01")


def calculate_rate(part: int, whole: int) -> Decimal:
    if whole <= 0:
        return Decimal("0.00")
    return ((Decimal(part) * 100) / Decimal(whole)).quantize(QUANT_TWO, rounding=ROUND_HALF_UP)


def calculate_median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    s, n = sorted(values), len(values)
    m = s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / Decimal(2)
    return m.quantize(QUANT_TWO, rounding=ROUND_HALF_UP)


def calculate_average(values: list[Decimal]) -> Decimal | None:
    return None if not values else (sum(values) / Decimal(len(values))).quantize(QUANT_TWO, rounding=ROUND_HALF_UP)


def item_resolution_hours(created_at: datetime, closed_at: datetime | None) -> Decimal | None:
    if closed_at is None:
        return None
    sec = max(0.0, (closed_at - created_at).total_seconds())
    return (Decimal(str(sec)) / Decimal(3600)).quantize(QUANT_TWO, rounding=ROUND_HALF_UP)


def item_age_days(created_at: datetime, closed_at: datetime | None, reference_time: datetime) -> Decimal:
    end = closed_at if closed_at is not None else reference_time
    sec = max(0.0, (end - created_at).total_seconds())
    return (Decimal(str(sec)) / Decimal(86400)).quantize(QUANT_TWO, rounding=ROUND_HALF_UP)


def author_key(item: dict[str, Any]) -> str:
    if item.get("author_id") is not None:
        return f"id:{item['author_id']}"
    return f"login:{item['author_login']}" if item.get("author_login") else "unknown"


def build_repository_summary(
    current_repos: list[dict[str, Any]], current_issues: list[dict[str, Any]],
    all_repos: list[dict[str, Any]], all_issues: list[dict[str, Any]],
    batch_id: Any, reference_time: datetime | None = None,
) -> list[dict[str, Any]]:
    repo_versions = Counter(r["github_repository_id"] for r in all_repos)
    issue_versions = Counter(i["github_issue_id"] for i in all_issues)
    issue_repo = {i["github_issue_id"]: i["github_repository_id"] for i in all_issues}
    repo_issue_changes = Counter(issue_repo[iid] for iid, cnt in issue_versions.items() if cnt > 1)

    issues_by_repo: dict[int, list[dict[str, Any]]] = {r["github_repository_id"]: [] for r in current_repos}
    for i in current_issues:
        if i["github_repository_id"] in issues_by_repo:
            issues_by_repo[i["github_repository_id"]].append(i)

    summary_rows = []
    for r in sorted(current_repos, key=lambda x: x["github_repository_id"]):
        rid = r["github_repository_id"]
        items = issues_by_repo[rid]
        issues, prs = [i for i in items if not i["is_pull_request"]], [i for i in items if i["is_pull_request"]]
        open_issues, closed_issues = [i for i in issues if i["state"] == "open"], [i for i in issues if i["state"] == "closed"]
        open_prs, closed_prs = [i for i in prs if i["state"] == "open"], [i for i in prs if i["state"] == "closed"]

        issue_res = [h for i in closed_issues if (h := item_resolution_hours(i["source_created_at"], i.get("source_closed_at"))) is not None]
        pr_res = [h for p in closed_prs if (h := item_resolution_hours(p["source_created_at"], p.get("source_closed_at"))) is not None]
        authors = {author_key(item) for item in items}
        unassigned = sum(1 for i in items if i["state"] == "open" and not i.get("assignees"))
        unlabeled = sum(1 for i in items if i["state"] == "open" and not i.get("labels"))
        c_dates = [i["source_created_at"] for i in items]
        cl_dates = [i["source_closed_at"] for i in items if i.get("source_closed_at")]

        summary_rows.append({
            "github_repository_id": rid, "full_name": r["full_name"],
            "description": r.get("description"), "language": r.get("language"), "archived": r["archived"],
            "source_created_at": r["source_created_at"], "source_updated_at": r.get("source_updated_at"),
            "stars_count": r["stars_count"], "forks_count": r["forks_count"],
            "open_issues_api_count": r["open_issues_count"], "total_items_count": len(items),
            "issues_total_count": len(issues), "prs_total_count": len(prs),
            "open_issues_count": len(open_issues), "closed_issues_count": len(closed_issues),
            "issue_close_rate_pct": calculate_rate(len(closed_issues), len(issues)),
            "open_prs_count": len(open_prs), "closed_prs_count": len(closed_prs),
            "pr_close_rate_pct": calculate_rate(len(closed_prs), len(prs)),
            "avg_issue_resolution_hours": calculate_average(issue_res), "median_issue_resolution_hours": calculate_median(issue_res),
            "avg_pr_resolution_hours": calculate_average(pr_res), "median_pr_resolution_hours": calculate_median(pr_res),
            "unique_authors_count": len(authors), "unassigned_open_items_count": unassigned, "unlabeled_open_items_count": unlabeled,
            "first_item_created_at": min(c_dates) if c_dates else None, "last_item_created_at": max(c_dates) if c_dates else None,
            "last_item_closed_at": max(cl_dates) if cl_dates else None,
            "repository_versions_count": repo_versions.get(rid, 1), "issue_versions_changed_count": repo_issue_changes.get(rid, 0),
            "valid_from": r["valid_from"], "source_batch_id": batch_id,
        })
    return summary_rows


def build_repository_version_history(all_repos: list[dict[str, Any]], batch_id: Any) -> list[dict[str, Any]]:
    by_repo: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in all_repos:
        by_repo[r["github_repository_id"]].append(r)
    history_rows = []
    for rid in sorted(by_repo):
        versions = sorted(by_repo[rid], key=lambda x: (x["valid_from"], x.get("repository_version_id", 0)))
        prev = None
        for idx, v in enumerate(versions, start=1):
            history_rows.append({
                "repository_version_id": v["repository_version_id"], "github_repository_id": rid,
                "full_name": v["full_name"], "version_number": idx,
                "stars_count": v["stars_count"], "stars_delta": 0 if idx == 1 else (v["stars_count"] - prev["stars_count"]),
                "forks_count": v["forks_count"], "forks_delta": 0 if idx == 1 else (v["forks_count"] - prev["forks_count"]),
                "open_issues_count": v["open_issues_count"], "open_issues_delta": 0 if idx == 1 else (v["open_issues_count"] - prev["open_issues_count"]),
                "archived": v["archived"], "valid_from": v["valid_from"], "valid_to": v.get("valid_to"),
                "is_current": v["is_current"], "source_batch_id": v.get("source_batch_id", batch_id),
            })
            prev = v
    return sorted(history_rows, key=lambda x: x["repository_version_id"])


def build_activity_monthly(
    current_issues: list[dict[str, Any]], current_repos: list[dict[str, Any]], batch_id: Any,
) -> list[dict[str, Any]]:
    repo_names = {r["github_repository_id"]: r["full_name"] for r in current_repos}
    grouped = defaultdict(lambda: defaultdict(lambda: {"created_count": 0, "closed_count": 0, "res_hours": []}))
    for item in current_issues:
        rid, item_type = item["github_repository_id"], ("pull_request" if item["is_pull_request"] else "issue")
        c_at, cl_at = item["source_created_at"], item.get("source_closed_at")
        c_m = date(c_at.year, c_at.month, 1)
        grouped[(rid, item_type)][c_m]["created_count"] += 1
        if cl_at is not None:
            cl_m = date(cl_at.year, cl_at.month, 1)
            grouped[(rid, item_type)][cl_m]["closed_count"] += 1
            if (h := item_resolution_hours(c_at, cl_at)) is not None:
                grouped[(rid, item_type)][cl_m]["res_hours"].append(h)

    activity_rows = []
    for (rid, item_type), months in sorted(grouped.items()):
        full_name = repo_names.get(rid, f"repo_{rid}")
        cum_created, cum_closed = 0, 0
        for m in sorted(months.keys()):
            data = months[m]
            created, closed = data["created_count"], data["closed_count"]
            cum_created += created
            cum_closed += closed
            activity_rows.append({
                "github_repository_id": rid, "period_month": m, "item_type": item_type,
                "full_name": full_name, "created_count": created, "closed_count": closed,
                "net_open_delta": created - closed, "cumulative_created_count": cum_created,
                "cumulative_closed_count": cum_closed, "avg_resolution_hours": calculate_average(data["res_hours"]), "source_batch_id": batch_id,
            })
    return sorted(activity_rows, key=lambda x: (x["github_repository_id"], x["period_month"], x["item_type"]))


def build_contributor_activity(
    current_issues: list[dict[str, Any]], current_repos: list[dict[str, Any]], batch_id: Any,
) -> list[dict[str, Any]]:
    repo_names = {r["github_repository_id"]: r["full_name"] for r in current_repos}
    grouped: dict[tuple[int, str], dict[str, Any]] = {}
    for item in current_issues:
        rid, a_key = item["github_repository_id"], author_key(item)
        key = (rid, a_key)
        if key not in grouped:
            grouped[key] = {
                "github_repository_id": rid, "author_key": a_key, "full_name": repo_names.get(rid, f"repo_{rid}"),
                "author_id": item.get("author_id"), "author_login": item.get("author_login") or "ghost",
                "total_items_count": 0, "issues_created_count": 0, "open_issues_count": 0, "closed_issues_count": 0,
                "prs_created_count": 0, "open_prs_count": 0, "closed_prs_count": 0, "res_hours": [],
                "first_created_at": None, "last_created_at": None, "source_batch_id": batch_id,
            }
        rec = grouped[key]
        rec["total_items_count"] += 1
        is_pr, state = item["is_pull_request"], item["state"]
        p = "prs" if is_pr else "issues"
        rec[f"{p}_created_count"] += 1
        if state in ("open", "closed"):
            rec[f"{state}_{p}_count"] += 1
        c_at, cl_at = item["source_created_at"], item.get("source_closed_at")
        rec["first_created_at"] = min(rec["first_created_at"] or c_at, c_at)
        rec["last_created_at"] = max(rec["last_created_at"] or c_at, c_at)
        if (
            cl_at is not None
            and (h := item_resolution_hours(c_at, cl_at)) is not None
        ):
            rec["res_hours"].append(h)

    for rec in grouped.values():
        rec["avg_resolution_hours"] = calculate_average(rec.pop("res_hours"))
    return sorted(grouped.values(), key=lambda x: (x["github_repository_id"], x["author_key"]))


def build_label_analytics(
    current_issues: list[dict[str, Any]], current_repos: list[dict[str, Any]], batch_id: Any,
) -> list[dict[str, Any]]:
    repo_names = {r["github_repository_id"]: r["full_name"] for r in current_repos}
    grouped: dict[tuple[int, int], dict[str, Any]] = {}
    for item in current_issues:
        rid = item["github_repository_id"]
        for lbl in item.get("labels") or []:
            lid = lbl.get("id")
            if not lid:
                continue
            key = (rid, lid)
            if key not in grouped:
                grouped[key] = {
                    "github_repository_id": rid, "label_id": lid, "full_name": repo_names.get(rid, f"repo_{rid}"),
                    "label_name": lbl.get("name"), "total_items_count": 0, "issues_count": 0, "prs_count": 0,
                    "open_items_count": 0, "closed_items_count": 0, "res_hours": [], "source_batch_id": batch_id,
                }
            rec = grouped[key]
            rec["total_items_count"] += 1
            rec["prs_count" if item["is_pull_request"] else "issues_count"] += 1
            if item["state"] in ("open", "closed"):
                rec[f"{item['state']}_items_count"] += 1
            if (
                item["state"] == "closed"
                and (cl_at := item.get("source_closed_at")) is not None
                and (h := item_resolution_hours(item["source_created_at"], cl_at)) is not None
            ):
                rec["res_hours"].append(h)

    for rec in grouped.values():
        rec["close_rate_pct"] = calculate_rate(rec["closed_items_count"], rec["total_items_count"])
        rec["avg_resolution_hours"] = calculate_average(rec.pop("res_hours"))
    return sorted(grouped.values(), key=lambda x: (x["github_repository_id"], x["label_id"]))


def build_issue_lifecycle_current(
    current_issues: list[dict[str, Any]], current_repos: list[dict[str, Any]],
    all_issues: list[dict[str, Any]], batch_id: Any, reference_time: datetime | None = None,
) -> list[dict[str, Any]]:
    ref_time = reference_time or datetime.now(UTC)
    repo_names = {r["github_repository_id"]: r["full_name"] for r in current_repos}
    issue_versions = Counter(i["github_issue_id"] for i in all_issues)
    rows = []
    for item in sorted(current_issues, key=lambda x: x["github_issue_id"]):
        iid, rid = item["github_issue_id"], item["github_repository_id"]
        c_at, cl_at = item["source_created_at"], item.get("source_closed_at")
        labels = sorted(item.get("labels") or [], key=lambda x: (x.get("name") or "", x.get("id", 0)))
        assignees = sorted(item.get("assignees") or [], key=lambda x: (x.get("login") or "", x.get("id", 0)))
        rows.append({
            "github_issue_id": iid, "github_repository_id": rid, "repository_full_name": repo_names.get(rid, f"repo_{rid}"),
            "issue_number": item["issue_number"], "item_type": "pull_request" if item["is_pull_request"] else "issue",
            "is_pull_request": item["is_pull_request"], "title": item["title"], "state": item["state"],
            "author_id": item.get("author_id"), "author_login": item.get("author_login"),
            "source_created_at": c_at, "source_updated_at": item.get("source_updated_at"), "source_closed_at": cl_at,
            "resolution_hours": item_resolution_hours(c_at, cl_at), "age_days": item_age_days(c_at, cl_at, ref_time),
            "labels_count": len(labels), "labels_csv": ", ".join(l["name"] for l in labels if "name" in l),
            "assignees_count": len(assignees), "assignees_csv": ", ".join(a["login"] for a in assignees if "login" in a),
            "scd2_versions_count": issue_versions.get(iid, 1), "valid_from": item["valid_from"], "source_batch_id": batch_id,
        })
    return rows
