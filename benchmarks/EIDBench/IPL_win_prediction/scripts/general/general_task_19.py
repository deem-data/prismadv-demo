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

    # Basic typing and derived fields
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    season_numeric = pd.to_numeric(df['season'], errors='coerce')
    year_from_date = df['date'].dt.year

    # ASSERTION_START
    # ASSERT season/date alignment before any season-based grouping
    assert season_numeric.notna().all()
    assert year_from_date.notna().all()
    assert (season_numeric.astype('int64') == year_from_date.astype('int64')).all()
    # ASSERTION_END
    df['season'] = season_numeric.astype(int)

    # Only League matches contribute to standings; summaries will be produced for all matches
    league_df = df[df['match_type'] == 'League'].copy()

    # ASSERTION_START
    # ASSERT opposing teams are different before computing winners/losers and points
    assert (league_df['team1'] != league_df['team2']).all()
    # ASSERTION_END
    # Winner presence depending on result
    non_nr = league_df[league_df['result'] != 'no result']
    # ASSERT winner present where a result exists
    # ASSERTION_START
    assert non_nr['winner'].notna().all()
    # ASSERTION_END
    # ASSERT winner must be one of the two teams in the fixture
    # ASSERTION_START
    w_in_teams = (non_nr['winner'] == non_nr['team1']) | (non_nr['winner'] == non_nr['team2'])
    assert w_in_teams.all()
    # ASSERTION_END
    # ASSERTION_START
    run_wkt_all_matches = df[df['result'].isin(['runs', 'wickets'])]
    run_wkt_all_matches_valid = run_wkt_all_matches.dropna(subset=['result_margin', 'winner'])
    if len(run_wkt_all_matches_valid) > 0:
        rm = run_wkt_all_matches_valid['result_margin']
    assert (rm > 0).all()
    assert np.array_equal(rm.values, np.floor(rm.values))
    # ASSERTION_END
    tie_nr = league_df[league_df['result'].isin(['tie', 'no result'])]
    # ASSERT super_over implies a tied result prior to super over resolution
    # ASSERTION_START
    so = df[df['super_over'] == 'Y']
    if len(so) > 0:
        assert (so['result'] == 'tie').all()
    # ASSERTION_END
    # For D/L method, ensure target_overs are valid before computing derived metrics
    dls = df[df['method'] == 'D/L']
    # ASSERTION_START
    if len(dls) > 0:
        dls_targets_present = dls.dropna(subset=['target_runs', 'target_overs'])
        if len(dls_targets_present) > 0:
            tr = dls_targets_present['target_runs']
            to = dls_targets_present['target_overs']
            assert (to > 0).all()
            assert (tr >= 0).all()
            assert np.array_equal(tr, np.floor(tr))
            assert np.array_equal(to, np.floor(to))

    # ASSERTION_END
    # Build post-match summaries (all matches)
    def summarize_row(row: pd.Series) -> str:
        t1 = row['team1']
        t2 = row['team2']
        res = row['result']
        w = row['winner'] if pd.notna(row['winner']) else None
        date_str = row['date'].date().isoformat() if not pd.isna(row['date']) else str(row['date'])
        venue = row['venue']
        add = ''
        if row.get('method') == 'D/L' and pd.notna(row.get('target_runs')) and pd.notna(row.get('target_overs')):
            # Safe because of D/L assertions above
            rrr = row['target_runs'] / row['target_overs']
            add = f" (DLS target {int(row['target_runs'])} in {int(row['target_overs'])} overs, req RR {rrr:.2f})"
        if res in ('runs', 'wickets') and pd.notna(row['result_margin']) and w is not None:
            loser = t2 if w == t1 else t1
            margin = int(row['result_margin'])
            return f"{date_str}: {w} beat {loser} by {margin} {res} at {venue}{add}"
        elif res == 'tie' and w is not None:
            opponent = t2 if w == t1 else t1
            if row.get('super_over') == 'Y':
                return f"{date_str}: {w} won via Super Over after tie vs {opponent} at {venue}{add}"
            else:
                return f"{date_str}: {t1} tied with {t2} at {venue}; winner adjudicated as {w}{add}"
        elif res == 'no result':
            return f"{date_str}: {t1} vs {t2} was abandoned at {venue}{add}"
        else:
            # Fallback if unexpected combination slips through (should be gated by assertions)
            return f"{date_str}: {t1} vs {t2} concluded; outcome recorded as '{res}' at {venue}{add}"

    summaries = df.copy()
    summaries['summary'] = summaries.apply(summarize_row, axis=1)
    summaries[['id', 'season', 'date', 'team1', 'team2', 'winner', 'result', 'result_margin', 'super_over', 'method',
               'summary']].to_csv(
        os.path.join(args.output, 'post_match_summaries.csv'), index=False
    )

    # Compute league points and standings (League matches only)
    # Prepare winner and loser mapping (safe because of winner assertions above)
    non_nr = league_df[league_df['result'] != 'no result'].copy()
    non_nr['loser'] = np.where(non_nr['winner'] == non_nr['team1'], non_nr['team2'], non_nr['team1'])

    win_tx = non_nr[['season', 'winner']].copy()
    win_tx['team'] = win_tx['winner']
    win_tx = win_tx.drop(columns=['winner'])
    win_tx['win'] = 1
    win_tx['loss'] = 0
    win_tx['nr'] = 0
    win_tx['points'] = 2

    lose_tx = non_nr[['season', 'loser']].copy()
    lose_tx['team'] = lose_tx['loser']
    lose_tx = lose_tx.drop(columns=['loser'])
    lose_tx['win'] = 0
    lose_tx['loss'] = 1
    lose_tx['nr'] = 0
    lose_tx['points'] = 0

    nr_tx_t1 = league_df[league_df['result'] == 'no result'][['season', 'team1']].copy()
    nr_tx_t1['team'] = nr_tx_t1['team1']
    nr_tx_t1 = nr_tx_t1.drop(columns=['team1'])
    nr_tx_t1['win'] = 0
    nr_tx_t1['loss'] = 0
    nr_tx_t1['nr'] = 1
    nr_tx_t1['points'] = 1

    nr_tx_t2 = league_df[league_df['result'] == 'no result'][['season', 'team2']].copy()
    nr_tx_t2['team'] = nr_tx_t2['team2']
    nr_tx_t2 = nr_tx_t2.drop(columns=['team2'])
    nr_tx_t2['win'] = 0
    nr_tx_t2['loss'] = 0
    nr_tx_t2['nr'] = 1
    nr_tx_t2['points'] = 1

    tx = pd.concat([win_tx, lose_tx, nr_tx_t1, nr_tx_t2], ignore_index=True)

    standings = tx.groupby(['season', 'team'], as_index=False).agg(
        wins=('win', 'sum'),
        losses=('loss', 'sum'),
        no_results=('nr', 'sum'),
        points=('points', 'sum')
    )
    standings['matches'] = standings['wins'] + standings['losses'] + standings['no_results']

    # Sort standings by season, then points desc, then wins desc
    standings = standings.sort_values(by=['season', 'points', 'wins'], ascending=[True, False, False])

    standings.to_csv(os.path.join(args.output, 'league_standings.csv'), index=False)


if __name__ == '__main__':
    main()
