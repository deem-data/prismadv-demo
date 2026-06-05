import argparse
import os
import pandas as pd
import numpy as np


def generate_points_table(df: pd.DataFrame) -> pd.DataFrame:
    # Work on a copy
    df = df.copy()

    # Focus on league-stage matches only for standings
    df = df[df['match_type'] == 'League'].copy()

    # Normalize types used downstream
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['season_int'] = pd.to_numeric(df['season'], errors='coerce')
    # ASSERTION_START
    assert df['id'].is_unique
    # ASSERTION_END
    # We rely on season as a calendar year for grouping and reporting
    # Matches must be between two distinct teams to award points correctly
    # ASSERTION_START
    assert (df['team1'] != df['team2']).all()
    # ASSERTION_END
    # Tie after 20 overs must imply a super over was played, and vice versa
    # ASSERTION_START
    assert ((df['result'] == 'tie') == (df['super_over'] == 'Y')).all()
    # ASSERTION_END
    # Construct per-team participation rows
    left = df[['id', 'season_int', 'team1', 'winner', 'result', 'super_over']].rename(columns={'team1': 'team'})
    right = df[['id', 'season_int', 'team2', 'winner', 'result', 'super_over']].rename(columns={'team2': 'team'})
    participants = pd.concat([left, right], ignore_index=True)

    # Before awarding points, ensure winner logic and NR logic are consistent
    # ASSERTION_START
    # For played matches, winner must be either team1 or team2 of that match
    check = df[['team1', 'team2', 'winner', 'result']].copy()
    mask_played = check['result'] != 'no result'
    assert ((check.loc[mask_played, 'winner'] == check.loc[mask_played, 'team1']) | (check.loc[mask_played, 'winner'] == check.loc[mask_played, 'team2'])).all()
    # ASSERTION_END
    # Compute per-team metrics
    participants['is_nr'] = participants['result'] == 'no result'
    participants['is_tie_in_overs'] = participants['super_over'] == 'Y'
    participants['is_winner'] = (participants['winner'] == participants['team']) & (~participants['is_nr'])
    participants['is_loser'] = (~participants['is_winner']) & (~participants['is_nr'])

    # Points: 2 for winner, 0 for loser, 1 each for no result
    participants['points'] = np.where(participants['is_nr'], 1, np.where(participants['is_winner'], 2, 0))

    agg = participants.groupby(['season_int', 'team'], as_index=False).agg(
        matches=('id', 'count'),
        wins=('is_winner', 'sum'),
        losses=('is_loser', 'sum'),
        no_results=('is_nr', 'sum'),
        super_over_played=('is_tie_in_overs', 'sum'),
        points=('points', 'sum')
    )

    # Derive win percentage
    denom = (agg['matches'] - agg['no_results']).replace({0: np.nan})
    agg['win_pct'] = (agg['wins'] / denom * 100).round(2)

    # Sort and rank within season by points, then wins
    agg.sort_values(['season_int', 'points', 'wins', 'team'], ascending=[True, False, False, True], inplace=True)
    agg['rank'] = agg.groupby('season_int')['points'].rank(method='dense', ascending=False).astype(int)

    # Final column order
    agg.rename(columns={'season_int': 'season'}, inplace=True)
    agg = agg[['season', 'rank', 'team', 'matches', 'wins', 'losses', 'no_results', 'super_over_played', 'points', 'win_pct']]

    return agg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    os.makedirs(output_path, exist_ok=True)

    input_file = os.path.join(input_path, 'new_data.csv')
    df = pd.read_csv(input_file)

    standings = generate_points_table(df)

    out_file = os.path.join(output_path, 'season_standings.csv')
    standings.to_csv(out_file, index=False)


if __name__ == '__main__':
    main()
