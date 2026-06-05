import argparse
import os

import numpy as np
import pandas as pd


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_csv = os.path.join(args.input, 'new_data.csv')
ensure_dir(args.output)

df = pd.read_csv(input_csv)

# Normalize common null-like values
for col in ['method', 'winner']:
    if col in df.columns:
        df[col] = df[col].replace({'NullValue': np.nan, 'null': np.nan, 'NULL': np.nan, 'None': np.nan, '': np.nan})

# Types for numeric columns used downstream
if 'result_margin' in df.columns:
    df['result_margin'] = pd.to_numeric(df['result_margin'], errors='coerce')
if 'target_overs' in df.columns:
    df['target_overs'] = pd.to_numeric(df['target_overs'], errors='coerce')

# Precompute frequently used columns
results = df['result'].astype(str)
super_over = df['super_over'].astype(str)

# ASSERTION_START
# Guard: team pairing and toss winner assignment are used to derive batting_first
assert (df['team1'] != df['team2']).all()
assert ((df['toss_winner'] == df['team1']) | (df['toss_winner'] == df['team2'])).all()
# ASSERTION_END
# Derive batting first and chasing team from toss decision
opp_of_toss = np.where(df['toss_winner'] == df['team1'], df['team2'], df['team1'])
batting_first = np.where(df['toss_decision'] == 'bat', df['toss_winner'], opp_of_toss)
chasing_team = np.where(df['toss_winner'] == batting_first, opp_of_toss, df['toss_winner'])

df['batting_first'] = batting_first
df['chasing_team'] = chasing_team

# ASSERTION_START
# Guard: super over usage will direct points allocation for ties
mask_so = (df['super_over'] == 'Y')
if mask_so.any():
    assert (df.loc[mask_so, 'result'] == 'tie').all()
# ASSERTION_END
# Guard: D/L method impacts effective overs used in downstream artifacts
# Effective overs for display/analytics
df['effective_overs'] = np.where(df['method'] == 'D/L', df['target_overs'], 20.0)

# ASSERTION_START
# Guard: result margin constraints before we render win-by strings and use integer conversion
mask_wkts = (df['result'] == 'wickets')
if mask_wkts.any():
    s = df.loc[mask_wkts, 'result_margin']
    assert s.notna().all()
    assert ((s % 1) == 0).all()
    assert (s >= 1).all()
mask_runs = (df['result'] == 'runs')
if mask_runs.any():
    s = df.loc[mask_runs, 'result_margin']
    assert s.notna().all()
    assert ((s % 1) == 0).all()
    assert (s > 0).all()
# ASSERTION_END
# Compose human-readable win-by description
win_by_text = []
for idx, row in df.iterrows():
    r = row['result']
    if r == 'runs':
        margin = int(row['result_margin'])
        win_by_text.append(f"{margin} runs")
    elif r == 'wickets':
        margin = int(row['result_margin'])
        win_by_text.append(f"{margin} wickets")
    elif r == 'tie':
        if row['super_over'] == 'Y':
            win_by_text.append('Super Over')
        else:
            win_by_text.append('Tie')
    elif r == 'no result':
        win_by_text.append('No Result')
    else:
        win_by_text.append('Unknown')

df['win_by'] = win_by_text

# Prepare accumulator for points table
teams = pd.unique(pd.concat([df['team1'], df['team2']])).tolist()

points = {t: {
    'team': t,
    'matches': 0,
    'wins': 0,
    'losses': 0,
    'ties': 0,
    'no_results': 0,
    'super_over_wins': 0,
    'points': 0,
    'net_run_margin': 0,  # + for winner by runs, - for loser by runs
    'net_wicket_margin': 0  # + for winner by wickets, - for loser by wickets
} for t in teams}


# Helper to ensure presence
def ensure_team(tn: str):
    if tn not in points:
        points[tn] = {
            'team': tn,
            'matches': 0,
            'wins': 0,
            'losses': 0,
            'ties': 0,
            'no_results': 0,
            'super_over_wins': 0,
            'points': 0,
            'net_run_margin': 0,
            'net_wicket_margin': 0
        }


# Iterate matches to compute points
for idx, row in df.iterrows():
    t1 = row['team1']
    t2 = row['team2']
    r = row['result']
    ensure_team(t1)
    ensure_team(t2)

    # All completed or NR matches count as played
    points[t1]['matches'] += 1
    points[t2]['matches'] += 1

    if r == 'no result':
        # Guard: winner must be null for NR before using None-safe logic downstream
        points[t1]['no_results'] += 1
        points[t2]['no_results'] += 1
        points[t1]['points'] += 1
        points[t2]['points'] += 1
        continue

# ASSERTION_START
# Guard: for decided matches (runs/wickets/tie), winner must be one of the two teams before computing loser
mask = df['result'].isin(['runs', 'wickets']) | ((df['result'] == 'tie') & (df['super_over'] == 'Y'))
relevant_matches = df.loc[mask]
assert relevant_matches['winner'].notna().all()
assert ((relevant_matches['winner'] == relevant_matches['team1']) | (
        relevant_matches['winner'] == relevant_matches['team2'])).all()
# ASSERTION_END
if r == 'runs':
    w = row['winner']
    l = t2 if w == t1 else t1
    margin = int(row['result_margin'])
    points[w]['wins'] += 1
    points[w]['points'] += 2
    points[l]['losses'] += 1
    points[w]['net_run_margin'] += margin
    points[l]['net_run_margin'] -= margin
elif r == 'wickets':
    w = row['winner']
    l = t2 if w == t1 else t1
    margin = int(row['result_margin'])
    points[w]['wins'] += 1
    points[w]['points'] += 2
    points[l]['losses'] += 1
    points[w]['net_wicket_margin'] += margin
    points[l]['net_wicket_margin'] -= margin
elif r == 'tie':
    if row['super_over'] == 'Y':
        w = row['winner']
        l = t2 if w == t1 else t1
        points[w]['wins'] += 1
        points[w]['super_over_wins'] += 1
        points[w]['points'] += 2
        points[l]['losses'] += 1
    else:
        points[t1]['ties'] += 1
        points[t2]['ties'] += 1
        points[t1]['points'] += 1
        points[t2]['points'] += 1
else:
    # Unknown result type; treat as no-result for safety
    points[t1]['no_results'] += 1
    points[t2]['no_results'] += 1
    points[t1]['points'] += 1
    points[t2]['points'] += 1

# Assemble points table
pt_df = pd.DataFrame.from_records(list(points.values()))
# Consistency: matches should equal sum of outcomes
sum_outcomes = pt_df[['wins', 'losses', 'ties', 'no_results']].sum(axis=1)
pt_df['matches'] = sum_outcomes

pt_df = pt_df.sort_values(by=['points', 'wins', 'net_run_margin', 'net_wicket_margin'],
                          ascending=[False, False, False, False]).reset_index(drop=True)

# Produce match outcomes view used by dashboards
match_outcomes = df[
    ['id', 'season', 'date', 'team1', 'team2', 'toss_winner', 'toss_decision', 'batting_first', 'chasing_team',
     'winner', 'result', 'result_margin', 'super_over', 'method', 'effective_overs', 'win_by', 'venue', 'city']].copy()

# Write outputs
pt_path = os.path.join(args.output, 'points_table.csv')
mo_path = os.path.join(args.output, 'match_outcomes.csv')
pt_df.to_csv(pt_path, index=False)
match_outcomes.to_csv(mo_path, index=False)

print(f"Wrote points table to: {pt_path}")
print(f"Wrote match outcomes to: {mo_path}")
