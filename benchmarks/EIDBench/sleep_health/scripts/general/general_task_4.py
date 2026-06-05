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
    df = pd.read_csv(input_csv)

    # ASSERTION_START
    from pandas.api.types import is_integer_dtype
    assert is_integer_dtype(df["Person ID"]) and (df["Person ID"] > 0).all() and df["Person ID"].is_unique
    # ASSERTION_END

    # ASSERTION_START
    sd = df["Sleep Duration"]
    assert sd.notna().all() and sd.between(3.0, 12.0).all()
    # ASSERTION_END

    # ASSERTION_START
    q = df["Quality of Sleep"].astype(float)
    assert q.between(4, 9).all() and (q.round() == q).all() and (q.between(6, 9).mean() >= 0.95)
    # ASSERTION_END

    # ASSERTION_START
    acceptable_bmi = {"Normal", "Normal Weight", "Overweight", "Obese"}
    assert df["BMI Category"].notna().all() and df["BMI Category"].isin(acceptable_bmi).all()
    # ASSERTION_END

    # ASSERTION_START
    bp_str = df["Blood Pressure"].astype(str)
    assert bp_str.str.match(r"^\d{2,3}/\d{2,3}$", na=False).all()
    # ASSERTION_END

    bp_split = df["Blood Pressure"].str.split("/", expand=True)
    df["BP_SYS"] = bp_split[0].astype(int)
    df["BP_DIA"] = bp_split[1].astype(int)

    # ASSERTION_START
    assert df["BP_SYS"].between(90, 200).all() and df["BP_DIA"].between(50, 130).all() and (
                df["BP_SYS"] > df["BP_DIA"]).all()
    # ASSERTION_END

    # ASSERTION_START
    sdcol = df["Sleep Disorder"]
    mask = sdcol.notna()
    assert sdcol[mask].isin(["Insomnia", "Sleep Apnea"]).all() and (sdcol.isna().mean() >= 0.5)
    # ASSERTION_END

    # Correlation checks and preparation for model calibration
    pa = df["Physical Activity Level"].astype(float)
    steps = df["Daily Steps"].astype(float)
    corr_pa_steps = pa.corr(steps)

    # ASSERTION_START
    import numpy as _np
    assert _np.isfinite(corr_pa_steps) and (corr_pa_steps > 0.4)
    # ASSERTION_END

    slope = ((pa - pa.mean()) * (steps - steps.mean())).mean() / (pa.var(ddof=0) if pa.var(ddof=0) != 0 else 1.0)
    intercept = steps.mean() - slope * pa.mean()
    steps_pred = slope * pa + intercept

    corr_sd_q = df["Sleep Duration"].astype(float).corr(df["Quality of Sleep"].astype(float))
    # ASSERTION_START
    import numpy as _np
    assert _np.isfinite(corr_sd_q) and (corr_sd_q > 0.2)
    # ASSERTION_END

    stress = df["Stress Level"].astype(float)
    corr_stress_q = stress.corr(df["Quality of Sleep"].astype(float))
    # ASSERTION_START
    import numpy as _np
    assert _np.isfinite(corr_stress_q) and (corr_stress_q < -0.3)
    # ASSERTION_END

    # Feature scaling
    duration_norm = (df["Sleep Duration"].astype(float) - 3.0) / 9.0
    qos_norm = (df["Quality of Sleep"].astype(float) - 4.0) / 5.0

    smin, smax = float(stress.min()), float(stress.max())
    stress_range = (smax - smin) if (smax - smin) > 0 else 1.0
    stress_score = 1.0 - (stress - smin) / stress_range

    sys_dev = (df["BP_SYS"].astype(float) - 120.0).abs() / 80.0
    dia_dev = (df["BP_DIA"].astype(float) - 80.0).abs() / 50.0
    bp_score = 1.0 - np.clip(0.5 * sys_dev + 0.5 * dia_dev, 0.0, 1.0)

    steps_mean = max(steps.mean(), 1.0)
    activity_score = 1.0 - np.clip((steps - steps_pred).abs() / steps_mean, 0.0, 1.0)

    bmi_penalty_map = {
        "Normal": 0.0,
        "Normal Weight": 0.0,
        "Overweight": 0.10,
        "Obese": 0.20,
    }
    bmi_penalty = df["BMI Category"].map(bmi_penalty_map).astype(float)

    unknown_penalty = 0.05
    disorder_penalty = (
        df["Sleep Disorder"].map({"Insomnia": 0.20, "Sleep Apnea": 0.30}).fillna(unknown_penalty)
    ).astype(float)

    synergy = np.clip(0.6 * (qos_norm + duration_norm) / 2.0 + 0.4 * np.sqrt(qos_norm * duration_norm), 0.0, 1.0)

    # Weight calibration using correlations
    w_synergy = 0.35 + 0.10 * float(min(max((corr_sd_q - 0.2) / 0.6, 0.0), 1.0))
    w_stress = 0.20 + 0.10 * float(min(max(((-corr_stress_q) - 0.3) / 0.5, 0.0), 1.0))
    w_activity = 0.20
    w_bp = 0.15

    w_sum = w_synergy + w_stress + w_activity + w_bp
    w_synergy /= w_sum
    w_stress /= w_sum
    w_activity /= w_sum
    w_bp /= w_sum

    base_score = (
            w_synergy * synergy +
            w_activity * activity_score +
            w_bp * bp_score +
            w_stress * stress_score
    )

    penalty_total = np.clip(0.5 * bmi_penalty + 0.5 * disorder_penalty, 0.0, 1.0)
    shi = np.clip(100.0 * (base_score * (1.0 - penalty_total)), 0.0, 100.0)

    df["SleepHealthIndex"] = shi.round(2)

    # Risk rules
    high_bp = (df["BP_SYS"] >= 140) | (df["BP_DIA"] >= 90)
    low_sleep = (df["Sleep Duration"] < 5.5) | (df["Quality of Sleep"] <= 5)
    low_index = df["SleepHealthIndex"] < 60

    reasons = []
    for i in range(len(df)):
        r = []
        if high_bp.iat[i]:
            r.append("bp")
        if low_sleep.iat[i]:
            r.append("sleep")
        if low_index.iat[i]:
            r.append("index")
        reasons.append(";".join(r) if r else "")

    df["RiskAlert"] = high_bp | low_sleep | low_index
    df["RiskReasons"] = reasons

    # Array-based write relying on positive, unique Person IDs
    max_id = int(df["Person ID"].max())
    shi_array = np.zeros(max_id + 1, dtype=float)
    alert_array = np.zeros(max_id + 1, dtype=np.int8)

    for pid, s, a in df[["Person ID", "SleepHealthIndex", "RiskAlert"]].itertuples(index=False):
        shi_array[int(pid)] = float(s)
        alert_array[int(pid)] = 1 if bool(a) else 0

    os.makedirs(args.output, exist_ok=True)
    df_out = df[["Person ID", "SleepHealthIndex", "RiskAlert", "RiskReasons"]].copy()
    df_out.to_csv(os.path.join(args.output, 'sleep_health_index.csv'), index=False)

    alerts = df_out[df_out["RiskAlert"]]
    alerts.to_csv(os.path.join(args.output, 'alerts.csv'), index=False)

    # Persist simple calibration summary
    calib = pd.DataFrame({
        "metric": [
            "corr_physicalActivity_dailySteps",
            "corr_sleepDuration_qualityOfSleep",
            "corr_stress_qualityOfSleep"
        ],
        "value": [
            round(float(corr_pa_steps), 4),
            round(float(corr_sd_q), 4),
            round(float(corr_stress_q), 4)
        ]
    })
    calib.to_csv(os.path.join(args.output, 'calibration_summary.csv'), index=False)


if __name__ == '__main__':
    main()
