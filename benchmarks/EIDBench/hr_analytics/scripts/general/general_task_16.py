import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_csv)

    # Ensure numeric dtypes where needed
    numeric_cols = [
        'Age', 'MonthlyIncome', 'YearsAtCompany', 'TotalWorkingYears',
        'YearsInCurrentRole', 'YearsSinceLastPromotion', 'YearsWithCurrManager',
        'WorkLifeBalance', 'JobSatisfaction', 'EnvironmentSatisfaction'
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Mappings used in downstream logic
    salary_slab_bounds = {
        'Upto 5k': (0, 5000),
        '5k-10k': (5001, 10000),
        '10k-15k': (10001, 15000),
        '15k+': (15001, np.inf),
    }
    salary_slab_ordinal = {'Upto 5k': 1, '5k-10k': 2, '10k-15k': 3, '15k+': 4}

    age_group_bounds = {
        '18-25': (18, 25),
        '26-35': (26, 35),
        '36-45': (36, 45),
        '46-55': (46, 55),
        '55+': (55, np.inf),
    }
    age_group_ordinal = {'18-25': 1, '26-35': 2, '36-45': 3, '46-55': 4, '55+': 5}

    def age_to_group(age_val):
        if pd.isna(age_val):
            return np.nan
        for k, (low, high) in age_group_bounds.items():
            if k == '55+':
                if age_val >= 55:
                    return '55+'
            else:
                if low <= age_val <= high:
                    return k
        return np.nan

    # Guard before using Age in normalization and downstream risk features
    # ASSERTION_START
    assert (df['Age'].isna() | (df['Age'] >= 18)).all()
    # ASSERTION_END
    # Prepare age group ordinal and cross features
    df['DerivedAgeGroup'] = df['Age'].apply(age_to_group)
    # ASSERTION_START
    valid_age_groups = set(age_group_ordinal.keys())
    assert df['AgeGroup'].dropna().isin(valid_age_groups).all()
    # ASSERTION_END
    df['AgeGroupOrd'] = df['AgeGroup'].map(age_group_ordinal)
    df['AgeNorm'] = (df['Age'] - 18) / (70 - 18)

    # Compensation features rely on slab ranges being consistent with MonthlyIncome
    # ASSERTION_START
    def _row_income_in_slab(r):
        if pd.isna(r['MonthlyIncome']):
            return True

        slab = r['SalarySlab']

        # Define continuous boundaries to correctly handle float incomes
        # and avoid failures in gaps between integer-defined ranges.
        continuous_salary_bounds = {
            'Upto 5k': (0, 5000),
            '5k-10k': (5000, 10000),
            '10k-15k': (10000, 15000),
            '15k+': (15000, np.inf),
        }

        if slab not in continuous_salary_bounds:
            return False

        lo, hi = continuous_salary_bounds[slab]
        income = r['MonthlyIncome']

        # Use [low, high] for the first bin and (low, high] for others.
        if slab == 'Upto 5k':
            return lo <= income <= hi
        else:
            return lo < income <= hi

    assert df.apply(_row_income_in_slab, axis=1).all()
    # ASSERTION_END
    # Use slab for calibration/imputation and risk shaping; requires strong monotonic relationship
    df['SlabOrd'] = df['SalarySlab'].map(salary_slab_ordinal)
    # Impute MonthlyIncome from slab medians if needed (future-proof); used in downstream scoring
    slab_median_income = df.groupby('SalarySlab')['MonthlyIncome'].transform('median')
    df['MonthlyIncomeFilled'] = df['MonthlyIncome'].fillna(slab_median_income)

    # Rank within slab to capture relative pay position independent of slab width
    df['IncomeRankInSlab'] = df.groupby('SalarySlab')['MonthlyIncomeFilled'].rank(pct=True)

    # Tenure-related constraints before computing ratios
    yac = df['YearsAtCompany']
    total = df['TotalWorkingYears']
    role = df['YearsInCurrentRole']
    promo = df['YearsSinceLastPromotion']
    mgr = df['YearsWithCurrManager'].fillna(0)
    # Safe ratios for tenure dynamics (avoid divide-by-zero with YearsAtCompany==0)
    yac_nonzero = yac.replace(0, np.nan)
    df['RoleTenureRatio'] = (role / yac_nonzero).clip(lower=0, upper=1).fillna(0)
    df['MgrTenureRatio'] = (mgr / yac_nonzero).clip(lower=0, upper=1).fillna(0)
    df['SincePromoRatio'] = (promo / yac_nonzero).clip(lower=0, upper=1).fillna(0)

    # Additional features
    df['OverTimeInd'] = (df['OverTime'] == 'Yes').astype(int)
    # Normalize satisfaction scores to [0,1] where higher is better
    for col in ['WorkLifeBalance', 'JobSatisfaction', 'EnvironmentSatisfaction']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['WLBScore'] = ((df['WorkLifeBalance'] - 1) / 3).clip(0, 1)
    df['JobSatScore'] = ((df['JobSatisfaction'] - 1) / 3).clip(0, 1)
    df['EnvSatScore'] = ((df['EnvironmentSatisfaction'] - 1) / 3).clip(0, 1)

    # Age-group risk baseline (ordered)
    age_group_risk_lookup = {
        1: 0.65,  # 18-25
        2: 0.55,  # 26-35
        3: 0.45,  # 36-45
        4: 0.50,  # 46-55
        5: 0.60,  # 55+
    }
    df['AgeGroupRisk'] = df['AgeGroupOrd'].map(age_group_risk_lookup).fillna(0.5)

    # Compensation-related risk: lower slab and lower rank within slab => higher risk
    df['SlabRiskComponent'] = (5 - df['SlabOrd']) / 4.0  # 1.0 for lowest slab -> 0.25 for highest
    df['WithinSlabUnderpay'] = 1.0 - df['IncomeRankInSlab']  # 1.0 = bottom of slab

    # Combine features into a risk score using a logistic transform
    # Weights reflect domain heuristics
    w = {
        'bias': -1.0,
        'overtime': 1.2,
        'wlb': -1.0,
        'jobsat': -0.8,
        'envsat': -0.5,
        'role_ratio': 0.6,
        'mgr_ratio': 0.4,
        'promo_ratio': 0.7,
        'age_group': 0.5,
        'slab_ord': 0.8,
        'within_slab': 0.6,
    }

    linear = (
            w['bias']
            + w['overtime'] * df['OverTimeInd']
            + w['wlb'] * df['WLBScore']
            + w['jobsat'] * df['JobSatScore']
            + w['envsat'] * df['EnvSatScore']
            + w['role_ratio'] * df['RoleTenureRatio']
            + w['mgr_ratio'] * df['MgrTenureRatio']
            + w['promo_ratio'] * df['SincePromoRatio']
            + w['age_group'] * df['AgeGroupRisk']
            + w['slab_ord'] * df['SlabRiskComponent']
            + w['within_slab'] * df['WithinSlabUnderpay']
    )

    df['AttritionRiskScore'] = 1.0 / (1.0 + np.exp(-linear))

    # Tiering for prioritization
    bins = [0.0, 0.35, 0.60, 1.0]
    labels = ['Low', 'Medium', 'High']
    df['RiskTier'] = pd.cut(df['AttritionRiskScore'], bins=bins, labels=labels, include_lowest=True, right=True)

    # Output final scores
    out_cols = [
        'EmpID', 'Department', 'JobRole', 'Age', 'AgeGroup', 'MonthlyIncome', 'SalarySlab',
        'YearsAtCompany', 'OverTime', 'WorkLifeBalance', 'JobSatisfaction', 'EnvironmentSatisfaction',
        'AttritionRiskScore', 'RiskTier'
    ]
    present_out_cols = [c for c in out_cols if c in df.columns]
    result_df = df[present_out_cols + ['SlabRiskComponent', 'WithinSlabUnderpay', 'RoleTenureRatio', 'MgrTenureRatio',
                                       'SincePromoRatio']]

    output_csv = os.path.join(args.output, 'attrition_risk_scores.csv')
    result_df.to_csv(output_csv, index=False)

    if __name__ == '__main__':
        main()
