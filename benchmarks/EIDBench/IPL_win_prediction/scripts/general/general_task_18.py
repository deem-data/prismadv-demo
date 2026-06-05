import argparse
import os
import json
import pandas as pd
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Parse date for downstream use
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
    # ASSERTION_START
    assert df['team1'].notna().all()
    assert df['team2'].notna().all()
    assert (df['team1'] != df['team2']).all()
    # ASSERTION_END
    # ASSERTION_START
    assert ((df['toss_winner'] == df['team1']) | (df['toss_winner'] == df['team2'])).all()
    # ASSERTION_END
    # Derive toss-related fields used in summaries
    df['toss_winner_side'] = np.where(df['toss_winner'] == df['team1'], 'team1', 'team2')
    df['batting_first'] = np.where(
        (df['toss_winner'] == df['team1']) & (df['toss_decision'] == 'bat'), df['team1'],
        np.where(
            (df['toss_winner'] == df['team2']) & (df['toss_decision'] == 'bat'), df['team2'],
            np.where(
                (df['toss_winner'] == df['team1']) & (df['toss_decision'] == 'field'), df['team2'],
                df['team1']
            )
        )
    )
    df['batting_second'] = np.where(df['batting_first'] == df['team1'], df['team2'], df['team1'])
    # ASSERTION_START
    mask_nores = df['result'].eq('no result')
    mask_played = ~mask_nores
    assert df.loc[mask_nores, 'winner'].isna().all()
    assert ((df.loc[mask_played, 'winner'] == df.loc[mask_played, 'team1']) | (df.loc[mask_played, 'winner'] == df.loc[mask_played, 'team2'])).all()
    # ASSERTION_END
    # Compute loser used in summaries
    df['loser'] = np.where(
        df['result'].ne('no result'),
        np.where(df['winner'] == df['team1'], df['team2'], df['team1']),
        pd.NA
    )
    # ASSERTION_START
    mask_notna_margin = df['result_margin'].notna()
    assert pd.to_numeric(df.loc[mask_notna_margin, 'result_margin'], errors='coerce').notna().all()

    mask_runs = df['result'].eq('runs')
    mask_wickets = df['result'].eq('wickets')

    margins_runs = pd.to_numeric(df.loc[mask_runs, 'result_margin'])
    assert margins_runs.notna().all()
    assert (margins_runs > 0).all()
    assert (margins_runs == np.floor(margins_runs)).all()

    margins_wickets = pd.to_numeric(df.loc[mask_wickets, 'result_margin'])
    assert margins_wickets.notna().all()
    assert (margins_wickets > 0).all()
    assert (margins_wickets == np.floor(margins_wickets)).all()
    # ASSERTION_END
    def build_summary(row):
        date_str = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
        venue = row['venue']
        season_val = row['season']
        match_id = row['id']
        tw = row['toss_winner']
        td = row['toss_decision']
        bf = row['batting_first']
        base = f'Season {season_val} - Match {match_id}'
        toss_part = f'Toss: {tw} elected to {td}.'
        innings_part = f' First innings: {bf}.'
        method_part = ''
        method_val = row['method']
        if pd.notna(method_val) and str(method_val).strip() != '' and str(method_val).strip().upper() != 'NAN':
            if str(method_val).strip() == 'D/L' and pd.notna(row['target_runs']) and pd.notna(row['target_overs']):
                try:
                    tr = int(float(row['target_runs']))
                except Exception:
                    tr = row['target_runs']
                try:
                    tovers = int(float(row['target_overs']))
                except Exception:
                    tovers = row['target_overs']
                method_part = f' Target {tr} in {tovers} overs (D/L).'
            else:
                method_part = f' ({method_val}).'
        if row['result'] == 'no result':
            return f'{base}: No result at {venue} on {date_str}. {toss_part}'
        if row['result'] == 'runs':
            margin = int(float(row['result_margin']))
            return f'{base}: {row['winner']} beat {row['loser']} by {margin} runs at {venue} on {date_str}. {toss_part}{innings_part}{method_part}'
        if row['result'] == 'wickets':
            margin = int(float(row['result_margin']))
            return f'{base}: {row['winner']} beat {row['loser']} by {margin} wickets at {venue} on {date_str}. {toss_part}{innings_part}{method_part}'
        if row['result'] == 'tie':
            return f'{base}: {row['winner']} won in Super Over after a tie at {venue} on {date_str}. {toss_part}{innings_part}{method_part}'
        return f'{base}: Result {row['result']} at {venue} on {date_str}. {toss_part}{innings_part}{method_part}'

    summaries = df.apply(build_summary, axis=1)

    publish_df = pd.DataFrame({
        'id': df['id'],
        'season': df['season'],
        'date': df['date'],
        'city': df['city'],
        'venue': df['venue'],
        'team1': df['team1'],
        'team2': df['team2'],
        'winner': df['winner'],
        'loser': df['loser'],
        'result': df['result'],
        'result_margin': df['result_margin'],
        'super_over': df['super_over'],
        'method': df['method'],
        'summary': summaries
    })

    csv_out = os.path.join(args.output, 'post_match_summaries.csv')
    publish_df.to_csv(csv_out, index=False)

    feed_path = os.path.join(args.output, 'syndication_feed.jsonl')
    with open(feed_path, 'w', encoding='utf-8') as f:
        for _, row in publish_df.iterrows():
            rec = {
                'id': int(row['id']),
                'season': str(row['season']),
                'winner': None if pd.isna(row['winner']) else str(row['winner']),
                'loser': None if pd.isna(row['loser']) else str(row['loser']),
                'result': str(row['result']),
                'result_margin': None if pd.isna(row['result_margin']) else float(row['result_margin']),
                'super_over': str(row['super_over']),
                'method': None if pd.isna(row['method']) else str(row['method']),
                'summary': row['summary']
            }
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    stats = {
        'published_count': int(len(publish_df)),
        'ties': int((df['result'] == 'tie').sum()),
        'no_results': int((df['result'] == 'no result').sum()),
        'runs_decisions': int((df['result'] == 'runs').sum()),
        'wickets_decisions': int((df['result'] == 'wickets').sum())
    }
    with open(os.path.join(args.output, 'publish_stats.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False)


if __name__ == '__main__':
    main()
