import argparse
import os

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_csv = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_csv)

# Prepare fields used later
# Parse blood pressure for downstream scoring
bp_split = df['Blood Pressure'].str.split('/', n=1, expand=True)
df['bp_sys'] = pd.to_numeric(bp_split[0], errors='coerce')
df['bp_dia'] = pd.to_numeric(bp_split[1], errors='coerce')
df['pulse_pressure'] = df['bp_sys'] - df['bp_dia']

# ASSERTION_START
# Guard and compute sleep duration dependent features
_sd = df['Sleep Duration']
assert _sd.notna().all()
assert ((_sd >= 3.0) & (_sd <= 14.0)).all()
assert (((_sd >= 5.0) & (_sd <= 9.0)).mean()) >= 0.80
# ASSERTION_END

df['sleep_duration_component'] = np.clip(1 - (np.abs(df['Sleep Duration'] - 8.0) / 5.0), 0, 1)

# ASSERTION_START
# Guard and compute sleep quality dependent features
_qos = df['Quality of Sleep']
assert _qos.notna().all()
assert ((_qos >= 1) & (_qos <= 10)).all()
assert ((_qos >= 6).mean()) >= 0.80
# ASSERTION_END

df['sleep_quality_component'] = df['Quality of Sleep'] / 10.0

# Combine into sleep component
# Emphasize duration slightly
df['sleep_component'] = np.clip(0.6 * df['sleep_duration_component'] + 0.4 * df['sleep_quality_component'], 0, 1)

# ASSERTION_START
# Guard and compute activity dependent features
_steps = df['Daily Steps']
assert _steps.notna().all()
assert ((_steps >= 0) & (_steps <= 40000)).all()
assert (((_steps >= 1000) & (_steps <= 20000)).mean()) >= 0.90
# ASSERTION_END

# Activity score blends steps and reported activity level
# Scale steps to 0..1 around 10k steps
steps_component = np.clip(df['Daily Steps'] / 10000.0, 0, 1)
activity_level_component = np.clip(df['Physical Activity Level'] / 100.0, 0, 1)
df['activity_component'] = np.clip(0.8 * steps_component + 0.2 * activity_level_component, 0, 1)

# ASSERTION_START
# Guard blood pressure fields before use in cardio metrics
import re

_bp = df['Blood Pressure']
pattern = re.compile(r'^\d{2,3}/\d{2,3}$')
assert _bp.str.fullmatch(pattern).all()
assert df['bp_sys'].notna().all() and df['bp_dia'].notna().all()
assert ((df['bp_sys'] >= 90) & (df['bp_sys'] <= 200)).all()
assert ((df['bp_dia'] >= 50) & (df['bp_dia'] <= 120)).all()
assert (df['bp_sys'] > df['bp_dia']).all()
assert ((df['pulse_pressure'] >= 20) & (df['pulse_pressure'] <= 80)).all()
# ASSERTION_END

# ASSERTION_START
# Guard heart rate before cardio metrics
_hr = df['Heart Rate']
assert _hr.notna().all()
assert ((_hr >= 40) & (_hr <= 200)).all()
assert (((_hr >= 50) & (_hr <= 100)).mean()) >= 0.85
# ASSERTION_END

# Cardio component derived from BP and HR
# Penalize deviations from 120/80 and HR around 70
sys_risk = np.clip((df['bp_sys'] - 120.0) / 40.0, 0, None) + np.clip((110.0 - df['bp_sys']) / 40.0, 0, None)
dia_risk = np.clip((df['bp_dia'] - 80.0) / 30.0, 0, None) + np.clip((70.0 - df['bp_dia']) / 30.0, 0, None)
hr_risk = np.clip(np.abs(df['Heart Rate'] - 70.0) / 30.0, 0, 1)
combined_bp_risk = np.clip(np.maximum(sys_risk, dia_risk), 0, 1)
df['cardio_component'] = np.clip(1 - (0.6 * combined_bp_risk + 0.4 * hr_risk), 0, 1)

# ASSERTION_START
# Correlation checks used as a data-quality gate before weekly aggregation
mask_sd_q = df['Sleep Duration'].notna() & df['Quality of Sleep'].notna()
corr_sd_q = df.loc[mask_sd_q, 'Sleep Duration'].corr(df.loc[mask_sd_q, 'Quality of Sleep'])
assert corr_sd_q >= 0.30
# ASSERTION_END

# ASSERTION_START
mask_steps_pal = df['Daily Steps'].notna() & df['Physical Activity Level'].notna()
corr_steps_pal = df.loc[mask_steps_pal, 'Daily Steps'].corr(df.loc[mask_steps_pal, 'Physical Activity Level'])
assert corr_steps_pal >= 0.60
# ASSERTION_END

# ASSERTION_START
mask_stress_q = df['Stress Level'].notna() & df['Quality of Sleep'].notna()
corr_stress_q = df.loc[mask_stress_q, 'Stress Level'].corr(df.loc[mask_stress_q, 'Quality of Sleep'])
assert corr_stress_q <= -0.30
# ASSERTION_END

# Stress factor adjustment
stress_norm = np.clip((df['Stress Level'] - 3.0) / 7.0, 0, 1)
df['stress_penalty'] = stress_norm

# Sleep disorder constraints before use in recommendations and penalties
# ASSERTION_START
sd_mask = df['Sleep Disorder'].notna()
valid_vals = df.loc[sd_mask, 'Sleep Disorder'].isin(['Insomnia', 'Sleep Apnea'])
assert valid_vals.all()
assert sd_mask.mean() >= 0.30
trimmed = df.loc[sd_mask, 'Sleep Disorder'].str.strip()
assert (trimmed == df.loc[sd_mask, 'Sleep Disorder']).all()
# ASSERTION_END

# Sleep disorder penalty
disorder_map = {'Insomnia': 0.85, 'Sleep Apnea': 0.75}
df['disorder_factor'] = 1.0
has_disorder = df['Sleep Disorder'].isin(disorder_map.keys())
df.loc[has_disorder, 'disorder_factor'] = df.loc[has_disorder, 'Sleep Disorder'].map(disorder_map)

# Compute final per-record sleep wellness score (0-100)
base = 0.5 * df['sleep_component'] + 0.2 * df['activity_component'] + 0.3 * df['cardio_component']
score = 100.0 * np.clip(base, 0, 1)
score_adjusted = np.clip(score * df['disorder_factor'] - 10.0 * df['stress_penalty'], 0, 100)
df['sleep_wellness_score'] = score_adjusted

# Aggregate weekly by person
agg = df.groupby('Person ID').agg({
    'Gender': 'first',
    'Age': 'first',
    'sleep_wellness_score': 'mean',
    'Sleep Duration': 'mean',
    'Quality of Sleep': 'mean',
    'Daily Steps': 'mean',
    'Heart Rate': 'mean',
    'bp_sys': 'mean',
    'bp_dia': 'mean',
    'Stress Level': 'mean'
}).reset_index()


# Derive primary sleep disorder per person (mode excluding NaN)
def primary_disorder(g):
    vals = g.dropna()
    if len(vals) == 0:
        return None
    return vals.value_counts().idxmax()


disorder_by_person = df.groupby('Person ID')['Sleep Disorder'].apply(primary_disorder).reset_index(
    name='Primary Sleep Disorder')
weekly = agg.merge(disorder_by_person, on='Person ID', how='left')
weekly.rename(columns={
    'sleep_wellness_score': 'weekly_sleep_wellness_score',
    'Sleep Duration': 'avg_sleep_hours',
    'Quality of Sleep': 'avg_sleep_quality',
    'Daily Steps': 'avg_daily_steps',
    'Heart Rate': 'avg_heart_rate',
    'bp_sys': 'avg_systolic_bp',
    'bp_dia': 'avg_diastolic_bp',
    'Stress Level': 'avg_stress_level'
}, inplace=True)


# Generate coaching recommendations
def gen_reco(row):
    recs = []
    if (row['avg_sleep_hours'] is not None) and (row['avg_sleep_hours'] < 7.0 or row['avg_sleep_quality'] < 6.0):
        recs.append('Target a consistent 7-9 hours; set a fixed bedtime and reduce screens 60 minutes before bed.')
    if (row['avg_daily_steps'] is not None) and (row['avg_daily_steps'] < 8000):
        recs.append('Increase activity: add 2k-3k steps per day with short walking meetings or post-lunch walks.')
    if (row['avg_stress_level'] is not None) and (row['avg_stress_level'] >= 7):
        recs.append('Practice 10 minutes of guided breathing or mindfulness twice daily to lower evening arousal.')
    if (row['avg_systolic_bp'] is not None and row['avg_diastolic_bp'] is not None) and (
            row['avg_systolic_bp'] >= 140 or row['avg_diastolic_bp'] >= 90 or row['avg_heart_rate'] >= 90):
        recs.append(
            'Monitor cardiovascular health; consider a BP check this week and consult a clinician if elevated persists.')
    if row['Primary Sleep Disorder'] == 'Insomnia':
        recs.append(
            'Consider CBT-I techniques: fixed wake time, stimulus control, and sleep restriction under guidance.')
    if row['Primary Sleep Disorder'] == 'Sleep Apnea':
        recs.append(
            'Ensure CPAP adherence and side-sleeping; consult a sleep specialist for device fit if comfort issues.')
    if not recs:
        recs.append('Maintain current routines; prioritize wind-down, daylight exposure, and regular activity.')
    return ' '.join(recs)


weekly['coaching_recommendations'] = weekly.apply(gen_reco, axis=1)

# Persist outputs
os.makedirs(args.output, exist_ok=True)
weekly_scores_path = os.path.join(args.output, 'weekly_sleep_scores.csv')
reco_path = os.path.join(args.output, 'coaching_recommendations.csv')

weekly_scores_cols = ['Person ID', 'Gender', 'Age', 'weekly_sleep_wellness_score', 'avg_sleep_hours',
                      'avg_sleep_quality', 'avg_daily_steps', 'avg_heart_rate', 'avg_systolic_bp', 'avg_diastolic_bp',
                      'avg_stress_level', 'Primary Sleep Disorder']
weekly[weekly_scores_cols].to_csv(weekly_scores_path, index=False)

weekly[['Person ID', 'coaching_recommendations']].to_csv(reco_path, index=False)
