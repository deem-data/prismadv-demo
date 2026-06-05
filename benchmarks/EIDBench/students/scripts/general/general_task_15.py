import argparse
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_csv)

    # Identify attendance column robustly (may contain a trailing tab)
    attendance_candidates = [c for c in df.columns if c.replace('\t', '').strip() == 'Daytime/evening attendance']
    attendance_col = attendance_candidates[0] if attendance_candidates else 'Daytime/evening attendance\t'

    # Column aliases
    col_target = 'Target'
    col_app_order = 'Application order'
    col_debtor = 'Debtor'
    col_tuition = 'Tuition fees up to date'
    col_scholar = 'Scholarship holder'

    col_adm_grade = 'Admission grade'
    col_prevq_grade = 'Previous qualification (grade)'

    s1_enrolled = 'Curricular units 1st sem (enrolled)'
    s1_approved = 'Curricular units 1st sem (approved)'
    s1_noeval = 'Curricular units 1st sem (without evaluations)'
    s1_evals = 'Curricular units 1st sem (evaluations)'
    s1_credited = 'Curricular units 1st sem (credited)'
    s1_grade = 'Curricular units 1st sem (grade)'

    s2_enrolled = 'Curricular units 2nd sem (enrolled)'
    s2_approved = 'Curricular units 2nd sem (approved)'
    s2_noeval = 'Curricular units 2nd sem (without evaluations)'
    s2_evals = 'Curricular units 2nd sem (evaluations)'
    s2_credited = 'Curricular units 2nd sem (credited)'

    # ASSERTION_START
    # ASSERT Target domain and base rates
    allowed_targets = {'Graduate', 'Dropout', 'Enrolled'}
    allowed_targets = {'Graduate', 'Dropout', 'Enrolled'}
    assert df[col_target].isin(allowed_targets).all()
    # ASSERTION_END
    # ASSERTION_START
    # Application order integrity and distribution
    # Financial consistency
    # Admissions and prior grades range and presence
    assert pd.api.types.is_numeric_dtype(df[col_adm_grade]) and df[col_adm_grade].notna().all()
    assert ((df[col_adm_grade] >= 0) & (df[col_adm_grade] <= 200)).all()
    # ASSERTION_END
    # ASSERTION_START
    assert pd.api.types.is_numeric_dtype(df[col_prevq_grade]) and df[col_prevq_grade].notna().all()
    assert ((df[col_prevq_grade] >= 0) & (df[col_prevq_grade] <= 200)).all()
    # ASSERTION_END
    # Correlation between admissions and previous qualification grades
    # First semester curricular consistency
    # ASSERTION_START
    e1 = df['Curricular units 1st sem (enrolled)']
    a1 = df['Curricular units 1st sem (approved)']
    w1 = df['Curricular units 1st sem (without evaluations)']
    v1 = df['Curricular units 1st sem (evaluations)']

    # Non-negativity for all used columns is required for safe_divide and feature logic
    assert (e1 >= 0).all()
    assert (a1 >= 0).all()
    assert (w1 >= 0).all()
    assert (v1 >= 0).all()

    # Ratios must be sensible for feature engineering (e.g., pass_rate <= 1)
    assert (a1 <= e1).all()
    assert (w1 <= e1).all()
    # ASSERTION_END
    # ASSERTION_START
    # First semester grade validity
    # Second semester curricular consistency
    e2 = df['Curricular units 2nd sem (enrolled)']
    a2 = df['Curricular units 2nd sem (approved)']
    w2 = df['Curricular units 2nd sem (without evaluations)']
    v2 = df['Curricular units 2nd sem (evaluations)']

    # Non-negativity for all used columns is required for safe_divide and feature logic
    assert (e2 >= 0).all()
    assert (a2 >= 0).all()
    assert (w2 >= 0).all()
    assert (v2 >= 0).all()

    # Ratios must be sensible for feature engineering (e.g., pass_rate <= 1)
    assert (a2 <= e2).all()
    assert (w2 <= e2).all()
    # ASSERTION_END
    # Second semester "without evaluations" mostly zero and non-negative integer
    # Feature engineering that relies on the verified constraints
    def safe_divide(num, den):
        den_safe = np.where(den > 0, den, 1)
        return np.where(den > 0, num / den_safe, 0.0)

    grade_scaled = df[col_adm_grade] / 200.0
    prevq_scaled = df[col_prevq_grade] / 200.0
    grade_consensus = 0.6 * grade_scaled + 0.4 * prevq_scaled

    first_sem_pass_rate = safe_divide(df[s1_approved].to_numpy(), df[s1_enrolled].to_numpy())
    first_sem_engagement = 1.0 - safe_divide(df[s1_noeval].to_numpy(), df[s1_enrolled].to_numpy())
    first_sem_eval_load = safe_divide(df[s1_evals].to_numpy(), df[s1_enrolled].to_numpy())

    second_sem_pass_rate = safe_divide(df[s2_approved].to_numpy(), df[s2_enrolled].to_numpy())
    second_sem_engagement = 1.0 - safe_divide(df[s2_noeval].to_numpy(), df[s2_enrolled].to_numpy())
    second_sem_eval_load = safe_divide(df[s2_evals].to_numpy(), df[s2_enrolled].to_numpy())

    financial_risk = (
            (df[col_debtor] == 1).astype(float)
            + (df[col_tuition] == 0).astype(float) * 0.5
            - (df[col_scholar] == 1).astype(float) * 0.5
    )
    financial_risk = np.clip(financial_risk, 0.0, 1.5)

    first_choice = (df[col_app_order] == 1).astype(int)

    # Base dropout rate used to set an alert threshold
    base_rates = df[col_target].value_counts(normalize=True)
    dropout_base = float(base_rates.get('Dropout', 0.0))
    risk_threshold = min(0.9, dropout_base + 0.08)

    # Assemble model features
    feature_frame = pd.DataFrame({
        'grade_scaled': grade_scaled,
        'prevq_scaled': prevq_scaled,
        'grade_consensus': grade_consensus,
        'first_sem_pass_rate': first_sem_pass_rate,
        'first_sem_engagement': first_sem_engagement,
        'first_sem_eval_load': first_sem_eval_load,
        'second_sem_pass_rate': second_sem_pass_rate,
        'second_sem_engagement': second_sem_engagement,
        'second_sem_eval_load': second_sem_eval_load,
        'financial_risk': financial_risk,
        'first_choice': first_choice,
        'daytime_attendance': df[attendance_col].astype(float),
        'age_at_enrollment': df['Age at enrollment'].astype(float),
        'unemployment_rate': df['Unemployment rate'].astype(float),
        'inflation_rate': df['Inflation rate'].astype(float),
        'gdp': df['GDP'].astype(float),
        'international': df['International'].astype(float),
        'displaced': df['Displaced'].astype(float),
        'gender': df['Gender'].astype(float),
        'debtor': df[col_debtor].astype(float),
        'tuition_up_to_date': df[col_tuition].astype(float),
        'scholarship': df[col_scholar].astype(float),
    })

    # Target encoding
    class_order = ['Graduate', 'Enrolled', 'Dropout']
    label_to_int = {cls: i for i, cls in enumerate(class_order)}
    y = df[col_target].map(label_to_int).astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        feature_frame.values, y.values, test_size=0.2, random_state=42, stratify=y.values
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    clf = LogisticRegression(max_iter=200, multi_class='multinomial', solver='lbfgs')
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    y_proba = clf.predict_proba(X_test_scaled)

    acc = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average='macro')
    report = classification_report(y_test, y_pred, target_names=class_order, output_dict=True)

    # Persist model artifacts
    joblib.dump({'scaler': scaler, 'model': clf, 'features': list(feature_frame.columns), 'class_order': class_order},
                os.path.join(args.output, 'early_warning_model.joblib'))

    metrics_path = os.path.join(args.output, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump({'accuracy': acc, 'f1_macro': f1_macro, 'classification_report': report}, f, indent=2)

    # Full-dataset scoring for deployment
    X_all_scaled = scaler.transform(feature_frame.values)
    proba_all = clf.predict_proba(X_all_scaled)
    pred_all = clf.predict(X_all_scaled)

    # Intervention queue focuses on Dropout risk
    dropout_idx = class_order.index('Dropout')
    dropout_prob = proba_all[:, dropout_idx]
    predicted_label = [class_order[i] for i in pred_all]

    preds_df = pd.DataFrame({
        'row_id': np.arange(len(df)),
        'predicted_label': predicted_label,
        'prob_Graduate': proba_all[:, class_order.index('Graduate')],
        'prob_Enrolled': proba_all[:, class_order.index('Enrolled')],
        'prob_Dropout': dropout_prob,
    })

    preds_df.to_csv(os.path.join(args.output, 'predictions.csv'), index=False)

    intervention_df = preds_df.loc[preds_df['prob_Dropout'] >= risk_threshold].sort_values('prob_Dropout',
                                                                                           ascending=False)
    intervention_df.to_csv(os.path.join(args.output, 'intervention_queue.csv'), index=False)


if __name__ == '__main__':
    main()
