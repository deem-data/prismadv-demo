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
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_csv)

    # Normalize dtypes
    num_cols = ['Age', 'Sleep Duration', 'Quality of Sleep', 'Physical Activity Level', 'Stress Level', 'Heart Rate',
                'Daily Steps']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # ASSERTION_START
    # Blood Pressure assertions before parsing and risk scoring
    _bp = df['Blood Pressure'].astype(str)
    _pat = r'^(\d{2,3})/(\d{2,3})$'
    assert _bp.str.fullmatch(_pat).all(), "Blood Pressure column must be in 'systolic/diastolic' format."
    # ASSERTION_END
    bp_parts = df['Blood Pressure'].astype(str).str.extract(r'^(\d{2,3})/(\d{2,3})$')
    df['bp_sys'] = bp_parts[0].astype(int)
    df['bp_dia'] = bp_parts[1].astype(int)

    # BP risk
    conds_bp = [
        (df['bp_sys'] >= 180) | (df['bp_dia'] >= 110),
        (df['bp_sys'] >= 160) | (df['bp_dia'] >= 100),
        (df['bp_sys'] >= 140) | (df['bp_dia'] >= 90),
        (df['bp_sys'] >= 130) | (df['bp_dia'] >= 85)
    ]
    choices_bp = [35, 28, 18, 6]
    df['bp_risk'] = np.select(conds_bp, choices_bp, default=0)

    # ASSERTION_START
    # Activity assumptions before deriving activity-based protection and vigorous bonus
    assert df['Daily Steps'].notna().all()
    assert df['Physical Activity Level'].notna().all()
    # ASSERTION_END
    rank_steps = df['Daily Steps'].rank(method='average', pct=True)
    rank_pa = df['Physical Activity Level'].rank(method='average', pct=True)
    df['activity_index'] = 0.5 * (rank_steps + rank_pa)
    df['activity_protect'] = 22.0 * df['activity_index']
    df['vigorous_bonus'] = ((df['Daily Steps'] >= 10000) & (df['Physical Activity Level'] >= 60)).astype(int) * 5.0

    # ASSERTION_START
    # Stress/Quality assumptions before blended risk
    assert df['Stress Level'].notna().all()
    assert df['Quality of Sleep'].notna().all()
    assert (df['Quality of Sleep'] <= 10).all()
    # ASSERTION_END
    df['sq_factor'] = df['Stress Level'] * (10 - df['Quality of Sleep']) / 10.0
    df['sq_risk'] = 2.8 * df['sq_factor']

    # Sleep duration risk
    dur = df['Sleep Duration']
    dur_conds = [
        dur < 5,
        (dur >= 5) & (dur < 6),
        (dur >= 6) & (dur < 7),
        (dur > 9)
    ]
    dur_vals = [22, 12, 6, 6]
    df['duration_risk'] = np.select(dur_conds, dur_vals, default=0)

    # BMI risk
    bmi_map = {
        'Obese': 12,
        'Overweight': 6,
        'Normal': 0,
        'Normal Weight': 0
    }
    df['bmi_risk'] = df['BMI Category'].map(bmi_map).fillna(0)

    # Heart rate risk (resting)
    hr = df['Heart Rate']
    hr_conds = [hr >= 90, (hr >= 80) & (hr < 90), (hr >= 70) & (hr < 80)]
    hr_vals = [6, 4, 2]
    df['hr_risk'] = np.select(hr_conds, hr_vals, default=0)

    # Age risk
    age = df['Age']
    age_conds = [age >= 65, (age >= 50) & (age < 65)]
    age_vals = [5, 3]
    df['age_risk'] = np.select(age_conds, age_vals, default=0)

    # Sleep disorder risk
    sd = df['Sleep Disorder'].fillna('')
    df['sd_risk'] = np.select([sd.str.contains('Sleep Apnea', case=False), sd.str.contains('Insomnia', case=False)],
                              [16, 10], default=0)

    # Aggregate risk, subtracting activity protection and bonus
    df['raw_risk'] = (
            df['bp_risk'] + df['sq_risk'] + df['duration_risk'] + df['bmi_risk'] + df['hr_risk'] + df['age_risk'] + df[
        'sd_risk']
            - df['activity_protect'] - df['vigorous_bonus']
    )

    df['risk_score'] = df['raw_risk'].clip(lower=0, upper=100).round(2)

    # Prioritization
    df['priority_bucket'] = pd.cut(df['risk_score'], bins=[-0.01, 25, 50, 75, 100],
                                   labels=['Low', 'Moderate', 'High', 'Critical'])
    df_sorted = df.sort_values('risk_score', ascending=False).reset_index(drop=True)

    out_cols = [
        'Person ID', 'risk_score', 'priority_bucket',
        'bp_risk', 'sq_risk', 'duration_risk', 'bmi_risk', 'hr_risk', 'age_risk', 'sd_risk',
        'activity_protect', 'vigorous_bonus'
    ]
    scores_path = os.path.join(args.output, 'sleep_risk_scores.csv')
    df_sorted[out_cols].to_csv(scores_path, index=False)

    top_path = os.path.join(args.output, 'priority_members.csv')
    df_sorted[['Person ID', 'risk_score', 'priority_bucket']].head(50).to_csv(top_path, index=False)


if __name__ == '__main__':
    main()
