import argparse
import os
import pandas as pd
import numpy as np


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

# Load data
input_csv = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_csv)

# Select columns used downstream
col_gdp = 'GDP'
col_unemp = 'Unemployment rate'
col_infl = 'Inflation rate'
col_app_order = 'Application order'
col_debtor = 'Debtor'
col_tuition = 'Tuition fees up to date'
col_adm = 'Admission grade'
col_prev = 'Previous qualification (grade)'

col_en1 = 'Curricular units 1st sem (enrolled)'
col_ap1 = 'Curricular units 1st sem (approved)'
col_cr1 = 'Curricular units 1st sem (credited)'
col_wo1 = 'Curricular units 1st sem (without evaluations)'
col_gr1 = 'Curricular units 1st sem (grade)'

col_en2 = 'Curricular units 2nd sem (enrolled)'
col_ap2 = 'Curricular units 2nd sem (approved)'
col_cr2 = 'Curricular units 2nd sem (credited)'
col_wo2 = 'Curricular units 2nd sem (without evaluations)'
col_gr2 = 'Curricular units 2nd sem (grade)'

# Macro constraints before computing macro stress
mac_gdp = pd.to_numeric(df[col_gdp], errors='coerce')
mac_unemp = pd.to_numeric(df[col_unemp], errors='coerce')
mac_infl = pd.to_numeric(df[col_infl], errors='coerce')
# ASSERTION_START
assert mac_gdp.notna().all() and mac_unemp.notna().all() and mac_infl.notna().all()
# Ensure standard deviation is non-zero to prevent division by zero in z-score calculation.
assert mac_gdp.std(ddof=0) > 0
assert mac_unemp.std(ddof=0) > 0
assert mac_infl.std(ddof=0) > 0
# ASSERTION_END
# Macro stress feature (higher = worse environment)
zg = (mac_gdp - mac_gdp.mean()) / mac_gdp.std(ddof=0)
zu = (mac_unemp - mac_unemp.mean()) / mac_unemp.std(ddof=0)
zi = (mac_infl - mac_infl.mean()) / mac_infl.std(ddof=0)
macro_stress = sigmoid(zu - zg + 0.3 * zi)

# Application order checks before mapping to weights
app_order = pd.to_numeric(df[col_app_order], errors='coerce').astype('Int64')
# ASSERTION_START
assert app_order.notna().all()
# The indexing operation `commit_weights[app_order.to_numpy()]` requires
# values to be valid indices for the `commit_weights` array.
assert app_order.between(1, 9).all()
# ASSERTION_END
# Map application order to commitment weights (1 -> strongest commitment)
# Index 0 is unused to align indexes with order values 1..9
commit_weights = np.array([0.0, 1.0, 0.85, 0.78, 0.70, 0.65, 0.60, 0.55, 0.50, 0.45])
commitment = commit_weights[app_order.to_numpy()]  # relies on 1..9 constraint

# Payment status consistency and prevalence before deriving arrears factor
is_debtor = pd.to_numeric(df[col_debtor], errors='coerce').astype(int)
fees_up_to_date = pd.to_numeric(df[col_tuition], errors='coerce').astype(int)
arrears = ((is_debtor == 1) | (fees_up_to_date == 0)).astype(int)

# Academic preparedness consistency before using grades
adm_grade = pd.to_numeric(df[col_adm], errors='coerce')
prev_grade = pd.to_numeric(df[col_prev], errors='coerce')
preparedness = 0.6 * (adm_grade / 200.0) + 0.4 * (prev_grade / 200.0)

# Semester 1 academic constraints before pass-rate and ratios
en1 = pd.to_numeric(df[col_en1], errors='coerce').astype(int)
ap1 = pd.to_numeric(df[col_ap1], errors='coerce').astype(int)
cr1 = pd.to_numeric(df[col_cr1], errors='coerce').astype(int)
wo1 = pd.to_numeric(df[col_wo1], errors='coerce').astype(int)
gr1 = pd.to_numeric(df[col_gr1], errors='coerce')
# ASSERTION_START
assert gr1.notna().all()
assert en1.notna().all()
assert ap1.notna().all()
assert wo1.notna().all()
assert (en1 >= 0).all()
assert (ap1 >= 0).all()
assert (wo1 >= 0).all()
assert (ap1 <= en1).all()
assert (wo1 <= en1).all()
assert (gr1 >= 0).all()
mask_en1_zero = (en1 == 0)
assert (gr1[mask_en1_zero] == 0).all()
# Check for non-zero standard deviation to prevent division by zero or NaN in slope calculation.
assert en1.std(ddof=0) > 0
# ASSERTION_END
pass_rate1 = np.where(en1 > 0, ap1 / en1.replace(0, np.nan), 1.0)
grade_norm1 = gr1 / 20.0
noeval_ratio1 = np.where(en1 > 0, wo1 / en1.replace(0, np.nan), 0.0)

# Estimate expected approvals from enrollment using simple linear relation (slope, intercept)
# Precondition: strong positive correlation ensured above
slope1 = ap1.std(ddof=0) / en1.std(ddof=0) * ap1.corr(en1)
intercept1 = ap1.mean() - slope1 * en1.mean()
expected_ap1 = slope1 * en1 + intercept1
success_gap1 = np.maximum(expected_ap1 - ap1, 0)
success_gap_ratio1 = np.where(en1 > 0, success_gap1 / en1.replace(0, np.nan), 0.0)

# Semester 2 academic constraints before pass-rate and ratios
en2 = pd.to_numeric(df[col_en2], errors='coerce').astype(int)
ap2 = pd.to_numeric(df[col_ap2], errors='coerce').astype(int)
cr2 = pd.to_numeric(df[col_cr2], errors='coerce').astype(int)
wo2 = pd.to_numeric(df[col_wo2], errors='coerce').astype(int)
gr2 = pd.to_numeric(df[col_gr2], errors='coerce')
# ASSERTION_START
assert gr2.notna().all()
assert en2.notna().all()
assert ap2.notna().all()
assert wo2.notna().all()
assert (en2 >= 0).all()
assert (ap2 >= 0).all()
assert (wo2 >= 0).all()
assert (ap2 <= en2).all()
assert (wo2 <= en2).all()
assert (gr2 >= 0).all()
mask_en2_zero = (en2 == 0)
assert (gr2[mask_en2_zero] == 0).all()
# Check for non-zero standard deviation to prevent division by zero or NaN in slope calculation.
assert en2.std(ddof=0) > 0
# ASSERTION_END
pass_rate2 = np.where(en2 > 0, ap2 / en2.replace(0, np.nan), 1.0)
grade_norm2 = gr2 / 20.0
noeval_ratio2 = np.where(en2 > 0, wo2 / en2.replace(0, np.nan), 0.0)

slope2 = ap2.std(ddof=0) / en2.std(ddof=0) * ap2.corr(en2)
intercept2 = ap2.mean() - slope2 * en2.mean()
expected_ap2 = slope2 * en2 + intercept2
success_gap2 = np.maximum(expected_ap2 - ap2, 0)
success_gap_ratio2 = np.where(en2 > 0, success_gap2 / en2.replace(0, np.nan), 0.0)

# Aggregate academic features
total_enrolled = en1 + en2
total_approved = ap1 + ap2
progress = np.where(total_enrolled > 0, total_approved / total_enrolled.replace(0, np.nan), 1.0)
mean_grade_norm = (grade_norm1 + grade_norm2) / 2.0
mean_noeval_ratio = (noeval_ratio1 + noeval_ratio2) / 2.0
mean_success_gap_ratio = (success_gap_ratio1 + success_gap_ratio2) / 2.0

# Risk composition
payment_component = 0.40 * arrears
progress_component = 0.25 * (1.0 - np.clip(progress, 0.0, 1.0))
grade_component = 0.10 * (1.0 - np.clip(mean_grade_norm, 0.0, 1.0))
gap_component = 0.10 * np.clip(mean_success_gap_ratio, 0.0, 1.0)
noeval_component = 0.05 * np.clip(mean_noeval_ratio, 0.0, 1.0)
commitment_component = 0.05 * (1.0 - np.clip(commitment, 0.0, 1.0))
macro_component = 0.05 * np.clip(macro_stress, 0.0, 1.0)
prep_component = 0.0 * (1.0 - np.clip(preparedness, 0.0, 1.0))  # reserved weight if needed

risk_raw = payment_component + progress_component + grade_component + gap_component + noeval_component + commitment_component + macro_component + prep_component
risk_score = np.clip(risk_raw, 0.0, 1.0)

# Produce advisor queue (top risks)
output = df.copy()
output['dropout_risk_score'] = risk_score
output['priority_tier'] = pd.cut(
    output['dropout_risk_score'],
    bins=[-0.01, 0.3, 0.5, 0.7, 1.0],
    labels=['Low', 'Moderate', 'High', 'Critical']
).astype(str)
output['row_id'] = np.arange(len(output))

# Persist outputs
scores_path = os.path.join(args.output, 'dropout_risk_scores.csv')
queue_path = os.path.join(args.output, 'advisor_intervention_queue.csv')

output[['row_id', 'dropout_risk_score', 'priority_tier']].to_csv(scores_path, index=False)

queue_cols = ['row_id', 'dropout_risk_score', 'priority_tier', col_app_order, col_debtor, col_tuition]
queue = output.sort_values('dropout_risk_score', ascending=False).head(200)
queue[queue_cols].to_csv(queue_path, index=False)
