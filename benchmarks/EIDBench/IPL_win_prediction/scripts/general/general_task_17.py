import argparse
import os

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    for col in ['result', 'toss_decision', 'super_over', 'method']:
        if col in df.columns:
            df[col] = df[col].astype(str)

    toss_decision_lower = df['toss_decision'].str.strip().str.lower()
    field_ratio = (toss_decision_lower == 'field').mean()
    season_context_prefix = "Chasing trend continued as"

    standings = {}

    def ensure_team(season, team):
        key = (season, team)
        if key not in standings:
            standings[key] = {
                'season': season,
                'team': team,
                'matches_played': 0,
                'wins': 0,
                'losses': 0,
                'ties': 0,
                'no_results': 0,
                'points': 0
            }

    summaries = []

    if 'date' in df.columns:
        try:
            df['_date'] = pd.to_datetime(df['date'], errors='coerce')
        except Exception:
            df['_date'] = pd.NaT
        df = df.sort_values(by=['_date', 'id'], ascending=[True, True]).drop(columns=['_date'], errors='ignore')

    for _, row in df.iterrows():
        season = str(row['season'])
        team1 = row['team1']
        team2 = row['team2']
        ensure_team(season, team1)
        ensure_team(season, team2)
        # ASSERTION_START
        assert team1 != team2
        # ASSERTION_END
        result = str(row['result']).strip().lower()
        winner = row['winner'] if pd.notna(row['winner']) else None
        method = row['method'] if pd.notna(row['method']) else None
        method = str(method) if method is not None else None
        target_overs = row['target_overs'] if 'target_overs' in row and pd.notna(row['target_overs']) else None
        target_runs = row['target_runs'] if 'target_runs' in row and pd.notna(row['target_runs']) else None

        dl_snippet = ""
        if method == 'D/L':
            # ASSERTION_START
            def is_floatable(val):
                if val is None:
                    return False
                try:
                    float(val)
                    return True
                except (ValueError, TypeError):
                    return False

            assert is_floatable(target_overs)
            # ASSERTION_END
            if target_runs is not None:
                dl_snippet = f" Target set to {int(float(target_runs))} in {float(target_overs):g} overs (D/L)."
            else:
                dl_snippet = f" Innings reduced to {float(target_overs):g} overs (D/L)."

        summary = None

        if result in ('runs', 'wickets'):
            # ASSERTION_START
            assert winner in {team1, team2}
            # ASSERTION_END
            margin = row['result_margin']
            if result == 'runs':
                # ASSERTION_START
                m = margin
                cond = (not pd.isna(m)) and (float(m) == int(float(m))) and (int(float(m)) > 0)
                assert cond
                # ASSERTION_END
                m_int = int(float(margin))
                loser = team2 if winner == team1 else team1
                summary = f"{season_context_prefix} {winner} defended and beat {loser} by {m_int} runs." + dl_snippet

                standings[(season, winner)]['wins'] += 1
                standings[(season, winner)]['matches_played'] += 1
                standings[(season, winner)]['points'] += 2
                standings[(season, loser)]['losses'] += 1
                standings[(season, loser)]['matches_played'] += 1

            else:
                # ASSERTION_START
                m = margin
                cond = (not pd.isna(m)) and (float(m) == int(float(m))) and (1 <= int(float(m)) <= 10)
                assert cond
                # ASSERTION_END
                m_int = int(float(margin))
                loser = team2 if winner == team1 else team1
                summary = f"{season_context_prefix} {winner} chased successfully, winning against {loser} by {m_int} wickets." + dl_snippet

                standings[(season, winner)]['wins'] += 1
                standings[(season, winner)]['matches_played'] += 1
                standings[(season, winner)]['points'] += 2
                standings[(season, loser)]['losses'] += 1
                standings[(season, loser)]['matches_played'] += 1

        elif result == 'tie':
            # ASSERTION_START
            so = str(row['super_over']).strip().upper()
            assert so == 'Y'
            # ASSERTION_END
            if (winner in {team1, team2}):
                loser = team2 if winner == team1 else team1
                summary = f"{season_context_prefix} scores were level after regular play; {winner} prevailed in the Super Over against {loser}." + dl_snippet
                standings[(season, winner)]['wins'] += 1
                standings[(season, winner)]['matches_played'] += 1
                standings[(season, winner)]['points'] += 2
                standings[(season, loser)]['losses'] += 1
                standings[(season, loser)]['matches_played'] += 1
            else:
                summary = f"{season_context_prefix} scores were level and the contest remained tied after the Super Over." + dl_snippet
                standings[(season, team1)]['ties'] += 1
                standings[(season, team2)]['ties'] += 1
                standings[(season, team1)]['matches_played'] += 1
                standings[(season, team2)]['matches_played'] += 1
                standings[(season, team1)]['points'] += 1
                standings[(season, team2)]['points'] += 1

        elif result == 'no result':
            summary = f"{season_context_prefix} play was inconclusive; no result was recorded." + dl_snippet
            standings[(season, team1)]['no_results'] += 1
            standings[(season, team2)]['no_results'] += 1
            standings[(season, team1)]['matches_played'] += 1
            standings[(season, team2)]['matches_played'] += 1
            standings[(season, team1)]['points'] += 1
            standings[(season, team2)]['points'] += 1
        else:
            summary = f"{season_context_prefix} outcome category '{result}' unrecognized."

        summaries.append({
            'id': int(row['id']),
            'season': season,
            'date': row['date'],
            'city': row['city'] if pd.notna(row['city']) else '',
            'venue': row['venue'],
            'team1': team1,
            'team2': team2,
            'toss_winner': row['toss_winner'],
            'toss_decision': row['toss_decision'],
            'winner': winner if winner is not None else '',
            'result': row['result'],
            'result_margin': row['result_margin'],
            'method': method if method is not None else '',
            'super_over': row['super_over'],
            'summary': summary.strip()
        })

    standings_df = pd.DataFrame(list(standings.values()))
    standings_df = standings_df.sort_values(by=['season', 'points', 'wins'], ascending=[True, False, False])

    os.makedirs(args.output, exist_ok=True)
    summaries_df = pd.DataFrame(summaries)
    summaries_df.to_csv(os.path.join(args.output, 'match_summaries.csv'), index=False)
    standings_df.to_csv(os.path.join(args.output, 'standings.csv'), index=False)


if __name__ == '__main__':
    main()
