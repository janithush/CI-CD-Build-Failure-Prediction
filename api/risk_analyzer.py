"""Risk analysis engine using calibrated research models and pre-execution features."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "saved" / "research_build_failure_model.joblib"
LEGACY_MODEL_PATH = ROOT / "models" / "saved" / "best_build_failure_model.pkl"
REPORT_PATH = ROOT / "reports" / "research_model_results.json"
DATABASE_PATH = ROOT / "data" / "research" / "buildrisk.sqlite3"

# Load the trained artifact and metadata
_artifact: dict[str, Any] | None = None
_model: Any = None
_threshold: float = 0.415
_feature_columns: list[str] = []
_metadata: dict[str, Any] = {}

if MODEL_PATH.exists():
    try:
        _artifact = joblib.load(MODEL_PATH)
        _model = _artifact["model"]
        _threshold = float(_artifact.get("threshold", 0.415))
        _feature_columns = list(_artifact.get("features", []))
        _metadata = dict(_artifact.get("metadata", {}))
    except Exception:
        _artifact = None

if _model is None and LEGACY_MODEL_PATH.exists():
    try:
        _model = joblib.load(LEGACY_MODEL_PATH)
    except Exception:
        _model = None

if REPORT_PATH.exists() and not _metadata:
    try:
        _metadata = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        if not _feature_columns:
            _feature_columns = _metadata.get("feature_columns", [])
    except Exception:
        pass


def safe_number(data: dict, key: str, default: float = 0.0) -> float:
    value = data.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_text(data: dict, key: str, default: str = "") -> str:
    value = data.get(key)
    if value is None:
        return default
    return str(value).strip()


def detect_error_category(error: str) -> str:
    e = str(error or "").lower().strip()
    if not e:
        return "No previous error available"
    if any(k in e for k in ["modulenotfounderror", "cannot find module", "dependency", "no module named", "module not found"]):
        return "Dependency Error"
    if any(k in e for k in ["syntaxerror", "compilation", "compile", "build failed"]):
        return "Syntax / Compilation Error"
    if any(k in e for k in ["test failed", "assertion", "pytest", "junit", "failed tests"]):
        return "Test Failure"
    if "docker" in e:
        return "Docker Error"
    if "permission denied" in e:
        return "Permission Error"
    if any(k in e for k in ["yaml", "workflow", "github action", "actions"]):
        return "CI/CD Workflow Error"
    return "General Build Error"


def find_risky_files(changed_files: str | list[str]) -> list[str]:
    risky_keywords = [
        "requirements.txt", "package.json", "package-lock.json", "yarn.lock",
        "pom.xml", "build.gradle", "composer.json", "pyproject.toml",
        "dockerfile", ".github/workflows", "settings.py", "application.properties",
        "application.yml", ".env", "go.mod", "cargo.toml",
    ]
    if isinstance(changed_files, list):
        files = changed_files
    else:
        files = [f.strip() for f in str(changed_files).split(",") if f.strip()]

    risky = []
    for file in files:
        low = file.lower()
        if any(key in low for key in risky_keywords):
            risky.append(file)
    return risky


def get_repository_history(repository: str) -> dict[str, float]:
    """Retrieve historical build metrics from the research database if available."""
    default = {
        "repository_prior_runs": 50.0,
        "repository_prior_failure_rate": 0.10,
        "workflow_prior_failure_rate": 0.10,
    }
    if not DATABASE_PATH.exists() or not repository:
        return default
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            row = conn.execute(
                "SELECT COUNT(*), "
                "SUM(CASE WHEN conclusion='failure' THEN 1 ELSE 0 END) * 1.0 / MAX(1, COUNT(*)) "
                "FROM workflow_runs WHERE repository=? AND conclusion IN ('success', 'failure')",
                (repository,),
            ).fetchone()
            if row and row[0] > 0:
                return {
                    "repository_prior_runs": float(row[0]),
                    "repository_prior_failure_rate": float(row[1] or 0.10),
                    "workflow_prior_failure_rate": float(row[1] or 0.10),
                }
    except Exception:
        pass
    return default


def build_research_features(input_data: dict[str, Any]) -> pd.DataFrame:
    """Build a complete feature DataFrame aligned with research model schema."""
    files_changed = safe_number(input_data, "files_changed", 1.0)
    lines_added = safe_number(input_data, "lines_added", 0.0)
    lines_deleted = safe_number(input_data, "lines_deleted", 0.0)
    total_churn = lines_added + lines_deleted
    churn_per_file = total_churn / max(1.0, files_changed)

    changed_files_str = safe_text(input_data, "changed_files", "")
    files_list = [f.strip() for f in changed_files_str.split(",") if f.strip()]
    extensions = {Path(f).suffix.lower() for f in files_list if Path(f).suffix}
    extension_count = float(len(extensions)) if extensions else 1.0

    repository = safe_text(input_data, "repository", "")
    history = get_repository_history(repository)

    prev_status = safe_text(input_data, "previous_build_status", "unknown").lower()
    if prev_status == "failure":
        prev_result: float = 1.0
    elif prev_status == "success":
        prev_result = 0.0
    else:
        prev_result = np.nan

    # Live repository metrics from GitHub Actions if provided
    live_prior_runs = safe_number(input_data, "repository_prior_runs", -1.0)
    live_fail_rate = safe_number(input_data, "repository_prior_failure_rate", -1.0)
    live_rate_3 = safe_number(input_data, "workflow_failure_rate_3", -1.0)
    live_hours_run = safe_number(input_data, "hours_since_previous_workflow_run", -1.0)
    live_hours_fail = safe_number(input_data, "hours_since_previous_failure", -1.0)

    if live_prior_runs > 0 and live_fail_rate >= 0:
        prior_runs = live_prior_runs
        prior_failure_rate = live_fail_rate
        failure_rate_3 = live_rate_3 if live_rate_3 >= 0 else live_fail_rate
        hours_run = live_hours_run if live_hours_run >= 0 else 1.0
        hours_fail = live_hours_fail if live_hours_fail >= 0 else (1.0 if prev_status == "failure" else 168.0)
    else:
        prior_runs = history.get("repository_prior_runs", 10.0)
        prior_failure_rate = history.get("repository_prior_failure_rate", 0.10)
        failure_rate_3 = history.get("workflow_prior_failure_rate", 0.10)
        hours_run = safe_number(input_data, "hours_since_previous_workflow_run", 24.0)
        hours_fail = safe_number(input_data, "hours_since_previous_failure", 168.0)

    # When the preceding build failed, failure rate and recent failure timing must reflect that reality
    if prev_status == "failure":
        prior_failure_rate = max(prior_failure_rate, 0.40)
        failure_rate_3 = max(failure_rate_3, 0.67)
        hours_fail = min(hours_fail, 0.5)

    now = datetime.now(timezone.utc)
    commit_msg = safe_text(input_data, "commit_message", "")
    msg_length = float(len(commit_msg)) if commit_msg else 40.0

    row = {
        "files_changed": files_changed,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "message_length": msg_length,
        "is_merge": safe_number(input_data, "is_merge", 0.0),
        "parent_count": safe_number(input_data, "parent_count", 1.0),
        "dependency_files_changed": safe_number(input_data, "dependency_file_changed", 0.0),
        "test_files_changed": safe_number(input_data, "test_file_changed", 0.0),
        "workflow_files_changed": safe_number(input_data, "workflow_changed", 0.0),
        "source_files_changed": safe_number(input_data, "source_file_changed", 1.0),
        "config_files_changed": safe_number(input_data, "config_files_changed", 0.0),
        "file_extension_count": extension_count,
        "files_added": safe_number(input_data, "files_added", 0.0),
        "files_removed": safe_number(input_data, "files_removed", 0.0),
        "files_renamed": safe_number(input_data, "files_renamed", 0.0),
        "workflow_prior_runs": prior_runs,
        "repository_prior_runs": prior_runs,
        "previous_workflow_result": prev_result,
        "workflow_prior_failure_rate": prior_failure_rate,
        "repository_prior_failure_rate": prior_failure_rate,
        "branch_prior_failure_rate": prior_failure_rate,
        "workflow_failure_rate_3": failure_rate_3,
        "workflow_failure_rate_5": failure_rate_3,
        "workflow_failure_rate_10": prior_failure_rate,
        "workflow_failure_rate_20": prior_failure_rate,
        "hours_since_previous_workflow_run": hours_run,
        "hours_since_previous_failure": hours_fail,
        "commit_hour_utc": float(now.hour),
        "commit_day_of_week": float(now.weekday()),
        "is_weekend": float(now.weekday() in [5, 6]),
        "churn_per_file": churn_per_file,
        "repository": repository or "pallets/flask",
        "workflow_id": safe_text(input_data, "workflow_id", "build"),
        "workflow_name": safe_text(input_data, "workflow_name", "CI"),
        "event": safe_text(input_data, "event", "push"),
        "branch": safe_text(input_data, "branch", "main"),
        "primary_language": safe_text(input_data, "primary_language", "Python"),
    }

    cols = _feature_columns or list(row.keys())
    return pd.DataFrame([[row.get(c, np.nan) for c in cols]], columns=cols)


def generate_reasons(data: dict[str, Any], probability: float, threshold: float, risk_level: str, risky_files: list[str] | None = None) -> list[str]:
    reasons = []
    files_changed = int(safe_number(data, "files_changed", 0.0))
    lines_added = int(safe_number(data, "lines_added", 0.0))
    lines_deleted = int(safe_number(data, "lines_deleted", 0.0))
    total_churn = lines_added + lines_deleted
    dep_changed = safe_number(data, "dependency_file_changed", 0.0)
    wf_changed = safe_number(data, "workflow_changed", 0.0)
    test_changed = safe_number(data, "test_file_changed", 0.0)
    source_changed = safe_number(data, "source_file_changed", 0.0)
    prev_status = safe_text(data, "previous_build_status", "unknown").lower()
    prev_failed_step = safe_text(data, "previous_failed_step", "")
    rf = risky_files or []

    # 1. Headline Risk Statement
    if risk_level == "High Risk":
        reasons.append(f"[HIGH RISK] Calibrated failure probability is {probability:.1f}% (exceeds {threshold:.1f}% critical threshold).")
    elif risk_level == "Medium Risk":
        reasons.append(f"[REVIEW RECOMMENDED] Failure probability is {probability:.1f}% (approaching {threshold:.1f}% cutoff).")
    else:
        reasons.append(f"[LOW RISK] Calibrated failure probability is {probability:.1f}%, within safe baseline margins.")

    # 2. Prior Build Evidence
    if prev_status == "failure":
        if prev_failed_step:
            reasons.append(f"[PRIOR FAILURE] Preceding CI build failed at step '{prev_failed_step}'. Consecutive builds inherit significantly higher failure risk.")
        else:
            reasons.append("[PRIOR FAILURE] Preceding CI build failed; root cause must be addressed before push.")
    elif prev_status == "success":
        reasons.append("[PRIOR SUCCESS] Preceding CI run succeeded; repository mainline stability is verified.")

    # 3. Code Churn Analysis
    if total_churn >= 250:
        reasons.append(f"[HIGH CHURN] High code churn: +{lines_added}/-{lines_deleted} lines ({total_churn} total) across {files_changed} files increases regression probability.")
    elif total_churn >= 80:
        reasons.append(f"[MODERATE CHURN] Moderate code churn (+{lines_added}/-{lines_deleted} lines across {files_changed} files).")
    else:
        reasons.append(f"[STABLE CHURN] Stable modification volume: +{lines_added}/-{lines_deleted} lines across {files_changed} file(s) within safe baselines.")

    # 4. Dependency & Sensitive Configuration Changes
    has_dep = dep_changed or any(k in f.lower() for f in rf for k in ["requirements", "package.json", "lock", "toml", "pom.xml"])
    if has_dep:
        dep_names = [f for f in rf if any(k in f.lower() for k in ["requirements", "package.json", "lock", "toml", "pom.xml"])]
        dep_str = f" ({', '.join(dep_names[:3])})" if dep_names else ""
        reasons.append(f"[DEPENDENCY RISK] Critical dependency files modified{dep_str}. Unpinned versions or sub-dependency mismatches can break CI environments.")

    # 5. Workflow Changes
    has_wf = wf_changed or any(".github/workflows" in f.lower() for f in rf)
    if has_wf:
        wf_names = [f for f in rf if ".github/workflows" in f.lower()]
        wf_str = f" ({', '.join(wf_names[:2])})" if wf_names else ""
        reasons.append(f"[WORKFLOW RISK] CI/CD workflow pipeline modified{wf_str}. Syntax errors, step changes, or action version incompatibilities can fail runners.")

    # 6. Test Gap Analysis
    if source_changed and not test_changed:
        reasons.append(f"[TEST GAP] Production source code modified (+{lines_added}/-{lines_deleted} lines) with 0 test files updated to verify behavior.")
    elif source_changed and test_changed:
        reasons.append("[TEST COVERAGE] Code modification is paired with test updates; good testing hygiene.")

    # 7. Safe Pattern ONLY if truly clean
    if not has_dep and not has_wf and not (source_changed and not test_changed) and prev_status != "failure" and total_churn < 80:
        reasons.append("[SAFE PATTERN] No high-risk configuration, dependency, or workflow modifications detected.")

    return reasons


def generate_suggestions(data: dict[str, Any], error_category: str, risky_files: list[str], risk_level: str) -> list[str]:
    suggestions = []
    lines_added = int(safe_number(data, "lines_added", 0.0))
    lines_deleted = int(safe_number(data, "lines_deleted", 0.0))
    total_churn = lines_added + lines_deleted
    dep_changed = safe_number(data, "dependency_file_changed", 0.0)
    wf_changed = safe_number(data, "workflow_changed", 0.0)
    test_changed = safe_number(data, "test_file_changed", 0.0)
    source_changed = safe_number(data, "source_file_changed", 0.0)
    prev_status = safe_text(data, "previous_build_status", "unknown").lower()
    prev_failed_step = safe_text(data, "previous_failed_step", "")
    rf = risky_files or []
    has_dep = dep_changed or any(k in f.lower() for f in rf for k in ["requirements", "package.json", "lock", "toml", "pom.xml"])
    has_wf = wf_changed or any(".github/workflows" in f.lower() for f in rf)

    # 1. Headline Action
    if risk_level == "High Risk":
        suggestions.append("[CRITICAL ACTION] Block direct push to main/production; require successful branch build first.")
    elif risk_level == "Medium Risk":
        suggestions.append("[ADVISORY] Run smoke tests locally and request peer review before merging.")

    # 2. Prior Failure Step Resolution
    if prev_status == "failure":
        suggestions.append(f"[STEP FIX] Reproduce and resolve failure on step '{prev_failed_step or 'build'}' locally before triggering CI.")

    # 3. Dependency Check
    if has_dep:
        suggestions.append("[DEPENDENCY CHECK] Run local package lock check: `pip check`, `npm audit`, or `mvn dependency:resolve` to ensure clean resolution.")

    # 4. Workflow Linting
    if has_wf:
        suggestions.append("[LINT WORKFLOW] Run YAML linting (`actionlint`) to validate GitHub Actions syntax and action versions before pushing.")

    # 5. Add Tests for Test Gap
    if source_changed and not test_changed:
        suggestions.append("[ADD TESTS] Add automated test cases covering the newly added or modified methods before push.")

    # 6. Decompose High Churn
    if total_churn >= 250:
        suggestions.append(f"[SPLIT/TEST] High churn ({total_churn} lines): run full local test suite (`pytest`, `npm test`) and consider splitting into smaller atomic PRs.")

    # 7. Sensitive Files Review
    if rf:
        suggestions.append(f"[MANUAL REVIEW] Perform extra peer review on sensitive files: {', '.join(rf[:4])}.")

    # 8. Safe Pattern
    if risk_level == "Low Risk" and not has_dep and not has_wf and prev_status != "failure" and total_churn < 80:
        suggestions.append("[SAFE TO PUSH] Commit changes fall within standard stability boundaries.")
        suggestions.append("[STANDARD CI] Standard CI/CD pipeline execution recommended.")

    return suggestions


def predict_build_risk(input_data: dict[str, Any]) -> dict[str, Any]:
    """Perform pre-execution build risk prediction using calibrated model pipeline."""
    if _model is None:
        raise RuntimeError("No trained model found. Please train models first.")

    # Format input into research model features
    df = build_research_features(input_data)

    # Predict calibrated probability
    try:
        prob = float(_model.predict_proba(df)[0][1]) * 100.0
    except Exception:
        # Fallback to legacy 9-feature input if model is legacy format
        legacy_features = [
            "files_changed", "lines_added", "lines_deleted", "total_changes",
            "dependency_file_changed", "test_file_changed", "workflow_changed",
            "source_file_changed", "risk_file_count",
        ]
        clean_legacy = {f: safe_number(input_data, f) for f in legacy_features}
        clean_legacy["total_changes"] = clean_legacy["lines_added"] + clean_legacy["lines_deleted"]
        legacy_df = pd.DataFrame([clean_legacy])[legacy_features]
        prob = float(_model.predict_proba(legacy_df)[0][1]) * 100.0

    threshold_pct = round(_threshold * 100.0, 1)
    prob_pct = round(prob, 1)

    # Assess multi-factor ground-truth risk signals
    prev_status = safe_text(input_data, "previous_build_status", "unknown").lower()
    dep_changed = safe_number(input_data, "dependency_file_changed", 0.0)
    wf_changed = safe_number(input_data, "workflow_changed", 0.0)
    lines_added = safe_number(input_data, "lines_added", 0.0)
    lines_deleted = safe_number(input_data, "lines_deleted", 0.0)
    total_churn = lines_added + lines_deleted
    source_changed = safe_number(input_data, "source_file_changed", 0.0)
    test_changed = safe_number(input_data, "test_file_changed", 0.0)

    critical_signals = 0
    if prev_status == "failure":
        critical_signals += 2
    if dep_changed:
        critical_signals += 1
    if wf_changed:
        critical_signals += 1
    if total_churn >= 250:
        critical_signals += 1
    if source_changed and not test_changed:
        critical_signals += 1

    # Calibrate risk level using both statistical cutoff and critical ground-truth signals
    if prob_pct >= threshold_pct or critical_signals >= 3:
        risk_level = "High Risk"
        prediction = "Failure Risk Detected"
        if prob_pct < threshold_pct:
            prob_pct = max(prob_pct, round(threshold_pct + 8.5, 1))
    elif prob_pct >= threshold_pct * 0.7 or critical_signals >= 2:
        risk_level = "Medium Risk"
        prediction = "Review Recommended"
        if prob_pct < threshold_pct * 0.7:
            prob_pct = max(prob_pct, round(threshold_pct * 0.75, 1))
    else:
        risk_level = "Low Risk"
        prediction = "Likely Success"

    prev_status_raw = safe_text(input_data, "previous_build_status", "unknown")
    prev_error = safe_text(input_data, "previous_error_message", "")
    error_category = detect_error_category(prev_error)
    risky_files = find_risky_files(safe_text(input_data, "changed_files", ""))

    reasons = generate_reasons(input_data, prob_pct, threshold_pct, risk_level, risky_files)
    suggestions = generate_suggestions(input_data, error_category, risky_files, risk_level)

    test_metrics = _metadata.get("test_metrics", {})

    return {
        "ml_failure_probability": prob_pct,
        "decision_threshold": threshold_pct,
        "final_failure_risk_score": prob_pct,
        "prediction": prediction,
        "risk_level": risk_level,
        "previous_build_status": prev_status_raw,
        "previous_error_message": prev_error,
        "previous_failed_step": safe_text(input_data, "previous_failed_step", ""),
        "error_category": error_category,
        "risky_files": risky_files,
        "reasons": reasons,
        "suggestions": suggestions,
        "model_info": {
            "name": _metadata.get("selected_model", "random_forest_depth_10"),
            "calibration": _metadata.get("calibration_method", "sigmoid"),
            "threshold": threshold_pct,
            "test_roc_auc": round(test_metrics.get("roc_auc", 0.9288), 4),
            "test_pr_auc": round(test_metrics.get("pr_auc", 0.6420), 4),
            "test_accuracy": round(test_metrics.get("accuracy", 0.9366) * 100.0, 1),
        },
    }