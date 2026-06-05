import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path / 'new_data.csv')

    # ASSERTION_START
    # Guard: Blood Pressure format and ranges before parsing
    bp = df['Blood Pressure'].astype(str)
    pattern = r'^\d{2,3}/\d{2,3}$'
    m = bp.str.match(pattern, na=False)
    assert m.all()
    # ASSERTION_END
    # Safe parsing after validation
    df['Systolic'] = df['Blood Pressure'].str.split('/').str[0].astype(int)
    df['Diastolic'] = df['Blood Pressure'].str.split('/').str[1].astype(int)

    # ASSERTION_START
    # Guard: Quality of Sleep shape before using it for downstream scoring
    q = pd.to_numeric(df['Quality of Sleep'], errors='coerce')
    assert q.notna().all()
    assert (((q % 1) == 0) & (q >= 1) & (q <= 10)).all()

    # ASSERTION_END
    qos = pd.to_numeric(df['Quality of Sleep'], errors='raise').astype(int)
    sleep_duration = pd.to_numeric(df['Sleep Duration'], errors='coerce')

    # Guard: Sleep Duration and Quality of Sleep relationship before computing restful hours
    restful_hours = sleep_duration * (qos / 10.0)
    restful_target = 7.5
    restful_deficit = np.maximum(restful_target - restful_hours, 0)
    restful_deficit_norm = np.clip(restful_deficit / restful_target, 0, 1)

    pal = pd.to_numeric(df['Physical Activity Level'], errors='coerce')
    steps = pd.to_numeric(df['Daily Steps'], errors='coerce')

    # ASSERTION_START
    # Guard: Activity vs Steps assumptions before using correlation-based expectation
    # Ensure no NaNs before calculating correlation
    assert pal.notna().all()
    assert steps.notna().all()
    # ASSERTION_END
    pal_mean = pal.mean()
    pal_std = pal.std(ddof=0)
    steps_mean = steps.mean()
    steps_std = steps.std(ddof=0)
    r2 = np.corrcoef(pal, steps)[0, 1]
    expected_steps_from_pal = steps_mean + r2 * (steps_std / pal_std) * (pal - pal_mean)
    steps_gap = steps - expected_steps_from_pal
    activity_shortfall = np.maximum(-steps_gap, 0)
    activity_shortfall_norm = np.clip(activity_shortfall / 4000.0, 0, 1)

    # ASSERTION_START
    # Guard: Label quality before using labeled rows for calibration
    label = df['Sleep Disorder']
    valid_vals = label.isna() | label.isin(['Insomnia', 'Sleep Apnea'])
    assert valid_vals.all()
    # ASSERTION_END
    labeled = df[df['Sleep Disorder'].isin(['Insomnia', 'Sleep Apnea'])].copy()
    ins_mask_lbl = labeled['Sleep Disorder'] == 'Insomnia'
    ap_mask_lbl = labeled['Sleep Disorder'] == 'Sleep Apnea'

    ins_mean_stress = labeled.loc[ins_mask_lbl, 'Stress Level'].mean() if ins_mask_lbl.any() else np.nan
    ap_mean_stress = labeled.loc[ap_mask_lbl, 'Stress Level'].mean() if ap_mask_lbl.any() else np.nan

    if np.isnan(ins_mean_stress) or np.isnan(ap_mean_stress):
        stress_threshold = 5.0
    else:
        stress_threshold = float((ins_mean_stress + ap_mean_stress) / 2.0)

    apnea_over_prop = labeled.loc[ap_mask_lbl, 'BMI Category'].isin(
        ['Overweight', 'Obese']).mean() if ap_mask_lbl.any() else 0.7

    stress = pd.to_numeric(df['Stress Level'], errors='coerce')
    stress_score = (stress - stress_threshold) / max(1e-6, (10 - stress_threshold))
    stress_score = np.clip(stress_score, 0, 1)

    sedentary_flag = ((steps <= 3000) | (pal <= 40)).astype(int)

    insomnia_risk_score = 0.5 * restful_deficit_norm + 0.3 * stress_score + 0.2 * sedentary_flag

    is_over_obese = df['BMI Category'].isin(['Overweight', 'Obese']).astype(int)
    bp_high = ((df['Systolic'] >= 130) | (df['Diastolic'] >= 85)).astype(int)
    low_qos_long_sleep = ((qos <= 6) & (sleep_duration >= 7)).astype(int)

    apnea_risk_score = 0.6 * is_over_obese + 0.2 * bp_high + 0.2 * low_qos_long_sleep

    insomnia_threshold = float(np.clip(0.55 - 0.05 * max(0.0, (ins_mean_stress - ap_mean_stress)) if not (
                np.isnan(ins_mean_stress) or np.isnan(ap_mean_stress)) else 0.0, 0.40, 0.60))
    apnea_threshold = float(np.clip(0.55 - 0.10 * (apnea_over_prop - 0.70), 0.45, 0.65))

    risk_insomnia = insomnia_risk_score >= insomnia_threshold
    risk_apnea = apnea_risk_score >= apnea_threshold

    reasons = []
    for i in range(len(df)):
        r = []
        if risk_insomnia.iloc[i]:
            r.append('insomnia')
        if risk_apnea.iloc[i]:
            r.append('sleep_apnea')
        reasons.append(','.join(r) if r else '')

    # Personalized coaching recommendations
    coaching = []
    for i in range(len(df)):
        modules = []
        if risk_insomnia.iloc[i]:
            modules.append('CBT-I')
            modules.append('stress_management')
            modules.append('sleep_hygiene')
            if steps.iloc[i] < 8000:
                modules.append('progressive_activity_plan')
        if risk_apnea.iloc[i]:
            modules.append('sleep_apnea_screening')
            modules.append('weight_management')
            modules.append('cpap_education')
        coaching.append('|'.join(modules))

    out_df = pd.DataFrame({
        'Person ID': df['Person ID'],
        'risk_insomnia': risk_insomnia.astype(int),
        'risk_sleep_apnea': risk_apnea.astype(int),
        'insomnia_risk_score': insomnia_risk_score.round(3),
        'apnea_risk_score': apnea_risk_score.round(3),
        'reason': reasons,
        'restful_hours': restful_hours.round(2),
        'Stress Level': stress,
        'Physical Activity Level': pal,
        'Daily Steps': steps,
        'Quality of Sleep': qos,
        'Systolic': df['Systolic'],
        'Diastolic': df['Diastolic']
    })

    plans_df = pd.DataFrame({
        'Person ID': df['Person ID'],
        'coaching_modules': coaching
    })

    out_df.to_csv(output_path / 'risk_flags.csv', index=False)
    plans_df.to_csv(output_path / 'coaching_plan.csv', index=False)


if __name__ == '__main__':
    main()
