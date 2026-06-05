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

    input_file = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_file)

    enrolled_col = 'Curricular units 1st sem (enrolled)'
    evals_col = 'Curricular units 1st sem (evaluations)'
    without_col = 'Curricular units 1st sem (without evaluations)'
    approved_col = 'Curricular units 1st sem (approved)'
    credited_col = 'Curricular units 1st sem (credited)'
    grade_col = 'Curricular units 1st sem (grade)'
    debtor_col = 'Debtor'
    uptodate_col = 'Tuition fees up to date'
    intl_col = 'International'
    nat_col = 'Nacionality'

    numeric_cols = [enrolled_col, evals_col, without_col, approved_col, credited_col,
                    grade_col, debtor_col, uptodate_col, intl_col, nat_col]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    enrolled = df[enrolled_col].astype(float)
    evals = df[evals_col].astype(float)
    without_evals = df[without_col].astype(float)
    approved = df[approved_col].astype(float)
    credited = df[credited_col].astype(float)
    grade = df[grade_col].astype(float)
    debtor = df[debtor_col].astype(int)
    uptodate = df[uptodate_col].astype(int)
    international = df[intl_col].astype(int)
    nationality = df[nat_col].astype(int)
    # ASSERTION_START
    assert np.isfinite(enrolled).all()
    assert np.isfinite(without_evals).all()
    assert (enrolled >= 0).all()
    assert (without_evals >= 0).all()
    assert (without_evals <= enrolled).all()
    # ASSERTION_END
    attended = enrolled - without_evals
    with np.errstate(divide='ignore', invalid='ignore'):
        evaluation_rate = np.where(enrolled > 0, attended / enrolled, 0.0)
    # ASSERTION_START
    assert np.isfinite(evals).all()
    assert np.isfinite(approved).all()
    assert (evals >= 0).all()
    assert (approved >= 0).all()
    assert (approved <= evals).all()
    # ASSERTION_END
    with np.errstate(divide='ignore', invalid='ignore'):
        pass_rate = np.where(evals > 0, approved / evals, 0.0)
    # ASSERTION_START
    assert np.isfinite(enrolled).all()
    assert np.isfinite(credited).all()
    assert (enrolled >= 0).all()
    assert (credited >= 0).all()
    assert (credited <= enrolled).all()
    # ASSERTION_END
    with np.errstate(divide='ignore', invalid='ignore'):
        credit_ratio = np.where(enrolled > 0, credited / enrolled, 0.0)
    # ASSERTION_START
    assert (grade >= 0.0).all() and (grade <= 20.0).all()
    # ASSERTION_END
    grade_norm = grade / 20.0

    intl_rate = (international == 1).mean()
    # ASSERTION_START
    assert debtor.isin([0, 1]).all()
    assert uptodate.isin([0, 1]).all()
    # ASSERTION_END
    compliance_rate = (uptodate == 1).mean()
    fees_flag = (uptodate == 0).astype(float)

    base_risk = (
            0.35 * (1.0 - pass_rate) +
            0.20 * (1.0 - evaluation_rate) +
            0.20 * (1.0 - credit_ratio) +
            0.20 * (1.0 - grade_norm) +
            0.05 * debtor.astype(float)
    )
    intl_uplift = 0.05 * (international == 1).astype(float)
    risk_score = np.clip(base_risk + intl_uplift, 0.0, 1.0)

    threshold = 0.60 - 0.10 * (compliance_rate - 0.90)
    threshold = float(np.clip(threshold, 0.40, 0.80))

    advisory_flag = risk_score >= threshold

    hold_required = ((uptodate == 0) | (debtor == 1))
    strict_hold = hold_required & advisory_flag

    hold_reason = np.where(strict_hold, 'FEE+ACADEMIC', np.where(hold_required, 'FEE', 'NONE'))
    hold_severity = np.where(strict_hold, 'STRICT', np.where(hold_required, 'STANDARD', 'NONE'))

    out = pd.DataFrame({
        'student_index': df.index,
        'dropout_risk_score': (risk_score * 100.0).round(2),
        'risk_threshold': np.full(len(df), round(threshold, 4)),
        'risk_flag': np.where(advisory_flag, 'HIGH', 'LOW'),
        'tuition_hold': hold_required.astype(int),
        'hold_severity': hold_severity,
        'hold_reason': hold_reason,
        'evaluation_rate': np.round(evaluation_rate, 4),
        'pass_rate': np.round(pass_rate, 4),
        'credit_ratio': np.round(credit_ratio, 4),
        'fees_flag': fees_flag.astype(int),
        'debtor': debtor,
        'tuition_up_to_date': uptodate,
        'international': international,
        'nationality': nationality
    })

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, 'early_warning_scores.csv')
    out.to_csv(out_path, index=False)

    summary = {
        'records': int(len(df)),
        'avg_dropout_risk_score': float(np.round(out['dropout_risk_score'].mean(), 2)),
        'hold_rate': float(np.round(out['tuition_hold'].mean(), 4)),
        'compliance_rate': float(np.round(compliance_rate, 4)),
        'international_rate': float(np.round(intl_rate, 4)),
        'risk_threshold': float(np.round(threshold, 4))
    }
    with open(os.path.join(args.output, 'early_warning_summary.json'), 'w') as f:
        json.dump(summary, f)


if __name__ == '__main__':
    main()
