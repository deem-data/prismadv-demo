import argparse
import os

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_csv = os.path.join(args.input, 'new_data.csv')
os.makedirs(args.output, exist_ok=True)

df = pd.read_csv(input_csv)

# ASSERTION_START
m = df['EmpID'].notna()
pattern_ok = df.loc[m, 'EmpID'].str.match(r'^RM\d{3,4}$', na=False)
non_empty = (df.loc[m, 'EmpID'].str.len() > 0).all()
assert pattern_ok.all() and df['EmpID'].is_unique and non_empty
# ASSERTION_END

df = df.set_index('EmpID', drop=False)

# ASSERTION_START
allowed_levels = {1, 2, 3, 4, 5}
level_ok = df['JobLevel'].isin(list(allowed_levels)).all()
share_l12 = ((df['JobLevel'] <= 2).sum()) / float(len(df))
share_l5 = ((df['JobLevel'] == 5).sum()) / float(len(df))
assert level_ok and (share_l12 >= 0.70) and (share_l5 <= 0.05)
# ASSERTION_END

df['BusinessTravel'] = df['BusinessTravel'].replace({'TravelRarely': 'Travel_Rarely'})

# ASSERTION_START
allowed_bt = {'Non-Travel', 'Travel_Rarely', 'Travel_Frequently'}
observed_bt = set(df['BusinessTravel'].dropna().unique().tolist())
subset_ok = observed_bt.issubset(allowed_bt)
share_rarely = (df['BusinessTravel'] == 'Travel_Rarely').sum() / float(len(df))
share_freq = (df['BusinessTravel'] == 'Travel_Frequently').sum() / float(len(df))
assert subset_ok and (0.60 <= share_rarely <= 0.80) and (0.15 <= share_freq <= 0.25)
# ASSERTION_END

# ASSERTION_START
mi = df['MonthlyIncome']
sl = df['SalarySlab']
mask_u5 = sl == 'Upto 5k'
mask_5_10 = sl == '5k-10k'
mask_10_15 = sl == '10k-15k'
mask_15p = sl == '15k+'
cond_u5 = (mi[mask_u5] < 5000).all()
cond_5_10 = ((mi[mask_5_10] >= 5000) & (mi[mask_5_10] < 10000)).all()
cond_10_15 = ((mi[mask_10_15] >= 10000) & (mi[mask_10_15] < 15000)).all()
cond_15p = (mi[mask_15p] >= 15000).all()
assert cond_u5 and cond_5_10 and cond_10_15 and cond_15p
# ASSERTION_END

# ASSERTION_START
pr4 = df['PerformanceRating'] == 4
pr3 = df['PerformanceRating'] == 3
cond_pr4 = (df.loc[pr4, 'PercentSalaryHike'] >= 12).all()
cond_pr3 = (df.loc[pr3, 'PercentSalaryHike'] <= 20).all()
means = df.groupby('PerformanceRating')['PercentSalaryHike'].mean()
has_both = (3 in means.index) and (4 in means.index)
cond_gap = has_both and ((means[4] - means[3]) >= 1.5)
assert cond_pr4 and cond_pr3 and cond_gap
# ASSERTION_END

# ASSERTION_START
mask_yalp = df['YearsAtCompany'].notna() & df['YearsSinceLastPromotion'].notna()
mask_yacr = df['YearsAtCompany'].notna() & df['YearsInCurrentRole'].notna()
mask_yacm = df['YearsAtCompany'].notna() & df['YearsWithCurrManager'].notna()
mask_twy = df['YearsAtCompany'].notna() & df['TotalWorkingYears'].notna()
cond1 = (df.loc[mask_yalp, 'YearsSinceLastPromotion'] <= df.loc[mask_yalp, 'YearsAtCompany']).all()
cond2 = (df.loc[mask_yacr, 'YearsInCurrentRole'] <= df.loc[mask_yacr, 'YearsAtCompany']).all()
cond3 = (df.loc[mask_yacm, 'YearsWithCurrManager'] <= df.loc[mask_yacm, 'YearsAtCompany']).all()
cond4 = (df.loc[mask_twy, 'YearsAtCompany'] <= df.loc[mask_twy, 'TotalWorkingYears']).all()
mask_zero = df['YearsAtCompany'] == 0
zero_ok_a = (df.loc[mask_zero, 'YearsSinceLastPromotion'] == 0).all()
zero_ok_b = (df.loc[mask_zero, 'YearsInCurrentRole'] == 0).all()
assert cond1 and cond2 and cond3 and cond4 and zero_ok_a and zero_ok_b
# ASSERTION_END

# Rating gap used to differentiate merit for high performers
rating_means = df.groupby('PerformanceRating')['PercentSalaryHike'].mean()
rating_gap_pct = (rating_means[4] - rating_means[3]) if (3 in rating_means.index and 4 in rating_means.index) else 1.5

# Compute components for merit planning
slab_base_rate_map = {
    'Upto 5k': 0.060,
    '5k-10k': 0.050,
    '10k-15k': 0.040,
    '15k+': 0.030,
}
df['slab_base_rate'] = df['SalarySlab'].map(slab_base_rate_map)

# Guard before use of slab_base_rate
# ASSERTION_START
assert df['slab_base_rate'].notna().all()
# ASSERTION_END

travel_adj_map = {
    'Non-Travel': 0.000,
    'Travel_Rarely': 0.002,
    'Travel_Frequently': 0.005,
}
df['travel_adj'] = df['BusinessTravel'].map(travel_adj_map)

# Use AgeGroup cohort weighting after validation
age_cohort_adj_map = {
    '18-25': 0.002,
    '26-35': 0.001,
    '36-45': 0.000,
    '46-55': 0.000,
    '55+': 0.000,
}
df['age_adj'] = df['AgeGroup'].map(age_cohort_adj_map)

# Guard before use of age_adj mapping
# ASSERTION_START
assert df['age_adj'].notna().all()
# ASSERTION_END

# Rating-based component leans on observed gap between PR=4 and PR=3
base_rating_component = np.where(df['PerformanceRating'] == 4, 0.030 + rating_gap_pct / 100.0, 0.030)

# Tenure-based smoothing; safe division ensured by earlier zero-constraints
yac = df['YearsAtCompany']
yicr = df['YearsInCurrentRole']
ratio = np.where(yac > 0, (yicr / yac).clip(upper=1.0), 0.0)

df['MeritIncreasePct'] = (
        df['slab_base_rate'] +
        base_rating_component +
        df['travel_adj'] +
        df['age_adj'] +
        (1 - ratio) * 0.010
)

# Cap to reasonable quarterly range [0.0, 0.20]
df['MeritIncreasePct'] = df['MeritIncreasePct'].clip(lower=0.0, upper=0.20)

df['MeritIncreaseAmt'] = (df['MonthlyIncome'] * df['MeritIncreasePct']).round(2)

# Promotion eligibility rules using validated fields
eligible = (
        (df['PerformanceRating'] == 4) &
        (df['JobLevel'] < 5) &
        (df['YearsInCurrentRole'] >= 1) &
        (df['YearsSinceLastPromotion'] >= 1) &
        (df['TotalWorkingYears'] >= 2)
)
df['PromotionEligible'] = eligible

# Department-level aggregation for planning
dept_summary = (
    df.groupby('Department')
    .agg(
        Headcount=('EmpID', 'count'),
        MeritPool=('MeritIncreaseAmt', 'sum'),
        AvgMeritPct=('MeritIncreasePct', 'mean'),
        Promotions=('PromotionEligible', 'sum')
    )
    .reset_index()
)

# Per-employee plan
plan_cols = [
    'EmpID', 'Department', 'JobLevel', 'MonthlyIncome', 'SalarySlab', 'PerformanceRating',
    'PercentSalaryHike', 'BusinessTravel', 'AgeGroup', 'YearsAtCompany', 'YearsInCurrentRole',
    'MeritIncreasePct', 'MeritIncreaseAmt', 'PromotionEligible'
]
employee_plan = df[plan_cols].copy()

employee_plan.to_csv(os.path.join(args.output, 'employee_comp_plan.csv'), index=False)
dept_summary.to_csv(os.path.join(args.output, 'department_comp_summary.csv'), index=False)
