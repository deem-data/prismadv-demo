import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_file = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_file)

    # Normalize fields used for decision logic
    df['result'] = df['result'].astype(str).str.strip().str.lower()
    df['toss_decision'] = df['toss_decision'].astype(str).str.strip().str.lower()
    df['super_over'] = df['super_over'].astype(str).str.strip().str.upper()

    # Coerce margin to numeric for validations and downstream numeric ops
    df['result_margin'] = pd.to_numeric(df['result_margin'], errors='coerce')
    # ASSERTION_START
    assert (df['team1'] != df['team2']).all()
    # ASSERTION_END
    # ASSERTION_START
    # A winner must be one of the participating teams or NaN.
    winner_is_a_team = (df['winner'] == df['team1']) | (df['winner'] == df['team2'])
    assert (winner_is_a_team | df['winner'].isna()).all()

    # Matches with 'no result' must not have a winner.
    no_result_mask = df['result'] == 'no result'
    assert df.loc[no_result_mask, 'winner'].isna().all()

    # Matches with a conclusive result (i.e., not a tie or 'no result') must have a winner.
    conclusive_mask = ~df['result'].isin(['no result', 'tie'])
    assert df.loc[conclusive_mask, 'winner'].notna().all()
    # ASSERTION_END
    # ASSERTION_START
    assert ((df['toss_winner'] == df['team1']) | (df['toss_winner'] == df['team2'])).all()
    # ASSERTION_END
    # ASSERTION_START
    # A result of 'wickets' or 'runs' must have a non-null result_margin.
    wickets_mask = df['result'] == 'wickets'
    runs_mask = df['result'] == 'runs'
    assert df.loc[wickets_mask | runs_mask, 'result_margin'].notna().all()

    # ASSERTION_END
    # ASSERTION_START
    assert ((df['super_over'] != 'Y') | (df['result'] == 'tie')).all()
    # ASSERTION_END
    # Safe integer representation for margins, used later in averages
    df['result_margin_int'] = df['result_margin'].round(0).astype('Int64')

    # Build a per-team match view (two rows per match)
    base_cols = ['id', 'match_type', 'toss_winner', 'toss_decision', 'winner', 'result', 'super_over', 'method',
                 'result_margin_int']
    left = df[['team1', 'team2'] + base_cols].copy()
    left = left.rename(columns={'team1': 'team', 'team2': 'opponent'})

    right = df[['team2', 'team1'] + base_cols].copy()
    right = right.rename(columns={'team2': 'team', 'team1': 'opponent'})

    teams_long = pd.concat([left, right], ignore_index=True)

    teams_long['toss_made_by_team'] = teams_long['team'] == teams_long['toss_winner']

    # Outcome points and denominator handling
    tie_no_so_mask = (teams_long['result'] == 'tie') & (teams_long['super_over'] != 'Y')
    won_mask = teams_long['team'] == teams_long['winner']

    denom = np.where(teams_long['result'] == 'no result', 0.0, 1.0)
    points = np.where(teams_long['result'] == 'no result', 0.0,
                      np.where(tie_no_so_mask, 0.5, np.where(won_mask, 1.0, 0.0)))

    teams_long['denom'] = denom
    teams_long['points'] = points

    # Winning margins by type for additional analytics
    teams_long['winning_runs_margin'] = teams_long['result_margin_int'].where(
        won_mask & (teams_long['result'] == 'runs'))
    teams_long['winning_wickets_margin'] = teams_long['result_margin_int'].where(
        won_mask & (teams_long['result'] == 'wickets'))

    # Focus on matches where the team actually made the toss decision
    decided = teams_long[teams_long['toss_made_by_team']].copy()

    # Aggregate by team, match stage, and toss decision
    group_cols = ['team', 'match_type', 'toss_decision']
    agg = decided.groupby(group_cols).agg(
        matches=('denom', 'sum'),
        win_points=('points', 'sum'),
        ties_wo_super_over=(
        'result', lambda s: (s.eq('tie')).sum() - ((decided.loc[s.index, 'super_over'] == 'Y').sum() if len(s) else 0)),
        super_over_deciders=('super_over', lambda s: (s.eq('Y')).sum()),
        avg_runs_margin=('winning_runs_margin', 'mean'),
        avg_wickets_margin=('winning_wickets_margin', 'mean')
    ).reset_index()

    # Filter out groups with zero denominator to avoid divide-by-zero
    agg = agg[agg['matches'] > 0]
    agg['win_rate'] = agg['win_points'] / agg['matches']

    # Order columns and write output
    agg = agg[['team', 'match_type', 'toss_decision', 'matches', 'win_points', 'win_rate',
               'ties_wo_super_over', 'super_over_deciders', 'avg_runs_margin', 'avg_wickets_margin']]

    out_file = os.path.join(args.output, 'team_win_rates_by_toss_and_stage.csv')
    agg.to_csv(out_file, index=False)


if __name__ == '__main__':
    main()
