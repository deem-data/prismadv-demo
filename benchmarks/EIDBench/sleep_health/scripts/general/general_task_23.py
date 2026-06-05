import argparse
import json
import os

import numpy as np
import pandas as pd


def classify_bp(sys, dia):
    if pd.isna(sys) or pd.isna(dia):
        return np.nan
    if sys >= 180 or dia >= 120:
        return "crisis"
    if sys >= 140 or dia >= 90:
        return "stage2"
    if (130 <= sys <= 139) or (80 <= dia <= 89):
        return "stage1"
    if (120 <= sys <= 129) and (dia < 80):
        return "elevated"
    if (sys < 120) and (dia < 80):
        return "normal"
    return "normal"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Ensure expected numeric types; coerce invalid to NaN for safe assertions
    numeric_cols = ['Sleep Duration', 'Quality of Sleep', 'Physical Activity Level', 'Stress Level', 'Heart Rate',
                    'Daily Steps']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Blood Pressure parsing
    bp_series = df['Blood Pressure'].astype(str)
    bp_match = bp_series.str.extract(r'^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$')
    df['bp_sys'] = pd.to_numeric(bp_match[0], errors='coerce')
    df['bp_dia'] = pd.to_numeric(bp_match[1], errors='coerce')
    # BP derived features
    df['bp_stage'] = [classify_bp(s, d) for s, d in zip(df['bp_sys'], df['bp_dia'])]
    df['map'] = df['bp_dia'] + (df['bp_sys'] - df['bp_dia']) / 3.0  # Mean Arterial Pressure

    # Heart Rate quality checks and derived factors
    hr_midband_prop = ((df['Heart Rate'] >= 50) & (df['Heart Rate'] <= 100)).mean()
    hr_outlier_weight = 1.0 / hr_midband_prop if hr_midband_prop > 0 else 1.0

    # Sleep Disorder label distribution checks
    sd_non_null = df['Sleep Disorder'].dropna()
    total_rows = len(df)
    nn = len(sd_non_null)
    p_non_null = nn / total_rows if total_rows > 0 else 0.0
    sd_counts = sd_non_null.value_counts(dropna=False)
    p_insomnia = (sd_counts.get('Insomnia', 0)) / nn if nn > 0 else np.nan
    p_apnea = (sd_counts.get('Sleep Apnea', 0)) / nn if nn > 0 else np.nan
    # ASSERTION_START
    allowed = {'Insomnia', 'Sleep Apnea', 'None'}
    non_null_values_ok = sd_non_null.isin(allowed).all()
    assert non_null_values_ok
    # ASSERTION_END
    # Use distribution to set condition weights (mean weight ~ 1)
    disorder_weights = {
        'Insomnia': 0.5 / p_insomnia if p_insomnia > 0 else 1.0,
        'Sleep Apnea': 0.5 / p_apnea if p_apnea > 0 else 1.0,
    }

    # Sleep Duration vs Quality relationships
    sleep_qs = df[['Sleep Duration', 'Quality of Sleep']].dropna()
    dur_quality_corr = sleep_qs['Sleep Duration'].corr(sleep_qs['Quality of Sleep'], method='pearson')
    short_mask = df['Sleep Duration'] < 6.0
    long_mask = df['Sleep Duration'] >= 8.0
    short_mean_q = df.loc[short_mask, 'Quality of Sleep'].mean()
    long_mean_q = df.loc[long_mask, 'Quality of Sleep'].mean()
    # Build a simple linear predictor of Quality from Duration (used in scoring)
    x = sleep_qs['Sleep Duration']
    y = sleep_qs['Quality of Sleep']
    var_x = float(x.var()) if len(x) > 1 else 0.0
    slope = (float(x.cov(y)) / var_x) if var_x > 1e-12 else 0.0
    intercept = float(y.mean() - slope * x.mean()) if len(x) > 0 else 0.0
    pred_quality = intercept + slope * df['Sleep Duration']

    # Daily Steps vs Physical Activity Level relationships
    pearson_steps_pa = df['Daily Steps'].corr(df['Physical Activity Level'], method='pearson')
    spearman_steps_pa = df['Daily Steps'].corr(df['Physical Activity Level'], method='spearman')
    pa_low = df['Physical Activity Level'].quantile(1.0 / 3.0)
    pa_high = df['Physical Activity Level'].quantile(2.0 / 3.0)
    top_pa = df[df['Physical Activity Level'] >= pa_high]
    bottom_pa = df[df['Physical Activity Level'] <= pa_low]
    top_steps_mean = top_pa['Daily Steps'].mean()
    bottom_steps_mean = bottom_pa['Daily Steps'].mean()
    pa60 = df[df['Physical Activity Level'] >= 60]
    pa60_prop_steps7000 = (pa60['Daily Steps'] >= 7000).mean() if len(pa60) > 0 else np.nan
    # Linear expectation of steps given PA
    pa = df['Physical Activity Level']
    steps = df['Daily Steps']
    var_pa = float(pa.var()) if len(pa) > 1 else 0.0
    beta = (float(pa.cov(steps)) / var_pa) if var_pa > 1e-12 else 0.0
    alpha = float(steps.mean() - beta * pa.mean()) if len(pa) > 0 else 0.0
    expected_steps = alpha + beta * pa
    expected_steps = expected_steps.clip(lower=1.0)

    # Subscores and penalties
    qual_norm = (df['Quality of Sleep'] / 10.0).clip(0.0, 1.0)
    dur_norm = ((df['Sleep Duration'] - 5.0) / (8.0 - 5.0)).clip(0.0, 1.0)
    w_dur = float(np.clip(dur_quality_corr, 0.0, 1.0))
    w_qual = 1.0 - w_dur
    sleep_component = 100.0 * (w_qual * qual_norm + w_dur * dur_norm)

    # Bonuses calibrated by cohort behavior
    resilience_bonus = np.where(short_mask & (df['Quality of Sleep'] >= (short_mean_q + 0.5)), 3.0, 0.0)
    long_bonus = np.where(long_mask & (df['Quality of Sleep'] >= long_mean_q), 2.0, 0.0)
    sleep_component = (sleep_component + resilience_bonus + long_bonus).clip(0.0, 100.0)

    steps_norm = (df['Daily Steps'] / 10000.0).clip(0.0, 1.0)
    alignment = (df['Daily Steps'] / expected_steps).clip(0.0, 2.0)
    alignment_norm = alignment.clip(0.0, 1.0)
    activity_component = 100.0 * (0.5 * steps_norm + 0.5 * alignment_norm)

    # Penalties
    hr = df['Heart Rate']
    hr_penalty = (
                         np.where(hr < 50, (50 - hr) / 50.0, 0.0) +
                         np.where(hr > 100, (hr - 100) / 100.0, 0.0)
                 ) * (0.15 * hr_outlier_weight)

    bp_penalty_map = {
        'normal': 0.0,
        'elevated': 0.05,
        'stage1': 0.10,
        'stage2': 0.20,
        'crisis': 0.40,
        np.nan: 0.15,
    }
    bp_penalty = df['bp_stage'].map(bp_penalty_map).fillna(0.15)

    sd_base_penalty = df['Sleep Disorder'].map({'Insomnia': 0.12, 'Sleep Apnea': 0.18}).fillna(0.0)
    sd_weight_series = df['Sleep Disorder'].map(disorder_weights).fillna(1.0)
    sd_penalty = sd_base_penalty * sd_weight_series

    penalty_points = 100.0 * (hr_penalty + bp_penalty + sd_penalty)

    overall_score = (0.6 * sleep_component + 0.4 * activity_component) - penalty_points
    overall_score = overall_score.clip(0.0, 100.0)

    # Triage logic
    crisis_condition = (df['bp_stage'] == 'crisis') | (df['bp_sys'] >= 180) | (df['bp_dia'] >= 120) | (hr > 120)
    high_condition = (
            crisis_condition |
            ((df['bp_stage'] == 'stage2') & ((sleep_component < 65) | (activity_component < 60))) |
            (df['Sleep Disorder'].isin(['Insomnia', 'Sleep Apnea']) & (sleep_component < 60))
    )
    medium_condition = (
            (~high_condition) & (
            (overall_score < 75) |
            ((df['Daily Steps'] < 5000) & (df['Physical Activity Level'] < 30)) |
            ((df['bp_stage'] == 'stage1') & (sleep_component < 70))
    )
    )
    triage_level = np.where(high_condition, 'High', np.where(medium_condition, 'Medium', 'None'))

    # Output artifacts
    out_df = pd.DataFrame({
        'Person ID': df['Person ID'],
        'Sleep Duration': df['Sleep Duration'],
        'Quality of Sleep': df['Quality of Sleep'],
        'Daily Steps': df['Daily Steps'],
        'Physical Activity Level': df['Physical Activity Level'],
        'Heart Rate': df['Heart Rate'],
        'Blood Pressure': df['Blood Pressure'],
        'bp_sys': df['bp_sys'],
        'bp_dia': df['bp_dia'],
        'bp_stage': df['bp_stage'],
        'sleep_component': np.round(sleep_component, 2),
        'activity_component': np.round(activity_component, 2),
        'sleep_wellness_score': np.round(overall_score, 2),
        'triage_level': triage_level,
        'Sleep Disorder': df['Sleep Disorder']
    })

    os.makedirs(args.output, exist_ok=True)
    scores_path = os.path.join(args.output, 'member_sleep_scores.csv')
    out_df.to_csv(scores_path, index=False)

    diagnostics = {
        'sleep_duration_quality': {
            'pearson_corr': float(dur_quality_corr),
            'short_sleep_mean_quality': float(short_mean_q) if not np.isnan(short_mean_q) else None,
            'long_sleep_mean_quality': float(long_mean_q) if not np.isnan(long_mean_q) else None
        },
        'steps_vs_pa': {
            'pearson_corr': float(pearson_steps_pa) if not np.isnan(pearson_steps_pa) else None,
            'spearman_corr': float(spearman_steps_pa) if not np.isnan(spearman_steps_pa) else None,
            'top_pa_mean_steps': float(top_steps_mean) if not np.isnan(top_steps_mean) else None,
            'bottom_pa_mean_steps': float(bottom_steps_mean) if not np.isnan(bottom_steps_mean) else None,
            'pa60_prop_steps7000': float(pa60_prop_steps7000) if not np.isnan(pa60_prop_steps7000) else None
        },
        'sleep_disorder_distribution': {
            'prop_non_null': float(p_non_null),
            'p_insomnia_within_non_null': float(p_insomnia),
            'p_apnea_within_non_null': float(p_apnea)
        },
        'heart_rate': {
            'midband_prop_50_100': float(hr_midband_prop)
        }
    }
    with open(os.path.join(args.output, 'dataset_diagnostics.json'), 'w') as f:
        json.dump(diagnostics, f, indent=2)


if __name__ == '__main__':
    main()
