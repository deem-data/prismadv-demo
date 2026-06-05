import argparse
import json
import os

import numpy as np
import pandas as pd


def compute_sleep_duration_risk(sleep_duration: pd.Series) -> pd.Series:
    under = (7.0 - sleep_duration).clip(lower=0)
    over = (sleep_duration - 9.0).clip(lower=0)
    return 1.2 * under + 1.0 * over


def compute_recovery_risk(qos: pd.Series, stress: pd.Series, sleep_duration: pd.Series) -> pd.Series:
    qos_norm = (qos.astype(float) - 5.0) / 5.0
    stress_norm = (stress.astype(float) - 5.0) / 5.0
    sd_norm = ((sleep_duration.clip(lower=3.0, upper=12.0) - 7.0) / 2.0)
    recovery = 0.5 * qos_norm + 0.3 * sd_norm - 0.4 * stress_norm
    return (-recovery).clip(lower=0) * 8.0


def compute_activity_risk(steps: pd.Series, pal: pd.Series) -> pd.Series:
    steps_norm = steps.clip(lower=0, upper=15000) / 15000.0
    pal_norm = pal.clip(lower=0, upper=120) / 120.0
    combined = 0.7 * steps_norm + 0.3 * pal_norm
    return (0.6 - combined).clip(lower=0) * 10.0


def compute_bp_components(bp_series: pd.Series) -> pd.DataFrame:
    parts = bp_series.str.split('/', expand=True)
    sys = parts[0].astype(int)
    dia = parts[1].astype(int)
    return pd.DataFrame({'systolic': sys, 'diastolic': dia})


def compute_bp_risk(sys: pd.Series, dia: pd.Series) -> pd.Series:
    normal = (sys < 120) & (dia < 80)
    elevated = (sys.between(120, 129)) & (dia < 80)
    stage1 = (sys.between(130, 139)) | (dia.between(80, 89))
    stage2 = (sys >= 140) | (dia >= 90)
    crisis = (sys >= 180) | (dia >= 120)
    risk = pd.Series(0.0, index=sys.index)
    risk = risk.mask(elevated, 2.0)
    risk = risk.mask(stage1, 5.0)
    risk = risk.mask(stage2, 8.0)
    risk = risk.mask(crisis, 12.0)
    return risk


def compute_hr_risk(hr: pd.Series) -> pd.Series:
    risk = pd.Series(0.0, index=hr.index)
    risk = risk.mask((hr < 50) | (hr > 110), 4.0)
    risk = risk.mask(((hr >= 50) & (hr <= 59)) | ((hr >= 101) & (hr <= 110)), 2.0)
    return risk


def bmi_risk_map(series: pd.Series) -> pd.Series:
    mapping = {
        'Normal': 0.0,
        'Normal Weight': 0.0,
        'Overweight': 3.0,
        'Obese': 6.0,
    }
    return series.map(mapping)


def sleep_disorder_penalty(series: pd.Series) -> pd.Series:
    mapping = {
        'Insomnia': 4.0,
        'Sleep Apnea': 6.0,
    }
    return series.map(mapping).fillna(0.0)


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)
input_file = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_file, na_values=['NullValue', 'null', 'NULL', 'NaN', 'nan'])
# ASSERTION_START
assert pd.to_numeric(df['Sleep Duration'], errors='coerce').notna().all()
# ASSERTION_END
sleep_dur_risk = compute_sleep_duration_risk(df['Sleep Duration'].astype(float))
# ASSERTION_START
q_sleep = pd.to_numeric(df['Quality of Sleep'], errors='coerce')
assert q_sleep.notna().all()
assert q_sleep.between(1, 10).all()

s_level = pd.to_numeric(df['Stress Level'], errors='coerce')
assert s_level.notna().all()
assert s_level.between(1, 10).all()

assert pd.to_numeric(df['Sleep Duration'], errors='coerce').notna().all()
# ASSERTION_END
recovery_risk = compute_recovery_risk(df['Quality of Sleep'], df['Stress Level'], df['Sleep Duration'])
# ASSERTION_START
assert pd.to_numeric(df['Daily Steps'], errors='coerce').notna().all()
assert pd.to_numeric(df['Physical Activity Level'], errors='coerce').notna().all()
# ASSERTION_END
activity_risk = compute_activity_risk(df['Daily Steps'].astype(float), df['Physical Activity Level'].astype(float))
# ASSERTION_START
assert df['Blood Pressure'].notna().all()
pattern_ok = df['Blood Pressure'].astype(str).str.match(r'^[0-9]+/[0-9]+$')
assert pattern_ok.all()
# ASSERTION_END
bp_parts = compute_bp_components(df['Blood Pressure'].astype(str))
bp_risk = compute_bp_risk(bp_parts['systolic'], bp_parts['diastolic'])

hr_risk = compute_hr_risk(df['Heart Rate'].astype(float))
# ASSERTION_START
allowed_bmi = {'Overweight', 'Normal', 'Obese', 'Normal Weight'}
assert df['BMI Category'].notna().all()
assert df['BMI Category'].isin(allowed_bmi).all()
# ASSERTION_END
bmi_risk = bmi_risk_map(df['BMI Category'])
sd_penalty = sleep_disorder_penalty(df['Sleep Disorder'])

age_risk = pd.cut(df['Age'].astype(float), bins=[-np.inf, 55, 60, 65, np.inf], labels=[0.0, 1.0, 2.0, 3.0]).astype(
    float)

stress_direct_risk = (df['Stress Level'].astype(float) - 6.0).clip(lower=0) * 0.8

risk_score = (
        sleep_dur_risk
        + recovery_risk
        + activity_risk
        + bp_risk
        + hr_risk
        + bmi_risk
        + sd_penalty
        + age_risk
        + stress_direct_risk
)

risk_tier = pd.cut(
    risk_score,
    bins=[-np.inf, 9, 17, 25, np.inf],
    labels=['Low', 'Moderate', 'High', 'Critical']
)

triggers = []
for i, row in df.iterrows():
    t = []
    if bp_parts.loc[i, 'systolic'] >= 140 or bp_parts.loc[i, 'diastolic'] >= 90:
        t.append('high_bp')
    if row['Sleep Duration'] < 6.0:
        t.append('short_sleep')
    if row['Sleep Duration'] > 9.0:
        t.append('long_sleep')
    if row['Quality of Sleep'] <= 6:
        t.append('low_sleep_quality')
    if row['Daily Steps'] < 5000:
        t.append('low_activity')
    if row['Stress Level'] >= 7:
        t.append('high_stress')
    if row['BMI Category'] == 'Obese':
        t.append('obesity')
    if pd.notna(row.get('Sleep Disorder')) and row.get('Sleep Disorder') in {'Insomnia', 'Sleep Apnea'}:
        t.append('sleep_disorder')
    triggers.append(';'.join(t))

output = pd.DataFrame({
    'Person ID': df['Person ID'],
    'Risk Score': risk_score.round(2),
    'Risk Tier': risk_tier.astype(str),
    'Triggers': triggers
})

output_file = os.path.join(args.output, 'sleep_risk_scores.csv')
output.to_csv(output_file, index=False)

alerts = output[output['Risk Tier'].isin(['High', 'Critical'])]
alerts_file = os.path.join(args.output, 'coaching_alerts.csv')
alerts.to_csv(alerts_file, index=False)

summary = {
    'total_employees': int(len(df)),
    'alerts_generated': int(len(alerts)),
    'avg_risk_score': float(risk_score.mean()),
}
with open(os.path.join(args.output, 'run_summary.json'), 'w') as f:
    json.dump(summary, f)
