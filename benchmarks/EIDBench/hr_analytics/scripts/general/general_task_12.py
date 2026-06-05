import argparse
import os

import numpy as np
import pandas as pd


def compute_age_group(age_series: pd.Series) -> pd.Series:
    bins = [18, 25, 35, 45, 55, np.inf]
    labels = ['18-25', '26-35', '36-45', '46-55', '55+']
    return pd.cut(age_series, bins=bins, labels=labels, right=True, include_lowest=True).astype(str)


def map_income_to_slab(income_series: pd.Series) -> pd.Series:
    s = income_series.astype(float)
    conditions = [
        (s > 0) & (s <= 5000),
        (s > 5000) & (s <= 10000),
        (s > 10000) & (s <= 15000),
        (s > 15000)
    ]
    choices = ['Upto 5k', '5k-10k', '10k-15k', '15k+']
    return np.select(conditions, choices, default=np.nan)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_file = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_file)

    # Age range guard prior to age-based segmentation
    # ASSERTION_START
    assert (df['Age'] >= 18).all()
    # ASSERTION_END
    # Age group consistency guard prior to using AgeGroup for segmentation
    # ASSERTION_START
    _computed_age_group = compute_age_group(df['Age'])
    assert (_computed_age_group == df['AgeGroup'].astype(str)).all()
    # ASSERTION_END
    # Age band segmentation (dashboard tile)
    age_order = pd.CategoricalDtype(categories=['18-25', '26-35', '36-45', '46-55', '55+'], ordered=True)
    seg = df[['AgeGroup']].copy()
    seg['AgeGroup'] = seg['AgeGroup'].astype(age_order)
    age_band = (
        seg.groupby('AgeGroup', dropna=False)
        .size()
        .reset_index(name='headcount')
        .sort_values('AgeGroup')
    )
    age_band['share'] = age_band['headcount'] / len(df)
    age_band.to_csv(os.path.join(args.output, 'age_band_distribution.csv'), index=False)

    # Salary band compliance checks prior to salary analytics
    # ASSERTION_START
    _derived_slab = map_income_to_slab(df['MonthlyIncome'])
    assert (df['SalarySlab'].astype(str) == pd.Series(_derived_slab).astype(str)).all()
    # ASSERTION_END
    # Salary band summary (dashboard tile)
    slab_order = pd.CategoricalDtype(categories=['Upto 5k', '5k-10k', '10k-15k', '15k+'], ordered=True)
    salary_summary = df[['SalarySlab']].copy()
    salary_summary['SalarySlab'] = salary_summary['SalarySlab'].astype(slab_order)
    salary_summary = (
        salary_summary.groupby('SalarySlab', dropna=False)
        .size()
        .reset_index(name='headcount')
        .sort_values('SalarySlab')
    )
    salary_summary['share'] = salary_summary['headcount'] / len(df)
    salary_summary.to_csv(os.path.join(args.output, 'salary_band_summary.csv'), index=False)

    # Role-Department consistency check prior to cross-tab/pipeline by org
    role_to_dept = {
        'Sales Executive': 'Sales',
        'Sales Representative': 'Sales',
        'Healthcare Representative': 'Sales',
        'Research Scientist': 'Research & Development',
        'Laboratory Technician': 'Research & Development',
        'Research Director': 'Research & Development',
        'Manufacturing Director': 'Research & Development',
        'Human Resources': 'Human Resources'
    }
    # ASSERTION_START
    _mask = df['JobRole'].isin(role_to_dept.keys())
    _expected = df.loc[_mask, 'JobRole'].map(role_to_dept)
    assert (df.loc[_mask, 'Department'].astype(str) == _expected.astype(str)).all()
    # ASSERTION_END
    # Role-Department matrix (dashboard tile)
    role_dept_matrix = (
        df.pivot_table(index='Department', columns='JobRole', aggfunc='size', fill_value=0)
        .reset_index()
    )
    role_dept_matrix.to_csv(os.path.join(args.output, 'role_department_matrix.csv'), index=False)

    # Manager tenure coverage guard prior to using it in pipeline metrics
    # Tenure relationship guards prior to ratios used in pipeline scoring
    # ASSERTION_START
    assert ((df['YearsAtCompany'] >= 0) & (df['YearsAtCompany'] <= df['TotalWorkingYears'])).all()
    # ASSERTION_END
    # ASSERTION_START
    assert ((df['YearsInCurrentRole'] >= 0) & (df['YearsInCurrentRole'] <= df['YearsAtCompany'])).all()
    # ASSERTION_END
    # Promotion pipeline metrics (dashboard tile)
    pipeline_df = df.copy()

    # Readiness flags
    pipeline_df['ready_now'] = (
            (pipeline_df['PerformanceRating'] >= 4) &
            (pipeline_df['YearsInCurrentRole'] >= 2) &
            (pipeline_df['YearsSinceLastPromotion'] >= 2)
    )
    pipeline_df['ready_soon'] = (
            (~pipeline_df['ready_now']) &
            (pipeline_df['PerformanceRating'] >= 3) &
            (pipeline_df['YearsInCurrentRole'] >= 1) &
            (pipeline_df['YearsSinceLastPromotion'] >= 1)
    )

    # Ratios used in scoring and reporting
    pipeline_df['internal_tenure_ratio'] = np.where(
        pipeline_df['YearsAtCompany'] > 0,
        pipeline_df['YearsInCurrentRole'] / pipeline_df['YearsAtCompany'],
        np.nan
    )
    pipeline_df['company_to_career_ratio'] = np.where(
        pipeline_df['TotalWorkingYears'] > 0,
        pipeline_df['YearsAtCompany'] / pipeline_df['TotalWorkingYears'],
        np.nan
    )

    agg = (
        pipeline_df
        .groupby(['Department', 'JobLevel'], as_index=False)
        .agg(
            headcount=('EmpID', 'count'),
            ready_now_count=('ready_now', 'sum'),
            ready_soon_count=('ready_soon', 'sum'),
            avg_performance=('PerformanceRating', 'mean'),
            avg_years_in_role=('YearsInCurrentRole', 'mean'),
            avg_years_since_last_promotion=('YearsSinceLastPromotion', 'mean'),
            avg_years_with_manager=('YearsWithCurrManager', 'mean'),
            avg_internal_tenure_ratio=('internal_tenure_ratio', 'mean'),
            avg_company_to_career_ratio=('company_to_career_ratio', 'mean')
        )
        .sort_values(['Department', 'JobLevel'])
    )
    agg.to_csv(os.path.join(args.output, 'promotion_pipeline.csv'), index=False)

    # Supplemental: manager stability by department for the dashboard
    manager_stability = (
        pipeline_df.groupby('Department', as_index=False)
        .agg(avg_years_with_manager=('YearsWithCurrManager', 'mean'))
        .sort_values('Department')
    )
    manager_stability.to_csv(os.path.join(args.output, 'manager_stability_by_department.csv'), index=False)

    if __name__ == '__main__':
        main()
