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

    # Column aliases for readability
    c1_enrolled = 'Curricular units 1st sem (enrolled)'
    c1_evals = 'Curricular units 1st sem (evaluations)'
    c1_approved = 'Curricular units 1st sem (approved)'
    c1_credited = 'Curricular units 1st sem (credited)'
    c1_without = 'Curricular units 1st sem (without evaluations)'
    c1_grade = 'Curricular units 1st sem (grade)'

    c2_enrolled = 'Curricular units 2nd sem (enrolled)'
    c2_evals = 'Curricular units 2nd sem (evaluations)'
    c2_approved = 'Curricular units 2nd sem (approved)'
    c2_credited = 'Curricular units 2nd sem (credited)'
    c2_without = 'Curricular units 2nd sem (without evaluations)'

    debtor_col = 'Debtor'
    tuition_col = 'Tuition fees up to date'

    numeric_cols = [
        c1_enrolled, c1_evals, c1_approved, c1_credited, c1_without, c1_grade,
        c2_enrolled, c2_evals, c2_approved, c2_credited, c2_without,
        debtor_col, tuition_col
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # ASSERTION_START
    # Academic progress - 1st semester
    c1_approved = 'Curricular units 1st sem (approved)'
    c1_evals = 'Curricular units 1st sem (evaluations)'
    # Pass rate calculation requires non-null, non-negative, and consistent values.
    assert (df[c1_approved] >= 0).all()
    assert (df[c1_evals] >= 0).all()
    assert (df[c1_approved] <= df[c1_evals]).all()
    # ASSERTION_END
    evals1_safe = df[c1_evals].replace(0, np.nan)
    pass_rate_1 = (df[c1_approved] / evals1_safe).fillna(0.0)
    # ASSERTION_START
    c1_enrolled = 'Curricular units 1st sem (enrolled)'
    c1_evals = 'Curricular units 1st sem (evaluations)'
    c1_without = 'Curricular units 1st sem (without evaluations)'
    # The calculation requires non-null, non-negative values.
    assert (df[c1_enrolled] >= 0).all()
    assert (df[c1_evals] >= 0).all()
    assert (df[c1_without] >= 0).all()
    # ASSERTION_END
    missing_recorded_1 = df[c1_enrolled] - (df[c1_evals] + df[c1_without])
    coverage_gap_1 = np.where(df[c1_enrolled] > 0, missing_recorded_1 / df[c1_enrolled], 0.0)

    # ASSERTION_START
    # Academic performance - 1st semester grade normalization
    c1_grade = 'Curricular units 1st sem (grade)'
    # Grade normalization requires a non-null grade on the 0-20 scale.
    assert ((df[c1_grade] >= 0) & (df[c1_grade] <= 20)).all()
    # ASSERTION_END
    grade_norm_1 = df[c1_grade] / 20.0
    grade_risk = 1.0 - grade_norm_1

    # ASSERTION_START
    # Academic progress - 2nd semester
    c2_approved = 'Curricular units 2nd sem (approved)'
    c2_evals = 'Curricular units 2nd sem (evaluations)'
    # Pass rate calculation requires non-null, non-negative, and consistent values.
    assert (df[c2_approved] >= 0).all()
    assert (df[c2_evals] >= 0).all()
    assert (df[c2_approved] <= df[c2_evals]).all()
    # ASSERTION_END
    evals2_safe = df[c2_evals].replace(0, np.nan)
    pass_rate_2 = (df[c2_approved] / evals2_safe).fillna(0.0)
    # ASSERTION_START
    c2_enrolled = 'Curricular units 2nd sem (enrolled)'
    c2_evals = 'Curricular units 2nd sem (evaluations)'
    c2_without = 'Curricular units 2nd sem (without evaluations)'
    # The calculation requires non-null, non-negative values.
    assert (df[c2_enrolled] >= 0).all()
    assert (df[c2_evals] >= 0).all()
    assert (df[c2_without] >= 0).all()
    # ASSERTION_END
    missing_recorded_2 = df[c2_enrolled] - (df[c2_evals] + df[c2_without])
    coverage_gap_2 = np.where(df[c2_enrolled] > 0, missing_recorded_2 / df[c2_enrolled], 0.0)

    zero_share_without2 = (df[c2_without] == 0).mean()
    non_zero_share_without2 = max(1.0 - zero_share_without2, 1e-6)
    rarity_multiplier = np.log1p(1.0 / non_zero_share_without2)
    rare_event_penalty = (df[c2_without] > 0).astype(float) * (0.05 * rarity_multiplier)

    # Financial status -> fee risk
    fee_risk = np.where(df[tuition_col] == 1, 0.0, np.where(df[debtor_col] == 1, 1.0, 0.3))

    # Build dropout risk score (higher = higher risk)
    risk_score = (
            0.25 * (1.0 - pass_rate_1) +
            0.25 * (1.0 - pass_rate_2) +
            0.10 * coverage_gap_1 +
            0.15 * coverage_gap_2 +
            0.15 * grade_risk +
            0.20 * fee_risk +
            rare_event_penalty
    )
    risk_score = np.maximum(risk_score, 0.0)

    out = pd.DataFrame({
        'student_row_id': np.arange(len(df)),
        'risk_score': risk_score.round(6),
        'fee_risk': fee_risk.round(6),
        'pass_rate_1': pass_rate_1.round(6),
        'pass_rate_2': pass_rate_2.round(6),
        'coverage_gap_1': np.round(coverage_gap_1, 6),
        'coverage_gap_2': np.round(coverage_gap_2, 6),
        'grade_risk': np.round(grade_risk, 6),
    })

    # Priority banding to drive advisor queue
    quantiles = out['risk_score'].quantile([0.7, 0.9]).values
    low_cut, high_cut = quantiles[0], quantiles[1]
    conditions = [
        out['risk_score'] >= high_cut,
        (out['risk_score'] >= low_cut) & (out['risk_score'] < high_cut),
        out['risk_score'] < low_cut
    ]
    choices = ['High', 'Medium', 'Low']
    out['priority'] = np.select(conditions, choices, default='Low')

    out.sort_values(['priority', 'risk_score'], ascending=[True, False], inplace=True)

    # Persist outputs
    out_file = os.path.join(args.output, 'weekly_dropout_risk_scores.csv')
    out.to_csv(out_file, index=False)

    # Export top 200 for immediate advisor outreach
    top_k = out[out['priority'] == 'High'].head(200)
    top_file = os.path.join(args.output, 'advisor_intervention_queue.csv')
    top_k.to_csv(top_file, index=False)


if __name__ == '__main__':
    main()
