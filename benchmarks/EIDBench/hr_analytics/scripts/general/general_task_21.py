import argparse
import json
import os

import numpy as np
import pandas as pd


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def age_to_group(age: float) -> str:
    if pd.isna(age):
        return np.nan
    a = int(age)
    if a >= 55:
        return '55+'
    elif a >= 46:
        return '46-55'
    elif a >= 36:
        return '36-45'
    elif a >= 26:
        return '26-35'
    else:
        return '18-25'


def compute_salary_slab(series: pd.Series) -> pd.Series:
    bins = [0, 5000, 10000, 15000, np.inf]
    labels = ['Upto 5k', '5k-10k', '10k-15k', '15k+']
    cats = pd.cut(series, bins=bins, labels=labels, right=True, include_lowest=False)
    return cats.astype(str)


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

input_csv = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_csv)

numeric_cols = [
    'Age', 'MonthlyIncome', 'YearsAtCompany', 'YearsInCurrentRole', 'TotalWorkingYears'
]
for c in numeric_cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')

df['AttritionFlag'] = (df['Attrition'] == 'Yes').astype(int)
base_rate = float(df['AttritionFlag'].mean())
base_logit = float(np.log(base_rate / (1 - base_rate))) if 0 < base_rate < 1 else 0.0

computed_age_group = df['Age'].apply(age_to_group)
age_group_rates = df.groupby('AgeGroup', dropna=False)['AttritionFlag'].mean()

mi = df['MonthlyIncome']
# ASSERTION_START
assert np.isfinite(mi).all() and (mi > 0).all()
# ASSERTION_END
salary_log = np.log(mi)

slab_from_income = compute_salary_slab(mi)
slab_rates = df.groupby('SalarySlab')['AttritionFlag'].mean()

exp_gap = df['TotalWorkingYears'] - df['YearsAtCompany']
role_gap = df['YearsAtCompany'] - df['YearsInCurrentRole']
# ASSERTION_START
assert ((exp_gap >= 0) & (role_gap >= 0)).all()
# ASSERTION_END
exp_gap_root = np.sqrt(exp_gap)
role_gap_root = np.sqrt(role_gap)

role_to_dept = {
    'Research Scientist': 'Research & Development',
    'Laboratory Technician': 'Research & Development',
    'Research Director': 'Research & Development',
    'Manufacturing Director': 'Research & Development',
    'Sales Executive': 'Sales',
    'Sales Representative': 'Sales',
    'Healthcare Representative': 'Sales',
}
mask_roles = df['JobRole'].isin(role_to_dept.keys())
expected_dept = df.loc[mask_roles, 'JobRole'].map(role_to_dept)
actual_dept = df.loc[mask_roles, 'Department']
dept_rates = df.groupby('Department')['AttritionFlag'].mean()

ot_rates = df.groupby('OverTime')['AttritionFlag'].mean()
rate_yes = float(ot_rates.get('Yes', np.nan))
rate_no = float(ot_rates.get('No', np.nan))
age_effect = df['AgeGroup'].map(age_group_rates).fillna(base_rate) - base_rate
department_effect = df['Department'].map(dept_rates).fillna(base_rate) - base_rate
slab_effect = df['SalarySlab'].map(slab_rates).fillna(base_rate) - base_rate

ot_effect = np.where(df['OverTime'] == 'Yes', rate_yes - base_rate, rate_no - base_rate)

std_log = float(salary_log.std(ddof=0))
if std_log > 0:
    salary_log_z = (salary_log - float(salary_log.mean())) / std_log
else:
    salary_log_z = pd.Series(0.0, index=df.index)

role_tenure_index = 1.0 / (1.0 + role_gap_root.replace(0, 0.0))
experience_index = exp_gap_root

w_age = 1.2
w_dept = 1.0
w_slab = 1.1
w_ot = 0.8
w_salary = 0.5
w_tenure = 0.7

z = (
        base_logit
        + w_age * age_effect.values
        + w_dept * department_effect.values
        + w_slab * slab_effect.values
        + w_ot * ot_effect
        + w_salary * (-salary_log_z.values)
        + w_tenure * (0.6 * role_tenure_index.values - 0.4 * experience_index.values)
)

risk = sigmoid(z)

out = pd.DataFrame({
    'EmpID': df['EmpID'],
    'AttritionRisk': risk
})

out['Rank'] = out['AttritionRisk'].rank(method='first', ascending=False).astype(int)
percentile = out['AttritionRisk'].rank(pct=True)
out['Priority'] = np.where(
    percentile >= 0.85, 'High', np.where(percentile >= 0.60, 'Medium', 'Low')
)
actions = {'High': 'Retention Outreach', 'Medium': 'Manager Check-in', 'Low': 'Monitor'}
out['Action'] = out['Priority'].map(actions)

scores_path = os.path.join(args.output, 'attrition_risk_scores.csv')
out.sort_values(['Priority', 'AttritionRisk'], ascending=[False, False]).to_csv(scores_path, index=False)

metrics = {
    'base_attrition_rate': float(base_rate),
    'overtime_attrition_rate': {'Yes': float(rate_yes), 'No': float(rate_no)},
    'age_group_attrition_rate': {str(k): float(v) for k, v in age_group_rates.to_dict().items()},
    'salary_slab_attrition_rate': {str(k): float(v) for k, v in slab_rates.to_dict().items()},
    'department_attrition_rate': {str(k): float(v) for k, v in dept_rates.to_dict().items()}
}
with open(os.path.join(args.output, 'calibration_metrics.json'), 'w') as f:
    json.dump(metrics, f, indent=2)
