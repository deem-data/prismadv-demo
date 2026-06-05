import argparse
import os

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_path = os.path.join(args.input, 'new_data.csv')
os.makedirs(args.output, exist_ok=True)

df = pd.read_csv(input_path)

# Merit cycle computations

# ASSERTION_START
pr = df['PerformanceRating']
hike = df['PercentSalaryHike']
cond_allowed = pr.isin([3, 4])
cond_range = (hike >= 10) & (hike <= 25)
cond_int = (hike % 1 == 0)
mean_3 = hike[pr == 3].mean()
mean_4 = hike[pr == 4].mean()
share_pr3 = (pr == 3).mean()
assert cond_allowed.all() and cond_range.all() and cond_int.all() and not np.isnan(mean_3) and not np.isnan(
    mean_4) and (mean_4 >= mean_3) and (share_pr3 >= 0.80)
# ASSERTION_END

rating_bonus_map = {3: 0.0, 4: 2.0}
df['rating_bonus'] = df['PerformanceRating'].map(rating_bonus_map)
df['recommended_percent'] = df['PercentSalaryHike'] + df['rating_bonus']

# ASSERTION_START
mi = df['MonthlyIncome']
slab = df['SalarySlab']
allowed_slabs = ['Upto 5k', '5k-10k', '10k-15k', '15k+']
expected_slab = pd.cut(mi, bins=[0, 5000, 10000, 15000, np.inf], labels=allowed_slabs, right=True, include_lowest=False)
share_low = (slab == 'Upto 5k').mean()
assert (mi > 0).all() and slab.isin(allowed_slabs).all() and (slab == expected_slab.astype(str)).all() and (
            share_low >= 0.45)
# ASSERTION_END

cap_map = {'Upto 5k': 20.0, '5k-10k': 15.0, '10k-15k': 12.0, '15k+': 10.0}
df['cap_percent'] = df['SalarySlab'].map(cap_map)
df['approved_percent'] = np.minimum(df['recommended_percent'], df['cap_percent'])
df['approved_amount'] = df['MonthlyIncome'] * (df['approved_percent'] / 100.0)

# Department budgets, relies on Department/JobRole consistency
# ASSERTION_START
dep = df['Department']
role = df['JobRole']
allowed_deps = {'Sales', 'Research & Development', 'Human Resources'}
mask_sales = role.isin(['Sales Executive', 'Sales Representative'])
mask_hr = role == 'Human Resources'
mask_rnd = role.isin(['Research Scientist', 'Laboratory Technician', 'Research Director', 'Manufacturing Director',
                      'Healthcare Representative'])
cond_dep_allowed = dep.isin(list(allowed_deps))
cond_sales = (dep[mask_sales] == 'Sales').all() if mask_sales.any() else True
cond_hr = (dep[mask_hr] == 'Human Resources').all() if mask_hr.any() else True
cond_rnd = (dep[mask_rnd] == 'Research & Development').all() if mask_rnd.any() else True
assert cond_dep_allowed.all() and cond_sales and cond_hr and cond_rnd
# ASSERTION_END

dept_budget = df.groupby('Department', as_index=False).agg(
    Headcount=('EmpID', 'count'),
    MeritBudget=('approved_amount', 'sum')
)

department_budget_path = os.path.join(args.output, 'dept_budgets.csv')
dept_budget.to_csv(department_budget_path, index=False)

# Attrition risk scoring

# ASSERTION_START
age_vals = pd.to_numeric(df['Age'], errors='coerce')
age_grp = df['AgeGroup']
allowed_age_grps = ['18-25', '26-35', '36-45', '46-55', '55+']
age_in_range = age_vals.between(18, 60, inclusive='both')
derived_age_grp = pd.cut(age_vals, bins=[17, 25, 35, 45, 55, np.inf], labels=allowed_age_grps, right=True)
mask_valid = age_vals.notna() & age_grp.notna()
cond_match = (age_grp[mask_valid].astype(str) == derived_age_grp[mask_valid].astype(str)).all()
assert age_in_range.all() and age_grp.isin(allowed_age_grps).all() and cond_match
# ASSERTION_END

age_weight_map = {
    '18-25': 0.5,
    '26-35': 0.2,
    '36-45': 0.0,
    '46-55': -0.2,
    '55+': -0.3
}
df['age_weight'] = df['AgeGroup'].map(age_weight_map)

yac = pd.to_numeric(df['YearsAtCompany'], errors='coerce')
ysp = pd.to_numeric(df['YearsSinceLastPromotion'], errors='coerce')
# ASSERTION_START
why = pd.to_numeric(df['TotalWorkingYears'], errors='coerce')
ycm = pd.to_numeric(df['YearsWithCurrManager'], errors='coerce')
yir = pd.to_numeric(df['YearsInCurrentRole'], errors='coerce')
cond_nonneg = (
        (yac[yac.notna()] >= 0).all() and
        (why[why.notna()] >= 0).all() and
        (ysp[ysp.notna()] >= 0).all() and
        (ycm[ycm.notna()] >= 0).all() and
        (yir[yir.notna()] >= 0).all()
)
mask_yac_why = yac.notna() & why.notna()
mask_yac_ysp = yac.notna() & ysp.notna()
mask_yac_ycm = yac.notna() & ycm.notna()
mask_yac_yir = yac.notna() & yir.notna()
cond_leq1 = (yac[mask_yac_why] <= why[mask_yac_why]).all()
cond_leq2 = (ysp[mask_yac_ysp] <= yac[mask_yac_ysp]).all()
cond_leq3 = (ycm[mask_yac_ycm] <= yac[mask_yac_ycm]).all()
cond_leq4 = (yir[mask_yac_yir] <= yac[mask_yac_yir]).all()
mask_zero = yac.notna() & ysp.notna() & (yac == 0)
cond_zero_imp = (ysp[mask_zero] == 0).all() if mask_zero.any() else True
assert cond_nonneg and cond_leq1 and cond_leq2 and cond_leq3 and cond_leq4 and cond_zero_imp
# ASSERTION_END

# Features for risk
safe_yac = yac.fillna(0)
safe_ysp = ysp.fillna(0)
den = safe_yac.replace(0, np.nan)
tenure_ratio = (safe_ysp / den).fillna(0.0)

ot_flag = (df['OverTime'] == 'Yes').astype(float)
job_sat_map = {1: 0.4, 2: 0.2, 3: -0.1, 4: -0.2}
wlb_map = {1: 0.5, 2: 0.2, 3: 0.0, 4: -0.1}
job_penalty = df['JobSatisfaction'].map(job_sat_map).astype(float)
wlb_penalty = df['WorkLifeBalance'].map(wlb_map).astype(float)

max_dist = max(1.0, float(df['DistanceFromHome'].max()))
dist_norm = df['DistanceFromHome'].astype(float) / max_dist

mgr_tenure = df['YearsWithCurrManager'].fillna(0).astype(float)
mgr_penalty = np.where(mgr_tenure < 1.0, 0.2, 0.0)

# ASSERTION_START
attr = df['Attrition']
cond_notnull = attr.notna().all()
cond_values = attr.isin(['Yes', 'No']).all()
share_no = (attr == 'No').mean()
assert cond_notnull and cond_values and (share_no >= 0.70)
# ASSERTION_END

yes_rate = (df['Attrition'] == 'Yes').mean()
intercept = float(np.log((yes_rate + 1e-6) / (1.0 - yes_rate + 1e-6)))

raw_score = (
        intercept
        + 1.2 * ot_flag
        + 0.8 * job_penalty
        + 0.7 * wlb_penalty
        + 0.6 * df['age_weight'].astype(float)
        + 0.7 * tenure_ratio.astype(float)
        + 0.5 * dist_norm.astype(float)
        + 0.3 * mgr_penalty.astype(float)
)

risk_score = 1.0 / (1.0 + np.exp(-raw_score))
df['AttritionRiskScore'] = risk_score
bins = [0.0, 0.4, 0.6, 1.0]
labels = ['Low', 'Medium', 'High']
df['RiskTier'] = pd.cut(df['AttritionRiskScore'], bins=bins, labels=labels, include_lowest=True, right=False)

# Outputs
risk_cols = ['EmpID', 'Department', 'JobRole', 'AgeGroup', 'AttritionRiskScore', 'RiskTier']
risk_out = os.path.join(args.output, 'risk_scores.csv')
df[risk_cols].to_csv(risk_out, index=False)

merit_cols = ['EmpID', 'MonthlyIncome', 'SalarySlab', 'PercentSalaryHike', 'PerformanceRating', 'rating_bonus',
              'cap_percent', 'approved_percent', 'approved_amount']
merit_out = os.path.join(args.output, 'merit_adjustments.csv')
df[merit_cols].to_csv(merit_out, index=False)
