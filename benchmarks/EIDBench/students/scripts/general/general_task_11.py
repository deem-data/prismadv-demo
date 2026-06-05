import argparse
import os

import numpy as np
import pandas as pd


def robust_divide(numer, denom, default=0.0):
    numer = np.asarray(numer)
    denom = np.asarray(denom)
    out = np.empty_like(numer, dtype=float)
    mask = denom != 0
    out[mask] = numer[mask] / denom[mask]
    out[~mask] = default
    return out


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

# Load data
input_csv = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_csv)

# Normalize column names (trim whitespace)
df.columns = [c.strip() for c in df.columns]

# Column aliases
c_target = 'Target'
c_day = 'Daytime/evening attendance'
c_age = 'Age at enrollment'
c_app_order = 'Application order'

c1_enr = 'Curricular units 1st sem (enrolled)'
c1_app = 'Curricular units 1st sem (approved)'
c1_cred = 'Curricular units 1st sem (credited)'
c1_woeval = 'Curricular units 1st sem (without evaluations)'
c1_grade = 'Curricular units 1st sem (grade)'

c2_enr = 'Curricular units 2nd sem (enrolled)'
c2_app = 'Curricular units 2nd sem (approved)'
c2_cred = 'Curricular units 2nd sem (credited)'
c2_woeval = 'Curricular units 2nd sem (without evaluations)'
c2_grade = 'Curricular units 2nd sem (grade)'

c_debtor = 'Debtor'
c_fees = 'Tuition fees up to date'
c_scholar = 'Scholarship holder'

c_prev_grade = 'Previous qualification (grade)'
c_admission = 'Admission grade'

c_unemp = 'Unemployment rate'
c_gdp = 'GDP'
c_infl = 'Inflation rate'

# Ensure numeric types for numeric columns used downstream
numeric_cols = [
    c_day, c_age, c_app_order,
    c1_enr, c1_app, c1_cred, c1_woeval, c1_grade,
    c2_enr, c2_app, c2_cred, c2_woeval, c2_grade,
    c_debtor, c_fees, c_scholar,
    c_prev_grade, c_admission,
    c_unemp, c_gdp, c_infl
]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# ASSERTION_START
# Guard Target assumptions before filtering
allowed_targets = {'Graduate', 'Dropout', 'Enrolled'}
assert df[c_target].isin(allowed_targets).all()

# ASSERTION_END
# Keep only currently enrolled for scoring; use all rows for global calibrations where needed
is_enrolled = df[c_target] == 'Enrolled'

# ASSERTION_START
# Application order is used in risk scoring; guard before use
assert (df[c_app_order] >= 1).all()
# ASSERTION_END
# ASSERTION_START
# Daytime/evening and age are used to shape behavioral risk; guard before use
assert df[c_day].isin([0, 1]).all()
assert (df[c_age] >= 16).all()
# ASSERTION_END
# ASSERTION_START
# Academic structure constraints for 1st semester; guard before computing ratios
e1 = df[c1_enr]
a1 = df[c1_app]
cr1 = df[c1_cred]
w1 = df[c1_woeval]
g1 = df[c1_grade]
assert (e1 >= 0).all()
assert (a1 >= 0).all()
assert (cr1 >= 0).all()
assert (w1 >= 0).all()
assert (a1 <= e1).all()
assert (cr1 <= e1).all()
assert (w1 <= e1).all()
assert (g1 >= 0).all()
# ASSERTION_END
# ASSERTION_START
# Academic structure constraints for 2nd semester; guard before computing ratios
e2 = df[c2_enr]
a2 = df[c2_app]
cr2 = df[c2_cred]
w2 = df[c2_woeval]
g2 = df[c2_grade]
assert (e2 >= 0).all()
assert (a2 >= 0).all()
assert (cr2 >= 0).all()
assert (w2 >= 0).all()
assert (a2 <= e2).all()
assert (cr2 <= e2).all()
assert (w2 <= e2).all()
assert (g2 >= 0).all()
# ASSERTION_END
# ASSERTION_START
# Financial constraints are used in financial risk calculation; guard before use
assert df[c_debtor].isin([0, 1]).all()
assert df[c_fees].isin([0, 1]).all()
assert df[c_scholar].isin([0, 1]).all()

# ASSERTION_END
# ASSERTION_START
# Admissions and prior grades inform preparedness; guard before using in normalization
assert (df[c_admission] >= 0).all()
assert (df[c_prev_grade] >= 0).all()
# ASSERTION_END
# ASSERTION_START
# Macroeconomic indicators shape overall headwinds; guard before building macro risk
assert (df[c_unemp] >= 0).all()
assert df[c_gdp].notna().all()
assert df[c_infl].notna().all()
# ASSERTION_END
# Build features needed for risk scoring
approval_rate_1 = robust_divide(df[c1_app], df[c1_enr], default=1.0)
woeval_rate_1 = robust_divide(df[c1_woeval], df[c1_enr], default=0.0)
credit_rate_1 = robust_divide(df[c1_cred], df[c1_enr], default=1.0)

grade1_norm = (df[c1_grade] / 20.0).clip(0, 1)

approval_rate_2 = robust_divide(df[c2_app], df[c2_enr], default=1.0)
woeval_rate_2 = robust_divide(df[c2_woeval], df[c2_enr], default=0.0)
credit_rate_2 = robust_divide(df[c2_cred], df[c2_enr], default=1.0)

grade2_norm = (df[c2_grade] / 20.0).clip(0, 1)

# Academic performance and engagement
fail_rate_1 = robust_divide(df[c1_enr] - df[c1_app], df[c1_enr], default=0.0).clip(0, 1)
fail_rate_2 = robust_divide(df[c2_enr] - df[c2_app], df[c2_enr], default=0.0).clip(0, 1)
no_eval_rate = 0.5 * woeval_rate_1 + 0.5 * woeval_rate_2

# Preparedness
adm_norm = (df[c_admission] / 200.0).clip(0, 1)
prev_norm = (df[c_prev_grade] / 200.0).clip(0, 1)
preparedness = (0.6 * adm_norm + 0.4 * prev_norm)

# Financial risk
financial_risk = (0.6 * df[c_debtor] + 0.3 * (1 - df[c_fees]) - 0.2 * df[c_scholar]).clip(0, 1)

# Attendance and age effects
is_day = (df[c_day] == 1).astype(int)
age_norm = ((df[c_age] - 16) / (70 - 16)).clip(0, 1)
attendance_risk = ((1 - is_day) * 0.25 + age_norm * 0.15).clip(0, 1)

# Application order effect (higher order => higher risk)
app_risk = ((df[c_app_order] - 1) / 8.0).clip(0, 1) * 0.2

# Macro headwinds
unemp_norm = ((df[c_unemp] - 5) / 15.0).clip(0, 1)
gdp_headwind = ((5 - df[c_gdp]) / 10.0).clip(0, 1)
infl_norm = ((df[c_infl] + 2) / 7.0).clip(0, 1)
macro_risk = (0.7 * unemp_norm + 0.2 * gdp_headwind + 0.1 * infl_norm).clip(0, 1)

# Aggregate academic risk (poor grades, failures, lack of evaluations)
academic_perf = (0.25 * approval_rate_1 + 0.25 * approval_rate_2 + 0.25 * grade1_norm + 0.25 * grade2_norm)
engagement_penalty = (0.6 * (fail_rate_1 * 0.5 + fail_rate_2 * 0.5) + 0.4 * no_eval_rate).clip(0, 1)
academic_risk = (1 - academic_perf) * 0.6 + engagement_penalty * 0.4
academic_risk = academic_risk.clip(0, 1)

# Combine components into final risk score
raw_risk = (
        0.45 * academic_risk +
        0.25 * financial_risk +
        0.15 * attendance_risk +
        0.10 * macro_risk +
        0.05 * app_risk
)
risk_score = raw_risk.clip(0, 1)

# Create output for enrolled students only
enrolled_scores = df.loc[is_enrolled, [c_target]].copy()
enrolled_scores['row_id'] = enrolled_scores.index
enrolled_scores['risk_score'] = risk_score[is_enrolled].values

# Priority tiers
bins = [0.0, 0.4, 0.7, 1.0]
labels = ['Low', 'Medium', 'High']
enrolled_scores['priority_tier'] = pd.cut(enrolled_scores['risk_score'], bins=bins, labels=labels, include_lowest=True,
                                          right=True)

# Sort by highest risk first for advisor outreach queue
enrolled_scores = enrolled_scores.sort_values('risk_score', ascending=False)

# Output files
scores_path = os.path.join(args.output, 'weekly_dropout_risk_scores.csv')
queue_path = os.path.join(args.output, 'advisor_outreach_queue.csv')

# Minimal output columns for downstream systems
enrolled_scores[['row_id', 'risk_score', 'priority_tier']].to_csv(scores_path, index=False)

# Top N queue (e.g., top 200 highest risk)
TOP_N = min(200, len(enrolled_scores))
enrolled_scores.head(TOP_N)[['row_id', 'risk_score', 'priority_tier']].to_csv(queue_path, index=False)

print(f"Wrote {len(enrolled_scores)} enrolled student risk scores to {scores_path}")
print(f"Wrote top {TOP_N} advisor outreach queue to {queue_path}")
