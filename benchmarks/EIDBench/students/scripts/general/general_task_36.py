import argparse
import os
import json
import pandas as pd
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

input_csv = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_csv)

c1_en = 'Curricular units 1st sem (enrolled)'
c1_ev = 'Curricular units 1st sem (evaluations)'
c1_ap = 'Curricular units 1st sem (approved)'
c1_wo = 'Curricular units 1st sem (without evaluations)'
c1_gr = 'Curricular units 1st sem (grade)'

c2_en = 'Curricular units 2nd sem (enrolled)'
c2_ev = 'Curricular units 2nd sem (evaluations)'
c2_ap = 'Curricular units 2nd sem (approved)'
c2_wo = 'Curricular units 2nd sem (without evaluations)'
c2_gr = 'Curricular units 2nd sem (grade)'

adm_gr = 'Admission grade'
debtor_col = 'Debtor'
paid_col = 'Tuition fees up to date'
intl_col = 'International'

to_numeric_cols = [c1_en, c1_ev, c1_ap, c1_wo, c1_gr,
                   c2_en, c2_ev, c2_ap, c2_wo, c2_gr,
                   adm_gr, debtor_col, paid_col, intl_col]
for col in to_numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

eligible1 = df[c1_en] - df[c1_wo]
# ASSERTION_START
assert (df[c1_en] >= 0).all()
assert (df[c1_wo] >= 0).all()
eligible1 = df[c1_en] - df[c1_wo]
assert (eligible1 >= 0).all()
assert (df[c1_ap] >= 0).all()
# ASSERTION_END
pass_rate1 = np.where(eligible1 > 0, df[c1_ap] / eligible1, 0.0)

eligible2 = df[c2_en] - df[c2_wo]
# ASSERTION_START
assert (df[c2_en] >= 0).all()
assert (df[c2_wo] >= 0).all()
eligible2 = df[c2_en] - df[c2_wo]
assert (eligible2 >= 0).all()
assert (df[c2_ap] >= 0).all()
# ASSERTION_END
pass_rate2 = np.where(eligible2 > 0, df[c2_ap] / eligible2, 0.0)

eligible_total = eligible1 + eligible2
approved_total = df[c1_ap] + df[c2_ap]
pass_rate = np.where(eligible_total > 0, approved_total / eligible_total, 0.0)
# ASSERTION_START
assert (df[c1_en] >= 0).all()
assert (df[c2_en] >= 0).all()
assert df[c1_gr].notna().all()
assert df[c2_gr].notna().all()
# ASSERTION_END
enrolled_total = df[c1_en] + df[c2_en]
weighted_avg_grade = np.where(enrolled_total > 0,
                              (df[c1_gr] * df[c1_en] + df[c2_gr] * df[c2_en]) / enrolled_total,
                              0.0)
grade_shortfall = 1.0 - (weighted_avg_grade / 20.0)
# ASSERTION_START
assert ((df[adm_gr] >= 0) & (df[adm_gr] <= 200)).all()
# ASSERTION_END
admission_risk = 1.0 - (df[adm_gr] / 200.0)
# ASSERTION_START
assert df[intl_col].isin([0, 1]).all()
# ASSERTION_END
intl_modifier = 0.03 * df[intl_col]
financial_flag = np.where((df[paid_col] == 0) | (df[debtor_col] == 1), 1.0, 0.0)

score_raw = (
    0.45 * financial_flag +
    0.30 * (1.0 - pass_rate) +
    0.15 * grade_shortfall +
    0.07 * admission_risk +
    intl_modifier
)

risk_score = np.clip(score_raw, 0.0, 1.0)

df_out = pd.DataFrame({
    'student_row': np.arange(len(df)),
    'risk_score': risk_score,
    'financial_flag': financial_flag.astype(int),
    'pass_rate': pass_rate,
    'weighted_avg_grade': weighted_avg_grade,
    'admission_grade': df[adm_gr],
    'International': df[intl_col].astype(int)
})

priority_labels = np.where(df_out['risk_score'] >= 0.65, 'high',
                           np.where(df_out['risk_score'] >= 0.40, 'medium', 'low'))
df_out['priority'] = priority_labels
df_out['priority_rank'] = df_out['risk_score'].rank(method='first', ascending=False).astype(int)

n_queue = int(max(1, min(int(len(df_out) * 0.1), 500)))
outreach_queue = df_out.sort_values(by='risk_score', ascending=False).head(n_queue)

scores_path = os.path.join(args.output, 'risk_scores.csv')
queue_path = os.path.join(args.output, 'outreach_queue.csv')
metrics_path = os.path.join(args.output, 'metrics.json')

df_out.to_csv(scores_path, index=False)
outreach_queue.to_csv(queue_path, index=False)

metrics = {
    'num_records': int(len(df)),
    'pct_paid_up': float((df[paid_col] == 1).mean()),
    'pct_debtor': float((df[debtor_col] == 1).mean()),
    'pct_domestic': float((df[intl_col] == 0).mean()),
    'avg_risk_score': float(df_out['risk_score'].mean()),
    'high_risk_count': int((df_out['priority'] == 'high').sum()),
    'medium_risk_count': int((df_out['priority'] == 'medium').sum()),
    'low_risk_count': int((df_out['priority'] == 'low').sum())
}

with open(metrics_path, 'w') as f:
    json.dump(metrics, f, indent=2)
