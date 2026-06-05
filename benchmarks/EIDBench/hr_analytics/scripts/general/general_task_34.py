import argparse
import os

import numpy as np
import pandas as pd


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_csv = os.path.join(args.input, 'new_data.csv')
os.makedirs(args.output, exist_ok=True)

df = pd.read_csv(input_csv)
# ASSERTION_START
assert df['EmpID'].notna().all()
assert df['EmpID'].is_unique
# ASSERTION_END
df = df.set_index('EmpID', drop=False)

# Age integrity checks before age-derived features
# ASSERTION_START
assert (df['Age'] >= 18).all()


# ASSERTION_END
# Salary slab alignment before slab-driven features
# ASSERTION_START

def _derive_slab(mi):
    if mi < 5000:
        return 'Upto 5k'
    elif mi < 10000:
        return '5k-10k'
    elif mi < 15000:
        return '10k-15k'
    else:
        return '15k+'


derived_slab = df['MonthlyIncome'].apply(_derive_slab)
assert (derived_slab == df['SalarySlab']).all()
# ASSERTION_END
# Experience consistency before tenure-dependent calculations
# ASSERTION_START
assert (df['TotalWorkingYears'] >= 0).all()
assert (df['YearsAtCompany'] >= 0).all()
cap = df['Age'] - 18
assert (df['TotalWorkingYears'] <= cap).all()
assert (df['YearsAtCompany'] <= df['TotalWorkingYears']).all()
# ASSERTION_END
# Attrition label sanity and base-rate stability before threshold calibration
# ASSERTION_START
assert df['Attrition'].isin(['Yes', 'No']).all()
# ASSERTION_END
# Feature engineering
retirement_age = 70
years_to_retirement = (retirement_age - df['Age']).clip(lower=0)

slab_to_tier = {'Upto 5k': 3, '5k-10k': 2, '10k-15k': 1, '15k+': 0}
df['salary_tier'] = df['SalarySlab'].map(slab_to_tier)

is_overtime = (df['OverTime'] == 'Yes').astype(float)
js_low = 1.0 - (df['JobSatisfaction'] - 1.0) / 3.0
env_low = 1.0 - (df['EnvironmentSatisfaction'] - 1.0) / 3.0
wlb_low = 1.0 - (df['WorkLifeBalance'] - 1.0) / 3.0

distance_norm = (df['DistanceFromHome'] / 30.0).clip(upper=1.0)

promo_norm = (df['YearsSinceLastPromotion'] / 10.0).clip(upper=1.0)

manager_years = df['YearsWithCurrManager'].fillna(df['YearsWithCurrManager'].median())
manager_short = 1.0 - (manager_years / 10.0).clip(upper=1.0)

perf_low = (df['PerformanceRating'] <= 3).astype(float)
train_low = 1.0 - (df['TrainingTimesLastYear'] / 6.0).clip(upper=1.0)
stock_deficit = 1.0 - (df['StockOptionLevel'] / 3.0).clip(upper=1.0)

experience_cap = (df['Age'] - 18).clip(lower=0)
experience_gap = (experience_cap - df['TotalWorkingYears']).clip(lower=0)

tenure_ratio = df['YearsAtCompany'] / df['TotalWorkingYears'].replace(0, np.nan)
tenure_ratio = tenure_ratio.fillna(0.0).clip(upper=1.0)

age_youngish = (df['Age'] <= 25).astype(float)
age_senior = (df['Age'] >= 55).astype(float)

# Risk model
linear = (
        0.5
        + 0.60 * is_overtime
        + 0.50 * wlb_low
        + 0.45 * js_low
        + 0.40 * env_low
        + 0.30 * distance_norm
        + 0.50 * promo_norm
        + 0.40 * (df['salary_tier'] / 3.0)
        + 0.15 * train_low
        + 0.25 * perf_low
        + 0.20 * stock_deficit
        + 0.20 * manager_short
        + 0.20 * (1.0 - tenure_ratio)
        + 0.20 * age_youngish
        + 0.10 * age_senior
)

# Calibration and score
score = sigmoid(linear - 2.0)
base_yes = (df['Attrition'] == 'Yes').mean()
alert_share = float(np.clip(2.0 * base_yes, 0.10, 0.40))
threshold = float(pd.Series(score).quantile(1.0 - alert_share))

risk_band = pd.cut(
    score,
    bins=[-np.inf, threshold * 0.8, threshold, np.inf],
    labels=['low', 'medium', 'high']
)

out_df = pd.DataFrame({
    'EmpID': df['EmpID'],
    'Department': df['Department'],
    'JobRole': df['JobRole'],
    'Age': df['Age'],
    'MonthlyIncome': df['MonthlyIncome'],
    'SalarySlab': df['SalarySlab'],
    'risk_score': score,
    'risk_band': risk_band.astype(str)
}).set_index('EmpID', drop=False)

out_path_scores = os.path.join(args.output, 'attrition_risk_scores.csv')
out_df.to_csv(out_path_scores, index=False)

hrbp_map = {
    'Sales': 'hrbp_sales@example.com',
    'Research & Development': 'hrbp_rd@example.com',
    'Human Resources': 'hrbp_hr@example.com'
}

alerts = out_df[out_df['risk_band'] == 'high'].copy()
alerts['hrbp_owner'] = alerts['Department'].map(hrbp_map).fillna('hrbp_general@example.com')
alerts['alert_priority'] = np.where(alerts['risk_score'] >= max(threshold, alerts['risk_score'].quantile(0.90)), 'P1',
                                    'P2')

alerts_path = os.path.join(args.output, 'hrbp_alerts.csv')
alerts[['EmpID', 'Department', 'JobRole', 'risk_score', 'alert_priority', 'hrbp_owner']].to_csv(alerts_path,
                                                                                                index=False)

workload = alerts.groupby('hrbp_owner', as_index=False).size().rename(columns={'size': 'alert_count'})
workload_path = os.path.join(args.output, 'hrbp_workload.csv')
workload.to_csv(workload_path, index=False)

summary = {
    'base_yes_rate': round(float(base_yes), 4),
    'alert_share_target': alert_share,
    'threshold': threshold,
    'alerts_count': int(alerts.shape[0])
}

with open(os.path.join(args.output, 'run_summary.json'), 'w') as f:
    import json

    json.dump(summary, f, indent=2)
