import pandas as pd
import numpy as np
import argparse
import os
import re


def triangular_score(x, low, opt_low, opt_high, high):
    arr = np.asarray(x, dtype=float)
    score = np.zeros_like(arr, dtype=float)
    left = (arr >= low) & (arr < opt_low)
    mid = (arr >= opt_low) & (arr <= opt_high)
    right = (arr > opt_high) & (arr <= high)
    score[left] = (arr[left] - low) / (opt_low - low)
    score[mid] = 1.0
    score[right] = (high - arr[right]) / (high - opt_high)
    score[(arr < low) | (arr > high)] = 0.0
    return score


def normalize(x, lower, upper):
    arr = np.asarray(x, dtype=float)
    denom = (upper - lower) if (upper - lower) != 0 else 1.0
    z = (arr - lower) / denom
    return np.clip(z, 0.0, 1.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    df = pd.read_csv(os.path.join(args.input, 'new_data.csv'))

    # ASSERTION_START
    sd = df['Sleep Duration'].astype(float)
    ok_range = (sd >= 3.0) & (sd <= 12.0)
    assert ok_range.all()
    typical = (sd >= 6.0) & (sd <= 9.0)
    frac_typical = typical.mean()
    assert frac_typical >= 0.70
    # ASSERTION_END

    sleep_dur_score = triangular_score(df['Sleep Duration'], low=3.0, opt_low=7.0, opt_high=9.0, high=12.0)

    # ASSERTION_START
    qos = df['Quality of Sleep']
    is_intlike = (qos == qos.astype(int))
    in_bounds = qos.between(1, 10)
    assert (is_intlike & in_bounds).all()
    # ASSERTION_END

    quality_score = df['Quality of Sleep'].astype(float) / 10.0

    # ASSERTION_START
    steps = df['Daily Steps'].astype(float)
    pal = df['Physical Activity Level'].astype(float)
    rx = steps.rank(method='average')
    ry = pal.rank(method='average')
    spearman = rx.corr(ry)
    assert spearman >= 0.5
    # ASSERTION_END

    s_min = float(np.percentile(df['Daily Steps'], 5))
    s_max = float(np.percentile(df['Daily Steps'], 95))
    steps_norm = normalize(df['Daily Steps'], s_min, s_max)
    pal_norm = normalize(df['Physical Activity Level'], 0.0, 100.0)
    base_activity = 0.5 * steps_norm + 0.5 * pal_norm

    # ASSERTION_START
    m = df['Physical Activity Level'].notna() & df['Daily Steps'].notna() & (df['Physical Activity Level'] >= 90)
    assert (df.loc[m, 'Daily Steps'] >= 8000).all()
    # ASSERTION_END

    very_active = (df['Physical Activity Level'] >= 90).astype(float)
    activity_score = np.clip(base_activity + 0.05 * very_active, 0.0, 1.0)

    bp_str = df['Blood Pressure'].astype(str)
    # ASSERTION_START
    pat = re.compile(r'^[0-9]{2,3}/[0-9]{2,3}$')
    valid_bp = bp_str.map(lambda x: bool(pat.match(x)))
    assert valid_bp.all()
    bp_parts_chk = bp_str.str.split('/', expand=True)
    s_chk = pd.to_numeric(bp_parts_chk[0], errors='coerce')
    d_chk = pd.to_numeric(bp_parts_chk[1], errors='coerce')
    mask_pair = s_chk.notna() & d_chk.notna()
    assert (s_chk[mask_pair] > d_chk[mask_pair]).all()
    # ASSERTION_END

    bp_parts = bp_str.str.split('/', expand=True)
    systolic = bp_parts[0].astype(int)
    diastolic = bp_parts[1].astype(int)
    map_pressure = diastolic + (systolic - diastolic) / 3.0
    bp_score = 1.0 - normalize(map_pressure, 95.0, 120.0)

    # ASSERTION_START
    stress = df['Stress Level'].astype(float)
    q = df['Quality of Sleep'].astype(float)
    pearson = stress.corr(q, method='pearson')
    assert pearson <= -0.2
    # ASSERTION_END

    stress_norm = normalize(df['Stress Level'], 1.0, 10.0)
    stress_component = 1.0 - stress_norm
    expected_quality = 1.0 - stress_norm
    gap = quality_score - expected_quality
    stress_quality_penalty = np.clip(-gap, 0.0, 1.0) * 0.10

    index_base = 0.35 * sleep_dur_score + 0.25 * quality_score + 0.20 * activity_score + 0.10 * stress_component + 0.10 * bp_score
    sleep_health_index = np.clip(index_base - stress_quality_penalty, 0.0, 1.0)

    alerts = []
    priorities = []
    reasons_col = []
    sdur = df['Sleep Duration'].astype(float)
    stress_n = stress_norm
    has_disorder = df.get('Sleep Disorder', pd.Series([np.nan] * len(df))).fillna('').isin(['Insomnia', 'Sleep Apnea'])

    for i in range(len(df)):
        reasons = []
        shi = float(sleep_health_index[i])
        if shi < 0.60:
            reasons.append('LOW_INDEX')
        if (stress_n[i] >= 0.70) and (quality_score[i] < 0.60):
            reasons.append('HIGH_STRESS_LOW_QUALITY')
        if (systolic[i] >= 140) or (diastolic[i] >= 90) or (map_pressure[i] >= 120):
            reasons.append('HYPERTENSION_PATTERN')
        if (sdur[i] < 6.0) or (sdur[i] > 9.0):
            reasons.append('INSUFFICIENT_SLEEP')
        if has_disorder[i] and shi < 0.75:
            reasons.append('DISORDER_FLAG')
        alerts.append('Yes' if len(reasons) > 0 else 'No')
        if 'HYPERTENSION_PATTERN' in reasons or 'LOW_INDEX' in reasons:
            priorities.append('High')
        elif len(reasons) > 0:
            priorities.append('Medium')
        else:
            priorities.append('None')
        reasons_col.append(';'.join(reasons))

    out = pd.DataFrame({
        'Person ID': df['Person ID'],
        'SleepHealthIndex': np.round(sleep_health_index, 3),
        'Alert': alerts,
        'Priority': priorities,
        'Reasons': reasons_col
    })
    out_path = os.path.join(args.output, 'sleep_health_index.csv')
    out.to_csv(out_path, index=False)


if __name__ == '__main__':
    main()
