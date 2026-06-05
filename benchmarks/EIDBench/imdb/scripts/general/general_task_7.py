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

    input_fp = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_fp)

    # Normalize keys
    df['Series_Title'] = df['Series_Title'].astype(str).str.strip()
    df['Released_Year'] = df['Released_Year'].astype(str).str.strip()
    df['title_year_key'] = df['Series_Title'] + '|' + df['Released_Year']
    # ASSERTION_START
    duplicate_key_mask = df['title_year_key'].duplicated(keep=False)
    assert (~duplicate_key_mask).all()
    # ASSERTION_END
    # Stable catalog ids (order-dependent, relies on unique title-year)
    df = df.sort_values(['Series_Title', 'Released_Year']).reset_index(drop=True)
    id_map = {k: i + 1 for i, k in enumerate(df['title_year_key'])}
    df['catalog_id'] = df['title_year_key'].map(id_map)

    # Poster checks before building asset ids
    poster_unique_ratio = df['Poster_Link'].nunique(dropna=True) / float(len(df))
    unique_posters = pd.Index(df['Poster_Link']).unique()
    poster_asset_id_map = {url: i + 1 for i, url in enumerate(unique_posters)}
    df['poster_asset_id'] = df['Poster_Link'].map(poster_asset_id_map)

    # Runtime parsing
    runtime_pattern = r'^\s*(\d+)\s*min\s*$'
    # ASSERTION_START
    assert df['Runtime'].astype(str).str.match(runtime_pattern).all()
    # ASSERTION_END
    df['Runtime_Minutes'] = df['Runtime'].astype(str).str.extract(runtime_pattern)[0].astype(int)
    # Ratings and votes
    df['IMDB_Rating'] = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
    # ASSERTION_START
    assert (df['IMDB_Rating'].isna() | ((df['IMDB_Rating'] >= 0.0) & (df['IMDB_Rating'] <= 10.0))).all()
    # ASSERTION_END
    df['No_of_Votes'] = pd.to_numeric(df['No_of_Votes'], errors='coerce').fillna(0).astype(int)

    # Bayesian quality score used for ranking
    R = df['IMDB_Rating']
    votes = df['No_of_Votes']
    m = float(np.quantile(votes, 0.60))
    C = float(R.mean())
    wr = (votes / (votes + m) * R) + (m / (votes + m) * C)

    df['Meta_score'] = pd.to_numeric(df['Meta_score'], errors='coerce')
    meta_scaled = (df['Meta_score'] / 10.0).fillna(C)
    df['quality_score'] = 0.8 * wr + 0.2 * meta_scaled

    frac_high = (df['IMDB_Rating'] >= 7.0).mean()
    # Curate and rank Top Picks
    base = df[df['IMDB_Rating'] >= 7.0].copy()
    base = base.drop_duplicates(subset=['title_year_key'], keep='first')
    base = base.sort_values(['quality_score', 'No_of_Votes'], ascending=[False, False])
    base['display_rank'] = np.arange(1, len(base) + 1)

    top_k = 100
    top_picks = base.head(top_k)

    top_cols = [
        'display_rank',
        'catalog_id',
        'Series_Title',
        'Released_Year',
        'IMDB_Rating',
        'No_of_Votes',
        'Runtime_Minutes',
        'Genre',
        'Certificate',
        'poster_asset_id',
        'Poster_Link',
        'quality_score'
    ]

    top_picks_out = os.path.join(args.output, 'top_picks.csv')
    top_picks[top_cols].to_csv(top_picks_out, index=False)

    manifest_out = os.path.join(args.output, 'assets_manifest.csv')
    df[['poster_asset_id', 'Poster_Link']].drop_duplicates().sort_values('poster_asset_id').to_csv(manifest_out,
                                                                                                   index=False)

    stats = {
        'total_input': int(len(df)),
        'unique_title_year': int(df['title_year_key'].nunique()),
        'unique_posters': int(df['Poster_Link'].nunique()),
        'poster_unique_ratio': float(poster_unique_ratio),
        'fraction_rating_ge_7': float(frac_high),
        'm_votes_threshold': float(m),
        'top_picks_count': int(len(top_picks))
    }
    stats_out = os.path.join(args.output, 'top_picks_stats.json')
    with open(stats_out, 'w') as f:
        json.dump(stats, f, indent=2)


if __name__ == '__main__':
    main()
