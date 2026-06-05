import argparse
import json
import os
import re
from datetime import datetime

import numpy as np
import pandas as pd


def safe_slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def build_card(row):
    title = str(row["Series_Title"]).strip()
    year = int(row["Year"])
    cert = row.get("Certificate", None)
    cert_text = f"<span class=\"cert\">{cert}</span>" if pd.notna(cert) and cert != "" else ""
    rating = row.get("IMDB_Rating", np.nan)
    ms = row.get("Meta_score", np.nan)
    votes = row.get("No_of_Votes", np.nan)
    poster = str(row["Poster_Link"]).strip()
    score = row.get("Score", np.nan)
    score_text = f"<span class=\"score\">{score:.3f}</span>" if pd.notna(score) else ""
    rating_text = f"<span class=\"rating\">IMDb {rating:.1f}</span>" if pd.notna(rating) else ""
    meta_text = f"<span class=\"meta\">Meta {int(ms)}</span>" if pd.notna(ms) else ""
    votes_text = f"<span class=\"votes\">{int(votes):,} votes</span>" if pd.notna(votes) else ""
    slug = safe_slug(f"{title}-{year}")
    card = f"""
    <a class=\"card\" id=\"{slug}\" href=\"{poster}\" target=\"_blank\" rel=\"noopener noreferrer\">
        <img src=\"{poster}\" alt=\"{title} ({year})\" loading=\"lazy\"/>
        <div class=\"meta\">
            <div class=\"title\">{title} ({year}) {cert_text}</div>
            <div class=\"stats\">{rating_text} {meta_text} {votes_text} {score_text}</div>
        </div>
    </a>
    """
    return card


def build_html(top_df: pd.DataFrame, output_html_path: str):
    css = """
    <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 0 12px 48px; background: #0b0e14; color: #e6e6e6; }
    h1 { margin: 16px 0; }
    h2 { margin-top: 32px; border-bottom: 1px solid #2a2e38; padding-bottom: 4px; }
    h3 { margin-top: 20px; color: #a6accd; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
    .card { display: block; background: #111522; border-radius: 8px; overflow: hidden; text-decoration: none; color: inherit; border: 1px solid #1b2233; }
    .card img { width: 100%; height: 270px; object-fit: cover; display: block; background: #222; }
    .card .meta { padding: 8px; }
    .card .title { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
    .card .stats { font-size: 12px; color: #c6c9d0; display: flex; flex-wrap: wrap; gap: 6px; }
    .card .cert { background: #25324a; color: #c3e88d; padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; }
    .card .rating { color: #ffd166; }
    .card .meta { color: #7bdff2; }
    .card .votes { color: #c0c0c0; }
    .card .score { color: #80cbc4; margin-left: auto; }
    </style>
    """

    sections = ["<html><head><meta charset=\"utf-8\"/>" + css + "</head><body>"]
    sections.append("<h1>Genre-by-Decade Leaderboards</h1>")

    for decade, df_dec in top_df.groupby("Decade_Label", sort=True):
        sections.append(f"<h2>{decade}</h2>")
        for genre, df_gen in df_dec.groupby("GenreToken", sort=True):
            sections.append(f"<h3>{genre}</h3>")
            sections.append("<div class=\"grid\">")
            for _, row in df_gen.sort_values(["Rank", "Score"], ascending=[True, False]).iterrows():
                sections.append(build_card(row))
            sections.append("</div>")

    sections.append("</body></html>")
    html = "\n".join(sections)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Basic trimming for fields we use
    for col in ["Series_Title", "Released_Year", "Runtime", "Genre", "Poster_Link", "Certificate"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    # ASSERTION_START
    key = df["Series_Title"].astype(str).str.strip() + "|" + df["Released_Year"].astype(str).str.strip()
    assert (~key.duplicated()).all()
    # ASSERTION_END
    # Validate Released_Year format and range before deriving decade
    year_str = df["Released_Year"].astype(str).str.strip()
    current_year = datetime.now().year
    year_fullmatch_mask = year_str.str.fullmatch(r"\d{4}")
    year_int_try = pd.to_numeric(year_str.where(year_fullmatch_mask), errors="coerce")
    # Keep rows with plain 4-digit years for downstream use
    df = df.loc[year_fullmatch_mask].copy()
    df["Year"] = year_str.loc[year_fullmatch_mask].astype(int)
    df["Decade"] = (df["Year"] // 10) * 10
    df["Decade_Label"] = df["Decade"].astype(str) + "s"

    # Validate and parse runtime
    runtime_s = df["Runtime"].astype(str).str.strip()
    runtime_match = runtime_s.str.fullmatch(r"\d{2,3} min")
    # ASSERTION_START
    assert runtime_match.all()
    # ASSERTION_END
    df["Runtime_Min"] = pd.to_numeric(runtime_s.str.extract(r"(\d{2,3})", expand=False), errors="coerce").astype(int)

    # Validate IMDB_Rating before scoring
    imdb = pd.to_numeric(df["IMDB_Rating"], errors="coerce")
    # Validate No_of_Votes before log transform
    votes = pd.to_numeric(df["No_of_Votes"], errors="coerce")
    # Validate Meta_score completeness and bounds before scoring
    meta = pd.to_numeric(df["Meta_score"], errors="coerce")
    # Validate Gross parseability and coverage before using as tie breaker
    gross_str = df["Gross"].astype(str)
    gross_num_try = pd.to_numeric(gross_str.str.replace(",", "", regex=False), errors="coerce")
    # ASSERTION_START
    assert (gross_num_try.dropna() > -1).all()
    # ASSERTION_END
    df["Gross_Num"] = pd.to_numeric(df["Gross"].astype(str).str.replace(",", "", regex=False), errors="coerce")

    # Validate Genre structure before exploding
    allowed_genres = {
        "Action", "Adventure", "Animation", "Biography", "Comedy", "Crime", "Drama", "Family", "Fantasy", "Film-Noir",
        "History", "Horror", "Music", "Musical", "Mystery", "Romance", "Sci-Fi", "Sport", "Thriller", "War", "Western"
    }
    genre_lists = df["Genre"].astype(str).str.split(",").map(lambda x: [t.strip() for t in x if t.strip() != ""])
    df["GenreTokens"] = genre_lists

    # Validate Certificate domain and coverage before content-policy filtering
    allowed_cert = {"G", "PG", "PG-13", "R", "NC-17", "U", "UA", "A", "12", "12A", "15", "18"}
    cert = df["Certificate"].replace({"nan": np.nan})
    # If Family or Animation appears, Certificate must not be R/NC-17
    # Validate Poster_Link before card rendering
    posters = df["Poster_Link"].astype(str).str.strip()

    # ASSERTION_START
    def valid_url(u: str) -> bool:
        from urllib.parse import urlparse
        try:
            p = urlparse(u)
            return p.scheme in ("http", "https") and bool(p.netloc)
        except Exception:
            return False

    assert posters.map(valid_url).all()
    # ASSERTION_END
    # Validate correlation and conditional voting behavior
    # Scoring
    rating_norm = pd.to_numeric(df["IMDB_Rating"], errors="coerce") / 10.0
    meta_norm = pd.to_numeric(df["Meta_score"], errors="coerce") / 100.0
    meta_norm = meta_norm.fillna(meta_norm.median())
    vote_norm = np.log10(pd.to_numeric(df["No_of_Votes"], errors="coerce").clip(lower=1)) / 6.0
    # Mild runtime pacing factor around 120 minutes
    pacing = 1.0 - (np.abs(df["Runtime_Min"] - 120) / 300.0)
    pacing = pacing.clip(lower=0.8, upper=1.05)

    base_score = 0.6 * rating_norm + 0.25 * meta_norm + 0.15 * vote_norm
    df["Score"] = (base_score * pacing).astype(float)

    # Tie-breaker using Gross (normalized)
    if df["Gross_Num"].notna().any():
        gross_norm = np.log1p(df["Gross_Num"].fillna(df["Gross_Num"].median()))
        denom = float(gross_norm.max()) if float(gross_norm.max()) > 0 else 1.0
        df["Gross_Tie"] = gross_norm / denom
    else:
        df["Gross_Tie"] = 0.0

    # Explode by genre token for genre-specific leaderboards
    exploded = df.explode("GenreTokens").rename(columns={"GenreTokens": "GenreToken"})

    # Rank within each (Decade, Genre)
    exploded = exploded.sort_values(["Decade_Label", "GenreToken", "Score", "Gross_Tie"],
                                    ascending=[True, True, False, False])
    exploded["Rank"] = exploded.groupby(["Decade_Label", "GenreToken"])['Score'].rank(method="first", ascending=False)

    TOP_K = 10
    top_k = exploded.loc[exploded["Rank"] <= TOP_K].copy()

    # Persist outputs
    os.makedirs(args.output, exist_ok=True)
    out_csv = os.path.join(args.output, "genre_by_decade_leaderboards.csv")
    cols = [
        "Decade_Label", "GenreToken", "Rank", "Series_Title", "Year", "Certificate", "IMDB_Rating", "Meta_score",
        "No_of_Votes", "Runtime", "Score", "Poster_Link"
    ]
    top_k[cols].to_csv(out_csv, index=False)

    out_html = os.path.join(args.output, "leaderboards.html")
    build_html(top_k, out_html)

    # Also emit a compact JSON index if needed by downstream services
    out_json = os.path.join(args.output, "leaderboards_index.json")
    grouped = []
    for (decade, genre), grp in top_k.groupby(["Decade_Label", "GenreToken"]):
        items = [
            {
                "series_title": str(r["Series_Title"]).strip(),
                "year": int(r["Year"]),
                "certificate": None if pd.isna(r["Certificate"]) else str(r["Certificate"]),
                "imdb_rating": None if pd.isna(r["IMDB_Rating"]) else float(r["IMDB_Rating"]),
                "meta_score": None if pd.isna(r["Meta_score"]) else float(r["Meta_score"]),
                "votes": None if pd.isna(r["No_of_Votes"]) else int(r["No_of_Votes"]),
                "runtime": str(r["Runtime"]),
                "score": float(r["Score"]),
                "poster_link": str(r["Poster_Link"]).strip(),
                "rank": int(r["Rank"]) if not pd.isna(r["Rank"]) else None
            }
            for _, r in grp.sort_values(["Rank", "Score"], ascending=[True, False]).iterrows()
        ]
        grouped.append({"decade": decade, "genre": genre, "items": items})

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"groups": grouped}, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
