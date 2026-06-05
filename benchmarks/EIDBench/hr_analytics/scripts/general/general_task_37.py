import argparse
import os

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

input_file = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_file)

# Derive fields used by downstream eligibility/compensation logic
agegroup_to_stage = {
    '18-25': 'early',
    '26-35': 'early',
    '36-45': 'mid',
    '46-55': 'senior',
    '55+': 'late'
}
df['CareerStage'] = df['AgeGroup'].map(agegroup_to_stage).fillna('unknown')
# Tenure relationship checks before computing ratios and derived features
# ASSERTION_START
yac = df['YearsAtCompany']
yicr = df['YearsInCurrentRole']
yslp = df['YearsSinceLastPromotion']
assert (yac >= 0).all()
assert (yicr >= 0).all()
assert (yslp >= 0).all()
assert (yicr <= yac).all()
assert (yslp <= yac).all()
mask_yac_eq_0 = yac == 0
assert (df.loc[mask_yac_eq_0, 'YearsInCurrentRole'] == 0).all()
assert (df.loc[mask_yac_eq_0, 'YearsSinceLastPromotion'] == 0).all()
# ASSERTION_END
# Ratios and derived tenure features
ratio_in_role = df['YearsInCurrentRole'] / df['YearsAtCompany']
ratio_in_role = ratio_in_role.replace([np.inf, -np.inf], np.nan).fillna(0.0)
stagnation_years = df['YearsAtCompany'] - df['YearsSinceLastPromotion']
sqrt_stagnation = np.sqrt(stagnation_years.clip(lower=0))

# Department and JobRole alignment checks before budget multipliers
# Budget multipliers by department
budget_multipliers = {
    'Sales': 1.00,
    'Research & Development': 1.05,
    'Human Resources': 0.95
}
df['BudgetMultiplier'] = df['Department'].map(budget_multipliers).fillna(1.00)

# Salary slab alignment and medians before compa ratios and caps
slab_order = ['Upto 5k', '5k-10k', '10k-15k', '15k+']
slab_bounds = {
    'Upto 5k': (0, 5000),  # (0, 5000]
    '5k-10k': (5000, 10000),  # (5000, 10000]
    '10k-15k': (10000, 15000),  # (10000, 15000]
    '15k+': (15000, np.inf)  # (15000, inf)
}
slab_caps = {
    'Upto 5k': 0.15,
    '5k-10k': 0.12,
    '10k-15k': 0.10,
    '15k+': 0.08
}

slab_medians = df.groupby('SalarySlab')['MonthlyIncome'].median()
# ASSERTION_START
s = df['SalarySlab']
mi = df['MonthlyIncome']
valid_slab = (
        ((s == 'Upto 5k') & (mi > 0) & (mi <= 5000)) |
        ((s == '5k-10k') & (mi > 5000) & (mi <= 10000)) |
        ((s == '10k-15k') & (mi > 10000) & (mi <= 15000)) |
        ((s == '15k+') & (mi > 15000))
)
assert valid_slab.all()
# ASSERTION_END
# Compa-ratio relative to slab median
df['SlabMedian'] = df['SalarySlab'].map(slab_medians.to_dict())
df['CompaRatio'] = (df['MonthlyIncome'] / df['SlabMedian']).replace([np.inf, -np.inf], np.nan).fillna(1.0)

# Base raise by performance
base_raise = np.where(df['PerformanceRating'] >= 4, 0.08, 0.03)
# Adjust for stagnation and time in role; diminish if already above slab median
stagnation_adj = 1.0 + 0.02 * sqrt_stagnation.clip(upper=5)
role_time_adj = 1.0 + 0.03 * ratio_in_role.clip(upper=1)
market_adj = 1.0 + 0.02 * (1 - df['CompaRatio'].clip(upper=1))
budget_adj = df['BudgetMultiplier']

recommended_raise = base_raise * stagnation_adj * role_time_adj * market_adj * budget_adj

# Cap by slab policy
cap_series = df['SalarySlab'].map(slab_caps)
recommended_raise = np.minimum(recommended_raise, cap_series)
recommended_raise = recommended_raise.clip(lower=0.0)

new_income = (df['MonthlyIncome'] * (1.0 + recommended_raise)).round(2)

# Promotion eligibility rules using career stage thresholds
required_years_by_stage = {
    'early': 2,
    'mid': 2,
    'senior': 1,
    'late': 1
}
required_years = df['CareerStage'].map(required_years_by_stage).fillna(2)

eligible_promo = (
        (df['PerformanceRating'] >= 4) &
        (df['YearsInCurrentRole'] >= required_years) &
        (df['YearsSinceLastPromotion'] >= 1) &
        (df['JobLevel'] < 5) &
        (df['Attrition'].str.upper() == 'NO')
)

# Output datasets for downstream engine
comp_out = df[['EmpID', 'EmployeeNumber', 'Department', 'JobRole', 'SalarySlab', 'MonthlyIncome']].copy()
comp_out['RecommendedRaisePct'] = recommended_raise.round(4)
comp_out['NewMonthlyIncome'] = new_income
comp_out['CompaRatio'] = df['CompaRatio'].round(4)

promo_out = df[
    ['EmpID', 'EmployeeNumber', 'Department', 'JobRole', 'JobLevel', 'PerformanceRating', 'YearsInCurrentRole',
     'YearsSinceLastPromotion', 'CareerStage']].copy()
promo_out['EligibleForPromotion'] = eligible_promo

comp_out.to_csv(os.path.join(args.output, 'compensation_recommendations.csv'), index=False)
promo_out.to_csv(os.path.join(args.output, 'promotion_eligibility.csv'), index=False)

# A filtered pre-validated subset that meets eligibility or high performers for downstream engine
downstream_feed = df.loc[
    (eligible_promo) | (df['PerformanceRating'] >= 4), ['EmpID', 'EmployeeNumber', 'Department', 'JobRole', 'JobLevel',
                                                        'PerformanceRating', 'MonthlyIncome', 'SalarySlab',
                                                        'CareerStage']].copy()
downstream_feed['RecommendedRaisePct'] = recommended_raise.round(4)
downstream_feed['NewMonthlyIncome'] = new_income

downstream_feed.to_csv(os.path.join(args.output, 'prevalidated_feed.csv'), index=False)
