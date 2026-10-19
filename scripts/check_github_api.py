import json
import os
import sys
import urllib.error
import urllib.request


def get_json(path):
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token or token == "replace_with_github_token":
        sys.exit("GITHUB_TOKEN_MISSING")

    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ppad-lab3",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
            print(f"HTTP {response.status}: {path}")
            print(
                "rate_limit:"
                f" remaining={response.headers.get('X-RateLimit-Remaining')}"
                f" limit={response.headers.get('X-RateLimit-Limit')}"
            )
            return data
    except urllib.error.HTTPError as error:
        print(f"GITHUB_HTTP_ERROR: status={error.code}, path={path}")
        print(f"request_id={error.headers.get('X-GitHub-Request-Id')}")
        sys.exit(1)
    except urllib.error.URLError:
        sys.exit(f"GITHUB_NETWORK_ERROR: path={path}")


def main():
    config_path = "/opt/airflow/config/repositories.json"

    with open(config_path, encoding="utf-8") as file:
        config = json.load(file)

    repositories = config.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        sys.exit("INVALID_REPOSITORY_LIST")

    for name in repositories:
        if not isinstance(name, str):
            sys.exit("INVALID_REPOSITORY_NAME")
        parts = name.split("/")
        if len(parts) != 2 or not all(parts):
            sys.exit("INVALID_REPOSITORY_NAME")

    if len({name.lower() for name in repositories}) != len(repositories):
        sys.exit("DUPLICATE_REPOSITORIES")

    user = get_json("/user")
    print(f"authenticated_login={user['login']}")

    if user["login"].lower() != "s3r6anita":
        sys.exit("UNEXPECTED_GITHUB_ACCOUNT")

    for name in repositories:
        print(f"\nCHECKING: {name}")

        repository = get_json(f"/repos/{name}")
        print(f"repository={repository['full_name']}")
        print(f"has_issues={repository['has_issues']}")

        if not repository["has_issues"]:
            sys.exit(f"ISSUES_DISABLED: {name}")

        issues = get_json(
            f"/repos/{name}/issues?state=all&per_page=1"
        )
        if not isinstance(issues, list):
            sys.exit(f"UNEXPECTED_ISSUES_RESPONSE: {name}")

        print(f"issue_items_in_test_response={len(issues)}")

    print(f"\nchecked_repositories={len(repositories)}")
    print("GITHUB_API_OK")

if __name__ == "__main__":
    main()