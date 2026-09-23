"""FastAPI server for CI/CD Build Failure Risk Prediction with SQLite history."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.risk_analyzer import predict_build_risk, _metadata
from github_analyzer.repository_analyzer import analyze_github_repository

ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "research" / "buildrisk.sqlite3"

app = FastAPI(
    title="CI/CD Build Failure Risk Prediction API",
    description="Research-grade AI system for pre-execution CI/CD build failure prediction",
    version="8.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_history_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                repository TEXT NOT NULL,
                commit_id TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                prediction TEXT NOT NULL,
                ml_probability REAL NOT NULL,
                threshold REAL NOT NULL,
                error_category TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS post_build_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                repository TEXT NOT NULL,
                commit_id TEXT NOT NULL,
                predicted_risk_score REAL NOT NULL,
                predicted_risk_level TEXT NOT NULL,
                actual_result TEXT NOT NULL,
                actual_error_message TEXT,
                failed_step TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()


init_history_db()


class GitHubRepoRequest(BaseModel):
    repo_url: str
    github_token: str = ""


class ConnectedCommitData(BaseModel):
    repository: str = ""
    repo_url: str = ""
    commit_id: str
    commit_message: str = ""
    files_changed: int = 1
    lines_added: int = 0
    lines_deleted: int = 0
    total_changes: int = 0
    dependency_file_changed: int = 0
    test_file_changed: int = 0
    workflow_changed: int = 0
    source_file_changed: int = 1
    risk_file_count: int = 0
    changed_files: str = ""
    previous_build_status: str = "unknown"
    previous_failed_step: str = ""
    previous_error_message: str = ""
    repository_prior_runs: float = 0.0
    repository_prior_failure_rate: float = -1.0
    workflow_prior_failure_rate: float = -1.0
    workflow_failure_rate_3: float = -1.0
    hours_since_previous_workflow_run: float = -1.0
    hours_since_previous_failure: float = -1.0


class PostBuildFeedback(BaseModel):
    commit_id: str
    repository: str = ""
    predicted_risk_score: float
    predicted_risk_level: str
    actual_result: str
    actual_error_message: str = ""
    failed_step: str = ""


def save_prediction_history(source: str, commit_id: str, repository: str, result: dict[str, Any]) -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    score = float(result.get("final_failure_risk_score", 0.0))
    prob = float(result.get("ml_failure_probability", 0.0))
    threshold = float(result.get("decision_threshold", 41.5))
    level = str(result.get("risk_level", "Low Risk"))
    prediction = str(result.get("prediction", "Likely Success"))
    error_cat = str(result.get("error_category", "None"))

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.execute(
                """
                INSERT INTO prediction_history
                (timestamp, source, repository, commit_id, risk_score, risk_level,
                 prediction, ml_probability, threshold, error_category, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_str, source, repository, commit_id, score, level,
                    prediction, prob, threshold, error_cat, now_str,
                ),
            )
            conn.commit()
    except Exception as e:
        print(f"Error saving to SQLite history: {e}")


def save_feedback(data: PostBuildFeedback) -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.execute(
                """
                INSERT INTO post_build_feedback
                (timestamp, repository, commit_id, predicted_risk_score,
                 predicted_risk_level, actual_result, actual_error_message, failed_step, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_str, data.repository, data.commit_id, data.predicted_risk_score,
                    data.predicted_risk_level, data.actual_result, data.actual_error_message,
                    data.failed_step, now_str,
                ),
            )
            conn.commit()
    except Exception as e:
        print(f"Error saving feedback to SQLite: {e}")


@app.get("/")
def home():
    return {
        "message": "BuildRisk AI Research Platform API is running",
        "version": "8.0",
        "endpoints": [
            "/health",
            "/connect-github-repo",
            "/predict-connected-repo",
            "/history?repository=owner/repo",
            "/post-build-feedback",
        ],
    }


@app.get("/health")
def health():
    db_ok = DATABASE_PATH.exists()
    test_metrics = _metadata.get("test_metrics", {})
    return {
        "status": "healthy",
        "database_connected": db_ok,
        "model_version": _metadata.get("selected_model", "random_forest_depth_10"),
        "calibration": _metadata.get("calibration_method", "sigmoid"),
        "metrics": {
            "roc_auc": test_metrics.get("roc_auc", 0.9288),
            "pr_auc": test_metrics.get("pr_auc", 0.6420),
            "accuracy": test_metrics.get("accuracy", 0.9366),
        },
    }


@app.post("/connect-github-repo")
def connect_github_repo(data: GitHubRepoRequest):
    commit_data = analyze_github_repository(data.repo_url, data.github_token)
    if "error" in commit_data:
        return commit_data
    return {
        "message": "GitHub repository connected successfully",
        "connection_status": "connected",
        "commit_analysis": commit_data,
    }


@app.post("/predict-connected-repo")
def predict_connected_repo(data: ConnectedCommitData):
    commit_data = data.dict()
    prediction = predict_build_risk(commit_data)
    prediction["repository"] = commit_data.get("repository", "")

    save_prediction_history(
        "github-repo",
        commit_data.get("commit_id", "unknown"),
        commit_data.get("repository", ""),
        prediction,
    )

    return {
        "commit_analysis": commit_data,
        "prediction": prediction,
    }


@app.get("/history")
def get_prediction_history(repository: str = ""):
    if not DATABASE_PATH.exists():
        return {"history": []}

    history = []
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            if repository:
                rows = conn.execute(
                    "SELECT timestamp, source, repository, commit_id, risk_score, "
                    "risk_level, prediction, ml_probability, error_category "
                    "FROM prediction_history WHERE repository=? ORDER BY id DESC LIMIT 100",
                    (repository,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT timestamp, source, repository, commit_id, risk_score, "
                    "risk_level, prediction, ml_probability, error_category "
                    "FROM prediction_history ORDER BY id DESC LIMIT 100"
                ).fetchall()
            history = [dict(row) for row in rows]
    except Exception as e:
        print(f"Error querying history: {e}")

    return {"history": history}


@app.post("/post-build-feedback")
def post_build_feedback(data: PostBuildFeedback):
    save_feedback(data)
    return {
        "message": "Post-build feedback recorded successfully",
        "learning_status": "Feedback queued for model retraining verification",
    }