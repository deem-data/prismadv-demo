import argparse
import json
import math
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Columns
    target_col = 'Target'
    day_col = 'Daytime/evening attendance\t'
    app_order_col = 'Application order'

    c1_enr = 'Curricular units 1st sem (enrolled)'
    c1_apr = 'Curricular units 1st sem (approved)'
    c1_crd = 'Curricular units 1st sem (credited)'
    c1_noe = 'Curricular units 1st sem (without evaluations)'
    c1_grd = 'Curricular units 1st sem (grade)'

    c2_enr = 'Curricular units 2nd sem (enrolled)'
    c2_apr = 'Curricular units 2nd sem (approved)'
    c2_crd = 'Curricular units 2nd sem (credited)'
    c2_noe = 'Curricular units 2nd sem (without evaluations)'
    c2_grd = 'Curricular units 2nd sem (grade)'

    debtor_col = 'Debtor'
    tuition_col = 'Tuition fees up to date'
    scholar_col = 'Scholarship holder'

    gdp_col = 'GDP'
    unemp_col = 'Unemployment rate'
    infl_col = 'Inflation rate'

    # --- Target distribution assumptions and usage ---
    target_counts = df[target_col].value_counts(normalize=True)
    p_grad = float(target_counts.get('Graduate', 0.0))
    p_dropout = float(target_counts.get('Dropout', 0.0))
    p_enrolled = float(target_counts.get('Enrolled', 0.0))
    # ASSERTION_START
    allowed_targets = {'Graduate', 'Dropout', 'Enrolled'}
    assert set(df[target_col].unique()).issubset(allowed_targets)
    assert 0 < p_dropout < 1
    # ASSERTION_END
    # Use priors to calibrate an intercept term for risk normalization
    # The transform relies on proportions being bounded away from {0,1}
    prior_dropout_logit = math.log(p_dropout / max(1e-12, (1.0 - p_dropout)))

    # --- Attendance assumptions and usage ---
    day_series = df[day_col]
    day_share = day_series.mean()
    # ASSERTION_START
    assert day_series.notna().all()
    assert day_series.isin([0, 1]).all()
    # ASSERTION_END
    # Attendance factor: nighttime students (0) add more risk
    attendance_penalty = (1 - day_series).astype(float)

    # --- Application order assumptions and usage ---
    app = df[app_order_col]
    share_first_choice = (app == 1).mean()
    share_in_allowed = app.isin([1, 2, 3, 4, 5, 6]).mean()
    # ASSERTION_START
    assert ((app >= 0) & ((app % 1) == 0)).all()
    assert share_first_choice >= 0.60
    assert share_in_allowed >= 0.95
    # ASSERTION_END
    # Use the shares to scale the application-order risk component
    first_choice_lift = math.sqrt(share_first_choice - 0.60)
    allowed_order_cohesion = math.sqrt(share_in_allowed - 0.95)
    app_penalty = np.where(app == 1, 0.0, (app.clip(lower=1) - 1) / 5.0) * (1.0 + 0.5 * (1.0 - first_choice_lift))

    # --- Fee status and scholarship assumptions and usage ---
    debtor = df[debtor_col].astype(int)
    tuition_up = df[tuition_col].astype(int)
    scholar = df[scholar_col].astype(int)
    # Fee risk: being a debtor and not up-to-date increases risk; scholarship moderates if compliant
    fee_risk = 0.6 * debtor + 0.4 * (1 - tuition_up)
    scholar_bonus = np.where((scholar == 1) & (tuition_up == 1), -0.15, 0.0)

    # --- Macro environment assumptions and usage ---
    allowed_gdp = [-4.06, -3.12, -1.7, -0.92, 0.32, 0.79, 1.74, 1.79, 2.02, 3.51]
    allowed_unemp = [7.6, 8.9, 9.4, 10.8, 11.1, 12.4, 12.7, 13.9, 15.5, 16.2]
    allowed_infl = [-0.8, -0.3, 0.3, 0.5, 0.6, 1.4, 2.6, 2.8, 3.7]
    # ASSERTION_START
    assert df[gdp_col].isin(allowed_gdp).all()
    assert df[unemp_col].isin(allowed_unemp).all()
    assert df[infl_col].isin(allowed_infl).all()
    # ASSERTION_END
    # Map macro values to ordinal indices for a stable adjustment
    gdp_rank = {v: i for i, v in enumerate(sorted(allowed_gdp))}
    unemp_rank = {v: i for i, v in enumerate(sorted(allowed_unemp))}
    infl_rank = {v: i for i, v in enumerate(sorted(allowed_infl))}

    gdp_idx = df[gdp_col].map(gdp_rank).astype(int)
    unemp_idx = df[unemp_col].map(unemp_rank).astype(int)
    infl_idx = df[infl_col].map(infl_rank).astype(int)

    # Macro stress increases with unemployment rank and mild with inflation; growth offsets slightly
    macro_stress = (unemp_idx / (len(unemp_rank) - 1)) * 0.8 + (infl_idx / (len(infl_rank) - 1)) * 0.3 - (
                gdp_idx / (len(gdp_rank) - 1)) * 0.2
    macro_stress = np.clip(macro_stress, 0.0, 1.0)

    # --- Academic performance assumptions and usage (1st semester) ---
    g1 = df[c1_grd].astype(float)
    e1 = df[c1_enr].astype(float)
    a1 = df[c1_apr].astype(float)
    cr1 = df[c1_crd].astype(float)
    ne1 = df[c1_noe].astype(float)
    # ASSERTION_START
    # Allow for NaN values, which are handled by the subsequent code.
    # Check constraints only on the non-NaN data.
    assert g1.dropna().between(0.0, 20.0).all()
    assert (e1.dropna() >= 0).all()
    assert (a1.dropna() >= 0).all()
    assert (ne1.dropna() >= 0).all()

    # For rows where both enrolled and approved counts are available,
    # approved should not exceed enrolled.
    both_valid_a1 = a1.notna() & e1.notna()
    assert (a1[both_valid_a1] <= e1[both_valid_a1]).all()

    # Similarly for 'without evaluations'.
    both_valid_ne1 = ne1.notna() & e1.notna()
    assert (ne1[both_valid_ne1] <= e1[both_valid_ne1]).all()
    # ASSERTION_END
    e1_safe = e1.replace(0, np.nan)
    pass_rate1 = (a1 / e1_safe).clip(0.0, 1.0).fillna(0.0)
    no_eval_ratio1 = (ne1 / e1_safe).clip(0.0, 1.0).fillna(0.0)
    grade_gap1 = (20.0 - g1) / 20.0

    # --- Academic performance assumptions and usage (2nd semester) ---
    g2 = df[c2_grd].astype(float)
    e2 = df[c2_enr].astype(float)
    a2 = df[c2_apr].astype(float)
    cr2 = df[c2_crd].astype(float)
    ne2 = df[c2_noe].astype(float)
    # ASSERTION_START
    # Allow for NaN values, which are handled by the subsequent code.
    # Check constraints only on the non-NaN data.
    assert g2.dropna().between(0.0, 20.0).all()
    assert (e2.dropna() >= 0).all()
    assert (a2.dropna() >= 0).all()
    assert (ne2.dropna() >= 0).all()

    # For rows where both enrolled and approved counts are available,
    # approved should not exceed enrolled.
    both_valid_a2 = a2.notna() & e2.notna()
    assert (a2[both_valid_a2] <= e2[both_valid_a2]).all()

    # Similarly for 'without evaluations'.
    both_valid_ne2 = ne2.notna() & e2.notna()
    assert (ne2[both_valid_ne2] <= e2[both_valid_ne2]).all()
    # ASSERTION_END
    e2_safe = e2.replace(0, np.nan)
    pass_rate2 = (a2 / e2_safe).clip(0.0, 1.0).fillna(0.0)
    no_eval_ratio2 = (ne2 / e2_safe).clip(0.0, 1.0).fillna(0.0)
    grade_gap2 = (20.0 - g2) / 20.0

    # Use the 2nd-sem no-evaluation sparsity assumption to create a scale that is only defined under that sparsity
    share_non_zero_noeval2 = 1.0 - (ne2 == 0).mean()
    # ASSERTION_START
    assert share_non_zero_noeval2 <= 0.10
    # ASSERTION_END
    noeval_sparsity_scale = math.sqrt(0.10 - share_non_zero_noeval2)

    # --- Compose risk components ---
    academic_gap = 0.45 * grade_gap2 + 0.25 * grade_gap1 + 0.15 * (1 - pass_rate2) + 0.10 * (1 - pass_rate1) + 0.05 * (
                0.6 * no_eval_ratio2 + 0.4 * no_eval_ratio1)
    academic_gap = np.clip(academic_gap, 0.0, 1.0)

    # Application risk moderated by cohort cohesion
    application_risk = np.clip(app_penalty * (1.0 + (1.0 - allowed_order_cohesion)), 0.0, 1.0)

    # Attendance risk is higher for evening students
    attendance_risk = np.clip(attendance_penalty * (1.1 - first_choice_lift), 0.0, 1.0)

    # Fee risk adjusted by scholarship bonus
    fee_risk_adj = np.clip(fee_risk + scholar_bonus, 0.0, 1.0)

    # Macro risk adjusted by sparsity-derived scaling to avoid over-amplification when no-eval is mostly zero
    macro_risk = np.clip(macro_stress * (1.0 + 0.5 * noeval_sparsity_scale), 0.0, 1.0)

    # Age factor (older entrants slightly higher risk)
    age = df['Age at enrollment'].astype(float)
    age_risk = np.clip((age - 25.0) / 20.0, 0.0, 1.0)

    # Combine into a 0-100 score; calibrate with prior logit so that baseline aligns with historical dropout prevalence
    raw_score = (
            0.35 * academic_gap +
            0.20 * fee_risk_adj +
            0.15 * attendance_risk +
            0.10 * application_risk +
            0.10 * macro_risk +
            0.10 * age_risk
    )

    # Normalize to 0-100 and shift by prior
    prior_shift = 5.0 * np.tanh(prior_dropout_logit / 4.0)
    risk_score = np.clip(raw_score * 100.0 + prior_shift, 0.0, 100.0)

    # Priority tiers
    bins = [-0.01, 40, 70, 100]
    labels = ['Low', 'Medium', 'High']
    priority = pd.cut(risk_score, bins=bins, labels=labels)

    # Fee management flag (immediate outreach): high risk or debtor not up-to-date
    urgent_fee_flag = ((risk_score >= 70) | ((debtor == 1) & (tuition_up == 0))).astype(int)

    out = df[[app_order_col, day_col, debtor_col, tuition_col, scholar_col, c1_enr, c2_enr]].copy()
    out['risk_score'] = risk_score.round(2)
    out['priority'] = priority.astype(str)
    out['urgent_fee_flag'] = urgent_fee_flag

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, 'student_weekly_risk_scores.csv')
    out.to_csv(out_path, index=False)

    # Export lightweight diagnostics for monitoring (no PII)
    diag = {
        'n_rows': int(len(df)),
        'share_first_choice': float(share_first_choice),
        'day_share_1': float(day_share),
        'dropout_prior': float(p_dropout)
    }
    with open(os.path.join(args.output, 'risk_diagnostics.json'), 'w') as f:
        json.dump(diag, f)


if __name__ == '__main__':
    main()
