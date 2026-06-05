import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    in_path = os.path.join(args.input, 'new_data.csv')
    out_dir = args.output
    os.makedirs(out_dir, exist_ok=True)

    df = pd.read_csv(in_path)

    # Normalize dtypes used downstream
    for col in ['result_margin', 'target_runs', 'target_overs']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    # ASSERTION_START
    # The nrr_proxy_delta calculation requires a positive target_overs for division,
    # but this only applies to rows where result == 'runs'.
    runs_mask = df['result'] == 'runs'
    assert (df.loc[runs_mask, 'target_overs'] > 0).all()
    # ASSERTION_END
    # Only league matches contribute to league table and seeding
    league = df[df['match_type'] == 'League'].copy()
    # ASSERTION_START
    decided_mask = league['result'].isin(['runs', 'wickets', 'tie'])
    w_ok = (league.loc[decided_mask, 'winner'] == league.loc[decided_mask, 'team1']) | (
                league.loc[decided_mask, 'winner'] == league.loc[decided_mask, 'team2'])
    assert w_ok.all()
    nr_mask = league['result'].eq('no result')
    assert league.loc[nr_mask, 'winner'].isna().all()
    # ASSERTION_END
    # ASSERTION_START
    wkt_mask = league['result'].eq('wickets')
    rm_wkt = league.loc[wkt_mask, 'result_margin']
    assert ((rm_wkt.notna()) & (rm_wkt >= 1) & (rm_wkt <= 10) & ((rm_wkt % 1) == 0)).all()
    runs_mask = league['result'].eq('runs')
    rm_runs = league.loc[runs_mask, 'result_margin']
    assert ((rm_runs.notna()) & (rm_runs > 0)).all()
    # ASSERTION_END
    # Expand matches to team-centric rows
    a = league.copy()
    a['team'] = a['team1']
    a['opponent'] = a['team2']

    b = league.copy()
    b['team'] = b['team2']
    b['opponent'] = b['team1']

    long = pd.concat([a, b], ignore_index=True, sort=False)

    # Points: 2 for winner (including super-over tie winner), 1 each for no result
    conds = [
        long['result'].eq('no result'),
        long['team'].eq(long['winner'])
    ]
    choices = [1, 2]
    long['points'] = np.select(conds, choices, default=0).astype(int)

    long['win'] = (long['team'] == long['winner']).astype(int)
    long['loss'] = ((long['team'] != long['winner']) & long['result'].isin(['runs', 'wickets', 'tie'])).astype(int)
    long['nr'] = long['result'].eq('no result').astype(int)

    # Net performance proxy used for seeding tie-break (uses D/L-adjusted overs when present)
    # Positive for winner, negative for loser; scaled for comparability across contexts
    sign = np.where(long['team'] == long['winner'], 1.0, -1.0)
    nrr_runs = np.where(long['result'].eq('runs'), sign * (long['result_margin'] / long['target_overs']), 0.0)
    nrr_wkts = np.where(long['result'].eq('wickets'), sign * (long['result_margin'] / 10.0), 0.0)
    nrr_tie = np.where(long['result'].eq('tie'), np.where(long['team'] == long['winner'], 0.02, -0.02), 0.0)
    long['nrr_proxy_delta'] = nrr_runs + nrr_wkts + nrr_tie

    # Track super-over wins/losses explicitly for transparency and potential tie-breaks
    long['so_win'] = ((long['result'] == 'tie') & (long['team'] == long['winner'])).astype(int)

    # Aggregate season/team
    agg = long.groupby(['season', 'team'], as_index=False).agg(
        points=('points', 'sum'),
        won=('win', 'sum'),
        lost=('loss', 'sum'),
        nr=('nr', 'sum'),
        nrr_proxy=('nrr_proxy_delta', 'sum'),
        so_wins=('so_win', 'sum')
    )
    agg['played'] = agg['won'] + agg['lost'] + agg['nr']

    # Order points table
    points_table = (
        agg.sort_values(['season', 'points', 'nrr_proxy', 'won', 'so_wins', 'team'],
                        ascending=[True, False, False, False, False, True])
    )

    # Seeding per season (top 4)
    points_table['seed'] = points_table.groupby('season').cumcount() + 1
    playoff_seeding = points_table[points_table['seed'] <= 4][['season', 'seed', 'team']]

    points_out = os.path.join(out_dir, 'league_points_table.csv')
    seeding_out = os.path.join(out_dir, 'playoff_seeding.csv')

    points_cols = ['season', 'team', 'played', 'won', 'lost', 'nr', 'points', 'nrr_proxy', 'so_wins']
    points_table.to_csv(points_out, index=False, columns=points_cols)
    playoff_seeding.to_csv(seeding_out, index=False)


if __name__ == '__main__':
    main()
