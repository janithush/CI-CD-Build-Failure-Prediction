"""Train, calibrate, select, and evaluate leakage-safe research models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURES = ROOT / "data" / "processed" / "research_features_strict.csv"
DEFAULT_MANIFEST = ROOT / "data" / "processed" / "research_split_manifest_strict.csv"
DEFAULT_MODEL = ROOT / "models" / "saved" / "research_build_failure_model_strict.joblib"
DEFAULT_REPORT = ROOT / "reports" / "research_model_results_strict.json"
RANDOM_SEED = 42

NUMERIC_FEATURES = [
    "files_changed", "lines_added", "lines_deleted", "message_length", "is_merge",
    "parent_count", "dependency_files_changed", "test_files_changed",
    "workflow_files_changed", "source_files_changed", "config_files_changed",
    "file_extension_count", "files_added", "files_removed", "files_renamed",
    "workflow_prior_runs", "repository_prior_runs", "previous_workflow_result",
    "workflow_prior_failure_rate", "repository_prior_failure_rate",
    "branch_prior_failure_rate", "workflow_failure_rate_3", "workflow_failure_rate_5",
    "workflow_failure_rate_10", "workflow_failure_rate_20",
    "hours_since_previous_workflow_run", "hours_since_previous_failure",
    "commit_hour_utc", "commit_day_of_week", "is_weekend", "churn_per_file",
]
CATEGORICAL_FEATURES = [
    "repository", "workflow_id", "workflow_name", "event", "branch", "primary_language"
]


def preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [("imputer", SimpleImputer(strategy="median", add_indicator=True)),
         ("scale", StandardScaler())]
    )
    categorical = Pipeline(
        [("imputer", SimpleImputer(strategy="most_frequent")),
         ("encode", OneHotEncoder(handle_unknown="ignore"))]
    )
    return ColumnTransformer(
        [("numeric", numeric, NUMERIC_FEATURES),
         ("categorical", categorical, CATEGORICAL_FEATURES)]
    )


def candidates(positive_weight: float) -> dict[str, object]:
    return {
        "dummy_prior": DummyClassifier(strategy="prior"),
        "logistic_c_0.1": LogisticRegression(
            C=0.1, max_iter=2000, class_weight="balanced", random_state=RANDOM_SEED
        ),
        "logistic_c_1": LogisticRegression(
            C=1.0, max_iter=2000, class_weight="balanced", random_state=RANDOM_SEED
        ),
        "decision_tree_depth_5": DecisionTreeClassifier(
            max_depth=5, min_samples_leaf=10, class_weight="balanced", random_state=RANDOM_SEED
        ),
        "random_forest_depth_10": RandomForestClassifier(
            n_estimators=300, max_depth=10, min_samples_leaf=3,
            class_weight="balanced", n_jobs=-1, random_state=RANDOM_SEED
        ),
        "xgboost_depth_3": XGBClassifier(
            n_estimators=300, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, scale_pos_weight=positive_weight,
            eval_metric="logloss", n_jobs=-1, random_state=RANDOM_SEED
        ),
        "xgboost_depth_5": XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, scale_pos_weight=positive_weight,
            eval_metric="logloss", n_jobs=-1, random_state=RANDOM_SEED
        ),
    }


def metric_values(y_true: pd.Series, probability: np.ndarray, threshold: float) -> dict:
    prediction = (probability >= threshold).astype(int)
    matrix = confusion_matrix(y_true, prediction, labels=[0, 1])
    return {
        "rows": int(len(y_true)),
        "failure_rate": float(y_true.mean()),
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, prediction)),
        "roc_auc": float(roc_auc_score(y_true, probability)),
        "pr_auc": float(average_precision_score(y_true, probability)),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "confusion_matrix": matrix.tolist(),
    }


def best_f1_threshold(y_true: pd.Series, probability: np.ndarray) -> float:
    options = np.linspace(0.05, 0.95, 181)
    scores = [f1_score(y_true, probability >= value, zero_division=0) for value in options]
    return float(options[int(np.argmax(scores))])


def bootstrap_intervals(
    y_true: pd.Series, probability: np.ndarray, samples: int = 1000,
    groups: pd.Series | None = None,
) -> dict[str, list[float]]:
    """Cluster bootstrap over commit groups: resample groups, keep all rows.

    Rows of one commit group are correlated (same change), so row-level
    bootstrap understates uncertainty.
    """
    rng = np.random.default_rng(RANDOM_SEED)
    y = np.asarray(y_true)
    if groups is None:
        clusters = [np.arange(len(y))]
    else:
        gdf = pd.Series(np.arange(len(y))).groupby(np.asarray(groups))
        clusters = [np.asarray(v) for v in gdf.indices.values()]
    values = {"roc_auc": [], "pr_auc": [], "brier_score": []}
    for _ in range(samples):
        pick = rng.integers(0, len(clusters), len(clusters))
        indices = np.concatenate([clusters[i] for i in pick])
        sampled_y = y[indices]
        sampled_p = probability[indices]
        if len(np.unique(sampled_y)) < 2:
            continue
        values["roc_auc"].append(roc_auc_score(sampled_y, sampled_p))
        values["pr_auc"].append(average_precision_score(sampled_y, sampled_p))
        values["brier_score"].append(brier_score_loss(sampled_y, sampled_p))
    return {
        name: [float(np.percentile(items, 2.5)), float(np.percentile(items, 97.5))]
        for name, items in values.items()
    }


def load_data(features_path: Path, manifest_path: Path) -> pd.DataFrame:
    data = pd.read_csv(features_path)
    manifest = pd.read_csv(manifest_path)
    keys = ["repository", "commit_id", "run_id", "run_attempt"]
    manifest = manifest[~manifest["split"].eq("purged")]
    data = data.merge(manifest[keys + ["split", "group_id"]], on=keys, how="inner", validate="one_to_one")
    for column in NUMERIC_FEATURES + CATEGORICAL_FEATURES:
        if column not in data:
            data[column] = np.nan
    data["workflow_id"] = data["workflow_id"].astype("string")
    return data.sort_values("run_started_at")


def train(data: pd.DataFrame) -> tuple[object, dict]:
    train_data = data[data["split"].eq("train")]
    validation = data[data["split"].eq("validation")]
    test = data[data["split"].eq("test")]
    if min(len(train_data), len(validation), len(test)) == 0:
        raise ValueError("Train, validation, and test splits must all contain rows")
    if min(train_data.build_result.nunique(), validation.build_result.nunique(), test.build_result.nunique()) < 2:
        raise ValueError("Every split must contain successes and failures")

    one_third = max(1, len(validation) // 3)
    selection = validation.iloc[:one_third]
    calibration = validation.iloc[one_third : 2 * one_third]
    threshold_data = validation.iloc[2 * one_third :]
    if min(len(selection), len(calibration), len(threshold_data)) < 10:
        raise ValueError("Validation split is too small for selection, calibration, and thresholding")

    feature_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    positive_weight = (train_data.build_result.eq(0).sum() /
                       max(1, train_data.build_result.eq(1).sum()))
    selection_results = {}
    fitted = {}
    for name, classifier in candidates(positive_weight).items():
        pipeline = Pipeline([("preprocess", preprocessor()), ("classifier", classifier)])
        pipeline.fit(train_data[feature_columns], train_data["build_result"])
        probability = pipeline.predict_proba(selection[feature_columns])[:, 1]
        selection_results[name] = metric_values(selection["build_result"], probability, 0.5)
        fitted[name] = pipeline

    eligible = {name: value for name, value in selection_results.items() if name != "dummy_prior"}
    best_name = max(eligible, key=lambda name: eligible[name]["pr_auc"])
    selected = fitted[best_name]
    calibrated = CalibratedClassifierCV(FrozenEstimator(selected), method="sigmoid")
    calibrated.fit(calibration[feature_columns], calibration["build_result"])
    threshold_probability = calibrated.predict_proba(threshold_data[feature_columns])[:, 1]
    threshold = best_f1_threshold(threshold_data["build_result"], threshold_probability)
    test_probability = calibrated.predict_proba(test[feature_columns])[:, 1]
    test_metrics = metric_values(test["build_result"], test_probability, threshold)
    test_metrics["confidence_intervals_95"] = bootstrap_intervals(
        test["build_result"], test_probability, groups=test["group_id"]
    )
    report = {
        "protocol": "docs/research_protocol.md",
        "selected_model": best_name,
        "selection_metric": "PR_AUC",
        "selection_results": selection_results,
        "calibration_method": "sigmoid",
        "threshold_selection": "maximum F1 on final validation third",
        "test_metrics": test_metrics,
        "feature_columns": feature_columns,
    }
    artifact = {
        "model": calibrated,
        "threshold": threshold,
        "features": feature_columns,
        "metadata": report,
    }
    return artifact, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model-output", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    data = load_data(args.features, args.manifest)
    artifact, report = train(data)
    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.model_output)
    args.report_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["test_metrics"], indent=2))
    print(f"Selected model: {report['selected_model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
