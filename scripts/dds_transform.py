import hashlib
import json
from datetime import datetime, timezone


BIGINT_MAX = 2**63 - 1


def integer(value, field, minimum=0):
    if type(value) is not int or not minimum <= value <= BIGINT_MAX:
        raise ValueError(f"INVALID_INTEGER: {field}")
    return value


def text(value, field, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"INVALID_TEXT: {field}")
    return value


def timestamp(value, field, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"INVALID_TIMESTAMP: {field}")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"TIMEZONE_REQUIRED: {field}")
    return result.astimezone(timezone.utc)


def normalized_members(items, attribute, field):
    if not isinstance(items, list):
        raise ValueError(f"INVALID_ARRAY: {field}")

    result = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"INVALID_ARRAY_ITEM: {field}")
        item_id = integer(item.get("id"), f"{field}.id", minimum=1)
        if item_id in seen:
            raise ValueError(f"DUPLICATE_ARRAY_ID: {field}")
        seen.add(item_id)
        result.append({
            "id": item_id,
            attribute: text(item.get(attribute), f"{field}.{attribute}"),
        })
    return sorted(result, key=lambda item: item["id"])


def json_default(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat(
            timespec="microseconds"
        )
    raise TypeError(f"UNSUPPORTED_HASH_TYPE: {type(value).__name__}")


def business_hash(business):
    encoded = json.dumps(
        business,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
        default=json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def repository_row(payload):
    if not isinstance(payload, dict):
        raise ValueError("INVALID_REPOSITORY_PAYLOAD")

    repository_id = integer(
        payload.get("id"), "repository.id", minimum=1
    )
    archived = payload.get("archived")
    if type(archived) is not bool:
        raise ValueError("INVALID_BOOLEAN: archived")

    business = {
        "full_name": text(payload.get("full_name"), "full_name"),
        "description": text(
            payload.get("description"), "description", nullable=True
        ),
        "language": text(
            payload.get("language"), "language", nullable=True
        ),
        "stars_count": integer(
            payload.get("stargazers_count"), "stars_count"
        ),
        "forks_count": integer(payload.get("forks_count"), "forks_count"),
        "open_issues_count": integer(
            payload.get("open_issues_count"), "open_issues_count"
        ),
        "archived": archived,
        "source_created_at": timestamp(
            payload.get("created_at"), "created_at"
        ),
    }
    return {
        "github_repository_id": repository_id,
        **business,
        "source_updated_at": timestamp(
            payload.get("updated_at"), "updated_at", nullable=True
        ),
        "hash_diff": business_hash(business),
    }


def issue_row(payload, github_issue_id, github_repository_id):
    if not isinstance(payload, dict):
        raise ValueError("INVALID_ISSUE_PAYLOAD")

    issue_id = integer(github_issue_id, "github_issue_id", minimum=1)
    if integer(payload.get("id"), "issue.id", minimum=1) != issue_id:
        raise ValueError("ISSUE_ID_MISMATCH")

    repository_id = integer(
        github_repository_id, "github_repository_id", minimum=1
    )
    author = payload.get("user")
    if author is not None and not isinstance(author, dict):
        raise ValueError("INVALID_AUTHOR")

    state = payload.get("state")
    if state not in ("open", "closed"):
        raise ValueError("INVALID_ISSUE_STATE")

    business = {
        "github_repository_id": repository_id,
        "issue_number": integer(
            payload.get("number"), "issue_number", minimum=1
        ),
        "title": text(payload.get("title"), "title"),
        "state": state,
        "is_pull_request": "pull_request" in payload,
        "author_id": (
            integer(author.get("id"), "author_id", minimum=1)
            if author is not None else None
        ),
        "author_login": (
            text(author.get("login"), "author_login")
            if author is not None else None
        ),
        "source_created_at": timestamp(
            payload.get("created_at"), "created_at"
        ),
        "source_closed_at": timestamp(
            payload.get("closed_at"), "closed_at", nullable=True
        ),
        "labels": normalized_members(
            payload.get("labels"), "name", "labels"
        ),
        "assignees": normalized_members(
            payload.get("assignees"), "login", "assignees"
        ),
    }
    return {
        "github_issue_id": issue_id,
        **business,
        "source_updated_at": timestamp(
            payload.get("updated_at"), "updated_at", nullable=True
        ),
        "hash_diff": business_hash(business),
    }
