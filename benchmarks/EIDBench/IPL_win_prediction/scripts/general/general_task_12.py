import argparse
import os

import numpy as np
import pandas as pd

VALID_RESULTS = {"runs", "wickets", "tie", "no result"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_fp = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_fp, keep_default_na=True, na_values=['NullValue'])

    df['result_margin'] = pd.to_numeric(df['result_margin'], errors='coerce')
    df['target_runs'] = pd.to_numeric(df['target_runs'], errors='coerce')
    df['target_overs'] = pd.to_numeric(df['target_overs'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
    # ASSERTION_START
    assert df['date'].notna().all()
    assert df['season'].notna().all()
    # ASSERTION_END
    # ASSERTION_START
    assert (df['team1'] != df['team2']).all()
    # ASSERTION_END
    # ASSERTION_START
    decided_mask = df['result'] != 'no result'
    subset_df = df.loc[decided_mask]

    toss_winner_non_null = subset_df['toss_winner'].notna().all()
    toss_winner_in_pair = ((subset_df['toss_winner'] == subset_df['team1']) | (
                subset_df['toss_winner'] == subset_df['team2'])).all()
    toss_decision_allowed = subset_df['toss_decision'].isin({'bat', 'field'}).all()
    assert toss_winner_non_null and toss_winner_in_pair and toss_decision_allowed
    # ASSERTION_END
    df['bat_first_team'] = np.where(
        df['toss_decision'] == 'bat',
        df['toss_winner'],
        np.where(df['toss_winner'] == df['team1'], df['team2'], df['team1'])
    )
    # ASSERTION_START
    result_allowed = df['result'].isin(VALID_RESULTS).all()

    winner_required_mask = df['result'].isin(['runs', 'wickets', 'tie']) | (df['super_over'] == 'Y')
    winner_ok = ((df['winner'] == df['team1']) | (df['winner'] == df['team2']))[winner_required_mask].all()

    nores_mask = df['result'] == 'no result'
    nores_winner_null = df.loc[nores_mask, 'winner'].isna().all()

    assert result_allowed and winner_ok and nores_winner_null
    # ASSERTION_END
    # ASSERTION_START
    wkts_mask = df['result'] == 'wickets'
    runs_mask = df['result'] == 'runs'

    wkts_vals = df.loc[wkts_mask, 'result_margin']
    runs_vals = df.loc[runs_mask, 'result_margin']

    wkts_int_ok = wkts_vals.notna().all() and ((np.floor(wkts_vals) == wkts_vals)).all()
    runs_int_ok = runs_vals.notna().all() and ((np.floor(runs_vals) == runs_vals)).all()

    assert wkts_int_ok and runs_int_ok

    # ASSERTION_END
    def build_result_string(row: pd.Series) -> str:
        r = row['result']
        if r == 'no result':
            return f"No result - {row['team1']} vs {row['team2']}"
        w = row['winner']
        opp = row['team2'] if w == row['team1'] else row['team1']
        if r == 'runs':
            m = int(row['result_margin'])
            base = f"{w} beat {opp} by {m} runs"
        elif r == 'wickets':
            m = int(row['result_margin'])
            base = f"{w} beat {opp} by {m} wickets"
        elif r == 'tie':
            base = f"Tied - Super Over: {w}"
        else:
            base = r
        if row['method'] == 'D/L':
            tr = int(row['target_runs']) if pd.notna(row['target_runs']) else None
            to = float(row['target_overs']) if pd.notna(row['target_overs']) else None
            base = f"{base} (DLS: target {tr} in {to} overs)"
        if pd.notna(row['player_of_match']):
            base = f"{base} | Player of Match: {row['player_of_match']}"
        return base

    df['final_result'] = df.apply(build_result_string, axis=1)

    season_cols = ['season', 'team1', 'team2', 'result', 'super_over', 'winner']
    base = df[season_cols].copy()

    team_entries = pd.concat([
        base.rename(columns={'team1': 'team'})[['season', 'team', 'team2', 'result', 'super_over', 'winner']].rename(
            columns={'team2': 'opponent'}),
        base.rename(columns={'team2': 'team'})[['season', 'team1', 'result', 'super_over', 'winner']].rename(
            columns={'team1': 'opponent'})
    ], ignore_index=True)

    team_entries['is_winner'] = team_entries['team'] == team_entries['winner']
    team_entries['is_decided'] = team_entries['result'].isin(['runs', 'wickets']) | (
                (team_entries['result'] == 'tie') & (team_entries['super_over'] == 'Y'))
    team_entries['is_loser'] = (~team_entries['is_winner']) & team_entries['is_decided']
    team_entries['is_noresult'] = team_entries['result'] == 'no result'

    team_entries['wins'] = team_entries['is_winner'].astype(int)
    team_entries['losses'] = team_entries['is_loser'].astype(int)
    team_entries['no_results'] = team_entries['is_noresult'].astype(int)
    team_entries['matches'] = 1

    team_entries['points'] = np.where(
        team_entries['is_winner'], 2,
        np.where(
            team_entries['is_noresult'] | ((team_entries['result'] == 'tie') & (team_entries['super_over'] != 'Y')), 1,
            0)
    )

    standings = (
        team_entries.groupby(['season', 'team'], as_index=False)[
            ['matches', 'wins', 'losses', 'no_results', 'points']].sum()
        .sort_values(['season', 'points', 'wins', 'team'], ascending=[True, False, False, True])
    )

    final_results_out = df[
        ['id', 'season', 'date', 'team1', 'team2', 'final_result', 'toss_winner', 'toss_decision', 'bat_first_team',
         'winner', 'result', 'result_margin', 'super_over', 'method', 'target_runs', 'target_overs',
         'player_of_match']].copy()

    final_results_out.to_csv(os.path.join(args.output, 'final_results.csv'), index=False)
    standings.to_csv(os.path.join(args.output, 'season_standings.csv'), index=False)


if __name__ == '__main__':
    main()
