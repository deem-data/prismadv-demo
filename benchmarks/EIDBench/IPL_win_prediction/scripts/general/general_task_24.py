import argparse
import os

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_csv = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(
    input_csv,
    na_values=['', 'NA', 'NaN', 'null', 'NULL', 'NullValue']
)

if not os.path.exists(args.output):
    os.makedirs(args.output, exist_ok=True)

# Focus on league-stage standings
if 'match_type' in df.columns:
    df = df[df['match_type'] == 'League'].copy()
else:
    df = df.copy()

# Normalize types
if 'target_runs' in df.columns:
    df['target_runs'] = pd.to_numeric(df['target_runs'], errors='coerce')
if 'result_margin' in df.columns:
    df['result_margin'] = pd.to_numeric(df['result_margin'], errors='coerce')
if 'target_overs' in df.columns:
    df['target_overs'] = pd.to_numeric(df['target_overs'], errors='coerce')
# ASSERTION_START
allowed_results = {'runs', 'wickets', 'tie', 'no result'}
assert df['result'].isin(allowed_results).all()
# ASSERTION_END
# ASSERTION_START
assert (df['team1'] != df['team2']).all()
# ASSERTION_END
# ASSERTION_START
mask_decided = df['result'].isin(['runs', 'wickets'])
assert df.loc[mask_decided, 'winner'].notna().all()
assert ((df.loc[mask_decided, 'winner'] == df.loc[mask_decided, 'team1']) | (
            df.loc[mask_decided, 'winner'] == df.loc[mask_decided, 'team2'])).all()
# ASSERTION_END
# ASSERTION_START
mask_no_result = df['result'] == 'no result'
assert df.loc[mask_no_result, 'winner'].isna().all()
mask_winner_na = df['winner'].isna()
assert df.loc[mask_winner_na, 'result'].isin(['no result', 'tie']).all()
# ASSERTION_END
# ASSERTION_START
rm_runs = df.loc[df['result'] == 'runs', 'result_margin']
assert rm_runs.notna().all() and (rm_runs >= 1).all() and ((rm_runs % 1) == 0).all()
assert df.loc[df['result'].isin(['tie', 'no result']), 'result_margin'].isna().all()
# ASSERTION_END
# ASSERTION_START
mask_completed = df['result'] != 'no result'
tr_completed = df.loc[mask_completed, 'target_runs']
assert tr_completed.notna().all() and (tr_completed > 0).all() and ((tr_completed % 1) == 0).all()

to_completed = df.loc[mask_completed, 'target_overs']
# target_overs must be positive if present, as it's used in NRR calculation.
# NaN is acceptable as it's filled later.
assert (to_completed.isna() | (to_completed > 0)).all()
# ASSERTION_END
# ASSERTION_START
season_coerced = pd.to_numeric(df['season'], errors='coerce')
assert season_coerced.notna().all()
assert (season_coerced % 1 == 0).all()
# ASSERTION_END
# Use season as integer for grouping
df['season'] = pd.to_numeric(df['season'], errors='raise').astype(int)

# Fill missing target_overs with 20.0 for stable NRR calculation
df['target_overs'] = df['target_overs'].fillna(20.0)

# Derive first and second innings runs based on target and result semantics
first_runs = (df['target_runs'] - 1).astype(float)
second_runs = pd.Series(index=df.index, dtype='float64')
second_runs.loc[df['result'] == 'runs'] = first_runs.loc[df['result'] == 'runs'] - df.loc[
    df['result'] == 'runs', 'result_margin']
second_runs.loc[df['result'] == 'wickets'] = first_runs.loc[df['result'] == 'wickets'] + 1.0
second_runs.loc[df['result'] == 'tie'] = first_runs.loc[df['result'] == 'tie']
# For no result, keep NaN to avoid affecting NRR

overs = df['target_overs'].astype(float)

records = []
for i, row in df.iterrows():
    season = int(row['season'])
    t1 = row['team1']
    t2 = row['team2']
    res = row['result']
    ov = float(row['target_overs']) if pd.notna(row['target_overs']) else 20.0
    fr = float(first_runs.loc[i]) if pd.notna(first_runs.loc[i]) else np.nan
    sr = float(second_runs.loc[i]) if pd.notna(second_runs.loc[i]) else np.nan

    if res == 'no result':
        records.append({
            'season': season, 'team': t1, 'matches': 1, 'wins': 0, 'losses': 0, 'ties': 0, 'no_results': 1,
            'points': 1, 'runs_for': 0.0, 'overs_for': 0.0, 'runs_against': 0.0, 'overs_against': 0.0
        })
        records.append({
            'season': season, 'team': t2, 'matches': 1, 'wins': 0, 'losses': 0, 'ties': 0, 'no_results': 1,
            'points': 1, 'runs_for': 0.0, 'overs_for': 0.0, 'runs_against': 0.0, 'overs_against': 0.0
        })
    elif res == 'tie':
        records.append({
            'season': season, 'team': t1, 'matches': 1, 'wins': 0, 'losses': 0, 'ties': 1, 'no_results': 0,
            'points': 1, 'runs_for': fr, 'overs_for': ov, 'runs_against': sr, 'overs_against': ov
        })
        records.append({
            'season': season, 'team': t2, 'matches': 1, 'wins': 0, 'losses': 0, 'ties': 1, 'no_results': 0,
            'points': 1, 'runs_for': sr, 'overs_for': ov, 'runs_against': fr, 'overs_against': ov
        })
    elif res in ('runs', 'wickets'):
        winner = row['winner']
        loser = t2 if winner == t1 else t1
        # Team1 perspective
        records.append({
            'season': season,
            'team': t1,
            'matches': 1,
            'wins': 1 if winner == t1 else 0,
            'losses': 1 if winner == t2 else 0,
            'ties': 0,
            'no_results': 0,
            'points': 2 if winner == t1 else 0,
            'runs_for': fr,
            'overs_for': ov,
            'runs_against': sr,
            'overs_against': ov
        })
        # Team2 perspective
        records.append({
            'season': season,
            'team': t2,
            'matches': 1,
            'wins': 1 if winner == t2 else 0,
            'losses': 1 if winner == t1 else 0,
            'ties': 0,
            'no_results': 0,
            'points': 2 if winner == t2 else 0,
            'runs_for': sr,
            'overs_for': ov,
            'runs_against': fr,
            'overs_against': ov
        })
    else:
        continue

standings_raw = pd.DataFrame.from_records(records)
if standings_raw.empty:
    # Write empty standings file if no league matches
    out_path = os.path.join(args.output, 'standings.csv')
    pd.DataFrame(
        columns=['season', 'team', 'matches', 'wins', 'losses', 'ties', 'no_results', 'points', 'nrr', 'runs_for',
                 'overs_for', 'runs_against', 'overs_against']).to_csv(out_path, index=False)
else:
    agg = standings_raw.groupby(['season', 'team'], as_index=False).agg({
        'matches': 'sum',
        'wins': 'sum',
        'losses': 'sum',
        'ties': 'sum',
        'no_results': 'sum',
        'points': 'sum',
        'runs_for': 'sum',
        'overs_for': 'sum',
        'runs_against': 'sum',
        'overs_against': 'sum'
    })

    # Compute NRR safely
    scored_rate = np.where(agg['overs_for'] > 0, agg['runs_for'] / agg['overs_for'], 0.0)
    conceded_rate = np.where(agg['overs_against'] > 0, agg['runs_against'] / agg['overs_against'], 0.0)
    nrr = scored_rate - conceded_rate
    agg['nrr'] = np.round(nrr, 3)

    agg = agg[
        ['season', 'team', 'matches', 'wins', 'losses', 'ties', 'no_results', 'points', 'nrr', 'runs_for', 'overs_for',
         'runs_against', 'overs_against']]

    agg = agg.sort_values(by=['season', 'points', 'nrr', 'wins', 'team'], ascending=[True, False, False, False, True])

    out_path = os.path.join(args.output, 'standings.csv')
    agg.to_csv(out_path, index=False)
