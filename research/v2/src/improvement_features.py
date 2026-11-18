"""Predeclared feature additions. No fitting or evaluation of outer outcomes here.
Inputs must be the same frozen strict feature table used for the reference.
Per-project change statistics use unique commits first observed strictly before
this prediction's start, never future changes or any outcome label.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

SIZE = ['files_changed', 'lines_added', 'lines_deleted', 'churn_per_file']
TYPES = ['test', 'dependency', 'workflow', 'source', 'config']
C1_COLUMNS = ([f'log1p_{x}' for x in SIZE]
              + [f'past_mean_relative_{x}' for x in SIZE]
              + [f'{x}_file_proportion' for x in TYPES])
C2_COLUMNS = ['workflow_ewma_half_life_10', 'workflow_history_missing',
              'workflow_previous_failure_missing', 'workflow_log1p_available_count',
              'workflow_hours_since_last_available_outcome']


def add_change_context(frame: pd.DataFrame) -> pd.DataFrame:
    d = frame.copy().reset_index(drop=True)
    d['run_started_at'] = pd.to_datetime(d.run_started_at, utc=True)
    for c in SIZE:
        values = pd.to_numeric(d[c], errors='coerce').clip(lower=0)
        d['log1p_' + c] = np.log1p(values)
        d['past_mean_relative_' + c] = np.nan
    denominator = pd.to_numeric(d.files_changed, errors='coerce').clip(lower=1)
    for kind in TYPES:
        d[kind + '_file_proportion'] = d[kind + '_files_changed'] / denominator
    for _, positions in d.groupby('repository', sort=True).indices.items():
        sub = d.iloc[positions]
        # A commit can trigger many workflows. Count that change once, with its
        # first observed prediction time. Simultaneous changes never see each other.
        unique = sub.sort_values(['run_started_at', 'commit_id'], kind='stable').drop_duplicates('commit_id')
        starts = unique.run_started_at.astype('int64').to_numpy()
        k = np.searchsorted(starts, sub.run_started_at.astype('int64').to_numpy(), side='left')
        for c in SIZE:
            vals = pd.to_numeric(unique[c], errors='coerce').to_numpy(dtype=float)
            valid = np.isfinite(vals)
            sums = np.r_[0., np.cumsum(np.where(valid, vals, 0.))]
            counts = np.r_[0, np.cumsum(valid)]
            mean = np.divide(sums[k], counts[k], out=np.full(len(k), np.nan), where=counts[k]>0)
            # A one-unit floor is fixed, not estimated from targets.
            ratio = pd.to_numeric(sub[c], errors='coerce').to_numpy(dtype=float) / np.maximum(mean, 1.)
            d.loc[positions, 'past_mean_relative_' + c] = ratio
    return d


def add_recency_history(frame: pd.DataFrame) -> pd.DataFrame:
    d = frame.copy().reset_index(drop=True)
    starts = pd.to_datetime(d.run_started_at, utc=True).astype('int64').to_numpy()
    avail = pd.to_datetime(d.outcome_available_at, utc=True).astype('int64').to_numpy()
    results = d.build_result.to_numpy(dtype=float)
    d['workflow_history_missing'] = d.workflow_prior_runs.eq(0).astype(int)
    d['workflow_previous_failure_missing'] = d.hours_since_previous_failure.isna().astype(int)
    d['workflow_log1p_available_count'] = np.log1p(d.workflow_prior_runs)
    d['workflow_ewma_half_life_10'] = np.nan
    d['workflow_hours_since_last_available_outcome'] = np.nan
    decay = 2. ** (-1. / 10.)
    for _, positions in d.groupby(['repository', 'workflow_id'], sort=True).indices.items():
        order = positions[np.argsort(avail[positions], kind='stable')]
        # NaT is not an available outcome.
        order = order[avail[order] != np.iinfo(np.int64).min]
        if not len(order):
            continue
        a = avail[order]
        ewma = np.empty(len(order)); weighted_sum = weight = 0.
        for j, row in enumerate(order):
            weighted_sum = decay * weighted_sum + results[row]
            weight = decay * weight + 1.
            ewma[j] = weighted_sum / weight
        k = np.searchsorted(a, starts[positions], side='left')
        valid = k > 0
        rows = positions[valid]
        d.loc[rows, 'workflow_ewma_half_life_10'] = ewma[k[valid]-1]
        d.loc[rows, 'workflow_hours_since_last_available_outcome'] = (starts[rows] - a[k[valid]-1]) / 3.6e12
    return d


def history_rich_mask(frame: pd.DataFrame) -> np.ndarray:
    """Fixed routing gate. No threshold search."""
    return frame.workflow_prior_runs.ge(5).to_numpy()
