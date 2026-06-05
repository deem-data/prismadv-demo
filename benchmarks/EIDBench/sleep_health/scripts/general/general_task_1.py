import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    input_file = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_file)

    # Normalize numeric columns
    numeric_cols = [
        'Daily Steps', 'Physical Activity Level', 'Sleep Duration',
        'Quality of Sleep', 'Age', 'Stress Level', 'Heart Rate'
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    mask_activity = df['Daily Steps'].notna() & df['Physical Activity Level'].notna()
    # ASSERTION_START
    corr = df.loc[mask_activity, 'Daily Steps'].corr(df.loc[mask_activity, 'Physical Activity Level'])
    assert corr > 0.5
    # ASSERTION_END

    # Fit a simple linear model to predict expected steps from activity level
    slope, intercept = np.polyfit(
        df.loc[mask_activity, 'Physical Activity Level'],
        df.loc[mask_activity, 'Daily Steps'], 1
    )
    expected_steps = df['Physical Activity Level'] * slope + intercept

    high_pa_mask = df['Physical Activity Level'].notna() & (df['Physical Activity Level'] >= 90)
    # ASSERTION_START
    assert (df.loc[high_pa_mask, 'Daily Steps'] >= 8000).all()
    # ASSERTION_END

    sd = df['Sleep Duration']
    # ASSERTION_START
    assert ((sd >= 3.0) & (sd <= 12.0)).all()
    # ASSERTION_END
    duration_log = np.log(sd)

    q = df['Quality of Sleep']
    int_like = q.dropna().apply(lambda x: float(x).is_integer())
    # ASSERTION_START
    assert int_like.all() and q.between(1, 10).all()
    # ASSERTION_END
    q_idx = q.astype(int)
    quality_penalty_map = np.array([0, 40, 35, 30, 25, 20, 15, 10, 5, 2, 0])
    quality_penalty = pd.Series(quality_penalty_map[q_idx.values], index=df.index)

    # ASSERTION_START
    bp_raw = df['Blood Pressure']
    bp_str = bp_raw.where(bp_raw.notna(), '')
    matches = bp_str.str.fullmatch(r'\d{2,3}/\d{2,3}')
    assert matches.all()
    # ASSERTION_END

    sys_dia = df['Blood Pressure'].str.split('/', expand=True).astype(int)
    df['systolic'] = sys_dia[0]
    df['diastolic'] = sys_dia[1]

    s = df['systolic']
    d = df['diastolic']
    # ASSERTION_START
    assert s.between(90, 200).all() and d.between(60, 120).all() and (s > d).all()
    # ASSERTION_END

    pulse_pressure = s - d
    pulse_pressure_log = np.log(pulse_pressure)

    # Sleep-related components
    sleep_duration_component = np.abs(sd - 8.0) * 7.0
    sleep_quality_component = quality_penalty
    sleep_disorder_component = df.get('Sleep Disorder', pd.Series(index=df.index, dtype=object)).fillna(
        '').str.strip().isin(['Insomnia', 'Sleep Apnea']).astype(int) * 25.0

    # Activity components
    steps = df['Daily Steps']
    expected_clipped = expected_steps.clip(lower=1)
    shortfall_ratio = np.maximum(0.0, 8000.0 - steps) / 8000.0
    shortfall_component = shortfall_ratio * 25.0
    mismatch_component = (np.abs(steps - expected_steps) / expected_clipped).clip(upper=1.5) * 8.0
    activity_component = shortfall_component + mismatch_component

    # Blood pressure components
    bp_stage_component = np.select(
        [
            (s >= 140) | (d >= 90),
            ((s >= 130) & (s < 140)) | ((d >= 80) & (d < 90)),
            ((s >= 120) & (s < 130)) & (d < 80)
        ],
        [30.0, 20.0, 10.0],
        default=0.0
    )
    pulse_pressure_component = np.clip((pulse_pressure_log - np.log(40.0)) * 5.0, 0.0, 10.0)

    # Other modifiers
    stress = df['Stress Level'].fillna(0)
    stress_component = (stress / 10.0) * 20.0

    bmi_map = {
        'Obese': 25.0,
        'Overweight': 10.0,
        'Normal': 0.0,
        'Normal Weight': 0.0
    }
    bmi_component = df['BMI Category'].map(bmi_map).fillna(5.0)

    age = df['Age'].fillna(0)
    age_component = np.select(
        [age >= 60, age >= 45],
        [10.0, 5.0],
        default=0.0
    )

    # Aggregate and cap risk score
    risk_score = (
            sleep_duration_component
            + sleep_quality_component
            + sleep_disorder_component
            + activity_component
            + bp_stage_component
            + pulse_pressure_component
            + stress_component
            + bmi_component
            + age_component
    ).clip(lower=0.0, upper=100.0)

    # Tiering for outreach prioritization
    risk_tier = pd.cut(
        risk_score,
        bins=[-np.inf, 39.999, 69.999, np.inf],
        labels=['Low', 'Medium', 'High']
    ).astype(str)

    # Output
    out_df = df[['Person ID']].copy()
    out_df['sleep_risk_score'] = risk_score.round(2)
    out_df['risk_tier'] = risk_tier

    output_file = os.path.join(args.output, 'member_sleep_risk_scores.csv')
    out_df.to_csv(output_file, index=False)


if __name__ == '__main__':
    main()
