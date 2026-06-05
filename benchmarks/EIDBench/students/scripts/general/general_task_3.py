import argparse
import json
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

    # Column references
    g_tuition = 'Tuition fees up to date'
    g_debtor = 'Debtor'
    g_admission = 'Admission grade'
    g_prev = 'Previous qualification (grade)'
    c1_enr = 'Curricular units 1st sem (enrolled)'
    c1_app = 'Curricular units 1st sem (approved)'
    c1_cred = 'Curricular units 1st sem (credited)'
    c1_woe = 'Curricular units 1st sem (without evaluations)'
    c1_grade = 'Curricular units 1st sem (grade)'
    c2_enr = 'Curricular units 2nd sem (enrolled)'
    c2_app = 'Curricular units 2nd sem (approved)'
    c2_cred = 'Curricular units 2nd sem (credited)'
    c2_woe = 'Curricular units 2nd sem (without evaluations)'
    c2_grade = 'Curricular units 2nd sem (grade)'
    g_age = 'Age at enrollment'
    g_day = 'Daytime/evening attendance\t'
    g_target = 'Target'

    # Type coercion for numeric ops
    num_cols = [
        g_tuition, g_debtor, g_admission, g_prev,
        c1_enr, c1_app, c1_cred, c1_woe, c1_grade,
        c2_enr, c2_app, c2_cred, c2_woe, c2_grade,
        g_age, g_day
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # ASSERTION_START
    # Finance integrity checks before computing financial risk
    assert df[g_tuition].notna().all()
    # ASSERTION_END
    finance_risk = ((df[g_tuition] == 0) | (df[g_debtor] == 1)).astype(float)

    # ASSERTION_START
    # Age checks and feature
    assert df[g_age].notna().all()
    # ASSERTION_END
    risk_age = np.where((df[g_age] < 17) | (df[g_age] > 45), 0.10, 0.00)

    # ASSERTION_START
    # Attendance checks and feature
    assert df[g_day].notna().all()
    # ASSERTION_END
    attendance_risk = np.where(df[g_day] == 0, 0.05, 0.00)

    # ASSERTION_START
    # Semester 1 structural checks before ratios
    sem1_unit_cols = [c1_enr, c1_app, c1_cred, c1_woe]
    for col in sem1_unit_cols:
        assert df[col].notna().all()
        assert (df[col] >= 0).all()

    assert (df[c1_app] <= df[c1_enr]).all()
    assert (df[c1_cred] <= df[c1_enr]).all()
    assert (df[c1_woe] <= df[c1_enr]).all()
    m1 = df[c1_enr] == 0
    assert ((df.loc[m1, c1_app] == 0) & (df.loc[m1, c1_cred] == 0) & (df.loc[m1, c1_woe] == 0)).all()
    # ASSERTION_END
    den1 = df[c1_enr].replace(0, np.nan)
    pass_rate1 = (df[c1_app] / den1).fillna(0.0)
    fail_rate1 = 1.0 - pass_rate1
    no_eval_ratio1 = (df[c1_woe] / den1).fillna(0.0)
    credit_ratio1 = (df[c1_cred] / den1).fillna(0.0)

    # ASSERTION_START
    # Semester 2 structural checks before ratios
    sem2_unit_cols = [c2_enr, c2_app, c2_cred, c2_woe]
    for col in sem2_unit_cols:
        assert df[col].notna().all()
        assert (df[col] >= 0).all()

    assert (df[c2_app] <= df[c2_enr]).all()
    assert (df[c2_cred] <= df[c2_enr]).all()
    assert (df[c2_woe] <= df[c2_enr]).all()
    m2 = df[c2_enr] == 0
    assert ((df.loc[m2, c2_app] == 0) & (df.loc[m2, c2_cred] == 0) & (df.loc[m2, c2_woe] == 0)).all()
    # ASSERTION_END
    den2 = df[c2_enr].replace(0, np.nan)
    pass_rate2 = (df[c2_app] / den2).fillna(0.0)
    fail_rate2 = 1.0 - pass_rate2
    no_eval_ratio2 = (df[c2_woe] / den2).fillna(0.0)
    credit_ratio2 = (df[c2_cred] / den2).fillna(0.0)

    # ASSERTION_START
    # Course grade integrity and features
    assert df[c1_grade].notna().all()
    assert df[c1_grade].between(0, 20).all()
    # ASSERTION_END
    # ASSERTION_START
    assert df[c2_grade].notna().all()
    assert df[c2_grade].between(0, 20).all()
    # ASSERTION_END
    grade_risk_1 = 1.0 - (df[c1_grade] / 20.0)
    grade_risk_2 = 1.0 - (df[c2_grade] / 20.0)

    # Admission vs previous qualification checks and preparedness feature
    diff_ap = (df[g_admission] - df[g_prev]).abs()
    # ASSERTION_START
    assert df[g_admission].notna().all()
    assert df[g_prev].notna().all()
    # ASSERTION_END
    prep_risk = 0.5 * np.clip(diff_ap / 50.0, 0.0, 1.0) + 0.5 * np.clip(1.0 - ((df[g_admission] + df[g_prev]) / 400.0),
                                                                        0.0, 1.0)

    # Aggregate academic risk
    fail_rate_avg = (fail_rate1 + fail_rate2) / 2.0
    no_eval_avg = (no_eval_ratio1 + no_eval_ratio2) / 2.0
    grade_risk_avg = (grade_risk_1 + grade_risk_2) / 2.0
    credit_gap_avg = 1.0 - (credit_ratio1 + credit_ratio2) / 2.0

    academic_risk = (
            0.40 * fail_rate_avg +
            0.30 * no_eval_avg +
            0.20 * grade_risk_avg +
            0.10 * credit_gap_avg
    )

    risk_score = (
            0.50 * academic_risk +
            0.30 * finance_risk +
            0.10 * prep_risk +
            0.05 * attendance_risk +
            0.05 * risk_age
    )

    risk_score = np.clip(risk_score, 0.0, 1.0)
    df['risk_score'] = risk_score

    # ASSERTION_START
    # Target checks prior to calibration and alert budgeting
    assert df[g_target].notna().all()
    # ASSERTION_END
    grad_ratio = (df[g_target] == 'Graduate').mean()
    alert_budget_share = float(1.0 - grad_ratio)
    quantile_cut = 1.0 - alert_budget_share
    quantile_cut = max(0.0, min(1.0, quantile_cut))
    threshold = df['risk_score'].quantile(quantile_cut)

    df['high_risk'] = df['risk_score'] >= threshold
    df['risk_tier'] = np.where(df['high_risk'], 'HIGH', np.where(df['risk_score'] >= threshold * 0.7, 'MEDIUM', 'LOW'))

    # Persist outputs
    scores_path = os.path.join(args.output, 'student_risk_scores.csv')
    alerts_path = os.path.join(args.output, 'advisor_alerts.csv')
    summary_path = os.path.join(args.output, 'calibration_summary.json')

    cols_out = ['risk_score', 'high_risk', 'risk_tier', g_tuition, g_debtor, g_day, g_age, g_target]
    existing_cols_out = [c for c in cols_out if c in df.columns]
    df_out = df.reset_index().rename(columns={'index': 'student_row_id'})

    df_out[['student_row_id'] + existing_cols_out].to_csv(scores_path, index=False)
    df_out.loc[df_out['high_risk'], ['student_row_id'] + existing_cols_out].to_csv(alerts_path, index=False)

    summary = {
        'threshold': float(threshold),
        'alert_budget_share': alert_budget_share,
        'total_records': int(len(df_out)),
        'alerts_emitted': int(df_out['high_risk'].sum()),
        'graduate_ratio': float(grad_ratio),
        'mean_risk_score': float(df['risk_score'].mean())
    }
    with open(summary_path, 'w') as f:
        json.dump(summary, f)


if __name__ == '__main__':
    main()
