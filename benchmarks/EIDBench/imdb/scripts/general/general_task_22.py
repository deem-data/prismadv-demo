import argparse
import json
import os

import numpy as np
import pandas as pd


def minmax_norm(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors='coerce')
    s = s.replace([np.inf, -np.inf], np.nan)
    if s.notna().sum() == 0:
        return pd.Series(0.0, index=s.index)
    s = s.fillna(s.dropna().min())
    min_v = s.min()
    max_v = s.max()
    if max_v == min_v:
        return pd.Series(1.0, index=s.index)
    return (s - min_v) / (max_v - min_v)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Basic type coercions used downstream
    df['IMDB_Rating'] = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
    df['Meta_score'] = pd.to_numeric(df['Meta_score'], errors='coerce')
    df['No_of_Votes'] = pd.to_numeric(df['No_of_Votes'], errors='coerce')
    df['Released_Year'] = pd.to_numeric(df['Released_Year'], errors='coerce')
    df['Runtime'] = df['Runtime'].astype(str)
    df['Certificate'] = df['Certificate'].astype(object)
    df['Genre'] = df['Genre'].astype(str)

    # Guard assumptions around IMDB_Rating before deriving rating buckets and quality blend
    # ASSERTION_START
    assert df['IMDB_Rating'].notna().all()
    assert df['IMDB_Rating'].between(0.0, 10.0).all()
    # ASSERTION_END
    # Buckets by 0.1 rating granularity (relies on quantization)
    df['rating_tenth'] = (df['IMDB_Rating'] * 10).astype(int)

    # Guard assumptions for No_of_Votes before Bayesian averaging and log-scaling
    # ASSERTION_START
    assert df['No_of_Votes'].notna().all()
    assert (df['No_of_Votes'] >= 0).all()
    # ASSERTION_END
    # Weighted (Bayesian) rating using vote counts
    C = df['IMDB_Rating'].mean()
    M = float(df['No_of_Votes'].quantile(0.60))
    v = df['No_of_Votes']
    R = df['IMDB_Rating']
    df['bayes_rating'] = (v / (v + M)) * R + (M / (v + M)) * C

    # ASSERTION_START
    # Guard assumptions around Meta_score and relationship to IMDB_Rating before blending quality
    meta_nonnull = df['Meta_score'].notna()
    if meta_nonnull.any():
        assert ((df.loc[meta_nonnull, 'Meta_score'] >= 0) & (df.loc[meta_nonnull, 'Meta_score'] <= 100)).all()
    # ASSERTION_END
    # Quality blend of IMDB and Meta when available
    meta10 = df['Meta_score'] / 10.0
    meta10_filled = meta10.where(meta10.notna(), df['IMDB_Rating'])
    df['quality_component'] = 0.6 * df['bayes_rating'] + 0.4 * meta10_filled

    # ASSERTION_START
    # Guard assumptions around Runtime before computing comfort/penalty factor
    extracted = df['Runtime'].str.extract(r'([0-9]{2,3})', expand=False)
    assert extracted.notna().all()
    # ASSERTION_END
    df['Runtime_minutes'] = df['Runtime'].str.extract(r'([0-9]{2,3})', expand=False).astype(int)
    deviation = (df['Runtime_minutes'] - 120).abs()
    runtime_factor = 1.0 - (deviation / 120.0) * 0.20
    df['runtime_factor'] = runtime_factor.clip(lower=0.80, upper=1.05)

    # Popularity component
    df['pop_component'] = np.log1p(df['No_of_Votes'])

    # Final quality-adjusted popularity score powering ranking
    df['qa_pop_score'] = 0.65 * minmax_norm(df['quality_component']) + 0.35 * minmax_norm(df['pop_component'])
    df['qa_pop_score'] = df['qa_pop_score'] * df['runtime_factor']

    # ASSERTION_START
    # Guard assumptions on Certificate before parental gating
    cert = df['Certificate']
    nonnull_cert = cert.notna()
    if nonnull_cert.any():
        # Define expected certificate values to ensure they can be mapped correctly.
        # This prevents silent fallbacks for unknown or malformed certificates.
        KNOWN_CERTS = {
            'U', 'G', 'PG', 'TV-PG', 'UA', 'PG-13', 'TV-14', 'U/A', 'GP',
            'R', 'TV-MA', 'NC-17', 'A', 'Not Rated', 'Unrated', 'Approved', 'Passed'
        }
        present_certs = set(cert.dropna().unique())
        assert present_certs.issubset(KNOWN_CERTS)
    # ASSERTION_END
    # Guard temporal constraints tied to Certificate before using both for policy checks
    # Guard assumptions on Genre structure and values before using it for kids-safety
    # Precompute genre flags
    df['genre_tokens'] = df['Genre'].str.split(', ')
    df['has_animation'] = df['genre_tokens'].apply(lambda xs: 'Animation' in xs)
    df['has_family'] = df['genre_tokens'].apply(lambda xs: 'Family' in xs)

    # Cross-field policy constraints used for parental filters
    # Kids-safe gating and maturity mapping
    maturity_map = {
        'U': 0, 'G': 0, 'PG': 1, 'TV-PG': 1, 'UA': 2, 'PG-13': 2, 'TV-14': 2,
        'R': 3, 'TV-MA': 3, 'NC-17': 3, 'A': 3, 'Not Rated': 2, 'Unrated': 2, 'Approved': 1, 'Passed': 1,
        'U/A': 2, 'GP': 2
    }
    df['maturity_level'] = df['Certificate'].map(maturity_map)
    df['is_kids_safe'] = (
                                 df['maturity_level'].fillna(3) <= 1
                         ) & (~df['genre_tokens'].apply(lambda xs: any(g in xs for g in ['Horror', 'Thriller'])))

    # Guard gross format before creating box-office carousel
    # Parse Gross for downstream usage
    df['Gross_int'] = pd.NA
    if df['Gross'].notna().any():
        gi = df['Gross'].dropna().astype(str).str.replace(',', '', regex=False)
        with np.errstate(all='ignore'):
            gi_num = pd.to_numeric(gi, errors='coerce')
        df.loc[gi_num.index, 'Gross_int'] = gi_num.astype('Int64')

    # Build outputs for search ranking and editorial carousels
    df['rank'] = df['qa_pop_score'].rank(ascending=False, method='first').astype(int)

    ranked_cols = [
        'Series_Title', 'qa_pop_score', 'rank', 'Certificate', 'Released_Year', 'Genre',
        'is_kids_safe', 'Poster_Link', 'IMDB_Rating', 'Meta_score', 'No_of_Votes', 'Gross_int'
    ]
    ranked_out = df.sort_values('qa_pop_score', ascending=False)[ranked_cols]
    ranked_out.to_csv(os.path.join(args.output, 'ranked_titles.csv'), index=False)

    # Carousels
    def to_items(sub: pd.DataFrame, n: int = 30):
        cols = ['Series_Title', 'qa_pop_score', 'Certificate', 'Released_Year', 'Genre', 'Poster_Link']
        items = sub.sort_values('qa_pop_score', ascending=False).head(n)[cols]
        return [
            {
                'title': r.Series_Title,
                'score': float(r.qa_pop_score),
                'certificate': None if pd.isna(r.Certificate) else str(r.Certificate),
                'year': None if pd.isna(r.Released_Year) else int(r.Released_Year),
                'genre': r.Genre,
                'poster': r.Poster_Link
            }
            for r in items.itertuples(index=False)
        ]

    top_overall = to_items(df, n=50)
    family_picks = to_items(df[df['is_kids_safe']], n=40)

    if df['Gross_int'].notna().any():
        box_office = df[df['Gross_int'].notna()].copy()
        box_office['gross_norm'] = minmax_norm(pd.to_numeric(box_office['Gross_int'], errors='coerce'))
        box_office['box_office_score'] = 0.5 * box_office['gross_norm'] + 0.5 * minmax_norm(box_office['qa_pop_score'])
        box_office_items = box_office.sort_values(['box_office_score', 'qa_pop_score'], ascending=False)
        box_office_items = box_office_items.head(40)
        box_office_out = [
            {
                'title': r.Series_Title,
                'gross': int(r.Gross_int) if not pd.isna(r.Gross_int) else None,
                'score': float(r.qa_pop_score),
                'certificate': None if pd.isna(r.Certificate) else str(r.Certificate),
                'year': None if pd.isna(r.Released_Year) else int(r.Released_Year),
                'poster': r.Poster_Link
            }
            for r in box_office_items.itertuples(index=False)
        ]
    else:
        box_office_out = []

    carousels = {
        'top_overall': top_overall,
        'family': family_picks,
        'box_office': box_office_out
    }

    with open(os.path.join(args.output, 'carousels.json'), 'w', encoding='utf-8') as f:
        json.dump(carousels, f, ensure_ascii=False, indent=2)

    # Search index for ranking integration
    search_index = df[['Series_Title', 'qa_pop_score', 'is_kids_safe', 'Certificate', 'Released_Year', 'Genre']].copy()
    search_index.rename(
        columns={'Series_Title': 'title', 'qa_pop_score': 'rank_score', 'Certificate': 'cert', 'Released_Year': 'year',
                 'Genre': 'genres'}, inplace=True)
    search_index.sort_values('rank_score', ascending=False).to_csv(os.path.join(args.output, 'search_index.csv'),
                                                                   index=False)


if __name__ == '__main__':
    main()
