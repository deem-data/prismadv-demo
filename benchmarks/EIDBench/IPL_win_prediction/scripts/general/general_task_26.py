import argparse
import os

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_file = os.path.join(args.input, 'new_data.csv')
output_dir = args.output
os.makedirs(output_dir, exist_ok=True)

# Load data
df = pd.read_csv(input_file)

# Basic type coercions used downstream
df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
df['season_int'] = pd.to_numeric(df['season'], errors='coerce').astype(int)
df['result_margin'] = pd.to_numeric(df['result_margin'], errors='coerce')
df['target_runs'] = pd.to_numeric(df['target_runs'], errors='coerce')
df['target_overs'] = pd.to_numeric(df['target_overs'], errors='coerce')
# ASSERTION_START
assert (df['season_int'] == df['date_dt'].dt.year).all()
assert df['season_int'].between(2008, 2024).all()
# ASSERTION_END
# Features that depend on season correctness
is_final = (df['match_type'] == 'Final').astype(int)
# ASSERTION_START
assert (df['team1'] != df['team2']).all()
mask_decisive = df['result'].isin(['runs', 'wickets', 'tie'])
valid_winner = df.loc[mask_decisive, 'winner'].eq(df.loc[mask_decisive, 'team1']) | df.loc[mask_decisive, 'winner'].eq(
    df.loc[mask_decisive, 'team2'])
assert valid_winner.all()
mask_no_result = df['result'].eq('no result')
assert df.loc[mask_no_result, 'winner'].isna().all()
# ASSERTION_END
# Train set excludes matches without a decisive outcome
train_mask = df['result'].isin(['runs', 'wickets', 'tie'])
df_train = df.loc[train_mask].copy()
# ASSERTION_START
runs_mask = df['result'].eq('runs')
wkts_mask = df['result'].eq('wickets')
rm_runs = df.loc[runs_mask, 'result_margin'].dropna()
rm_wkts = df.loc[wkts_mask, 'result_margin'].dropna()
assert (rm_runs > 0).all() and (np.mod(rm_runs, 1) == 0).all()
assert (np.mod(rm_wkts, 1) == 0).all() and rm_wkts.between(1, 10).all()
# ASSERTION_END
# ASSERTION_START
to_series = df_train['target_overs']
assert to_series.notna().all() and (to_series > 0).all() and (to_series <= 20.0).all()
# ASSERTION_END
# ASSERTION_START
tr_series = df_train['target_runs']
assert tr_series.notna().all() and (tr_series >= 0).all()
# ASSERTION_END
# Label: 1 if team1 won, else 0
label = (df_train['winner'] == df_train['team1']).astype(int)

# Feature engineering
features = pd.DataFrame({
    'match_id': df_train['id'],
    'season': df_train['season_int'],
    'is_final': (df_train['match_type'] == 'Final').astype(int),
    'team1': df_train['team1'],
    'team2': df_train['team2'],
    'toss_winner_is_team1': (df_train['toss_winner'] == df_train['team1']).astype(int),
    'toss_decision_bat': (df_train['toss_decision'] == 'bat').astype(int),
    'super_over_flag': (df_train['super_over'] == 'Y').astype(int),
    'target_runs': df_train['target_runs'].astype(float),
    'target_overs': df_train['target_overs'].astype(float),
    'target_run_rate': (df_train['target_runs'] / df_train['target_overs']).astype(float),
    'revised_overs_shortfall': (20.0 - df_train['target_overs']).astype(float),
    'result_type_wickets': (df_train['result'] == 'wickets').astype(int),
    'margin_runs': np.where(df_train['result'].eq('runs'), df_train['result_margin'].fillna(0), 0).astype(float),
    'margin_wickets': np.where(df_train['result'].eq('wickets'), df_train['result_margin'].fillna(0), 0).astype(int)
})

features['label_team1_win'] = label

output_file = os.path.join(output_dir, 'winprob_training_dataset.csv')
features.to_csv(output_file, index=False)
