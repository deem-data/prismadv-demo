import argparse
import os
import re
from datetime import date

import numpy as np
import pandas as pd


def slugify(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80]


def to_cdn(url: str) -> str:
    if not isinstance(url, str):
        return url
    # Expecting Amazon media image URLs; convert size variant to a standard UX342 size
    try:
        new_url = re.sub(r"\._V1_.+?\.jpg", "._V1_UX342_.jpg", url)
        return new_url
    except Exception:
        return url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_file = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_file)

    # Basic type coercions needed by downstream logic
    df['IMDB_Rating'] = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
    df['No_of_Votes'] = pd.to_numeric(df['No_of_Votes'], errors='coerce').fillna(0).astype(int)
    df['Released_Year'] = pd.to_numeric(df['Released_Year'], errors='coerce').astype('Int64')
    df['Meta_score'] = pd.to_numeric(df['Meta_score'], errors='coerce')
    # ASSERTION_START
    valid_ratings = df['IMDB_Rating'].dropna()
    assert ((valid_ratings >= 0.0) & (valid_ratings <= 10.0)).all()
    # ASSERTION_END
    # ASSERTION_START
    assert ~df.duplicated(['Series_Title', 'Released_Year']).any()
    # ASSERTION_END
    current_year = date.today().year
    # ASSERTION_START
    assert df['Released_Year'].notna().all() and (
            (df['Released_Year'] >= 1900) & (df['Released_Year'] <= current_year)).all()
    # ASSERTION_END
    # ASSERTION_START
    assert df['Runtime'].astype(str).str.extract(r'(\d+)')[0].notna().all()
    # ASSERTION_END
    df['RuntimeMinutes'] = df['Runtime'].astype(str).str.extract(r'(\d+)')[0].astype(int)

    allowed_certificates = {
        'U', 'UA', 'U/A', 'A', 'G', 'PG', 'PG-13', 'R', 'NC-17', 'Not Rated', 'TV-14', 'TV-MA'
    }
    cert_canonical_map = {'U/A': 'UA'}
    cert_norm = df['Certificate'].replace(cert_canonical_map)
    cert_norm = cert_norm.where(cert_norm.isin({
        'U', 'UA', 'A', 'G', 'PG', 'PG-13', 'R', 'NC-17', 'Not Rated', 'TV-14', 'TV-MA'
    }), other=np.nan)
    df['CertificateNorm'] = cert_norm.fillna('Not Rated')
    df['Poster_CDN'] = df['Poster_Link'].apply(to_cdn)

    pairs = df[['IMDB_Rating', 'Meta_score']].dropna()
    corr = pairs['IMDB_Rating'].corr(pairs['Meta_score']) if len(pairs) > 1 else np.nan
    meta_weight = 0.3 if (pd.notna(corr) and corr > 0.4) else 0.1
    df['MetaNorm'] = df['Meta_score'] / 10.0
    df['MetaNormFilled'] = df['MetaNorm'].fillna(df['IMDB_Rating'])
    df['HybridRating'] = meta_weight * df['MetaNormFilled'] + (1.0 - meta_weight) * df['IMDB_Rating']

    m = df['No_of_Votes'].quantile(0.70)
    C = df['HybridRating'].mean()
    v = df['No_of_Votes']
    R = df['HybridRating']
    df['WeightedRank'] = (v / (v + m)) * R + (m / (v + m)) * C

    filtered = df[(df['IMDB_Rating'] >= 7.0)].copy()

    # Rank and pick top titles for the daily feed
    top_n = 200
    today = date.today().isoformat()

    filtered['catalog_id'] = filtered.apply(lambda r: f"{slugify(str(r['Series_Title']))}-{int(r['Released_Year'])}",
                                            axis=1)

    feed_cols = [
        'catalog_id', 'Series_Title', 'Released_Year', 'Genre', 'IMDB_Rating', 'Meta_score',
        'No_of_Votes', 'RuntimeMinutes', 'CertificateNorm', 'Poster_CDN', 'WeightedRank',
        'Overview', 'Director', 'Star1', 'Star2', 'Star3', 'Star4'
    ]

    available_cols = [c for c in feed_cols if c in filtered.columns]
    top_feed = (
        filtered.sort_values(['WeightedRank', 'No_of_Votes', 'IMDB_Rating'], ascending=[False, False, False])
        .head(top_n)[available_cols]
        .copy()
    )

    top_feed.insert(0, 'feed_date', today)

    output_file = os.path.join(args.output, f'top_movies_catalog_{today}.csv')
    top_feed.to_csv(output_file, index=False)


if __name__ == '__main__':
    main()
