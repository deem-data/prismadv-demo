import argparse
import json
import os

import numpy as np
import pandas as pd


def logistic(x):
    return 1.0 / (1.0 + np.exp(-x))


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

# Load data
input_csv = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_csv)

# ---- Pay band audit setup ----
allowed_slabs = ["Upto 5k", "5k-10k", "10k-15k", "15k+"]

# ASSERTION_START
assert set(df["SalarySlab"].dropna().unique()).issubset(set(allowed_slabs))
# ASSERTION_END

# Row-level consistency of MonthlyIncome vs SalarySlab boundaries
mi = df["MonthlyIncome"]
sl = df["SalarySlab"]

in_upto_5k = (sl == "Upto 5k") & (mi > 0) & (mi <= 5000)
in_5k_10k = (sl == "5k-10k") & (mi > 5000) & (mi <= 10000)
in_10k_15k = (sl == "10k-15k") & (mi > 10000) & (mi <= 15000)
in_15k_plus = (sl == "15k+") & (mi > 15000)

row_ok = in_upto_5k | in_5k_10k | in_10k_15k | in_15k_plus
# ASSERTION_START
assert row_ok.all()
# ASSERTION_END

# Median monotonicity across slabs
df["SalarySlab"] = pd.Categorical(df["SalarySlab"], categories=allowed_slabs, ordered=True)
medians = df.groupby("SalarySlab", observed=False)["MonthlyIncome"].median()
ordered_medians = np.array([medians.loc[s] for s in allowed_slabs])

# ASSERTION_START
assert np.all(np.diff(ordered_medians) > 0)
# ASSERTION_END

# Use median progression to derive a compensation progression index (used later in risk scoring)
progression_logs = np.log(ordered_medians[1:] / ordered_medians[:-1])
progression_index = float(np.mean(progression_logs))

# Department and role integrity used for downstream grouping
dept_allowed = {"Sales", "Research & Development", "Human Resources"}

# ASSERTION_START
assert set(df["Department"].dropna().unique()).issubset(dept_allowed)
# ASSERTION_END

sales_roles = {"Sales Executive", "Sales Representative"}
rd_roles = {"Research Scientist", "Laboratory Technician", "Research Director", "Manufacturing Director"}
hr_roles = {"Human Resources"}

# ASSERTION_START
mask_sales = df["JobRole"].isin(sales_roles)
mask_rd = df["JobRole"].isin(rd_roles)
mask_hr = df["JobRole"].isin(hr_roles)
assert (df.loc[mask_sales, "Department"] == "Sales").all()
assert (df.loc[mask_rd, "Department"] == "Research & Development").all()
assert (df.loc[mask_hr, "Department"] == "Human Resources").all()
# ASSERTION_END

# Department share check prior to department-weighted metrics
rd_share = (df["Department"] == "Research & Development").mean()

# ASSERTION_START
assert rd_share >= 0.60
# ASSERTION_END

# ---- Age and AgeGroup integrity used for risk segmentation ----
# ASSERTION_START
assert df["Age"].between(18, 65).all()
# ASSERTION_END

allowed_age_groups = {"18-25", "26-35", "36-45", "46-55", "55+"}

# ASSERTION_START
assert set(df["AgeGroup"].dropna().unique()).issubset(allowed_age_groups)
# ASSERTION_END

age = df["Age"]
ageg = df["AgeGroup"]

# ASSERTION_START
m_18_25 = (ageg == "18-25")
m_26_35 = (ageg == "26-35")
m_36_45 = (ageg == "36-45")
m_46_55 = (ageg == "46-55")
m_55p = (ageg == "55+")
assert ((~m_18_25) | (age.between(18, 25))).all()
assert ((~m_26_35) | (age.between(26, 35))).all()
assert ((~m_36_45) | (age.between(36, 45))).all()
assert ((~m_46_55) | (age.between(46, 55))).all()
assert ((~m_55p) | (age >= 55)).all()
# ASSERTION_END

major_groups = df["AgeGroup"].isin(["26-35", "36-45"]).mean()
# ASSERTION_START
assert major_groups >= 0.70
# ASSERTION_END

# ---- Tenure logical constraints and coverage ----
# ASSERTION_START
assert (df["YearsSinceLastPromotion"] <= df["YearsAtCompany"]).all()
# ASSERTION_END

# ASSERTION_START
assert (df["YearsInCurrentRole"] <= df["YearsAtCompany"]).all()
# ASSERTION_END

# ASSERTION_START
mask_mngr = df["YearsWithCurrManager"].notna() & df["YearsAtCompany"].notna()
assert (df.loc[mask_mngr, "YearsWithCurrManager"] <= df.loc[mask_mngr, "YearsAtCompany"]).all()
# ASSERTION_END

# ASSERTION_START
assert (df["YearsAtCompany"] <= df["TotalWorkingYears"]).all()
# ASSERTION_END

# ASSERTION_START
assert (df["TotalWorkingYears"] <= (df["Age"] - 15)).all()
# ASSERTION_END

# ASSERTION_START
assert df["YearsWithCurrManager"].notna().mean() >= 0.95
# ASSERTION_END

# Features derived from tenure that depend on constraints above
external_experience = (df["TotalWorkingYears"] - df["YearsAtCompany"]).clip(lower=0)
career_start_age = df["Age"] - df["TotalWorkingYears"]
manager_ratio = np.where(df["YearsAtCompany"] > 0, df["YearsWithCurrManager"].fillna(0) / df["YearsAtCompany"], 1.0)
manager_ratio = np.clip(manager_ratio, 0.0, 1.0)

# Use square root; requires non-negative external_experience
ext_exp_signal = np.sqrt(external_experience)
career_start_signal = (career_start_age - 15).clip(lower=0)

# ---- Performance and compensation change checks ----
# ASSERTION_START
assert set(df["PerformanceRating"].dropna().unique()).issubset({3, 4})
# ASSERTION_END

# ASSERTION_START
assert df["PercentSalaryHike"].between(11, 25).all()
# ASSERTION_END

# ASSERTION_START
mean_hike_by_rating = df.groupby("PerformanceRating", observed=False)["PercentSalaryHike"].mean()
mean3 = float(mean_hike_by_rating.get(3, np.nan))
mean4 = float(mean_hike_by_rating.get(4, np.nan))
assert mean4 >= mean3
# ASSERTION_END

# ASSERTION_START
pct_pr3 = (df["PerformanceRating"] == 3).mean()
assert pct_pr3 >= 0.80
# ASSERTION_END

# Performance factors for risk scoring
perf_adj = np.where(df["PerformanceRating"] == 4, 0.95, 1.05)
comp_change_norm = (25 - df["PercentSalaryHike"]) / 14.0
comp_change_norm = np.clip(comp_change_norm, 0.0, 2.0)

# ---- Attrition and OverTime distribution checks for calibration ----
# ASSERTION_START
assert set(df["Attrition"].dropna().unique()).issubset({"Yes", "No"})
# ASSERTION_END

# ASSERTION_START
assert set(df["OverTime"].dropna().unique()).issubset({"Yes", "No"})
# ASSERTION_END

attr = (df["Attrition"] == "Yes").astype(int)
ot_yes = (df["OverTime"] == "Yes")

overall_attr_rate = attr.mean()
ot_yes_prop = ot_yes.mean()
# ASSERTION_START
assert (overall_attr_rate >= 0.10) and (overall_attr_rate <= 0.25)
assert (ot_yes_prop >= 0.20) and (ot_yes_prop <= 0.40)
# ASSERTION_END

rate_yes = np.where(ot_yes.sum() > 0, attr[ot_yes].mean(), np.nan)
rate_no = np.where((~ot_yes).sum() > 0, attr[~ot_yes].mean(), np.nan)
# ASSERTION_START
assert rate_yes >= 1.2 * rate_no
# ASSERTION_END

# Calibrate OT multiplier from observed rates
ot_multiplier = np.where(ot_yes, np.log((rate_yes + 1e-6) / (rate_no + 1e-6)), 0.0)

# ---- Risk scoring ----
# Satisfaction composite (normalized to 0..1 dissatisfaction)
satisfaction_cols = ["JobSatisfaction", "EnvironmentSatisfaction", "WorkLifeBalance"]
sat_mean = df[satisfaction_cols].mean(axis=1)
dissat = 1.0 - (sat_mean - 1.0) / 3.0

dissat = np.clip(dissat, 0.0, 1.0)

# Tenure-related signals
no_promo_signal = np.where(df["YearsAtCompany"] > 0,
                           df["YearsSinceLastPromotion"] / df["YearsAtCompany"],
                           0.0)
no_promo_signal = np.clip(no_promo_signal, 0.0, 1.0)

role_stagnation = 1.0 - manager_ratio

# Age weighting
age_weights = {
    "18-25": 1.10,
    "26-35": 1.00,
    "36-45": 0.95,
    "46-55": 0.90,
    "55+": 0.88,
}
age_w = df["AgeGroup"].map(age_weights).astype(float)

# Department influence (calibrated with R&D majority)
dept_weight = df["Department"].map({
    "Research & Development": 0.0 + np.log(max(rd_share, 1e-6) / 0.60),
    "Sales": 0.05,
    "Human Resources": 0.02,
}).astype(float)

# Compensation progression signal leveraged from global bands
comp_progression_signal = progression_index

# Assemble linear score
intercept = np.log(overall_attr_rate / max(1e-6, 1 - overall_attr_rate))
linear_score = (
        intercept
        + 0.8 * dissat
        + 0.6 * no_promo_signal
        + 0.4 * role_stagnation
        + 0.3 * comp_change_norm
        + 0.35 * ot_multiplier
        + 0.1 * (ext_exp_signal / (ext_exp_signal.max() if ext_exp_signal.max() > 0 else 1))
        + 0.05 * (career_start_signal / (career_start_signal.max() if career_start_signal.max() > 0 else 1))
        + 0.2 * dept_weight
        - 0.1 * comp_progression_signal
)

risk_score = logistic(linear_score) * age_w * perf_adj
risk_score = np.clip(risk_score, 0.0, 1.0)

# Build attrition risk output
risk_out = df[["EmpID", "EmployeeNumber", "Department", "JobRole", "AgeGroup", "OverTime", "PerformanceRating",
               "PercentSalaryHike"]].copy()
risk_out["attrition_risk_score"] = risk_score
risk_out_path = os.path.join(args.output, "attrition_risk_scores.csv")
risk_out.to_csv(risk_out_path, index=False)

# ---- Pay-band audit outputs ----
# Group audit by Department and SalarySlab
salary_ok = row_ok

pay_audit = (
    df.assign(salary_ok=salary_ok)
    .groupby(["Department", "SalarySlab"], observed=False)
    .agg(
        headcount=("EmpID", "count"),
        median_income=("MonthlyIncome", "median"),
        min_income=("MonthlyIncome", "min"),
        max_income=("MonthlyIncome", "max"),
        pct_in_range=("salary_ok", "mean"),
    )
    .reset_index()
)

# Add global band progression index so auditors can compare progression health
pay_audit["band_progression_index"] = progression_index

pay_out_path = os.path.join(args.output, "pay_band_audit.csv")
pay_audit.to_csv(pay_out_path, index=False)

# Also produce a small JSON summary for governance dashboards
summary = {
    "overall_attrition_rate": float(overall_attr_rate),
    "overtime_yes_proportion": float(ot_yes_prop),
    "overtime_attrition_ratio": float(rate_yes / max(1e-9, rate_no)),
    "rd_share": float(rd_share),
    "age_majority_share_26_45": float(major_groups),
    "band_progression_index": float(progression_index),
}
with open(os.path.join(args.output, "kpi_summary.json"), "w") as f:
    json.dump(summary, f)
