import argparse
import json
import os
import re

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

input_csv = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_csv)

# Basic type coercion for numeric columns
num_cols = [
    'Age', 'Heart Rate', 'Daily Steps', 'Sleep Duration',
    'Quality of Sleep', 'Physical Activity Level', 'Stress Level'
]
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')

mask_pal_steps = df['Daily Steps'].notna() & df['Physical Activity Level'].notna()
x_steps = df.loc[mask_pal_steps, 'Daily Steps'].astype(float)
y_pal = df.loc[mask_pal_steps, 'Physical Activity Level'].astype(float)
pearson_pal_steps = x_steps.corr(y_pal)
spearman_pal_steps = x_steps.rank(method='average').corr(y_pal.rank(method='average'))
# ASSERTION_START
# Guard the correlation structure between Daily Steps and Physical Activity Level before deriving a mapping
assert (pearson_pal_steps >= 0.6) and (spearman_pal_steps >= 0.6)
# ASSERTION_END

# Build a simple linear mapper from Physical Activity Level to Steps for blending
x = y_pal
y = x_steps
var_x = np.var(x, ddof=0)
cov_xy = np.cov(x, y, ddof=0)[0, 1]
beta_steps_from_pal = cov_xy / (var_x + 1e-12)
alpha_steps_from_pal = y.mean() - beta_steps_from_pal * x.mean()

# Compute blended activity signal to stabilize activity-derived component
pal_pred_steps = alpha_steps_from_pal + beta_steps_from_pal * df['Physical Activity Level'].astype(float)
blended_steps = 0.6 * df['Daily Steps'].astype(float) + 0.4 * pal_pred_steps

mask_dur_q = df['Sleep Duration'].notna() & df['Quality of Sleep'].notna()
dur = df.loc[mask_dur_q, 'Sleep Duration'].astype(float)
qos = df.loc[mask_dur_q, 'Quality of Sleep'].astype(float)
pearson_dur_q = dur.corr(qos)
spearman_dur_q = dur.rank(method='average').corr(qos.rank(method='average'))
# ASSERTION_START
# Guard the relation between Sleep Duration and Quality of Sleep before building a residual-based consistency score
assert (pearson_dur_q >= 0.3) and (spearman_dur_q >= 0.3)
# ASSERTION_END

# Linear model: predict Quality of Sleep from Sleep Duration to compute residuals
var_dur = np.var(dur, ddof=0)
cov_dur_q = np.cov(dur, qos, ddof=0)[0, 1]
beta_q_from_dur = cov_dur_q / (var_dur + 1e-12)
alpha_q_from_dur = qos.mean() - beta_q_from_dur * dur.mean()
pred_qos = alpha_q_from_dur + beta_q_from_dur * df['Sleep Duration'].astype(float)
resid_q = df['Quality of Sleep'].astype(float) - pred_qos

mask_stress_q = df['Stress Level'].notna() & df['Quality of Sleep'].notna()
s = df.loc[mask_stress_q, 'Stress Level'].astype(float)
q = df.loc[mask_stress_q, 'Quality of Sleep'].astype(float)
spearman_stress_q = s.rank(method='average').corr(q.rank(method='average'))
# ASSERTION_START
# Guard monotonic inverse relationship between Stress Level and Quality of Sleep before using stress-driven adjustment
assert spearman_stress_q <= -0.2
# ASSERTION_END

# ASSERTION_START
# Guard Blood Pressure format before parsing
bp_series = df['Blood Pressure']
mask_bp = bp_series.notna()
pat = re.compile(r'^[0-9]{2,3}/[0-9]{2,3}$')
checks = bp_series[mask_bp].apply(lambda v: bool(pat.match(v)))
assert mask_bp.sum() > 0 and checks.all()
# ASSERTION_END

# Parse Blood Pressure
bp_parts = df['Blood Pressure'].str.extract(r'(?P<Systolic>\d{2,3})/(?P<Diastolic>\d{2,3})')
df['Systolic'] = pd.to_numeric(bp_parts['Systolic'], errors='coerce')
df['Diastolic'] = pd.to_numeric(bp_parts['Diastolic'], errors='coerce')

syst = df['Systolic']
dias = df['Diastolic']
order_ok = (syst > dias)
range_ok = syst.between(90, 200) & dias.between(50, 120)
# ASSERTION_START
# Guard BP numeric plausibility and ordering before using BP-derived risk
assert order_ok.all() and range_ok.all()
# ASSERTION_END

# ASSERTION_START
# Guard typical-range coverage for BP before tuning risk scaling
typical_ok_mask = syst.between(100, 160) & dias.between(60, 100)
coverage = typical_ok_mask.mean()
assert coverage >= 0.90
# ASSERTION_END

sd = df['Sleep Disorder']
lab_mask = sd.notna()
allowed = {'Sleep Apnea', 'Insomnia'}
valid_values = df.loc[lab_mask, 'Sleep Disorder'].isin(allowed)
share_labeled = lab_mask.mean()
apnea_share = (df.loc[lab_mask, 'Sleep Disorder'] == 'Sleep Apnea').mean() if lab_mask.any() else 0.0
# ASSERTION_START
# Guard label integrity and prevalence before using labels to calibrate triage thresholds
assert valid_values.all() and (share_labeled >= 0.35) and (share_labeled <= 0.50) and (apnea_share >= 0.45) and (
        apnea_share <= 0.55)
# ASSERTION_END

# Activity score (0-20): z-normalize blended steps, squash to [0,1]
bs = blended_steps.astype(float)
bs_mean = float(bs.mean())
bs_std = float(bs.std(ddof=0)) or 1.0
bs_z = (bs - bs_mean) / bs_std
activity_score = (np.tanh(bs_z) + 1.0) / 2.0 * 20.0

# Duration score (0-30): best near 8h
sdur = df['Sleep Duration'].astype(float)
duration_score = (1.0 - np.minimum(np.abs(sdur - 8.0) / 3.0, 1.0)) * 30.0

# Quality score (0-30): map 3..9 to 0..1 (clip)
qos_raw = df['Quality of Sleep'].astype(float)
quality_score = np.clip((qos_raw - 3.0) / 6.0, 0.0, 1.0) * 30.0

# Stress score (0-10): higher stress lowers score
stress = df['Stress Level'].astype(float)
stress_mean = float(stress.mean())
stress_std = float(stress.std(ddof=0)) or 1.0
stress_z = (stress - stress_mean) / stress_std
stress_score = (np.tanh(-stress_z) + 1.0) / 2.0 * 10.0

# BP score (0-10): penalize elevation from ~120/80
syst = df['Systolic'].astype(float)
dias = df['Diastolic'].astype(float)
spen = np.clip((syst - 120.0) / 80.0, 0.0, 1.0)
dpen = np.clip((dias - 80.0) / 40.0, 0.0, 1.0)
bp_score = (1.0 - (0.5 * spen + 0.5 * dpen)) * 10.0

# Consistency score (0-10): how close QoS is to duration-predicted QoS
resid_abs = np.abs(resid_q.astype(float))
q_std = float(qos_raw.std(ddof=0)) or 1.0
consistency_score = (1.0 - np.clip(resid_abs / (2.0 * q_std), 0.0, 1.0)) * 10.0

# Aggregate Sleep Health Score (0-100)
sleep_health_score = duration_score + quality_score + activity_score + stress_score + bp_score + consistency_score
sleep_health_score = np.clip(sleep_health_score, 0.0, 100.0)

# Triage risk: Apnea
bmi_map = {'Obese': 1.0, 'Overweight': 0.6, 'Normal': 0.0, 'Normal Weight': 0.0}
bmi_factor = df['BMI Category'].map(bmi_map).fillna(0.0).astype(float)
age = df['Age'].astype(float)
age_factor = np.clip((age - 40.0) / 30.0, 0.0, 1.0)
hr = df['Heart Rate'].astype(float)
hr_factor = np.clip((hr - 70.0) / 50.0, 0.0, 1.0)

a_bp = 0.5 * np.clip((syst - 130.0) / 60.0, 0.0, 1.0) + 0.5 * np.clip((dias - 85.0) / 35.0, 0.0, 1.0)
apnea_risk = np.clip(0.35 * bmi_factor + 0.25 * a_bp + 0.20 * age_factor + 0.20 * hr_factor, 0.0, 1.0)

# Triage risk: Insomnia
dur_short = np.clip((7.0 - sdur) / 3.0, 0.0, 1.0)
q_low = np.clip((6.0 - qos_raw) / 3.0, 0.0, 1.0)
stress_high = np.clip((stress - 6.0) / 4.0, 0.0, 1.0)
steps_low = np.clip((10000.0 - df['Daily Steps'].astype(float)) / 10000.0, 0.0, 1.0)
insomnia_risk = np.clip(0.40 * dur_short + 0.30 * q_low + 0.20 * stress_high + 0.10 * steps_low, 0.0, 1.0)

# Calibrate triage thresholds using label prevalence
share_labeled = lab_mask.mean()
apnea_share = (df.loc[lab_mask, 'Sleep Disorder'] == 'Sleep Apnea').mean()
prior_apnea = share_labeled * apnea_share
prior_insomnia = share_labeled * (1.0 - apnea_share)

apnea_threshold = float(np.quantile(apnea_risk, max(0.0, min(1.0, 1.0 - prior_apnea + 1e-9))))
insomnia_threshold = float(np.quantile(insomnia_risk, max(0.0, min(1.0, 1.0 - prior_insomnia + 1e-9))))

triage_apnea = apnea_risk >= apnea_threshold
triage_insomnia = insomnia_risk >= insomnia_threshold

# Prepare outputs
out_df = pd.DataFrame({
    'Person ID': df['Person ID'],
    'Sleep Health Score': sleep_health_score.round(2),
    'Apnea Risk Score': apnea_risk.round(3),
    'Insomnia Risk Score': insomnia_risk.round(3),
    'Triage Apnea': triage_apnea.astype(bool),
    'Triage Insomnia': triage_insomnia.astype(bool),
    'Systolic': syst.round(0).astype(int),
    'Diastolic': dias.round(0).astype(int)
})

out_csv = os.path.join(args.output, 'sleep_health_scores.csv')
out_df.to_csv(out_csv, index=False)

# Also write a brief calibration/diagnostics JSON
calib = {
    'correlations': {
        'pearson_steps_pal': float(pearson_pal_steps),
        'spearman_steps_pal': float(spearman_pal_steps),
        'pearson_duration_quality': float(pearson_dur_q),
        'spearman_duration_quality': float(spearman_dur_q),
        'spearman_stress_quality': float(spearman_stress_q)
    },
    'label_prevalence': {
        'share_labeled': float(share_labeled),
        'apnea_share_among_labeled': float(apnea_share),
        'prior_apnea': float(prior_apnea),
        'prior_insomnia': float(prior_insomnia)
    },
    'triage_thresholds': {
        'apnea': float(apnea_threshold),
        'insomnia': float(insomnia_threshold)
    }
}
with open(os.path.join(args.output, 'triage_diagnostics.json'), 'w') as f:
    json.dump(calib, f, indent=2)
