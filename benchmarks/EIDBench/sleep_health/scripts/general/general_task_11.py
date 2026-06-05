import argparse
import os

import numpy as np
import pandas as pd


def bp_stage_risk(sys_arr: np.ndarray, dia_arr: np.ndarray) -> np.ndarray:
    sys = sys_arr
    dia = dia_arr
    risk = np.zeros(len(sys), dtype=float)
    normal = (sys < 120) & (dia < 80)
    elevated = (sys >= 120) & (sys <= 129) & (dia < 80)
    stage1 = ((sys >= 130) & (sys <= 139)) | ((dia >= 80) & (dia <= 89))
    stage2 = ((sys >= 140) & (sys <= 180)) | ((dia >= 90) & (dia <= 120))
    crisis = (sys > 180) | (dia > 120)
    risk[normal] = 0.05
    risk[elevated] = 0.2
    risk[stage1] = 0.5
    risk[stage2] = 0.8
    risk[crisis] = 1.0
    return risk


def build_recommendations(row: pd.Series) -> str:
    recs = []
    # Sleep duration coaching
    if row['Sleep Duration'] < 6.0:
        recs.append("Target 7–9 hours nightly; add a 15–30 min wind-down before bed.")
    elif row['Sleep Duration'] > 9.0:
        recs.append("Keep time-in-bed under 9 hours; maintain a consistent wake time.")

    # Quality of sleep
    if row['qos'] <= 6:
        recs.append("Optimize sleep hygiene: dim lights, avoid screens 60 min pre-bed, keep bedroom cool and dark.")

    # Stress management
    if row['Stress Level'] >= 7:
        recs.append("Practice 10 minutes of breathing or body-scan each evening; consider CBT-I techniques.")

    # Activity alignment
    if row['Physical Activity Level'] < 60:
        recs.append("Add 2000–3000 steps/day via 3x10-min brisk walks.")
    elif row['Physical Activity Level'] >= 90:
        recs.append("Maintain vigorous activity days with >9000 steps and 1–2 easy recovery days.")

    # BMI and blood pressure considerations
    if str(row['BMI Category']).lower() in {"overweight", "obese"}:
        recs.append("Pair sleep regularity with nutrition planning to support weight management.")
    if (row['Systolic'] >= 140) or (row['Diastolic'] >= 90):
        recs.append("Discuss blood pressure with your clinician; consider home BP monitoring.")

    # High-risk escalation
    if row['risk_score'] >= 70:
        recs.append("Consider a sleep study to evaluate for apnea; use snore/SpO2 tracking if available.")

    return " • ".join(recs[:6])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    input_csv = os.path.join(args.input, 'new_data.csv')

    df = pd.read_csv(input_csv)

    # Normalize dtypes used downstream
    numeric_cols = ['Sleep Duration', 'Quality of Sleep', 'Physical Activity Level', 'Stress Level', 'Daily Steps',
                    'Heart Rate', 'Age']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Prepare series references used across assertions and logic
    dur = df['Sleep Duration']
    # ASSERTION_START
    assert dur.notna().all()
    # ASSERTION_END
    # Sleep duration features
    typical_min, typical_max = 5.0, 9.0
    sleep_adequacy = np.clip((dur.values - typical_min) / (typical_max - typical_min), 0.0, 1.0)
    duration_risk = 1.0 - sleep_adequacy

    qos = df['Quality of Sleep']
    # ASSERTION_START
    qos_notna = qos.notna().all()
    assert qos_notna
    qos_is_integer = np.isclose(qos % 1, 0).all()
    assert qos_is_integer
    qos_in_bounds = ((qos >= 1) & (qos <= 10)).all()
    assert qos_in_bounds

    # ASSERTION_END
    df['qos'] = qos.astype(int)
    qos_norm = df['qos'] / 10.0
    qos_risk = 1.0 - qos_norm.values

    # Blood Pressure parsing prepared before guard
    bp_str = df['Blood Pressure'].astype(str)
    bp_parts = bp_str.str.split('/', expand=True)
    sys_vals = pd.to_numeric(bp_parts[0], errors='coerce')
    dia_vals = pd.to_numeric(bp_parts[1], errors='coerce')
    # ASSERTION_START
    assert (sys_vals > 0).all() and (dia_vals > 0).all()
    # ASSERTION_END
    df['Systolic'] = sys_vals.astype(int)
    df['Diastolic'] = dia_vals.astype(int)

    pal = df['Physical Activity Level']
    steps = df['Daily Steps']
    # ASSERTION_START
    assert pal.notna().all() and steps.notna().all()

    # ASSERTION_END
    # Activity alignment model (simple linear fit)
    if len(df) >= 2:
        slope, intercept = np.polyfit(pal.values, steps.values, 1)
    else:
        slope, intercept = 100.0, 0.0
    expected_steps = slope * pal.values + intercept
    expected_steps = np.maximum(expected_steps, 1.0)
    activity_mismatch = np.clip(np.abs(steps.values - expected_steps) / expected_steps, 0.0, 1.0)

    # Additional risk contributors
    stress = df['Stress Level'].values
    stress_risk = np.clip((stress - 3.0) / 7.0, 0.0, 1.0)

    bmi = df['BMI Category'].astype(str).str.lower()
    bmi_risk_map = {
        'normal': 0.05,
        'normal weight': 0.05,
        'overweight': 0.3,
        'obese': 0.6,
    }
    bmi_risk = bmi.map(bmi_risk_map).fillna(0.1).values

    # Blood pressure risk
    bp_risk = bp_stage_risk(df['Systolic'].values, df['Diastolic'].values)

    # Combine risk components (weights sum to 1.0)
    w_duration = 0.25
    w_qos = 0.20
    w_bp = 0.25
    w_stress = 0.15
    w_activity = 0.10
    w_bmi = 0.05

    risk_raw = (
            w_duration * duration_risk +
            w_qos * qos_risk +
            w_bp * bp_risk +
            w_stress * stress_risk +
            w_activity * activity_mismatch +
            w_bmi * bmi_risk
    )

    risk_raw = np.clip(risk_raw, 0.0, 1.0)
    risk_score = (risk_raw * 100.0).round(1)

    # Bands
    bands = pd.cut(risk_score, bins=[-0.1, 33.3, 66.6, 100.0], labels=['Low', 'Moderate', 'High'])

    out = df.copy()
    out['risk_score'] = risk_score
    out['risk_band'] = bands.astype(str)

    # Recommendations
    out['recommendations'] = out.apply(build_recommendations, axis=1)

    # Select output columns
    cols = [
        'Person ID', 'Gender', 'Age', 'BMI Category', 'Blood Pressure', 'Systolic', 'Diastolic',
        'Sleep Duration', 'Quality of Sleep', 'Physical Activity Level', 'Daily Steps',
        'Stress Level', 'risk_score', 'risk_band', 'recommendations'
    ]
    cols = [c for c in cols if c in out.columns]
    output_df = out[cols]

    output_csv = os.path.join(args.output, 'member_risk_scores.csv')
    output_df.to_csv(output_csv, index=False)


if __name__ == '__main__':
    main()
