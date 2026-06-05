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

# Normalize BusinessTravel values used downstream
travel_map = {
    'TravelRarely': 'Travel_Rarely',
    'Travel_Rarely': 'Travel_Rarely',
    'Travel_Frequently': 'Travel_Frequently',
    'Non-Travel': 'Non-Travel'
}
df['BusinessTravel'] = df['BusinessTravel'].map(lambda x: travel_map.get(x, x))
# ASSERTION_START
allowed_travel = {'Non-Travel', 'Travel_Rarely', 'Travel_Frequently'}
bt = df['BusinessTravel']
assert bt.notna().all() and bt.isin(allowed_travel).all()
# ASSERTION_END
# ASSERTION_START
empnum = df['EmployeeNumber']
assert empnum.notna().all() and empnum.is_unique

# ASSERTION_END
df = df.set_index('EmployeeNumber', drop=False)
# ASSERTION_START
mi = df['MonthlyIncome']
slab = df['SalarySlab']

# Basic checks
slab_allowed = {'Upto 5k', '5k-10k', '10k-15k', '15k+'}
assert slab.isin(slab_allowed).all()
assert (mi >= 0).all()


# Check for consistency between income and slab
def get_slab_from_income(income):
    if income <= 5000:
        return 'Upto 5k'
    elif income <= 10000:
        return '5k-10k'
    elif income <= 15000:
        return '10k-15k'
    else:
        return '15k+'


expected_slab = mi.apply(get_slab_from_income)
assert (slab == expected_slab).all()
# ASSERTION_END
# ASSERTION_START
pr = df['PerformanceRating']
assert pr.isin([3, 4]).all()
# ASSERTION_END
# ASSERTION_START
yicr = df['YearsInCurrentRole']
ysp = df['YearsSinceLastPromotion']
assert (yicr >= 0).all() and (ysp >= 0).all()

# ASSERTION_END
# Merit guideline by performance
perf_guideline_pct = {3: 0.12, 4: 0.18}
df['perf_guideline_pct'] = df['PerformanceRating'].map(perf_guideline_pct)

# Cap by salary slab
slab_cap_pct = {'Upto 5k': 0.20, '5k-10k': 0.18, '10k-15k': 0.15, '15k+': 0.12}
df['slab_cap_pct'] = df['SalarySlab'].map(slab_cap_pct)

# Multipliers that depend on normalized categorical assumptions
df['age_weight'] = np.where(df['AgeGroup'] == '26-35', 1.02, 1.00)
travel_multiplier_map = {'Travel_Frequently': 1.01, 'Travel_Rarely': 1.00, 'Non-Travel': 1.00}
df['travel_multiplier'] = df['BusinessTravel'].map(travel_multiplier_map)

# Proposed merit percent and amount
base_merit_pct = np.minimum(df['perf_guideline_pct'], df['PercentSalaryHike'] / 100.0)
adjusted_merit_pct = base_merit_pct * df['age_weight'] * df['travel_multiplier']
df['proposed_merit_pct'] = np.minimum(adjusted_merit_pct, df['slab_cap_pct'])
df['proposed_merit_amount'] = (df['MonthlyIncome'] * df['proposed_merit_pct']).round(2)

# Promotion eligibility and impact
eligible = (
        (df['PerformanceRating'] == 4) &
        (df['YearsInCurrentRole'] >= 2) &
        (df['YearsSinceLastPromotion'] >= 1) &
        (df['JobLevel'] < 5)
)
df['promotion_eligible'] = eligible
promo_raise_pct_map = {1: 0.10, 2: 0.08, 3: 0.07, 4: 0.06, 5: 0.0}
df['promotion_raise_pct'] = df['JobLevel'].map(promo_raise_pct_map)
df.loc[~df['promotion_eligible'], 'promotion_raise_pct'] = 0.0
df['promotion_amount'] = (df['MonthlyIncome'] * df['promotion_raise_pct']).round(2)

# Supplemental pools that implicitly rely on cohort distribution assumptions
low_slab_mask = df['SalarySlab'].isin(['Upto 5k', '5k-10k'])
df['compression_pool_share'] = np.where(low_slab_mask, 0.003, 0.0)
df['compression_amount'] = (df['MonthlyIncome'] * df['compression_pool_share']).round(2)

age_26_35_mask = (df['AgeGroup'] == '26-35')
df['emerging_talent_supp_pct'] = np.where(age_26_35_mask, 0.005, 0.0)
df['emerging_talent_amount'] = (df['MonthlyIncome'] * df['emerging_talent_supp_pct']).round(2)

# Department-level budgets
agg = df.groupby('Department').agg(
    headcount=('EmpID', 'count'),
    base_pay=('MonthlyIncome', 'sum'),
    merit_pool=('proposed_merit_amount', 'sum'),
    promotion_pool=('promotion_amount', 'sum'),
    compression_pool=('compression_amount', 'sum'),
    emerging_talent_pool=('emerging_talent_amount', 'sum')
).reset_index()

agg['total_budget'] = (
            agg['merit_pool'] + agg['promotion_pool'] + agg['compression_pool'] + agg['emerging_talent_pool']).round(2)

# Output files
budgets_out = os.path.join(args.output, 'department_compensation_budgets.csv')
agg.to_csv(budgets_out, index=False)

details_cols = [
    'EmployeeNumber', 'EmpID', 'Department', 'MonthlyIncome', 'SalarySlab', 'PerformanceRating', 'PercentSalaryHike',
    'proposed_merit_pct', 'proposed_merit_amount', 'promotion_eligible', 'promotion_raise_pct', 'promotion_amount',
    'BusinessTravel', 'age_weight', 'travel_multiplier', 'compression_amount', 'emerging_talent_amount'
]
emp_out = os.path.join(args.output, 'employee_compensation_proposals.csv')
df[details_cols].to_csv(emp_out, index=False)
