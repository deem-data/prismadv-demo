import pandas as pd
import numpy as np
import argparse
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Normalize values used downstream
    for col in ['result', 'toss_decision']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
    if 'super_over' in df.columns:
        df['super_over'] = df['super_over'].astype(str).str.strip().str.upper()
    if 'method' in df.columns:
        df['method'] = df['method'].replace(['', 'NA', 'NaN', 'nan', 'NULL', 'Null', 'null', 'None', 'NullValue'], np.nan)

    # Coerce numerics
    for num_col in ['target_runs', 'target_overs', 'result_margin']:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors='coerce')

    # Parse date and season
    df['parsed_date'] = pd.to_datetime(df['date'], errors='coerce')
    df['season_int'] = pd.to_numeric(df['season'], errors='coerce')

    # ASSERTION_START
    # Use season/date downstream for grouping; guard before use
    assert df['parsed_date'].notna().all()
    # ASSERTION_END
    # ASSERTION_START
    assert (df['season_int'] == df['parsed_date'].dt.year).all()
    # ASSERTION_END
    # Settlement needs result domain to be tight
    allowed_results = {'runs', 'wickets', 'tie', 'no result'}
    # ASSERTION_START
    assert df['result'].isin(allowed_results).all()
    # ASSERTION_END
    # ASSERTION_START
    # Tie-super over coupling and domain of super_over
    tie_mask = df['result'] == 'tie'
    assert (df.loc[tie_mask, 'super_over'] == 'Y').all()
    # ASSERTION_END
    # ASSERTION_START
    assert (df.loc[df['super_over'] == 'Y', 'result'] == 'tie').all()
    # ASSERTION_END
    # Result margin consistency before converting to ints for settlement text
    runs_mask = df['result'] == 'runs'
    wkts_mask = df['result'] == 'wickets'
    # ASSERTION_START
    pos_int_margin_mask = df.loc[runs_mask | wkts_mask, 'result_margin'].notna() & (
        (df.loc[runs_mask | wkts_mask, 'result_margin'] > 0) &
        (np.floor(df.loc[runs_mask | wkts_mask, 'result_margin']) == df.loc[runs_mask | wkts_mask, 'result_margin'])
    )
    assert pos_int_margin_mask.all()
    # ASSERTION_END
    # ASSERTION_START
    # Winner/team/toss constraints needed for settlement strings and KPIs
    assert (df['team1'] != df['team2']).all()
    # ASSERTION_END
    # ASSERTION_START
    not_nr_mask = df['result'] != 'no result'
    assert df.loc[not_nr_mask].apply(lambda r: r['winner'] in {r['team1'], r['team2']}, axis=1).all()
    # ASSERTION_END
    # Prepare integers for margins used in settlement text
    df['margin_int'] = np.where(runs_mask | wkts_mask, df['result_margin'].astype('Int64'), pd.NA)

    # Build loser for resulted matches
    def other_team(row):
        if pd.isna(row['winner']):
            return pd.NA
        return row['team2'] if row['winner'] == row['team1'] else row['team1']

    df['loser'] = df.apply(other_team, axis=1)

    # Build settlement strings for outcome and margin markets
    def settlement_text(row):
        if row['result'] == 'no result':
            return 'VOID: no result'
        if row['result'] == 'tie':
            return f"{row['winner']} won after Super Over"
        if row['result'] == 'runs':
            return f"{row['winner']} beat {row['loser']} by {int(row['margin_int'])} runs"
        if row['result'] == 'wickets':
            return f"{row['winner']} beat {row['loser']} by {int(row['margin_int'])} wickets"
        return 'UNSETTLED'

    settlement = df.copy()
    settlement['settlement'] = settlement.apply(settlement_text, axis=1)

    # Save settled markets view
    settlement_out = settlement[['id', 'season', 'date', 'team1', 'team2', 'winner', 'result', 'result_margin', 'super_over', 'settlement']].copy()
    settlement_out.to_csv(os.path.join(args.output, 'settled_markets.csv'), index=False)

    # ASSERTION_START
    # Guard method/target constraints before computing rate KPIs
    assert (df['target_runs'].isna() | (df['target_runs'] == 0) | (df['target_overs'] > 0)).all()
    # ASSERTION_END
    # Required run rate per match
    df['req_run_rate'] = df['target_runs'] / df['target_overs']

    # ASSERTION_START
    # Toss decision checks before KPI calculation
    assert df['toss_decision'].isin({'field', 'bat'}).all()
    # ASSERTION_END
    # ASSERTION_START
    # Toss winner membership among teams used in KPI calc
    assert df.apply(lambda r: r['toss_winner'] in {r['team1'], r['team2']}, axis=1).all()
    # ASSERTION_END
    # Build season-level toss advantage KPIs
    kpi_df = df[df['result'] != 'no result'].copy()
    kpi_df['toss_winner_won'] = (kpi_df['toss_winner'] == kpi_df['winner']).astype(int)

    # Overall per-season rates
    season_rates = (
        kpi_df.groupby('season_int')
              .agg(matches=('id', 'size'),
                   toss_winner_match_win_rate=('toss_winner_won', 'mean'),
                   avg_req_run_rate=('req_run_rate', 'mean'))
              .reset_index()
    )

    # Decision-conditional success of toss winner
    decision_rates = (
        kpi_df.groupby(['season_int', 'toss_decision'])
              .agg(decision_toss_winner_win_rate=('toss_winner_won', 'mean'),
                   decision_matches=('id', 'size'))
              .reset_index()
              .pivot(index='season_int', columns='toss_decision', values='decision_toss_winner_win_rate')
              .rename(columns={'field': 'field_toss_winner_win_rate', 'bat': 'bat_toss_winner_win_rate'})
    )

    kpis = season_rates.merge(decision_rates, on='season_int', how='left')
    kpis['toss_decision_advantage'] = kpis['field_toss_winner_win_rate'] - kpis['bat_toss_winner_win_rate']

    kpis = kpis.rename(columns={'season_int': 'season'})
    kpis.to_csv(os.path.join(args.output, 'season_toss_kpis.csv'), index=False)


if __name__ == '__main__':
    main()
