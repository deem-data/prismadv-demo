import argparse
import json
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    matches_path = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(matches_path)

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['result_margin'] = pd.to_numeric(df['result_margin'], errors='coerce')
    df['target_runs'] = pd.to_numeric(df['target_runs'], errors='coerce')
    df['target_overs'] = pd.to_numeric(df['target_overs'], errors='coerce')
    # ASSERTION_START
    assert df['date'].notna().all()
    # ASSERTION_END
    # ASSERTION_START
    assert (df['team1'] != df['team2']).all()
    # ASSERTION_END
    # ASSERTION_START
    assert ((df['toss_winner'] == df['team1']) | (df['toss_winner'] == df['team2'])).all()
    # ASSERTION_END
    # ASSERTION_START
    mask_decisive = ~df['result'].isin(['no result', 'tie'])
    assert ((df.loc[mask_decisive, 'winner'] == df.loc[mask_decisive, 'team1']) | (
            df.loc[mask_decisive, 'winner'] == df.loc[mask_decisive, 'team2'])).all()
    # ASSERTION_END
    # ASSERTION_START
    m_w = df.loc[df['result'] == 'wickets', 'result_margin']
    m_r = df.loc[df['result'] == 'runs', 'result_margin']
    assert (m_w > 0).all()
    assert (m_r > 0).all()
    # ASSERTION_END
    base_cols = ['id', 'season', 'date', 'winner', 'result', 'result_margin', 'super_over', 'toss_winner', 'team1',
                 'team2']
    df_base = df[base_cols].copy()

    t1 = df_base.copy()
    t1['team'] = t1['team1']
    t1['opponent'] = t1['team2']
    t2 = df_base.copy()
    t2['team'] = t2['team2']
    t2['opponent'] = t2['team1']

    t1['is_winner'] = t1['winner'] == t1['team']
    t2['is_winner'] = t2['winner'] == t2['team']

    t1['toss_won'] = t1['toss_winner'] == t1['team']
    t2['toss_won'] = t2['toss_winner'] == t2['team']

    t1['points'] = np.where(t1['result'] == 'no result', 1, np.where(t1['is_winner'], 2, 0))
    t2['points'] = np.where(t2['result'] == 'no result', 1, np.where(t2['is_winner'], 2, 0))

    t1['win_by_runs'] = np.where((t1['is_winner']) & (t1['result'] == 'runs'), t1['result_margin'], 0)
    t2['win_by_runs'] = np.where((t2['is_winner']) & (t2['result'] == 'runs'), t2['result_margin'], 0)

    t1['win_by_wkts'] = np.where((t1['is_winner']) & (t1['result'] == 'wickets'), t1['result_margin'], 0)
    t2['win_by_wkts'] = np.where((t2['is_winner']) & (t2['result'] == 'wickets'), t2['result_margin'], 0)

    long_df = pd.concat([t1, t2], ignore_index=True)

    long_df['played'] = 1
    long_df['win'] = ((long_df['result'] != 'no result') & long_df['is_winner']).astype(int)
    long_df['loss'] = ((long_df['result'] != 'no result') & (~long_df['is_winner'])).astype(int)
    long_df['tie'] = (long_df['result'] == 'tie').astype(int)
    long_df['no_result'] = (long_df['result'] == 'no result').astype(int)
    long_df['win_after_toss_win'] = ((long_df['toss_won']) & (long_df['win'] == 1)).astype(int)
    long_df['toss_wins'] = long_df['toss_won'].astype(int)

    agg = long_df.groupby(['season', 'team'], as_index=False).agg(
        matches=('played', 'sum'),
        wins=('win', 'sum'),
        losses=('loss', 'sum'),
        ties=('tie', 'sum'),
        no_result=('no_result', 'sum'),
        points=('points', 'sum'),
        toss_wins=('toss_wins', 'sum'),
        wins_after_winning_toss=('win_after_toss_win', 'sum'),
        run_wins=('win_by_runs', lambda s: (s > 0).sum()),
        wicket_wins=('win_by_wkts', lambda s: (s > 0).sum()),
        avg_run_margin=('win_by_runs', lambda s: s[s > 0].mean() if (s > 0).any() else 0.0),
        avg_wickets_remaining=('win_by_wkts', lambda s: s[s > 0].mean() if (s > 0).any() else 0.0)
    )

    agg['points_per_match'] = agg['points'] / agg['matches'].replace(0, np.nan)
    agg['points_per_match'] = agg['points_per_match'].fillna(0.0)

    agg = agg.sort_values(['season', 'points', 'wins', 'avg_run_margin', 'avg_wickets_remaining'],
                          ascending=[True, False, False, False, False])

    standings_path = os.path.join(args.output, 'standings.csv')
    agg.to_csv(standings_path, index=False)

    seasons = sorted(agg['season'].dropna().unique())
    for s in seasons:
        s_table = agg[agg['season'] == s].copy()
        s_table = s_table.sort_values(['points', 'wins', 'avg_run_margin', 'avg_wickets_remaining'],
                                      ascending=[False, False, False, False])
        top_teams = s_table.head(4)[['team', 'points', 'wins', 'losses', 'no_result']].to_dict(orient='records')

        s_matches = df[df['season'] == s].copy()
        s_matches = s_matches.sort_values('date')
        total_games = len(s_matches)
        tie_games = int((s_matches['result'] == 'tie').sum())
        no_result_games = int((s_matches['result'] == 'no result').sum())

        dashboard = {
            'season': str(s),
            'total_games': total_games,
            'tie_games': tie_games,
            'no_result_games': no_result_games,
            'top_teams': top_teams
        }
        s = s.replace("/", "_") if isinstance(s, str) else s
        dash_path = os.path.join(args.output, f'season_{s}_dashboard.json')
        with open(dash_path, 'w') as f:
            json.dump(dashboard, f, indent=2)


if __name__ == '__main__':
    main()
