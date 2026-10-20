import copy
import unittest

from scripts.dds_transform import issue_row, repository_row


class TransformTests(unittest.TestCase):
    def setUp(self):
        self.issue = {
            "id": 101,
            "number": 7,
            "title": "Example issue",
            "state": "open",
            "user": {"id": 10, "login": "alice"},
            "created_at": "2026-10-19T19:00:00Z",
            "updated_at": "2026-10-19T20:00:00Z",
            "closed_at": None,
            "labels": [
                {"id": 2, "name": "bug"},
                {"id": 1, "name": "help wanted"},
            ],
            "assignees": [
                {"id": 20, "login": "bob"},
                {"id": 10, "login": "alice"},
            ],
        }
        self.repository = {
            "id": 500,
            "full_name": "example/project",
            "description": None,
            "language": "Kotlin",
            "stargazers_count": 10,
            "forks_count": 2,
            "open_issues_count": 1,
            "archived": False,
            "created_at": "2026-10-19T19:00:00Z",
            "updated_at": "2026-10-19T20:00:00Z",
        }

    def issue_hash(self, payload):
        return issue_row(payload, 101, 500)["hash_diff"]

    def test_array_order_does_not_change_hash(self):
        changed = copy.deepcopy(self.issue)
        changed["labels"].reverse()
        changed["assignees"].reverse()

        self.assertEqual(
            self.issue_hash(self.issue),
            self.issue_hash(changed),
        )
        row = issue_row(changed, 101, 500)
        self.assertEqual([x["id"] for x in row["labels"]], [1, 2])
        self.assertEqual([x["id"] for x in row["assignees"]], [10, 20])

    def test_member_attribute_changes_hash(self):
        for field, attribute in (
            ("labels", "name"),
            ("assignees", "login"),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.issue)
                changed[field][0][attribute] = "changed"
                self.assertNotEqual(
                    self.issue_hash(self.issue),
                    self.issue_hash(changed),
                )

    def test_title_change_changes_hash(self):
        changed = copy.deepcopy(self.issue)
        changed["title"] = "Changed title"
        self.assertNotEqual(
            self.issue_hash(self.issue),
            self.issue_hash(changed),
        )

    def test_non_business_fields_do_not_change_hash(self):
        changed = copy.deepcopy(self.issue)
        changed["updated_at"] = "2026-10-20T19:00:00Z"
        changed["body"] = "Changed body"
        changed["comments"] = 100

        self.assertEqual(
            self.issue_hash(self.issue),
            self.issue_hash(changed),
        )
        self.assertNotEqual(
            issue_row(self.issue, 101, 500)["source_updated_at"],
            issue_row(changed, 101, 500)["source_updated_at"],
        )

    def test_issue_id_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ISSUE_ID_MISMATCH"):
            issue_row(self.issue, 999, 500)

    def test_duplicate_members_are_rejected(self):
        for field in ("labels", "assignees"):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.issue)
                changed[field].append(copy.deepcopy(changed[field][0]))
                with self.assertRaisesRegex(
                    ValueError, "DUPLICATE_ARRAY_ID"
                ):
                    issue_row(changed, 101, 500)

    def test_null_author_is_supported(self):
        changed = copy.deepcopy(self.issue)
        changed["user"] = None
        row = issue_row(changed, 101, 500)
        self.assertIsNone(row["author_id"])
        self.assertIsNone(row["author_login"])

    def test_equivalent_timezones_have_same_hash(self):
        changed = copy.deepcopy(self.issue)
        changed["created_at"] = "2026-10-19T22:00:00+03:00"
        self.assertEqual(
            self.issue_hash(self.issue),
            self.issue_hash(changed),
        )

    def test_boolean_is_not_a_counter(self):
        changed = copy.deepcopy(self.repository)
        changed["stargazers_count"] = True
        with self.assertRaisesRegex(ValueError, "INVALID_INTEGER"):
            repository_row(changed)

    def test_repository_counter_changes_hash(self):
        changed = copy.deepcopy(self.repository)
        changed["stargazers_count"] += 1
        self.assertNotEqual(
            repository_row(self.repository)["hash_diff"],
            repository_row(changed)["hash_diff"],
        )

    def test_input_payloads_are_not_modified(self):
        original_issue = copy.deepcopy(self.issue)
        original_repository = copy.deepcopy(self.repository)

        issue_row(self.issue, 101, 500)
        repository_row(self.repository)

        self.assertEqual(self.issue, original_issue)
        self.assertEqual(self.repository, original_repository)


if __name__ == "__main__":
    unittest.main()
