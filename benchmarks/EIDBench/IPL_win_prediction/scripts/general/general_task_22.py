import argparse
import json
import os

import numpy as np
import pandas as pd


def compute_group_kpis(g: pd.DataFrame) -> pd.Series:
    total = len(g)
    played_cnt = int(g['played'].sum())

    toss_win_rate = float(g.loc[g['played'], 'toss_won_match'].mean()) if played_cnt > 0 else np.nan
    chasing_win_rate = float(g.loc[g['played'], 'chasing_win'].mean()) if played_cnt > 0 else np.nan

    avg_margin_runs = float(g.loc[g['is_runs'], 'margin_runs'].mean()) if g['is_runs'].any() else np.nan
    avg_margin_wickets = float(g.loc[g['is_wickets'], 'margin_wkts'].mean()) if g['is_wickets'].any() else np.nan

    return pd.Series({
        'matches': total,
        'matches_played': played_cnt,
        'toss_win_rate': toss_win_rate,
        'chasing_win_rate': chasing_win_rate,
        'avg_margin_runs': avg_margin_runs,
        'avg_margin_wickets': avg_margin_wickets,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    input_file = os.path.join(args.input, 'new_data.csv')

    df = pd.read_csv(input_file)

    # Basic normalization
    df['season'] = df['season'].astype(str).str.strip()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['result_lc'] = df['result'].astype(str).str.strip().str.lower()
    df['toss_decision_lc'] = df['toss_decision'].astype(str).str.strip().str.lower()
    df['super_over_u'] = df['super_over'].astype(str).str.strip().str.upper()

    # Coerce margins to numeric for downstream math
    df['result_margin'] = pd.to_numeric(df['result_margin'], errors='coerce')
    # ASSERTION_START
    assert (df['team1'] != df['team2']).all()
    assert ((df['toss_winner'] == df['team1']) | (df['toss_winner'] == df['team2'])).all()
    # ASSERTION_END
    # Derive chasing team using toss decision
    df['chasing_team'] = np.where(
        df['toss_decision_lc'] == 'field',
        df['toss_winner'],
        np.where(df['toss_winner'] == df['team1'], df['team2'], df['team1'])
    )

    # Played indicator (exclude no result)
    df['played'] = df['result_lc'] != 'no result'
    # ASSERTION_START
    played_subset = df.loc[df['played']]
    is_valid_winner = (played_subset['winner'] == played_subset['team1']) | (
                played_subset['winner'] == played_subset['team2'])
    assert (is_valid_winner | played_subset['winner'].isna()).all()
    # ASSERTION_END
    # Toss impact features
    df['toss_won_match'] = df['played'] & (df['toss_winner'] == df['winner'])

    # Result-type flags
    df['is_runs'] = df['result_lc'] == 'runs'
    df['is_wickets'] = df['result_lc'] == 'wickets'
    # ASSERTION_START
    runs_mask = df['is_runs']
    result_margin_runs = df.loc[runs_mask, 'result_margin']
    assert (result_margin_runs.isna() | (result_margin_runs > 0)).all()

    wickets_mask = df['is_wickets']
    result_margin_wickets = df.loc[wickets_mask, 'result_margin']
    assert (result_margin_wickets.isna() | (result_margin_wickets > 0)).all()
    # ASSERTION_END
    # Chasing outcome
    df['chasing_win'] = df['played'] & (df['winner'] == df['chasing_team'])

    # Victory margins (typed by mode)
    df['margin_runs'] = np.where(df['is_runs'], df['result_margin'], np.nan)
    df['margin_wkts'] = np.where(df['is_wickets'], df['result_margin'], np.nan)

    # KPI by (season, match_type)
    kpi_sm = df.groupby(['season', 'match_type']).apply(compute_group_kpis).reset_index()

    # Champions (winner of the Final per season)
    finals = df[df['match_type'].astype(str).str.strip().str.casefold() == 'final']
    # ASSERTION_START
    finals_counts = finals.groupby('season').size()
    assert (finals_counts == 1).all()
    # ASSERTION_END
    champions = finals[['season', 'winner']].rename(columns={'winner': 'champion'}).drop_duplicates('season')

    # KPI by season (all match types combined)
    kpi_s = df.groupby('season').apply(compute_group_kpis).reset_index()
    season_summary = kpi_s.merge(champions, on='season', how='left')

    # Persist KPIs
    kpi_sm_out = os.path.join(args.output, 'season_matchtype_kpis.csv')
    kpi_sm.to_csv(kpi_sm_out, index=False)

    season_summary_out = os.path.join(args.output, 'season_summary.csv')
    season_summary.to_csv(season_summary_out, index=False)

    # Alerts for latest season
    season_ints = pd.to_numeric(df['season'], errors='coerce')
    latest_season = str(int(np.nanmax(season_ints))) if not np.isnan(np.nanmax(season_ints)) else None

    alerts = []
    if latest_season is not None:
        row_league = kpi_sm[(kpi_sm['season'] == latest_season) & (kpi_sm['match_type'] == 'League')]
        if not row_league.empty:
            r = row_league.iloc[0]
            if pd.notna(r['toss_win_rate']) and r['toss_win_rate'] >= 0.6:
                alerts.append({
                    'type': 'toss_impact_high',
                    'season': latest_season,
                    'match_type': 'League',
                    'value': round(float(r['toss_win_rate']), 4)
                })
            if pd.notna(r['chasing_win_rate']) and r['chasing_win_rate'] >= 0.55:
                alerts.append({
                    'type': 'chasing_dominant',
                    'season': latest_season,
                    'match_type': 'League',
                    'value': round(float(r['chasing_win_rate']), 4)
                })
        row_final = kpi_sm[
            (kpi_sm['season'] == latest_season) & (kpi_sm['match_type'].astype(str).str.strip() == 'Final')]
        if not row_final.empty:
            rf = row_final.iloc[0]
            champ = champions.loc[champions['season'] == latest_season, 'champion']
            champ_val = champ.iloc[0] if not champ.empty else None
            alerts.append({
                'type': 'season_champion',
                'season': latest_season,
                'champion': champ_val,
                'avg_margin_runs_final': (
                    None if pd.isna(rf['avg_margin_runs']) else round(float(rf['avg_margin_runs']), 2)),
                'avg_margin_wickets_final': (
                    None if pd.isna(rf['avg_margin_wickets']) else round(float(rf['avg_margin_wickets']), 2))
            })

    alerts_out = os.path.join(args.output, 'alerts.json')
    with open(alerts_out, 'w', encoding='utf-8') as f:
        json.dump({'alerts': alerts}, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
