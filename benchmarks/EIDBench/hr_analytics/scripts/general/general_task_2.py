import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_file = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_file)

    # Coerce numeric columns
    numeric_cols = [
        'MonthlyIncome', 'PercentSalaryHike', 'JobLevel', 'EmployeeNumber', 'EmployeeCount', 'StandardHours', 'Age',
        'YearsAtCompany', 'YearsInCurrentRole', 'YearsWithCurrManager', 'YearsSinceLastPromotion', 'TotalWorkingYears',
        'PerformanceRating'
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # ASSERTION_START
    # EmpID/EmployeeNumber checks before indexing and any dedup-sensitive aggregations
    m1 = df['EmpID'].notna()
    m2 = df['EmployeeNumber'].notna()
    uniq1 = df['EmpID'].is_unique
    uniq2 = df['EmployeeNumber'].is_unique
    pos = (df['EmployeeNumber'] > 0)
    map1 = df.groupby('EmpID')['EmployeeNumber'].nunique().eq(1).all()
    map2 = df.groupby('EmployeeNumber')['EmpID'].nunique().eq(1).all()
    assert m1.all() and m2.all() and uniq1 and uniq2 and pos.all() and map1 and map2
    # ASSERTION_END

    # Use EmpID as stable index for downstream logic that assumes 1:1 mapping
    df = df.set_index('EmpID', drop=False)

    # ASSERTION_START
    # Constant columns used for FTE and headcount math
    cond_const = df['StandardHours'].eq(80) & df['EmployeeCount'].eq(1) & df['Over18'].eq('Y')
    assert cond_const.all()
    # ASSERTION_END

    # ASSERTION_START
    # Performance and salary hike used to project next-quarter comp
    pr_valid = df['PerformanceRating'].isin([3, 4])
    psh_nonnull = df['PercentSalaryHike'].notna()
    psh_range = df['PercentSalaryHike'].between(10, 25, inclusive='both')
    means = df.groupby('PerformanceRating')['PercentSalaryHike'].mean()
    higher_for_4 = (3 in means.index and 4 in means.index and means.loc[4] > means.loc[3])
    assert pr_valid.all() and psh_nonnull.all() and psh_range.all() and higher_for_4
    # ASSERTION_END

    # ASSERTION_START
    # Age and AgeGroup used for benefits-rate assignment
    allowed_ag = {'18-25': (18, 25), '26-35': (26, 35), '36-45': (36, 45), '46-55': (46, 55), '55+': (55, np.inf)}
    ag_nonnull = df['AgeGroup'].notna()
    age_nonnull = df['Age'].notna()
    ag_in_set = df['AgeGroup'].isin(list(allowed_ag.keys()))
    age_in_range = df['Age'].between(18, 65, inclusive='both')
    mask_ag = age_nonnull & ag_nonnull
    lower = df.loc[mask_ag, 'AgeGroup'].map(lambda x: allowed_ag[x][0])
    upper = df.loc[mask_ag, 'AgeGroup'].map(lambda x: allowed_ag[x][1])
    bracket_ok = ((df.loc[mask_ag, 'Age'] >= lower) & (df.loc[mask_ag, 'Age'] <= upper)).all()
    assert age_nonnull.all() and ag_nonnull.all() and ag_in_set.all() and age_in_range.all() and bracket_ok
    # ASSERTION_END

    # ASSERTION_START
    # Salary slab and income used for slab premiums and comp projections
    slabs = df['SalarySlab']
    inc = df['MonthlyIncome']
    slab_nonnull = slabs.notna()
    inc_nonnull_pos = inc.notna() & (inc > 0)
    allowed_slabs = ['Upto 5k', '5k-10k', '10k-15k', '15k+']
    slab_allowed = slabs.isin(allowed_slabs)
    in_range = (
            ((slabs == 'Upto 5k') & inc.between(0, 5000, inclusive='both')) |
            ((slabs == '5k-10k') & inc.between(5001, 10000, inclusive='both')) |
            ((slabs == '10k-15k') & inc.between(10001, 15000, inclusive='both')) |
            ((slabs == '15k+') & (inc >= 15001))
    )
    assert slab_nonnull.all() and inc_nonnull_pos.all() and slab_allowed.all() and in_range.all()
    # ASSERTION_END

    df['BusinessTravel'] = df['BusinessTravel'].replace({'TravelRarely': 'Travel_Rarely'})

    # ASSERTION_START
    # BusinessTravel used to add travel premium into budgets
    bt_nonnull = df['BusinessTravel'].notna()
    bt_allowed = df['BusinessTravel'].isin(['Non-Travel', 'Travel_Rarely', 'Travel_Frequently'])
    assert bt_nonnull.all() and bt_allowed.all()
    # ASSERTION_END

    # ASSERTION_START
    # OverTime and Attrition used for overtime premium and attrition rate calc
    ot_nonnull = df['OverTime'].notna()
    ot_allowed = df['OverTime'].isin(['Yes', 'No'])
    at_nonnull = df['Attrition'].notna()
    at_allowed = df['Attrition'].isin(['Yes', 'No'])
    assert ot_nonnull.all() and ot_allowed.all() and at_nonnull.all() and at_allowed.all()
    # ASSERTION_END

    # ASSERTION_START
    # Tenure constraints before manager adjustment/tenure-based adjustments
    fields = ['YearsAtCompany', 'YearsInCurrentRole', 'YearsWithCurrManager', 'YearsSinceLastPromotion',
              'TotalWorkingYears']
    nonneg_ok = True
    for f in fields:
        nonneg_ok = nonneg_ok and ((df[f].isna()) | (df[f] >= 0)).all()
    mask_a = df['YearsAtCompany'].notna() & df['TotalWorkingYears'].notna()
    m1 = (df.loc[mask_a, 'YearsAtCompany'] <= df.loc[mask_a, 'TotalWorkingYears']).all()
    mask_b = df['YearsWithCurrManager'].notna() & df['YearsAtCompany'].notna()
    m2 = (df.loc[mask_b, 'YearsWithCurrManager'] <= df.loc[mask_b, 'YearsAtCompany']).all()
    mask_c = df['YearsInCurrentRole'].notna() & df['YearsAtCompany'].notna()
    m3 = (df.loc[mask_c, 'YearsInCurrentRole'] <= df.loc[mask_c, 'YearsAtCompany']).all()
    mask_d = df['YearsSinceLastPromotion'].notna() & df['YearsAtCompany'].notna()
    m4 = (df.loc[mask_d, 'YearsSinceLastPromotion'] <= df.loc[mask_d, 'YearsAtCompany']).all()
    mask_e = df['TotalWorkingYears'].notna() & df['Age'].notna()
    m5 = (df.loc[mask_e, 'TotalWorkingYears'] <= df.loc[mask_e, 'Age'] - 18).all()
    pct_nonnull_mgr = df['YearsWithCurrManager'].notna().mean()
    assert nonneg_ok and m1 and m2 and m3 and m4 and m5 and (pct_nonnull_mgr >= 0.95)
    # ASSERTION_END

    # Compensation modeling components
    benefits_rate_map = {'18-25': 0.25, '26-35': 0.28, '36-45': 0.30, '46-55': 0.33, '55+': 0.35}
    df['benefits_rate'] = df['AgeGroup'].map(benefits_rate_map).astype(float)

    travel_premium_map = {'Non-Travel': 0.00, 'Travel_Rarely': 0.02, 'Travel_Frequently': 0.05}
    df['travel_premium'] = df['BusinessTravel'].map(travel_premium_map).astype(float)

    overtime_premium_map = {'No': 0.0, 'Yes': 0.10}
    df['overtime_premium'] = df['OverTime'].map(overtime_premium_map).astype(float)

    slab_premium_map = {'Upto 5k': 0.00, '5k-10k': 0.02, '10k-15k': 0.04, '15k+': 0.06}
    df['slab_premium'] = df['SalarySlab'].map(slab_premium_map).astype(float)

    df['joblevel_adj'] = 0.005 * (df['JobLevel'] - 1).astype(float)

    df['manager_adj'] = np.where(df['YearsWithCurrManager'].fillna(0) < 1, 0.01, 0.0)

    df['fte'] = df['StandardHours'] / 80.0

    df['adj_income'] = df['MonthlyIncome'] * (1.0 + df['PercentSalaryHike'] / 100.0)

    df['monthly_comp_w_overheads'] = (
            df['adj_income'] * (
            1.0
            + df['benefits_rate']
            + df['travel_premium']
            + df['overtime_premium']
            + df['slab_premium']
            + df['joblevel_adj']
            + df['manager_adj']
    ) * df['fte']
    )

    df['quarterly_comp'] = df['monthly_comp_w_overheads'] * 3.0

    # Active employees budget only
    df['active_quarterly_comp'] = np.where(df['Attrition'] == 'No', df['quarterly_comp'], 0.0)

    # Group-level metrics
    grouped = df.groupby(['Department', 'JobRole'], as_index=False).agg(
        headcount=('EmployeeCount', 'sum'),
        attrition_count=('Attrition', lambda s: (s == 'Yes').sum()),
        quarterly_budget=('active_quarterly_comp', 'sum')
    )
    grouped['attrition_rate'] = grouped['attrition_count'] / grouped['headcount']

    out_path = os.path.join(args.output, 'dept_role_quarterly_planning.csv')
    grouped.to_csv(out_path, index=False)


if __name__ == '__main__':
    main()
