import copy
import unittest
from datetime import UTC, date, datetime
from decimal import Decimal

from scripts.cdm_transform import (
    build_activity_monthly,
    build_contributor_activity,
    build_issue_lifecycle_current,
    build_label_analytics,
    build_repository_summary,
    build_repository_version_history,
    calculate_average,
    calculate_median,
    calculate_rate,
    item_age_days,
    item_resolution_hours,
)


class TestCdmTransform(unittest.TestCase):
    def setUp(self):
        self.batch_id = "00000000-0000-0000-0000-000000000001"
        self.now = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)

        utc = UTC
        self.repo_1_v1 = {
            "repository_version_id": 1, "github_repository_id": 100, "full_name": "example/project-one",
            "description": "First project", "language": "Kotlin", "stars_count": 100, "forks_count": 20,
            "open_issues_count": 5, "archived": False,
            "source_created_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=utc),
            "source_updated_at": datetime(2026, 2, 1, 0, 0, 0, tzinfo=utc),
            "valid_from": datetime(2026, 2, 1, 0, 0, 0, tzinfo=utc),
            "valid_to": datetime(2026, 3, 1, 0, 0, 0, tzinfo=utc),
            "is_current": False, "source_batch_id": self.batch_id,
        }
        self.repo_1_v2 = {
            "repository_version_id": 2, "github_repository_id": 100, "full_name": "example/project-one",
            "description": "First project updated", "language": "Kotlin", "stars_count": 150, "forks_count": 25,
            "open_issues_count": 6, "archived": False,
            "source_created_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=utc),
            "source_updated_at": datetime(2026, 3, 1, 0, 0, 0, tzinfo=utc),
            "valid_from": datetime(2026, 3, 1, 0, 0, 0, tzinfo=utc),
            "valid_to": None, "is_current": True, "source_batch_id": self.batch_id,
        }
        self.issue_1 = {
            "issue_version_id": 10, "github_issue_id": 1001, "github_repository_id": 100,
            "issue_number": 1, "title": "Bug in parser", "state": "closed", "is_pull_request": False,
            "author_id": 201, "author_login": "alice",
            "source_created_at": datetime(2026, 2, 10, 10, 0, 0, tzinfo=utc),
            "source_updated_at": datetime(2026, 2, 12, 10, 0, 0, tzinfo=utc),
            "source_closed_at": datetime(2026, 2, 12, 10, 0, 0, tzinfo=utc),
            "labels": [{"id": 1, "name": "bug"}, {"id": 2, "name": "kmp"}],
            "assignees": [{"id": 301, "login": "dev1"}],
            "valid_from": datetime(2026, 2, 12, 10, 0, 0, tzinfo=utc),
            "valid_to": None, "is_current": True, "source_batch_id": self.batch_id,
        }
        self.issue_2 = {
            "issue_version_id": 11, "github_issue_id": 1002, "github_repository_id": 100,
            "issue_number": 2, "title": "Feature request", "state": "open", "is_pull_request": False,
            "author_id": 202, "author_login": "bob",
            "source_created_at": datetime(2026, 2, 15, 12, 0, 0, tzinfo=utc),
            "source_updated_at": datetime(2026, 2, 15, 12, 0, 0, tzinfo=utc),
            "source_closed_at": None, "labels": [{"id": 3, "name": "enhancement"}],
            "assignees": [], "valid_from": datetime(2026, 2, 15, 12, 0, 0, tzinfo=utc),
            "valid_to": None, "is_current": True, "source_batch_id": self.batch_id,
        }
        self.pr_1 = {
            "issue_version_id": 12, "github_issue_id": 1003, "github_repository_id": 100,
            "issue_number": 3, "title": "Fix parser", "state": "closed", "is_pull_request": True,
            "author_id": 201, "author_login": "alice",
            "source_created_at": datetime(2026, 3, 1, 8, 0, 0, tzinfo=utc),
            "source_updated_at": datetime(2026, 3, 1, 20, 0, 0, tzinfo=utc),
            "source_closed_at": datetime(2026, 3, 1, 20, 0, 0, tzinfo=utc),
            "labels": [{"id": 1, "name": "bug"}], "assignees": [{"id": 301, "login": "dev1"}],
            "valid_from": datetime(2026, 3, 1, 20, 0, 0, tzinfo=utc),
            "valid_to": None, "is_current": True, "source_batch_id": self.batch_id,
        }

    def test_calculate_rate_and_zero_division(self):
        self.assertEqual(calculate_rate(5, 10), Decimal("50.00"))
        self.assertEqual(calculate_rate(1, 3), Decimal("33.33"))
        self.assertEqual(calculate_rate(0, 0), Decimal("0.00"))
        self.assertEqual(calculate_rate(10, 0), Decimal("0.00"))

    def test_calculate_median_odd_and_even(self):
        self.assertIsNone(calculate_median([]))
        self.assertEqual(
            calculate_median([Decimal("10.00")]), Decimal("10.00")
        )
        self.assertEqual(
            calculate_median([Decimal("30.00"), Decimal("10.00"), Decimal("20.00")]),
            Decimal("20.00"),
        )
        self.assertEqual(
            calculate_median(
                [Decimal("10.00"), Decimal("20.00"), Decimal("30.00"), Decimal("40.00")]
            ),
            Decimal("25.00"),
        )

    def test_calculate_average(self):
        self.assertIsNone(calculate_average([]))
        self.assertEqual(
            calculate_average([Decimal("10.00"), Decimal("20.00")]),
            Decimal("15.00"),
        )
        self.assertEqual(
            calculate_average([Decimal("10.00"), Decimal("11.00"), Decimal("12.00")]),
            Decimal("11.00"),
        )

    def test_item_resolution_and_age(self):
        c_at = datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC)
        cl_at = datetime(2026, 2, 2, 12, 0, 0, tzinfo=UTC)  # 36 hours
        res_h = item_resolution_hours(c_at, cl_at)
        self.assertEqual(res_h, Decimal("36.00"))

        self.assertIsNone(item_resolution_hours(c_at, None))

        age_closed = item_age_days(c_at, cl_at, self.now)
        self.assertEqual(age_closed, Decimal("1.50"))

        age_open = item_age_days(c_at, None, self.now)
        # from 2026-02-01 to 2026-10-20 is 261 days + 12 hours = 261.50 days
        self.assertGreater(age_open, Decimal("260.00"))

    def test_repository_summary_kpis(self):
        current_repos = [self.repo_1_v2]
        all_repos = [self.repo_1_v1, self.repo_1_v2]
        current_issues = [self.issue_1, self.issue_2, self.pr_1]
        all_issues = [self.issue_1, self.issue_2, self.pr_1]

        summaries = build_repository_summary(
            current_repos,
            current_issues,
            all_repos,
            all_issues,
            self.batch_id,
            self.now,
        )
        self.assertEqual(len(summaries), 1)
        s = summaries[0]
        expected = {
            "github_repository_id": 100, "total_items_count": 3, "issues_total_count": 2, "prs_total_count": 1,
            "open_issues_count": 1, "closed_issues_count": 1, "issue_close_rate_pct": Decimal("50.00"),
            "open_prs_count": 0, "closed_prs_count": 1, "pr_close_rate_pct": Decimal("100.00"),
            "avg_issue_resolution_hours": Decimal("48.00"), "avg_pr_resolution_hours": Decimal("12.00"),
            "unique_authors_count": 2, "unassigned_open_items_count": 1, "unlabeled_open_items_count": 0,
            "repository_versions_count": 2, "issue_versions_changed_count": 0,
        }
        for k, v in expected.items():
            self.assertEqual(s[k], v)

    def test_repository_version_history_deltas(self):
        all_repos = [self.repo_1_v1, self.repo_1_v2]
        history = build_repository_version_history(all_repos, self.batch_id)

        self.assertEqual(len(history), 2)
        v1, v2 = history[0], history[1]
        self.assertEqual((v1["version_number"], v1["stars_delta"], v1["forks_delta"], v1["open_issues_delta"]), (1, 0, 0, 0))
        self.assertEqual((v2["version_number"], v2["stars_delta"], v2["forks_delta"], v2["open_issues_delta"]), (2, 50, 5, 1))

    def test_activity_monthly_aggregation_and_cumulative(self):
        current_issues = [self.issue_1, self.issue_2, self.pr_1]
        current_repos = [self.repo_1_v2]

        monthly = build_activity_monthly(
            current_issues, current_repos, self.batch_id
        )
        self.assertGreaterEqual(len(monthly), 2)

        # Issues: 2 created in Feb, 1 closed in Feb
        feb = next(m for m in monthly if m["period_month"] == date(2026, 2, 1) and m["item_type"] == "issue")
        self.assertEqual(
            (feb["created_count"], feb["closed_count"], feb["net_open_delta"], feb["cumulative_created_count"]),
            (2, 1, 1, 2),
        )

        # Sum of created_count must equal total current items
        total_created = sum(m["created_count"] for m in monthly)
        self.assertEqual(total_created, len(current_issues))

    def test_contributor_activity_metrics(self):
        current_issues = [self.issue_1, self.issue_2, self.pr_1]
        current_repos = [self.repo_1_v2]

        contributors = build_contributor_activity(
            current_issues, current_repos, self.batch_id
        )
        self.assertEqual(len(contributors), 2)

        alice = next(c for c in contributors if c["author_login"] == "alice")
        self.assertEqual(
            (alice["total_items_count"], alice["issues_created_count"], alice["prs_created_count"], alice["closed_issues_count"], alice["closed_prs_count"]),
            (2, 1, 1, 1, 1),
        )

        total_items = sum(c["total_items_count"] for c in contributors)
        self.assertEqual(total_items, len(current_issues))

    def test_label_analytics_unnesting_and_rates(self):
        current_issues = [self.issue_1, self.issue_2, self.pr_1]
        current_repos = [self.repo_1_v2]

        labels = build_label_analytics(
            current_issues, current_repos, self.batch_id
        )
        # Labels: bug (id=1, count=2), kmp (id=2, count=1), enhancement (id=3, count=1)
        self.assertEqual(len(labels), 3)

        bug = next(l for l in labels if l["label_id"] == 1)
        self.assertEqual(
            (bug["total_items_count"], bug["issues_count"], bug["prs_count"], bug["closed_items_count"], bug["close_rate_pct"]),
            (2, 1, 1, 2, Decimal("100.00")),
        )

    def test_issue_lifecycle_current_enrichment(self):
        current_issues = [self.issue_1, self.issue_2, self.pr_1]
        current_repos = [self.repo_1_v2]
        all_issues = [self.issue_1, self.issue_2, self.pr_1]

        lifecycle = build_issue_lifecycle_current(
            current_issues,
            current_repos,
            all_issues,
            self.batch_id,
            self.now,
        )
        self.assertEqual(len(lifecycle), 3)
        row1 = next(x for x in lifecycle if x["github_issue_id"] == 1001)
        self.assertEqual(
            (row1["labels_csv"], row1["assignees_csv"], row1["state"], row1["resolution_hours"], row1["scd2_versions_count"]),
            ("bug, kmp", "dev1", "closed", Decimal("48.00"), 1),
        )

    def test_null_author_handling(self):
        orphan_issue = copy.deepcopy(self.issue_1)
        orphan_issue["author_id"] = None
        orphan_issue["author_login"] = None

        contributors = build_contributor_activity(
            [orphan_issue], [self.repo_1_v2], self.batch_id
        )
        self.assertEqual(len(contributors), 1)
        self.assertEqual(contributors[0]["author_key"], "unknown")
        self.assertEqual(contributors[0]["author_login"], "ghost")
        self.assertIsNone(contributors[0]["author_id"])

    def test_null_author_key_consistency(self):
        orphan1 = copy.deepcopy(self.issue_1)
        orphan1["author_id"] = None
        orphan1["author_login"] = None

        orphan2 = copy.deepcopy(self.issue_2)
        orphan2["author_id"] = None
        orphan2["author_login"] = None

        issues = [orphan1, orphan2]
        repos = [self.repo_1_v2]

        summary = build_repository_summary(
            repos, issues, repos, issues, self.batch_id
        )
        contributors = build_contributor_activity(issues, repos, self.batch_id)

        self.assertEqual(len(summary), 1)
        self.assertEqual(len(contributors), 1)
        self.assertEqual(summary[0]["unique_authors_count"], len(contributors))
        self.assertEqual(contributors[0]["author_key"], "unknown")

    def test_input_immutability(self):
        orig_repos = copy.deepcopy([self.repo_1_v1, self.repo_1_v2])
        orig_issues = copy.deepcopy([self.issue_1, self.issue_2, self.pr_1])

        repos_copy = copy.deepcopy(orig_repos)
        issues_copy = copy.deepcopy(orig_issues)

        r_c, i_c = [repos_copy[1]], issues_copy
        build_repository_summary(r_c, i_c, repos_copy, i_c, self.batch_id)
        build_repository_version_history(repos_copy, self.batch_id)
        build_activity_monthly(i_c, r_c, self.batch_id)
        build_contributor_activity(i_c, r_c, self.batch_id)
        build_label_analytics(i_c, r_c, self.batch_id)
        build_issue_lifecycle_current(i_c, r_c, i_c, self.batch_id)

        self.assertEqual(repos_copy, orig_repos)
        self.assertEqual(issues_copy, orig_issues)


if __name__ == "__main__":
    unittest.main()
