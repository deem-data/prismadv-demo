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

    input_file = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_file)

    # Basic type coercion for numeric fields
    num_cols = ['Sleep Duration', 'Quality of Sleep', 'Physical Activity Level', 'Stress Level', 'Daily Steps', 'Age',
                'Heart Rate']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Parse blood pressure into systolic/diastolic
    bp_str = df['Blood Pressure'].astype(str)
    bp_parts = bp_str.str.extract(r'(?P<SBP>\d{2,3})/(?P<DBP>\d{2,3})')
    df['SBP'] = pd.to_numeric(bp_parts['SBP'], errors='coerce')
    df['DBP'] = pd.to_numeric(bp_parts['DBP'], errors='coerce')
    # ASSERTION_START
    assert df['SBP'].notna().all() and (df['SBP'] > 0).all()
    assert df['DBP'].notna().all() and (df['DBP'] > 0).all()
    assert (df['SBP'] >= df['DBP']).all()
    # ASSERTION_END
    # Blood pressure derived metrics
    df['PP'] = df['SBP'] - df['DBP']
    df['MAP'] = df['DBP'] + df['PP'] / 3.0

    # Sleep duration range guard before computing debt and regression features
    sleep_hours = df['Sleep Duration'].astype(float)
    # Sleep debt relative to 8 hours (clipped at [-2, 5] to bound effect)
    df['sleep_debt'] = np.clip(8.0 - sleep_hours, -2.0, 5.0)
    df['sleep_debt_pos'] = np.maximum(df['sleep_debt'], 0.0)

    # Relationship between sleep duration and quality; compute correlation then guard before regression-based features
    qual = df['Quality of Sleep'].astype(float)
    # Handle potential constant vectors safely
    if sleep_hours.std(ddof=0) == 0 or qual.std(ddof=0) == 0:
        corr_sleep_qual = np.nan
    else:
        corr_sleep_qual = float(np.corrcoef(sleep_hours, qual)[0, 1])
    # ASSERTION_START
    assert df['Sleep Duration'].notna().all() and (df['Sleep Duration'] >= 0).all() and (
            df['Sleep Duration'] <= 24).all()
    assert df['Quality of Sleep'].notna().all() and (df['Quality of Sleep'] >= 1).all() and (
            df['Quality of Sleep'] <= 10).all()
    # ASSERTION_END
    slope_sq = corr_sleep_qual * (qual.std(ddof=0) / (sleep_hours.std(ddof=0) + 1e-9))
    intercept_sq = qual.mean() - slope_sq * sleep_hours.mean()
    pred_quality = slope_sq * sleep_hours + intercept_sq
    df['restfulness_residual'] = qual - pred_quality

    # Steps vs physical activity calibration
    steps = df['Daily Steps'].astype(float)
    pal = df['Physical Activity Level'].astype(float)
    if steps.std(ddof=0) == 0 or pal.std(ddof=0) == 0:
        corr_steps_pal = np.nan
    else:
        corr_steps_pal = float(np.corrcoef(steps, pal)[0, 1])
    # ASSERTION_START
    assert df['Daily Steps'].notna().all() and (df['Daily Steps'] >= 0).all()
    assert df['Physical Activity Level'].notna().all() and (df['Physical Activity Level'] >= 0).all()
    # ASSERTION_END
    slope_sp = corr_steps_pal * (pal.std(ddof=0) / (steps.std(ddof=0) + 1e-9))
    intercept_sp = pal.mean() - slope_sp * steps.mean()
    pal_from_steps = slope_sp * steps + intercept_sp
    df['activity_blend'] = 0.5 * pal + 0.5 * pal_from_steps

    # Validate apnea-BMI coupling before using apnea factor in scoring
    # Scoring helpers
    def scale01(x, lo, hi):
        return np.clip((x - lo) / (hi - lo + 1e-9), 0.0, 1.0)

    # Risk components
    df['bp_index'] = scale01(df['MAP'], 85.0, 130.0)

    bmi_map = {
        'Normal': 0.0,
        'Normal Weight': 0.0,
        'Overweight': 0.6,
        'Obese': 1.0,
    }
    df['bmi_risk'] = df['BMI Category'].astype(str).map(bmi_map).fillna(0.3)

    df['age_index'] = scale01(df['Age'].astype(float), 30.0, 70.0)
    df['hr_index'] = scale01(df['Heart Rate'].astype(float), 55.0, 95.0)
    df['stress_index'] = scale01(df['Stress Level'].astype(float), 3.0, 8.0)

    # Sleep risk combines debt and negative residuals (i.e., worse-than-expected QoS for the hours slept)
    sleep_debt_index = scale01(df['sleep_debt_pos'], 0.0, 5.0)
    resid_penalty = np.clip(-df['restfulness_residual'], 0.0, None)
    resid_index = scale01(resid_penalty, 0.0, max(1.0, float(resid_penalty.quantile(0.9))))
    df['sleep_risk'] = 0.6 * sleep_debt_index + 0.4 * resid_index

    # Activity protection (higher activity lowers risk)
    act_index = scale01(df['activity_blend'], float(df['activity_blend'].quantile(0.1)),
                        float(df['activity_blend'].quantile(0.9)))
    df['activity_protect'] = 1.0 - act_index

    # Apnea factor
    apnea_mask = df['Sleep Disorder'].astype(str) == 'Sleep Apnea'
    overweight_obese = df['BMI Category'].astype(str).isin(['Overweight', 'Obese'])
    apnea_cnt = int(apnea_mask.sum())
    if apnea_cnt > 0:
        apnea_ratio = ((apnea_mask & overweight_obese).sum()) / max(apnea_cnt, 1)
    else:
        apnea_ratio = 0.60
    apnea_multiplier = 1.0 + max(0.0, apnea_ratio - 0.60)
    df['apnea_component'] = apnea_multiplier * (
            apnea_mask.astype(float) * (0.05 + 0.05 * overweight_obese.astype(float)))

    # Aggregate cardiometabolic risk [0,1]
    df['risk_score'] = (
            0.25 * df['bp_index'] +
            0.20 * df['bmi_risk'] +
            0.15 * df['age_index'] +
            0.10 * df['stress_index'] +
            0.10 * df['hr_index'] +
            0.15 * df['sleep_risk'] +
            0.10 * df['activity_protect'] +
            df['apnea_component']
    )
    df['risk_score'] = df['risk_score'].clip(0.0, 1.0)

    # Prioritization: top quartile of risk
    threshold = float(df['risk_score'].quantile(0.75))
    df['prioritized_for_outreach'] = df['risk_score'] >= threshold

    # Save outputs
    out_full = df[['Person ID', 'risk_score', 'prioritized_for_outreach']].copy()
    out_full.sort_values(by=['prioritized_for_outreach', 'risk_score', 'Person ID'], ascending=[False, False, True],
                         inplace=True)
    out_full.to_csv(os.path.join(args.output, 'prioritized_members.csv'), index=False)

    detail_cols = [
        'Person ID', 'SBP', 'DBP', 'MAP', 'PP', 'bp_index', 'bmi_risk', 'age_index',
        'hr_index', 'stress_index', 'sleep_risk', 'activity_protect', 'apnea_component', 'risk_score'
    ]
    df[detail_cols].to_csv(os.path.join(args.output, 'risk_scores_detailed.csv'), index=False)


if __name__ == '__main__':
    main()
