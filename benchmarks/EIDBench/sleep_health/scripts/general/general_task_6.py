import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # ASSERTION_START
    # Blood pressure format and parsing
    bp_mask = df['Blood Pressure'].notna()
    pattern_ok = df.loc[bp_mask, 'Blood Pressure'].str.fullmatch(r'\d{2,3}/\d{2,3}')
    assert pattern_ok.all()
    # ASSERTION_END

    bp_parts = df['Blood Pressure'].str.split('/', expand=True)
    df['bp_systolic'] = bp_parts[0].astype(int)
    df['bp_diastolic'] = bp_parts[1].astype(int)

    # ASSERTION_START
    assert (df['bp_systolic'] - df['bp_diastolic'] >= 5).all()
    # ASSERTION_END

    # Sleep duration checks used by downstream transforms
    # ASSERTION_START
    sd = df['Sleep Duration']
    assert ((sd >= 3.0) & (sd <= 14.0)).all()
    # ASSERTION_END

    # Transforms that require the above bounds
    df['sleep_log_edge'] = np.log(df['Sleep Duration'] - 2.99)
    df['sleep_upper_headroom'] = np.sqrt(14.01 - df['Sleep Duration'])

    # ASSERTION_START
    # Quality-of-sleep distribution expectation
    qos = df['Quality of Sleep']
    qos_mask = qos.notna()
    within_6_9 = (qos >= 6) & (qos <= 9)
    frac_within = within_6_9[qos_mask].mean() if qos_mask.any() else 0.0
    assert frac_within >= 0.90
    # ASSERTION_END

    # ASSERTION_START
    # Spearman correlation between sleep duration and quality
    sd2 = df['Sleep Duration']
    q2 = df['Quality of Sleep']
    m2 = sd2.notna() & q2.notna()
    corr_sd_q = sd2[m2].corr(q2[m2], method='spearman')
    assert (not pd.isna(corr_sd_q)) and (corr_sd_q >= 0.2)
    # ASSERTION_END

    pal = df['Physical Activity Level']
    pal_mask = pal.notna()
    pal_int = (pal == np.floor(pal))
    pal_range = (pal >= 0) & (pal <= 100)
    # ASSERTION_START
    # Physical activity level validity
    assert (pal_int[pal_mask] & pal_range[pal_mask]).all()
    # ASSERTION_END

    steps = df['Daily Steps']
    steps_mask = steps.notna()
    steps_range = (steps >= 0) & (steps <= 50000)
    # ASSERTION_START
    # Daily steps validity
    assert steps_range[steps_mask].all()
    # ASSERTION_END

    pair_mask_as = pal_mask & steps_mask
    corr_pal_steps = pal[pair_mask_as].corr(steps[pair_mask_as], method='spearman')
    # ASSERTION_START
    # Correlation between activity level and daily steps
    assert (not pd.isna(corr_pal_steps)) and (corr_pal_steps >= 0.4)
    # ASSERTION_END

    # Derived features for scoring
    # Blood pressure risk (vectorized)
    sys_v = df['bp_systolic']
    dia_v = df['bp_diastolic']
    stage2 = (sys_v >= 140) | (dia_v >= 90)
    stage1 = ((sys_v >= 130) & (sys_v <= 139)) | ((dia_v >= 80) & (dia_v <= 89))
    elevated = ((sys_v >= 120) & (sys_v <= 129)) & (dia_v < 80)
    df['bp_risk'] = np.select([stage2, stage1, elevated], [1.0, 0.7, 0.3], default=0.0)

    # Sleep need index from duration vs recommended band (7-9) and quality
    dur = df['Sleep Duration']
    sleep_deficit = np.where(dur < 7.0, 7.0 - dur, np.where(dur > 9.0, dur - 9.0, 0.0))
    sleep_deficit_scaled = np.minimum(sleep_deficit / 4.0, 1.0)
    qos_norm = ((df['Quality of Sleep'].clip(6, 9) - 6) / 3.0).clip(0, 1)
    df['sleep_need_index'] = (0.6 * sleep_deficit_scaled + 0.4 * (1.0 - qos_norm)).clip(0, 1)

    # Activity shortfall index
    steps_norm = np.log1p(df['Daily Steps']) / np.log(50001)
    pal_norm = df['Physical Activity Level'] / 100.0
    df['sedentary_index'] = (1.0 - (0.5 * steps_norm + 0.5 * pal_norm)).clip(0, 1)

    # Stress normalization (expected business scale 0-1)
    df['stress_norm'] = ((df['Stress Level'] - 3.0) / 5.0).clip(0, 1)

    # Sleep disorder flag boosts priority
    disorder_flag = df['Sleep Disorder'].notna()
    df['disorder_boost'] = np.where(disorder_flag, 0.1, 0.0)

    # Eligibility and prioritization
    df['eligible'] = (
            (df['sleep_need_index'] > 0.25) |
            (df['bp_risk'] >= 0.3) |
            (df['stress_norm'] > 0.5)
    )

    base_priority = (
            0.45 * df['sleep_need_index'] +
            0.20 * df['bp_risk'] +
            0.20 * df['stress_norm'] +
            0.15 * df['sedentary_index']
    )
    df['priority_score'] = (base_priority + df['disorder_boost']).clip(0, 1)

    # For ineligible members, set priority to 0 (used by downstream orchestration)
    df.loc[~df['eligible'], 'priority_score'] = 0.0

    # Output
    out_cols = [
        'Person ID', 'eligible', 'priority_score',
        'sleep_need_index', 'sedentary_index', 'bp_risk', 'stress_norm'
    ]
    output_path = os.path.join(args.output, 'sleep_coaching_scores.csv')
    os.makedirs(args.output, exist_ok=True)
    df[out_cols].to_csv(output_path, index=False)


if __name__ == '__main__':
    main()
