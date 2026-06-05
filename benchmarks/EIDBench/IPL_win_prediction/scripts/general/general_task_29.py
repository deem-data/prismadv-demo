import argparse
import os

import numpy as np
import pandas as pd


def compute_standings(df: pd.DataFrame) -> pd.DataFrame:
    played_mask = df["result"] != "no result"
    df_played = df.loc[played_mask, ["season_int", "team1", "team2", "winner", "result"]].copy()
    df_played["loser"] = np.where(df_played["winner"] == df_played["team1"], df_played["team2"],
                                  df_played["team1"])  # relies on winner being one of the teams

    wins = (
        df_played.groupby(["season_int", "winner"]).size().rename("wins")
    )
    losses = (
        df_played.groupby(["season_int", "loser"]).size().rename("losses")
    )

    # Matches played counts both teams for all rows
    side_a = df[["season_int", "team1"]].rename(columns={"team1": "team"})
    side_b = df[["season_int", "team2"]].rename(columns={"team2": "team"})
    matches = (
        pd.concat([side_a, side_b], ignore_index=True)
        .groupby(["season_int", "team"]).size().rename("matches")
    )

    # No result counts both teams
    nr = df.loc[df["result"] == "no result", ["season_int", "team1", "team2"]]
    if not nr.empty:
        nr_flat = pd.concat([
            nr[["season_int", "team1"]].rename(columns={"team1": "team"}),
            nr[["season_int", "team2"]].rename(columns={"team2": "team"}),
        ], ignore_index=True)
        no_result = nr_flat.groupby(["season_int", "team"]).size().rename("no_result")
    else:
        no_result = pd.Series(dtype="int64", name="no_result")

    # Ties (occur before super over) count participation for both teams
    ties = df.loc[df["result"] == "tie", ["season_int", "team1", "team2"]]
    if not ties.empty:
        ties_flat = pd.concat([
            ties[["season_int", "team1"]].rename(columns={"team1": "team"}),
            ties[["season_int", "team2"]].rename(columns={"team2": "team"}),
        ], ignore_index=True)
        ties_count = ties_flat.groupby(["season_int", "team"]).size().rename("ties")
    else:
        ties_count = pd.Series(dtype="int64", name="ties")

    # Assemble standings
    standings = (
        pd.concat([matches, wins, losses, no_result, ties_count], axis=1)
        .fillna(0)
        .reset_index()
        .rename(columns={"winner": "team"})
    )
    # wins and losses currently keyed by team value under their respective Series index names
    # After concat, columns names remain aligned

    # Ensure integer types for counts
    for col in ["matches", "wins", "losses", "no_result", "ties"]:
        if col in standings.columns:
            standings[col] = standings[col].astype(int)
        else:
            standings[col] = 0

    standings["points"] = standings["wins"] * 2 + standings["no_result"] * 1

    # Sort within season
    standings = standings.sort_values(["season_int", "points", "wins"], ascending=[True, False, False]).reset_index(
        drop=True)
    return standings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_csv)

    # Normalize dtypes used downstream
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df["season_int"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    # Guard winner semantics before computing loser and points
    mask_played = df["result"] != "no result"
    # ASSERTION_START
    assert df["team1"].notna().all()
    assert df["team2"].notna().all()
    assert df.loc[mask_played, "winner"].notna().all()
    assert ((df.loc[mask_played, "winner"] == df.loc[mask_played, "team1"]) | (
                df.loc[mask_played, "winner"] == df.loc[mask_played, "team2"])).all()
    # ASSERTION_END
    # Result margin semantics used for KPI calculations
    mask_runs = df["result"] == "runs"
    mask_wkts = df["result"] == "wickets"
    mask_tie_or_no = df["result"].isin(["tie", "no result"])  # used to ensure null margins
    # ASSERTION_START
    s_runs = df.loc[mask_runs, "result_margin"]
    s_wkts = df.loc[mask_wkts, "result_margin"]
    assert s_runs.notna().all()
    assert np.isfinite(s_runs).all()
    assert (s_runs > 0).all()
    assert np.isclose(s_runs, np.floor(s_runs)).all()
    assert s_wkts.notna().all()
    assert np.isfinite(s_wkts).all()
    assert ((s_wkts >= 1) & (s_wkts <= 10)).all()
    assert np.isclose(s_wkts, np.floor(s_wkts)).all()
    # ASSERTION_END
    # Safe integer margins after checks
    df["margin_int"] = df["result_margin"].where(mask_runs | mask_wkts).astype("Int64")

    # ASSERTION_START
    # Super over relationship used for broadcast KPI slice
    # Toss winner used to compute correlation with match winner
    mask_played = df["result"] != "no result"
    assert (
            (df.loc[mask_played, "toss_winner"] == df.loc[mask_played, "team1"]) |
            (df.loc[mask_played, "toss_winner"] == df.loc[mask_played, "team2"])
    ).all()
    # ASSERTION_END
    # Standings per season
    standings = compute_standings(df)
    standings.to_csv(os.path.join(args.output, 'standings.csv'), index=False)

    # Player of the Match leaderboards (top 10 per season)
    pom = df[["season_int", "player_of_match"]].dropna()
    pom_counts = pom.groupby(["season_int", "player_of_match"]).size().rename("awards").reset_index()
    pom_counts = pom_counts.sort_values(["season_int", "awards"], ascending=[True, False])
    pom_counts["rank"] = pom_counts.groupby("season_int")["awards"].rank(method="first", ascending=False).astype(int)
    top_pom = pom_counts.loc[pom_counts["rank"] <= 10]
    top_pom.to_csv(os.path.join(args.output, 'leaderboard_player_of_match.csv'), index=False)

    # Broadcast KPIs per season
    played = df[df["result"] != "no result"].copy()
    played["toss_win_and_match_win"] = (played["toss_winner"] == played["winner"]).astype(int)
    toss_win_rate = (
        played.groupby("season_int")["toss_win_and_match_win"].mean().rename("toss_win_match_win_rate")
    )

    avg_margin_runs = (
        df.loc[mask_runs].groupby("season_int")["margin_int"].mean().rename("avg_margin_runs")
    )
    avg_margin_wkts = (
        df.loc[mask_wkts].groupby("season_int")["margin_int"].mean().rename("avg_margin_wickets")
    )
    super_over_counts = df.loc[df["super_over"] == "Y"].groupby("season_int").size().rename("super_over_matches")
    tie_counts = df.loc[df["result"] == "tie"].groupby("season_int").size().rename("ties")

    kpis = pd.concat([toss_win_rate, avg_margin_runs, avg_margin_wkts, super_over_counts, tie_counts], axis=1).fillna(0)
    # Ensure numeric types
    for col in ["toss_win_match_win_rate", "avg_margin_runs", "avg_margin_wickets"]:
        if col in kpis.columns:
            kpis[col] = kpis[col].astype(float)
    for col in ["super_over_matches", "ties"]:
        if col in kpis.columns:
            kpis[col] = kpis[col].astype(int)

    kpis.reset_index().to_csv(os.path.join(args.output, 'broadcast_kpis_by_season.csv'), index=False)

    # Super over matches detail for editorial
    super_over_detail = df.loc[df["super_over"] == "Y", [
        "id", "season_int", "date", "team1", "team2", "winner", "player_of_match", "city", "venue"
    ]].sort_values(["season_int", "date"])
    super_over_detail.to_csv(os.path.join(args.output, 'super_over_matches.csv'), index=False)


if __name__ == '__main__':
    main()
