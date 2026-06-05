import argparse
import os
import re

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_file = os.path.join(args.input, 'new_data.csv')
os.makedirs(args.output, exist_ok=True)

df = pd.read_csv(input_file)

# Select and coerce relevant columns
sleep_duration = pd.to_numeric(df['Sleep Duration'], errors='coerce')
qos = pd.to_numeric(df['Quality of Sleep'], errors='coerce')
stress = pd.to_numeric(df['Stress Level'], errors='coerce')
hr = pd.to_numeric(df['Heart Rate'], errors='coerce')
steps = pd.to_numeric(df['Daily Steps'], errors='coerce')
pal = pd.to_numeric(df['Physical Activity Level'], errors='coerce')
bp_series = df['Blood Pressure']
bmi_cat = df['BMI Category']
sleep_disorder = df['Sleep Disorder'] if 'Sleep Disorder' in df.columns else pd.Series([np.nan] * len(df))

# ASSERTION_START
# Sleep Duration assumptions before using it
assert sleep_duration.notna().all()
assert ((sleep_duration >= 3) & (sleep_duration <= 12)).all()
share_5_9 = ((sleep_duration >= 5) & (sleep_duration <= 9)).mean()
assert share_5_9 >= 0.70
# ASSERTION_END

# Use Sleep Duration in scoring
optimal_sleep = 7.5
sleep_duration_dev = (sleep_duration - optimal_sleep).abs()
duration_component = np.clip(sleep_duration_dev / 4.5, 0.0, 1.0)

# ASSERTION_START
# Quality of Sleep assumptions and usage
assert qos.notna().all()
vals = qos.dropna()
is_integer = np.isclose(vals, np.round(vals))
assert is_integer.all()
assert vals.between(1, 10, inclusive='both').all()
prop_qos_ge6 = (qos >= 6).mean()
assert prop_qos_ge6 >= 0.85
# ASSERTION_END

qos_component = np.clip((10 - qos) / 9.0, 0.0, 1.0)

# Correlation-based calibration between Sleep Duration and Quality of Sleep
mask_dq = sleep_duration.notna() & qos.notna()
if mask_dq.sum() >= 2:
    corr_dur_qos = sleep_duration[mask_dq].corr(qos[mask_dq])
else:
    corr_dur_qos = np.nan
# ASSERTION_START
assert not np.isnan(corr_dur_qos) and corr_dur_qos >= 0.3
# ASSERTION_END

# Use regression only after correlation check to predict expected QoS from duration
coef_dq = np.polyfit(sleep_duration[mask_dq].values, qos[mask_dq].values, 1)
qos_pred = coef_dq[0] * sleep_duration + coef_dq[1]
qos_gap = np.clip((qos_pred - qos) / 4.0, -1.0, 1.0)
qos_gap_penalty = np.clip(-qos_gap, 0.0, 1.0)

# Stress correlations and usage
mask_sq = stress.notna() & qos.notna()
mask_sd = stress.notna() & sleep_duration.notna()
if mask_sq.sum() >= 2:
    corr_stress_qos = stress[mask_sq].corr(qos[mask_sq])
else:
    corr_stress_qos = np.nan
if mask_sd.sum() >= 2:
    corr_stress_sleep = stress[mask_sd].corr(sleep_duration[mask_sd])
else:
    corr_stress_sleep = np.nan
# ASSERTION_START
assert not np.isnan(corr_stress_qos) and corr_stress_qos <= -0.3
assert not np.isnan(corr_stress_sleep) and corr_stress_sleep <= -0.2
# ASSERTION_END

# Stress penalty scaled to [0,1]
stress_component = np.clip((stress - 3.0) / 5.0, 0.0, 1.0)

# ASSERTION_START
# Heart Rate assumptions and usage
assert hr.notna().all()
assert hr.between(40, 120, inclusive='both').all()
share_mid_hr = ((hr >= 55) & (hr <= 95)).mean()
assert share_mid_hr >= 0.80
# ASSERTION_END

# Heart rate risk: 0 in [55,95], rising to 1 at 40 or 120
hr_low_pen = np.where(hr < 55, (55 - hr) / (55 - 40), 0.0)
hr_high_pen = np.where(hr > 95, (hr - 95) / (120 - 95), 0.0)
hr_component = np.clip(hr_low_pen + hr_high_pen, 0.0, 1.0)

# ASSERTION_START
# Blood Pressure assumptions before parsing
assert bp_series.notna().all()
pattern = re.compile(r'^\d{2,3}/\d{2,3}$')
match_mask = bp_series.astype(str).str.match(pattern)
assert match_mask.all()
# ASSERTION_END

# Parse BP and validate ranges
bp_split = bp_series.astype(str).str.split('/', n=1, expand=True)
systolic = pd.to_numeric(bp_split[0], errors='coerce')
diastolic = pd.to_numeric(bp_split[1], errors='coerce')
# ASSERTION_START
m = systolic.notna() & diastolic.notna()
assert m.all()
assert systolic[m].between(90, 200, inclusive='both').all()
assert diastolic[m].between(50, 120, inclusive='both').all()
assert (systolic[m] > diastolic[m]).all()
# ASSERTION_END

# Blood pressure risk relative to 120/80 baseline
bp_sys_pen = np.clip((systolic - 120) / (200 - 120), 0.0, 1.0)
bp_dia_pen = np.clip((diastolic - 80) / (120 - 80), 0.0, 1.0)
bp_component = np.maximum(bp_sys_pen, bp_dia_pen)

# Daily Steps and Physical Activity Level relationships
mask_ps = steps.notna() & pal.notna()
if mask_ps.sum() >= 2:
    corr_steps_pal = steps[mask_ps].corr(pal[mask_ps])
else:
    corr_steps_pal = np.nan
# ASSERTION_START
assert not np.isnan(corr_steps_pal) and corr_steps_pal >= 0.5
zero_pal_mask = (pal == 0) & mask_ps
assert (steps[zero_pal_mask] <= 1000).all()
# ASSERTION_END

# Linear fit steps ~ a*pal + b for residual-based activity risk
coef_sp = np.polyfit(pal[mask_ps].values, steps[mask_ps].values, 1)
pred_steps = coef_sp[0] * pal + coef_sp[1]
activity_component = np.clip((pred_steps - steps) / 4000.0, 0.0, 1.0)

# BMI Category assumptions and usage
valid_bmi = {'Overweight', 'Normal', 'Obese', 'Normal Weight'}
# ASSERTION_START
assert bmi_cat.notna().all()
assert bmi_cat.isin(valid_bmi).all()
prop_norm_over = bmi_cat.isin(['Normal', 'Overweight']).mean()
assert prop_norm_over >= 0.80
# ASSERTION_END

bmi_risk_map = {
    'Normal': 0.0,
    'Normal Weight': 0.0,
    'Overweight': 0.4,
    'Obese': 1.0,
}
bmi_component = bmi_cat.map(bmi_risk_map).fillna(0.0)

sd = sleep_disorder
mask_sd_nonnull = sd.notna()
sa_mask = mask_sd_nonnull & (sd == 'Sleep Apnea')
obese_over_mask = bmi_cat.isin(['Overweight', 'Obese'])
sa_count = sa_mask.sum()
ratio_ok = True if sa_count == 0 else ((sa_mask & obese_over_mask).sum() / sa_count) >= 0.60
# ASSERTION_START
assert ratio_ok
# ASSERTION_END

disorder_risk_map = {'Sleep Apnea': 1.0, 'Insomnia': 0.6}
base_disorder_component = sd.map(disorder_risk_map).fillna(0.0)
# Amplify apnea risk when paired with higher BMI
apnea_with_weight = ((sd == 'Sleep Apnea') & bmi_cat.isin(['Overweight', 'Obese'])).astype(float)
disorder_component = np.clip(base_disorder_component + 0.2 * apnea_with_weight, 0.0, 1.0)

# Aggregate risk score [0,1]
risk_score = (
        0.20 * duration_component +
        0.15 * qos_component +
        0.05 * qos_gap_penalty +
        0.10 * stress_component +
        0.10 * hr_component +
        0.15 * bp_component +
        0.10 * activity_component +
        0.07 * bmi_component +
        0.08 * disorder_component
)
risk_score = np.clip(risk_score, 0.0, 1.0)

# Coaching alert logic
alerts = []
for i in range(len(df)):
    pid = df.loc[i, 'Person ID'] if 'Person ID' in df.columns else i
    score = float(risk_score.iloc[i])
    msg = None
    alert_type = None

    sys_i = float(systolic.iloc[i]) if not pd.isna(systolic.iloc[i]) else np.nan
    dia_i = float(diastolic.iloc[i]) if not pd.isna(diastolic.iloc[i]) else np.nan
    hr_i = float(hr.iloc[i]) if not pd.isna(hr.iloc[i]) else np.nan
    sd_i = sleep_disorder.iloc[i] if not pd.isna(sleep_disorder.iloc[i]) else None
    bmi_i = bmi_cat.iloc[i] if not pd.isna(bmi_cat.iloc[i]) else None

    if score >= 0.70:
        alert_type = 'HIGH_RISK'
        if (sd_i == 'Sleep Apnea') or ((sys_i >= 140 or dia_i >= 90) and bmi_i in ['Overweight', 'Obese']):
            msg = 'High sleep risk with cardiometabolic flags; suggest apnea screening and clinical review.'
        else:
            msg = 'High sleep risk; intensive coaching and evaluation recommended.'
    elif score >= 0.40:
        alert_type = 'MODERATE_RISK'
        if sd_i == 'Insomnia':
            msg = 'Moderate sleep risk; deliver CBT-I micro-lessons and wind-down routine.'
        elif steps.iloc[i] < 7000 and pal.iloc[i] < 60:
            msg = 'Moderate sleep risk; increase daytime activity and maintain sleep schedule.'
        else:
            msg = 'Moderate sleep risk; personalized sleep hygiene tips.'
    else:
        alert_type = 'LOW_RISK'
        msg = 'Maintain current habits; reinforce consistency and recovery days.'

    alerts.append({'Person ID': pid, 'risk_score': round(score, 4), 'alert_type': alert_type, 'coaching_message': msg})

# Outputs
scores_out = pd.DataFrame(
    {'Person ID': df['Person ID'] if 'Person ID' in df.columns else range(len(df)), 'risk_score': risk_score})
alerts_out = pd.DataFrame(alerts)

scores_out.to_csv(os.path.join(args.output, 'risk_scores.csv'), index=False)
alerts_out.to_csv(os.path.join(args.output, 'coaching_alerts.csv'), index=False)
