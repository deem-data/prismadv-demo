import argparse
import os
import json
import re
import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_file = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_file)

    # Normalize dtypes used downstream
    numeric_cols = [
        'Age', 'MonthlyIncome', 'YearsAtCompany', 'YearsSinceLastPromotion', 'YearsInCurrentRole',
        'TotalWorkingYears', 'YearsWithCurrManager', 'WorkLifeBalance', 'JobSatisfaction',
        'DistanceFromHome'
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # ASSERTION_START
    assert df['EmpID'].notna().all()
    assert df['EmpID'].is_unique
    empid_ok = df['EmpID'].map(lambda x: isinstance(x, str) and re.fullmatch(r'^[A-Za-z0-9]+$', x) is not None)
    assert empid_ok.all()
    # ASSERTION_END

    df = df.set_index('EmpID', drop=False)

    # Age and AgeGroup checks before age-derived features
    # ASSERTION_START
    allowed_age_groups = {'18-25', '26-35', '36-45', '46-55', '55+'}
    assert df['Age'].notna().all()
    assert ((df['Age'] >= 18) & (df['Age'] <= 65)).all()
    assert df['AgeGroup'].isin(allowed_age_groups).all()
    m_18_25 = df['AgeGroup'] == '18-25'
    m_26_35 = df['AgeGroup'] == '26-35'
    m_36_45 = df['AgeGroup'] == '36-45'
    m_46_55 = df['AgeGroup'] == '46-55'
    m_55p = df['AgeGroup'] == '55+'
    c1 = ((df.loc[m_18_25, 'Age'] >= 18) & (df.loc[m_18_25, 'Age'] <= 25)).all()
    c2 = ((df.loc[m_26_35, 'Age'] >= 26) & (df.loc[m_26_35, 'Age'] <= 35)).all()
    c3 = ((df.loc[m_36_45, 'Age'] >= 36) & (df.loc[m_36_45, 'Age'] <= 45)).all()
    c4 = ((df.loc[m_46_55, 'Age'] >= 46) & (df.loc[m_46_55, 'Age'] <= 55)).all()
    c5 = (df.loc[m_55p, 'Age'] >= 55).all()
    share_26_35 = (df['AgeGroup'] == '26-35').mean()
    assert c1 and c2 and c3 and c4 and c5 and (share_26_35 >= 0.35)
    # ASSERTION_END

    # Income/Salaries checks before income-derived features
    # ASSERTION_START
    allowed_slabs = {'Upto 5k', '5k-10k', '10k-15k', '15k+'}
    assert df['SalarySlab'].isin(allowed_slabs).all()
    assert df['MonthlyIncome'].notna().all()
    assert (df['MonthlyIncome'] > 0).all()
    m_upto5k = df['SalarySlab'] == 'Upto 5k'
    m_5_10 = df['SalarySlab'] == '5k-10k'
    m_10_15 = df['SalarySlab'] == '10k-15k'
    m_15p = df['SalarySlab'] == '15k+'
    ck1 = (df.loc[m_upto5k, 'MonthlyIncome'] <= 5000).all()
    ck2 = ((df.loc[m_5_10, 'MonthlyIncome'] > 5000) & (df.loc[m_5_10, 'MonthlyIncome'] <= 10000)).all()
    ck3 = ((df.loc[m_10_15, 'MonthlyIncome'] > 10000) & (df.loc[m_10_15, 'MonthlyIncome'] <= 15000)).all()
    ck4 = (df.loc[m_15p, 'MonthlyIncome'] > 15000).all()
    assert ck1 and ck2 and ck3 and ck4
    share_upto5k = m_upto5k.mean()
    assert share_upto5k >= 0.45
    # ASSERTION_END

    # Tenure and manager fields checks before tenure-derived ratios
    # ASSERTION_START
    nonneg_int_cols = ['YearsAtCompany', 'YearsSinceLastPromotion', 'YearsInCurrentRole', 'TotalWorkingYears']
    ok = True
    for c in nonneg_int_cols:
        s = df[c].dropna()
        if not ((s >= 0).all() and ((s % 1) == 0).all()):
            ok = False
            break
    assert ok
    assert df['YearsWithCurrManager'].notna().mean() >= 0.95
    mask_mgr = df['YearsWithCurrManager'].notna() & df['YearsAtCompany'].notna()
    mask_role = df['YearsInCurrentRole'].notna() & df['YearsAtCompany'].notna()
    mask_prom = df['YearsSinceLastPromotion'].notna() & df['YearsAtCompany'].notna()
    mask_total = df['YearsAtCompany'].notna() & df['TotalWorkingYears'].notna()
    assert (df.loc[mask_mgr, 'YearsWithCurrManager'] <= df.loc[mask_mgr, 'YearsAtCompany']).all()
    assert (df.loc[mask_role, 'YearsInCurrentRole'] <= df.loc[mask_role, 'YearsAtCompany']).all()
    assert (df.loc[mask_prom, 'YearsSinceLastPromotion'] <= df.loc[mask_prom, 'YearsAtCompany']).all()
    assert (df.loc[mask_total, 'YearsAtCompany'] <= df.loc[mask_total, 'TotalWorkingYears']).all()
    zmask = df['YearsAtCompany'] == 0
    assert (df.loc[zmask, 'YearsInCurrentRole'] == 0).all()
    # ASSERTION_END

    # Categorical and target distribution checks before rate-based calibration
    # ASSERTION_START
    assert df['OverTime'].isin({'Yes', 'No'}).all()
    assert df['Attrition'].isin({'Yes', 'No'}).all()
    js_non_null = df['JobSatisfaction'].notna()
    wlb_non_null = df['WorkLifeBalance'].notna()
    assert ((df.loc[js_non_null, 'JobSatisfaction'] >= 1) & (df.loc[js_non_null, 'JobSatisfaction'] <= 4)).all()
    assert ((df.loc[wlb_non_null, 'WorkLifeBalance'] >= 1) & (df.loc[wlb_non_null, 'WorkLifeBalance'] <= 4)).all()
    assert (df['WorkLifeBalance'] == 3).mean() >= 0.50
    assert (df['JobSatisfaction'] >= 3).mean() >= 0.55
    overall_attr_rate = (df['Attrition'] == 'Yes').mean()
    assert (overall_attr_rate >= 0.10) and (overall_attr_rate <= 0.30)
    # Ensure OverTime risk separation
    ot_yes = df['OverTime'] == 'Yes'
    ot_no = df['OverTime'] == 'No'
    rate_ot_yes = (df.loc[ot_yes, 'Attrition'] == 'Yes').mean() if ot_yes.any() else np.nan
    rate_ot_no = (df.loc[ot_no, 'Attrition'] == 'Yes').mean() if ot_no.any() else np.nan
    assert pd.notna(rate_ot_yes) and pd.notna(rate_ot_no) and (rate_ot_yes >= 1.3 * rate_ot_no)
    # Average JobSatisfaction separation by Attrition
    js_yes = df.loc[df['Attrition'] == 'Yes', 'JobSatisfaction'].mean()
    js_no = df.loc[df['Attrition'] == 'No', 'JobSatisfaction'].mean()
    assert js_yes < js_no
    # ASSERTION_END

    # Derived features for risk scoring
    # Income risk from SalarySlab (heavier risk on lower slabs)
    slab_weight = {
        'Upto 5k': 1.0,
        '5k-10k': 0.6,
        '10k-15k': 0.3,
        '15k+': 0.0,
    }
    df['risk_income'] = df['SalarySlab'].map(slab_weight)

    # Overtime risk scaled by observed uplift
    ot_yes = df['OverTime'] == 'Yes'
    ot_no = df['OverTime'] == 'No'
    rate_ot_yes = (df.loc[ot_yes, 'Attrition'] == 'Yes').mean()
    rate_ot_no = (df.loc[ot_no, 'Attrition'] == 'Yes').mean()
    uplift_ot = max(0.0, min(1.0, (rate_ot_yes / rate_ot_no) - 1.0)) if rate_ot_no > 0 else 0.0
    df['risk_ot'] = np.where(df['OverTime'] == 'Yes', uplift_ot, 0.0)

    # WorkLifeBalance risk: center at 3
    wlb_map = {1: 1.0, 2: 0.5, 3: 0.0, 4: -0.05}
    df['risk_wlb'] = df['WorkLifeBalance'].map(wlb_map).fillna(0.0)

    # JobSatisfaction risk: lower satisfaction -> higher risk
    df['risk_js'] = (4 - df['JobSatisfaction']) / 3.0
    df['risk_js'] = df['risk_js'].clip(lower=0.0, upper=1.0)

    # Tenure risks
    # Role stagnation: ratio of time in current role vs company tenure
    denom = df['YearsAtCompany'].replace(0, np.nan)
    df['role_ratio'] = (df['YearsInCurrentRole'] / denom).fillna(0.0)
    df['risk_role_stagnation'] = df['role_ratio'].clip(0, 1)

    # Promotion lag risk, capped
    df['risk_promo_lag'] = (df['YearsSinceLastPromotion'] / 5.0).clip(0, 1)

    # Manager continuity risk: short time with manager relative to tenure
    df['mgr_ratio'] = (df['YearsWithCurrManager'] / denom).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    df['risk_mgr_churn'] = (1.0 - df['mgr_ratio']).clip(0, 1)

    # Age band risk: slight bump for early-career groups
    age_risk_map = {
        '18-25': 0.25,
        '26-35': 0.15,
        '36-45': 0.05,
        '46-55': 0.00,
        '55+': 0.00,
    }
    df['risk_age_band'] = df['AgeGroup'].map(age_risk_map).fillna(0.0)

    # Commute risk (proxy)
    df['risk_commute'] = (df['DistanceFromHome'] / 30.0).clip(0, 1)

    # Combine with weights (sum ~ 1.0)
    w = {
        'risk_income': 0.25,
        'risk_ot': 0.15,
        'risk_wlb': 0.10,
        'risk_js': 0.12,
        'risk_role_stagnation': 0.10,
        'risk_promo_lag': 0.10,
        'risk_mgr_churn': 0.08,
        'risk_age_band': 0.05,
        'risk_commute': 0.05,
    }
    df['risk_raw'] = (
        w['risk_income'] * df['risk_income'] +
        w['risk_ot'] * df['risk_ot'] +
        w['risk_wlb'] * df['risk_wlb'] +
        w['risk_js'] * df['risk_js'] +
        w['risk_role_stagnation'] * df['risk_role_stagnation'] +
        w['risk_promo_lag'] * df['risk_promo_lag'] +
        w['risk_mgr_churn'] * df['risk_mgr_churn'] +
        w['risk_age_band'] * df['risk_age_band'] +
        w['risk_commute'] * df['risk_commute']
    )

    # Squash to [0,1]
    df['risk_score'] = df['risk_raw'].clip(0, 1)

    # Threshold calibrated by target prevalence
    overall_attr_rate = (df['Attrition'] == 'Yes').mean()
    high_threshold = float(np.clip(2.0 * overall_attr_rate, 0.20, 0.50))
    med_threshold = high_threshold / 2.0

    df['risk_tier'] = np.where(
        df['risk_score'] >= high_threshold, 'High',
        np.where(df['risk_score'] >= med_threshold, 'Medium', 'Low')
    )

    # Recommended action based on top contributing risks
    def recommend_action(row):
        if row['risk_tier'] != 'High':
            return 'Monitor'
        # Priority: compensation, work-life, manager, growth
        if row['risk_income'] >= 0.8 and row['JobSatisfaction'] <= 2:
            return 'CompensationReview'
        if (row['OverTime'] == 'Yes') and (row['WorkLifeBalance'] <= 2):
            return 'FlexibleSchedule'
        if row['risk_role_stagnation'] >= 0.7 or row['risk_promo_lag'] >= 0.8:
            return 'CareerProgressionPlan'
        if row['risk_mgr_churn'] >= 0.7:
            return 'ManagerCheckIn'
        return 'Engagement1on1'

    df['recommended_action'] = df.apply(recommend_action, axis=1)

    # Prepare outputs
    scores_cols = [
        'EmpID', 'Department', 'JobRole', 'Age', 'AgeGroup', 'MonthlyIncome', 'SalarySlab',
        'OverTime', 'WorkLifeBalance', 'JobSatisfaction', 'YearsAtCompany', 'YearsInCurrentRole',
        'YearsSinceLastPromotion', 'YearsWithCurrManager', 'TotalWorkingYears',
        'risk_score', 'risk_tier', 'recommended_action'
    ]
    scores_df = df[scores_cols].copy()

    actions_df = scores_df.loc[scores_df['risk_tier'] == 'High', ['EmpID', 'Department', 'JobRole', 'recommended_action']].copy()

    os.makedirs(args.output, exist_ok=True)
    scores_path = os.path.join(args.output, 'employee_risk_scores.csv')
    actions_path = os.path.join(args.output, 'retention_actions.csv')
    scores_df.to_csv(scores_path, index=False)
    actions_df.to_csv(actions_path, index=False)

    # Summary metrics for monitoring
    metrics = {
        'n_employees': int(df.shape[0]),
        'overall_attrition_rate': overall_attr_rate,
        'high_risk_threshold': high_threshold,
        'high_risk_count': int((df['risk_tier'] == 'High').sum()),
        'medium_risk_count': int((df['risk_tier'] == 'Medium').sum()),
        'low_risk_count': int((df['risk_tier'] == 'Low').sum()),
        'upto5k_share': float((df['SalarySlab'] == 'Upto 5k').mean()),
        'age_26_35_share': float((df['AgeGroup'] == '26-35').mean())
    }
    with open(os.path.join(args.output, 'metrics.json'), 'w') as f:
        json.dump(metrics, f)


if __name__ == '__main__':
    main()
