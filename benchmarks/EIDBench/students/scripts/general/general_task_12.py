import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Ensure numeric types for fields used downstream
    numeric_cols = [
        'Curricular units 1st sem (enrolled)',
        'Curricular units 1st sem (evaluations)',
        'Curricular units 1st sem (without evaluations)',
        'Curricular units 1st sem (approved)',
        'Curricular units 1st sem (grade)',
        'Curricular units 2nd sem (grade)',
        'Admission grade',
        'Previous qualification (grade)',
        'Debtor',
        'Tuition fees up to date',
        'Scholarship holder',
        'Application order'
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # 1st semester academic engagement features
    s1_enrolled = df['Curricular units 1st sem (enrolled)']
    s1_eval = df['Curricular units 1st sem (evaluations)']
    s1_without = df['Curricular units 1st sem (without evaluations)']
    s1_approved = df['Curricular units 1st sem (approved)']
    s1_grade = df['Curricular units 1st sem (grade)']
    # ASSERTION_START
    x = s1_enrolled
    assert x.notna().all()
    assert x.ge(0).all()
    # ASSERTION_END
    # ASSERTION_START
    a = s1_eval
    b = s1_enrolled
    we = s1_without
    assert a.notna().all()
    assert we.notna().all()
    assert (a.ge(0) & b.ge(0) & we.ge(0)).all()
    # ASSERTION_END
    eval_ratio = np.where(s1_enrolled > 0, s1_eval / s1_enrolled, 0.0)
    # ASSERTION_START
    u = s1_approved
    v = s1_eval
    assert u.notna().all()
    assert v.notna().all()
    assert (u.ge(0) & v.ge(0)).all()
    assert (u <= v).all()
    assert (u[v == 0] == 0).all()
    # ASSERTION_END
    approved_ratio = np.where(s1_eval > 0, s1_approved / s1_eval, 0.0)

    # Grade features and stability between semesters
    g1 = s1_grade
    g2 = df['Curricular units 2nd sem (grade)']
    # ASSERTION_START
    assert g1.notna().all()
    assert (g1.ge(0.0) & g1.le(20.0)).all()
    # ASSERTION_END
    # ASSERTION_START
    g_2 = g2
    assert g_2.notna().all()
    assert (g_2.ge(0.0) & g_2.le(20.0)).all()
    # ASSERTION_END
    avg_grade = (g1 + g2) / 2.0
    grade_diff = (g1 - g2).abs()
    consistency = 1.0 - (grade_diff / 6.0)
    consistency = np.clip(consistency, 0.0, 1.0)

    # Preparedness features from pre-entry grades
    adm = df['Admission grade']
    pq = df['Previous qualification (grade)']
    # ASSERTION_START
    assert adm.notna().all() and pq.notna().all()
    assert (adm.ge(0.0) & adm.le(200.0)).all()
    assert (pq.ge(0.0) & pq.le(200.0)).all()
    # ASSERTION_END
    prep_mean = (adm + pq) / 2.0
    prep_score = prep_mean / 200.0
    prep_closeness = 1.0 - (np.abs(adm - pq) / 50.0)
    prep_closeness = np.clip(prep_closeness, 0.0, 1.0)

    # Financial status features
    debtor = df['Debtor'].astype('Int64')
    fees_ok = df['Tuition fees up to date'].astype('Int64')
    schol = df['Scholarship holder'].astype('Int64')
    # ASSERTION_START
    deb = debtor.astype('float')
    fees = fees_ok.astype('float')
    sch = schol.astype('float')
    assert pd.Series(deb).isin([0, 1]).all()
    assert pd.Series(fees).isin([0, 1]).all()
    assert pd.Series(sch).isin([0, 1]).all()
    # ASSERTION_END
    # Application order features
    app_order = df['Application order']
    # ASSERTION_START
    ao = app_order
    assert ao.notna().all()
    # ASSERTION_END
    # Risk components
    lack_eval_flag = (s1_without > 0).astype(int)
    risk_engagement = 0.7 * (1.0 - eval_ratio) + 0.3 * (1.0 - approved_ratio) + 0.1 * lack_eval_flag
    risk_engagement = np.clip(risk_engagement, 0.0, 1.0)

    risk_grades = 1.0 - (avg_grade / 20.0)
    risk_grades = risk_grades * (1.0 + (1.0 - consistency) * 0.5)
    risk_grades = np.clip(risk_grades, 0.0, 1.0)

    risk_prep = (1.0 - prep_score) * 0.75 + (1.0 - prep_closeness) * 0.25
    risk_prep = np.clip(risk_prep, 0.0, 1.0)

    risk_financial = 0.6 * debtor.astype(float).values + 0.4 * (1.0 - fees_ok.astype(float).values)
    risk_financial = risk_financial + np.where((schol == 1) & (fees_ok == 0), 0.2, 0.0)
    risk_financial = np.clip(risk_financial, 0.0, 1.0)

    app_adj = np.where(app_order == 1, -0.05, 0.0) + np.where(app_order.isin([0, 9]), 0.05, 0.0)

    risk_score = 0.35 * risk_engagement + 0.25 * risk_grades + 0.20 * risk_prep + 0.20 * risk_financial + app_adj
    risk_score = np.clip(risk_score, 0.0, 1.0)

    # Outputs
    out = pd.DataFrame({
        'student_id': np.arange(len(df)) + 1,
        'risk_score': risk_score,
        'risk_engagement': risk_engagement,
        'risk_grades': risk_grades,
        'risk_prep': risk_prep,
        'risk_financial': risk_financial,
        'Application order': app_order,
        'Debtor': debtor,
        'Tuition fees up to date': fees_ok,
        'Scholarship holder': schol,
        'Curricular units 1st sem (grade)': g1,
        'Curricular units 2nd sem (grade)': g2,
        'eval_ratio_1st': eval_ratio,
        'approved_ratio_1st': approved_ratio,
    })

    bins = [0.0, 0.33, 0.66, 1.0]
    labels = ['low', 'medium', 'high']
    out['risk_band'] = pd.cut(out['risk_score'], bins=bins, labels=labels, include_lowest=True, right=True)

    out['recommended_action'] = np.where((out['risk_financial'] >= 0.5) & (out['risk_score'] >= 0.4),
                                         'tuition_collection', 'retention_outreach')

    out['priority_score'] = out['risk_score'] * 0.7 + out['risk_financial'] * 0.3 + np.where(
        out['recommended_action'] == 'tuition_collection', 0.05, 0.0)

    out_sorted = out.sort_values(by=['priority_score', 'risk_score'], ascending=[False, False])

    out_file = os.path.join(args.output, 'student_risk_scores.csv')
    out_sorted.to_csv(out_file, index=False)

    retention_queue = out_sorted[out_sorted['recommended_action'] == 'retention_outreach'].head(200)
    tuition_queue = out_sorted[out_sorted['recommended_action'] == 'tuition_collection'].head(200)

    retention_queue.to_csv(os.path.join(args.output, 'retention_queue.csv'), index=False)
    tuition_queue.to_csv(os.path.join(args.output, 'tuition_collection_queue.csv'), index=False)


if __name__ == '__main__':
    main()
