import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    input_file = os.path.join(args.input, 'new_data.csv')

    df = pd.read_csv(input_file)

    # Normalize and coerce types used downstream
    df['result'] = df['result'].astype(str).str.strip().str.lower()
    df['super_over'] = df['super_over'].astype(str).str.strip().str.upper()
    df['result_margin'] = pd.to_numeric(df.get('result_margin'), errors='coerce')
    df['date'] = pd.to_datetime(df.get('date'), errors='coerce')

    # Masks used throughout
    mask_runs = df['result'] == 'runs'
    mask_wkts = df['result'] == 'wickets'
    mask_tie = df['result'] == 'tie'
    mask_nr = df['result'] == 'no result'
    mask_decided = mask_runs | mask_wkts
    # ASSERTION_START
    # Enforce that a tie implies a super over, as assumed by the summary logic.
    cond_tie_implies_super = (~mask_tie | (df['super_over'] == 'Y')).all()
    assert cond_tie_implies_super

    # ASSERTION_END
    # ASSERTION_START
    # Validate run-margin constraints before computing scaled factors
    def check_runs_margin(s):
        s2 = pd.to_numeric(s, errors='coerce')
        return s2.notna() & (np.floor(s2) == s2) & (s2 > 0)

    assert check_runs_margin(df.loc[mask_runs, 'result_margin']).all()
    # ASSERTION_END
    # Compute scaled factor for runs
    df['run_factor'] = np.nan
    df.loc[mask_runs, 'run_factor'] = (df.loc[mask_runs, 'result_margin'].astype(int).clip(upper=200) / 200.0).astype(
        float)

    # ASSERTION_START
    # Validate wicket-margin constraints before computing scaled factors
    def check_wickets_margin(s):
        s2 = pd.to_numeric(s, errors='coerce')
        return s2.notna() & (np.floor(s2) == s2) & (s2 >= 1) & (s2 <= 10)

    assert check_wickets_margin(df.loc[mask_wkts, 'result_margin']).all()
    # ASSERTION_END
    # Compute scaled factor for wickets (1..10 -> 0.1..1.0)
    df['wk_factor'] = np.nan
    df.loc[mask_wkts, 'wk_factor'] = (df.loc[mask_wkts, 'result_margin'].astype(int) / 10.0).astype(float)
    # ASSERTION_START
    # Guard loser derivation logic and team validity
    # All valid matches must have two distinct, non-null teams.
    mask_match = mask_decided | mask_tie | mask_nr
    assert df.loc[mask_match, ['team1', 'team2']].notna().all().all()
    assert (df.loc[mask_match, 'team1'] != df.loc[mask_match, 'team2']).all()

    # Winner must be non-null if the match was decided.
    assert df.loc[mask_decided, 'winner'].notna().all()

    # For decided matches, the winner must be one of the two teams.
    valid_winner = (df['winner'] == df['team1']) | (df['winner'] == df['team2'])
    assert valid_winner[mask_decided].all()
    # ASSERTION_END
    # Derive losing team for decided matches
    loser_calc = np.where(
        df['winner'].eq(df['team1']), df['team2'],
        np.where(df['winner'].eq(df['team2']), df['team1'], pd.NA)
    )
    df['loser'] = pd.Series(loser_calc, index=df.index)
    df.loc[~mask_decided, 'loser'] = pd.NA
    # Outcome summaries per match
    summary = pd.Series(index=df.index, dtype=object)
    # Decided by runs
    if mask_runs.any():
        summary.loc[mask_runs] = (
                df.loc[mask_runs, 'winner'].astype(str)
                + ' won by '
                + df.loc[mask_runs, 'result_margin'].astype(int).astype(str)
                + ' runs'
        )
    # Decided by wickets
    if mask_wkts.any():
        summary.loc[mask_wkts] = (
                df.loc[mask_wkts, 'winner'].astype(str)
                + ' won by '
                + df.loc[mask_wkts, 'result_margin'].astype(int).astype(str)
                + ' wickets'
        )
    # Tied (super over expected from assertion)
    if mask_tie.any():
        summary.loc[mask_tie] = (
                df.loc[mask_tie, 'team1'].astype(str)
                + ' and '
                + df.loc[mask_tie, 'team2'].astype(str)
                + ' tied; Super Over'
        )
    # No result
    if mask_nr.any():
        summary.loc[mask_nr] = 'Match abandoned; no result'

    df['outcome_summary'] = summary

    # Points allocation and per-team match events
    # Positive impact for winners in decided matches
    df['pos_impact'] = 0.0
    df.loc[mask_runs, 'pos_impact'] = df.loc[mask_runs, 'run_factor']
    df.loc[mask_wkts, 'pos_impact'] = df.loc[mask_wkts, 'wk_factor']

    # Build events for standings
    events = []

    # Winners (decided)
    winners_ev = df.loc[mask_decided, ['id', 'season', 'date', 'winner', 'pos_impact']].copy()
    winners_ev.rename(columns={'winner': 'team'}, inplace=True)
    winners_ev['outcome'] = 'W'
    winners_ev['points'] = 2
    winners_ev['net_impact'] = winners_ev['pos_impact']
    events.append(winners_ev[['id', 'season', 'date', 'team', 'outcome', 'points', 'net_impact']])

    # Losers (decided)
    losers_ev = df.loc[mask_decided, ['id', 'season', 'date', 'loser', 'pos_impact']].copy()
    losers_ev.rename(columns={'loser': 'team'}, inplace=True)
    losers_ev['outcome'] = 'L'
    losers_ev['points'] = 0
    losers_ev['net_impact'] = -losers_ev['pos_impact']
    events.append(losers_ev[['id', 'season', 'date', 'team', 'outcome', 'points', 'net_impact']])

    # Ties -> one point each
    if mask_tie.any():
        tie_ev_t1 = df.loc[mask_tie, ['id', 'season', 'date', 'team1']].copy()
        tie_ev_t1.rename(columns={'team1': 'team'}, inplace=True)
        tie_ev_t1['outcome'] = 'T'
        tie_ev_t1['points'] = 1
        tie_ev_t1['net_impact'] = 0.0

        tie_ev_t2 = df.loc[mask_tie, ['id', 'season', 'date', 'team2']].copy()
        tie_ev_t2.rename(columns={'team2': 'team'}, inplace=True)
        tie_ev_t2['outcome'] = 'T'
        tie_ev_t2['points'] = 1
        tie_ev_t2['net_impact'] = 0.0

        events.extend([
            tie_ev_t1[['id', 'season', 'date', 'team', 'outcome', 'points', 'net_impact']],
            tie_ev_t2[['id', 'season', 'date', 'team', 'outcome', 'points', 'net_impact']],
        ])

    # No result -> one point each
    if mask_nr.any():
        nr_ev_t1 = df.loc[mask_nr, ['id', 'season', 'date', 'team1']].copy()
        nr_ev_t1.rename(columns={'team1': 'team'}, inplace=True)
        nr_ev_t1['outcome'] = 'NR'
        nr_ev_t1['points'] = 1
        nr_ev_t1['net_impact'] = 0.0

        nr_ev_t2 = df.loc[mask_nr, ['id', 'season', 'date', 'team2']].copy()
        nr_ev_t2.rename(columns={'team2': 'team'}, inplace=True)
        nr_ev_t2['outcome'] = 'NR'
        nr_ev_t2['points'] = 1
        nr_ev_t2['net_impact'] = 0.0

        events.extend([
            nr_ev_t1[['id', 'season', 'date', 'team', 'outcome', 'points', 'net_impact']],
            nr_ev_t2[['id', 'season', 'date', 'team', 'outcome', 'points', 'net_impact']],
        ])

    events_df = pd.concat(events, ignore_index=True) if events else pd.DataFrame(
        columns=['id', 'season', 'date', 'team', 'outcome', 'points', 'net_impact']
    )

    # Aggregate to standings per season/team
    if not events_df.empty:
        agg = events_df.groupby(['season', 'team']).agg(
            played=('id', 'count'),
            wins=('outcome', lambda s: (s == 'W').sum()),
            losses=('outcome', lambda s: (s == 'L').sum()),
            ties=('outcome', lambda s: (s == 'T').sum()),
            no_results=('outcome', lambda s: (s == 'NR').sum()),
            points=('points', 'sum'),
            net_impact=('net_impact', 'sum')
        ).reset_index()
        agg['win_pct'] = np.where(
            agg['played'] > 0,
            (agg['wins'] / agg['played']).round(4),
            0.0
        )
    else:
        agg = pd.DataFrame(
            columns=['season', 'team', 'played', 'wins', 'losses', 'ties', 'no_results', 'points', 'net_impact',
                     'win_pct'])

    # Per-match summaries output
    match_summaries = df[
        ['id', 'season', 'date', 'match_type', 'team1', 'team2', 'winner', 'loser', 'result', 'result_margin',
         'super_over', 'outcome_summary']].copy()

    # Also include per-match points awarded to each team for transparency
    # Decided matches
    match_summaries['points_team1'] = 0
    match_summaries['points_team2'] = 0
    match_summaries.loc[mask_decided & df['winner'].eq(df['team1']), 'points_team1'] = 2
    match_summaries.loc[mask_decided & df['winner'].eq(df['team2']), 'points_team2'] = 2
    # Ties and NR
    match_summaries.loc[mask_tie | mask_nr, ['points_team1', 'points_team2']] = 1

    match_summaries.sort_values(['season', 'date', 'id'], inplace=True)
    agg.sort_values(['season', 'points', 'net_impact', 'win_pct'], ascending=[True, False, False, False], inplace=True)

    match_summaries.to_csv(os.path.join(args.output, 'match_summaries.csv'), index=False)
    agg.to_csv(os.path.join(args.output, 'standings_by_season.csv'), index=False)


if __name__ == '__main__':
    main()
