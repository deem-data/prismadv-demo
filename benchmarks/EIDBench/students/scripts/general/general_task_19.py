import argparse
import os

import numpy as np
import pandas as pd


def compute_standing_category(score_series):
    good = score_series >= 0.60
    warn = (score_series >= 0.45) & (score_series < 0.60)
    result = np.where(good, 'Good', np.where(warn, 'Warning', 'Probation'))
    return pd.Series(result, index=score_series.index)


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

input_file = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_file)

# Column aliases for readability
CE1 = 'Curricular units 1st sem (enrolled)'
EV1 = 'Curricular units 1st sem (evaluations)'
AP1 = 'Curricular units 1st sem (approved)'
CR1 = 'Curricular units 1st sem (credited)'
WE1 = 'Curricular units 1st sem (without evaluations)'
GR1 = 'Curricular units 1st sem (grade)'

CE2 = 'Curricular units 2nd sem (enrolled)'
EV2 = 'Curricular units 2nd sem (evaluations)'
AP2 = 'Curricular units 2nd sem (approved)'
CR2 = 'Curricular units 2nd sem (credited)'
WE2 = 'Curricular units 2nd sem (without evaluations)'
GR2 = 'Curricular units 2nd sem (grade)'

DEBTOR = 'Debtor'
FEES = 'Tuition fees up to date'
SCH = 'Scholarship holder'
# ASSERTION_START
assert (df[EV1] >= 0).all()
assert (df[AP1] >= 0).all()
assert (df[AP1] <= df[EV1]).all()
# ASSERTION_END
# ASSERTION_START
assert ((df[GR1] >= 0) & (df[GR1] <= 20)).all()
# ASSERTION_END
grade_norm_1 = df[GR1] / 20.0
approved_rate_1 = df[AP1] / df[EV1].replace({0: np.nan})
approved_rate_1 = approved_rate_1.fillna(0.0).clip(0, 1)
credit_load_1 = np.where(df[CE1] > 0, df[CR1] / df[CE1], 0.0)
term1_score = 0.65 * grade_norm_1 + 0.35 * approved_rate_1
term1_standing = compute_standing_category(term1_score)
# ASSERTION_START
assert (df[EV2] >= 0).all()
assert (df[AP2] >= 0).all()
assert (df[WE2] >= 0).all()
assert (df[AP2] <= df[EV2]).all()
# ASSERTION_END
# ASSERTION_START
assert ((df[GR2] >= 0) & (df[GR2] <= 20)).all()
# ASSERTION_END
grade_norm_2 = df[GR2] / 20.0
approved_rate_2 = df[AP2] / df[EV2].replace({0: np.nan})
approved_rate_2 = approved_rate_2.fillna(0.0).clip(0, 1)
credit_load_2 = np.where(df[CE2] > 0, df[CR2] / df[CE2], 0.0)

term2_score = 0.65 * grade_norm_2 + 0.35 * approved_rate_2
term2_standing_base = compute_standing_category(term2_score)
no_show_flag_2 = df[WE2] > 0
term2_standing = np.where(
    no_show_flag_2 & (term2_standing_base == 'Good'), 'Warning',
    np.where(no_show_flag_2 & (term2_standing_base == 'Warning'), 'Probation', term2_standing_base)
)
term2_standing = pd.Series(term2_standing, index=df.index)

# Overall academic standing for early intervention
overall_score = (term1_score + term2_score) / 2.0
overall_standing = compute_standing_category(overall_score)

# Financial integrity and scholarship eligibility checks
financial_ok = (df[FEES] == 1) & (df[DEBTOR] == 0)

# Scholarship renewal eligibility (policy-like rules)
meets_academic_threshold = (
        (grade_norm_1 >= 0.60) & (grade_norm_2 >= 0.60) &
        (approved_rate_1 >= 0.50) & (approved_rate_2 >= 0.50)
)

renewal_eligible = (df[SCH] == 1) & financial_ok & meets_academic_threshold

# Construct early-intervention outputs
out = pd.DataFrame({
    'student_index': df.index,
    'term1_score': term1_score.round(4),
    'term1_standing': term1_standing,
    'term2_score': term2_score.round(4),
    'term2_standing': term2_standing,
    'overall_score': overall_score.round(4),
    'overall_standing': overall_standing,
    'financial_ok': financial_ok,
    'scholarship_holder': df[SCH].astype(bool),
    'scholarship_renewal_eligible': renewal_eligible,
    'attendance_flag_term2': no_show_flag_2
})

# Derive actionable flags for early intervention workflows
out['needs_intervention'] = (
        (out['overall_standing'] != 'Good') |
        (~out['financial_ok']) |
        ((out['scholarship_holder']) & (~out['scholarship_renewal_eligible']))
)

output_file = os.path.join(args.output, 'academic_standing_and_scholarship_eligibility.csv')
out.to_csv(output_file, index=False)

print(f'Wrote results to {output_file}')
