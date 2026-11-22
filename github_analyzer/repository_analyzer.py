import os
import re
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"


def load_env_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token and ENV_FILE.exists():
        try:
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GITHUB_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        except Exception:
            pass
    return token


# ==================================================
# Extract owner and repository name from GitHub URL
# ==================================================

def extract_owner_repo(repo_url):

    pattern = r"github\.com/([^/]+)/([^/]+)"

    match = re.search(
        pattern,
        repo_url
    )


    if not match:

        return None, None


    owner = match.group(1)

    repo = (
        match.group(2)
        .replace(".git", "")
    )


    return owner, repo





# ==================================================
# Create GitHub API headers
# ==================================================

def github_headers(github_token=""):
    # Explicit session token only. Never silently load a repository .env secret.
    headers={"Accept":"application/vnd.github+json", "User-Agent":"BuildRisk-local-demo"}
    token=str(github_token or "").strip()
    if token:headers["Authorization"]="Bearer "+token
    return headers





# ==================================================
# Analyze GitHub Repository
# ==================================================

def analyze_github_repository(
        repo_url,
        github_token=""
):


    owner, repo = extract_owner_repo(
        repo_url
    )


    if not owner or not repo:


        return {

            "error":
            "Invalid GitHub repository URL"

        }



    headers = github_headers(
        github_token
    )



    # ==================================================
    # Get latest commit
    # ==================================================


    commits_url = (

        f"https://api.github.com/repos/"
        f"{owner}/{repo}/commits"

    )



    response = requests.get(
        commits_url,
        headers=headers
    )



    if response.status_code != 200:
        error_msg = f"Unable to access GitHub repository (Status: {response.status_code})"
        if response.status_code == 401:
            error_msg = "GitHub Token Error: 401 Bad credentials. Clear the token input or provide a valid personal access token."
        elif response.status_code == 404:
            error_msg = f"Repository '{owner}/{repo}' not found. Please verify the repository URL."
        elif response.status_code == 403:
            error_msg = "GitHub API rate limit exceeded. Please provide a valid Personal Access Token."
        return {
            "error": error_msg,
            "status_code": response.status_code
        }




    commits = response.json()



    if not commits:


        return {

            "error":
            "No commits found"

        }




    latest_commit = commits[0]



    commit_id = (
        latest_commit["sha"]
    )


    commit_message = (

        latest_commit
        ["commit"]
        ["message"]

    )




    # ==================================================
    # Commit details
    # ==================================================


    details_url = (

        f"https://api.github.com/repos/"
        f"{owner}/{repo}/commits/"
        f"{commit_id}"

    )



    detail_response = requests.get(

        details_url,
        headers=headers

    )



    if detail_response.status_code != 200:


        return {

            "error":
            "Unable to fetch commit details"

        }




    commit_data = (
        detail_response.json()
    )




    files = (
        commit_data
        .get(
            "files",
            []
        )
    )



    changed_files = []


    for file in files:


        changed_files.append(

            file["filename"]

        )




    lines_added = (

        commit_data
        .get(
            "stats",
            {}
        )
        .get(
            "additions",
            0
        )

    )



    lines_deleted = (

        commit_data
        .get(
            "stats",
            {}
        )
        .get(
            "deletions",
            0
        )

    )





    # ==================================================
    # File type analysis
    # ==================================================



    dependency_files = [

        "requirements.txt",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pom.xml",
        "build.gradle",
        "composer.json",
        "pyproject.toml"

    ]



    dependency_changed = any(

        file.lower()
        .endswith(
            tuple(
                dependency_files
            )
        )

        for file in changed_files

    )




    workflow_changed = any(

        ".github/workflows"

        in file.lower()

        for file in changed_files

    )





    test_changed = any(

        "test"

        in file.lower()

        or

        "tests/"

        in file.lower()


        for file in changed_files

    )





    source_changed = any(


        file.lower()
        .endswith(

            (

                ".py",
                ".java",
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
                ".php",
                ".html",
                ".css"

            )

        )


        for file in changed_files

    )





    risk_count = sum(

        [

            dependency_changed,
            workflow_changed,
            test_changed,
            source_changed

        ]

    )





    # ==================================================
    # GitHub Actions previous build
    # ==================================================


    previous_status = "unknown"

    previous_failed_step = ""

    previous_error = ""



    actions_url = (

        f"https://api.github.com/repos/"
        f"{owner}/{repo}/actions/runs"

    )



    action_response = requests.get(

        actions_url,
        headers=headers

    )



    prior_runs_count = 0
    prior_failure_count = 0
    recent_3_failure_count = 0
    recent_3_total = 0
    hours_since_last_failure = 168.0
    hours_since_last_run = 24.0
    prior_failure_rate = 0.10
    failure_rate_3 = 0.10

    if action_response.status_code == 200:
        runs = action_response.json().get("workflow_runs", [])


        if runs:
            latest_run = runs[0]
            previous_status = (
                latest_run.get("conclusion")
                or "running"
            )

            if previous_status == "failure":
                previous_failed_step = (
                    latest_run.get("name", "GitHub Action")
                )
                previous_error = (
                    "Previous GitHub Action failed"
                )

            now_dt = datetime.now(timezone.utc)
            completed_runs = [r for r in runs if r.get("conclusion") in ("success", "failure")]
            prior_runs_count = len(completed_runs)

            if completed_runs:
                prior_failure_count = sum(1 for r in completed_runs if r.get("conclusion") == "failure")
                recent_3 = completed_runs[:3]
                recent_3_total = len(recent_3)
                recent_3_failure_count = sum(1 for r in recent_3 if r.get("conclusion") == "failure")

                try:
                    created_raw = latest_run.get("created_at", "").replace("Z", "+00:00")
                    run_dt = datetime.fromisoformat(created_raw)
                    hours_since_last_run = max(0.01, (now_dt - run_dt).total_seconds() / 3600.0)
                except Exception:
                    pass

                for r in completed_runs:
                    if r.get("conclusion") == "failure":
                        try:
                            fail_raw = r.get("created_at", "").replace("Z", "+00:00")
                            fail_dt = datetime.fromisoformat(fail_raw)
                            hours_since_last_failure = max(0.01, (now_dt - fail_dt).total_seconds() / 3600.0)
                            break
                        except Exception:
                            pass

        prior_failure_rate = (prior_failure_count / max(1, prior_runs_count)) if prior_runs_count > 0 else (1.0 if previous_status == "failure" else 0.10)
        failure_rate_3 = (recent_3_failure_count / max(1, recent_3_total)) if recent_3_total > 0 else prior_failure_rate





    # ==================================================
    # Final output for AI model
    # ==================================================

    return {
        "repository": f"{owner}/{repo}",
        "repo_url": repo_url,
        "commit_id": commit_id,
        "commit_message": commit_message,
        "files_changed": len(changed_files),
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "total_changes": lines_added + lines_deleted,
        "dependency_file_changed": int(dependency_changed),
        "test_file_changed": int(test_changed),
        "workflow_changed": int(workflow_changed),
        "source_file_changed": int(source_changed),
        "risk_file_count": risk_count,
        "changed_files": ", ".join(changed_files),
        "previous_build_status": previous_status,
        "previous_failed_step": previous_failed_step,
        "previous_error_message": previous_error,
        "repository_prior_runs": float(prior_runs_count),
        "repository_prior_failure_rate": float(prior_failure_rate),
        "workflow_prior_failure_rate": float(prior_failure_rate),
        "workflow_failure_rate_3": float(failure_rate_3),
        "hours_since_previous_workflow_run": float(hours_since_last_run),
        "hours_since_previous_failure": float(hours_since_last_failure),
    }