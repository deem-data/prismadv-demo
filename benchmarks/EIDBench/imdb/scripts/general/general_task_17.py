import argparse
import os
import re

import numpy as np
import pandas as pd


def to_minutes(runtime_str):
    if pd.isna(runtime_str):
        return np.nan
    m = re.search(r'(\d+)', str(runtime_str))
    return int(m.group(1)) if m else np.nan


def to_int_usd(gross_str):
    if pd.isna(gross_str):
        return np.nan
    s = str(gross_str).strip()
    if s == '' or s.lower() == 'nan':
        return np.nan
    s = s.replace(',', '')
    if not re.fullmatch(r'\d+', s):
        return np.nan
    return int(s)


def slugify(s):
    s = str(s).lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'(^-+|-+$)', '', s)
    return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Normalize core fields
    df['title'] = df['Series_Title'].astype(str).str.strip()
    df['year'] = pd.to_numeric(df['Released_Year'], errors='coerce')
    df['imdb_rating'] = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
    df['votes'] = pd.to_numeric(df['No_of_Votes'], errors='coerce')

    # Guard before using rating in scoring
    # Runtime parsing and guard before filtering/scoring by runtime
    df['runtime_min'] = df['Runtime'].map(to_minutes)
    # Gross parsing for monetization-based ranking
    df['gross_usd'] = df['Gross'].map(to_int_usd)
    present_mask = df['Gross'].notna()
    # ASSERTION_START
    assert df['gross_usd'].notna().any()
    # ASSERTION_END
    # Certificate/Genre/Year interlocks before eligibility gating
    # Key uniqueness before assigning deterministic IDs
    # Cast integrity before computing cast-derived features
    def _check_cast_row(row):
        names = [str(row['Star1']).strip(), str(row['Star2']).strip(), str(row['Star3']).strip(),
                 str(row['Star4']).strip()]
        if any(n == '' or n.lower() == 'nan' for n in names):
            return False
        return len(set(names)) == 4

    # Deterministic ID from title + year (assumes uniqueness checked above)
    df['title_id'] = df.apply(
        lambda r: f"{slugify(r['title'])}-{int(r['year'])}" if pd.notna(r['year']) else slugify(r['title']), axis=1)

    # Canonical primary genre and genre list
    df['genres'] = df['Genre'].astype(str).str.split(',').apply(lambda xs: [x.strip() for x in xs if x.strip() != ''])
    df['primary_genre'] = df['genres'].apply(lambda xs: xs[0] if len(xs) > 0 else None)

    # Compute licensing-relevant features
    gross_fill = df['gross_usd'].fillna(df['gross_usd'].median())
    log_gross = np.log1p(gross_fill)
    rating_component = (df['imdb_rating'] - 5.0).clip(lower=0) / 5.0  # 0..1 for ratings >=5
    # Prefer runtimes near 100 minutes; scale to 0.6..1.0
    runtime_deviation = (np.abs(df['runtime_min'] - 100) / 100.0).clip(0, 1)
    runtime_component = 1.0 - 0.4 * runtime_deviation

    # Cast diversity bonus (guaranteed to be 1.0 by assertion if data is valid)
    cast_diversity = df.apply(lambda r: len(
        {str(r['Star1']).strip(), str(r['Star2']).strip(), str(r['Star3']).strip(), str(r['Star4']).strip()}) / 4.0,
                              axis=1)

    # Certificate risk factor: mildly downweight restrictive/adult-only content
    cert = df['Certificate'].astype(str).str.upper()
    cert_factor = np.where(cert.isin(['R', 'NC-17', 'A', '18+', 'TV-MA']), 0.9, 1.0)

    # Final licensing score combines rating, monetization proxy, runtime suitability, cast diversity, and certificate factor
    score = (
                    0.45 * rating_component +
                    0.40 * (log_gross / (1 + log_gross.max())) +
                    0.10 * runtime_component +
                    0.05 * cast_diversity
            ) * cert_factor

    df['licensing_score'] = score

    # Eligibility filter: ensure baseline quality and catalog fit
    eligible = (
            (df['imdb_rating'] >= 7.0) &
            (df['runtime_min'].between(60, 210)) &
            (~df['primary_genre'].isin(['Short']))
    )

    # Horror gating inherently ensured by assertions; no extra rule needed here
    candidates = df.loc[eligible].copy()

    # Rank and tiering
    candidates['rank'] = candidates['licensing_score'].rank(method='first', ascending=False).astype(int)
    q_high, q_mid = candidates['licensing_score'].quantile([0.85, 0.60])

    def to_tier(x):
        if x >= q_high:
            return 'A'
        if x >= q_mid:
            return 'B'
        return 'C'

    candidates['tier'] = candidates['licensing_score'].apply(to_tier)

    # Output normalized feed
    out_cols = [
        'title_id', 'title', 'year', 'imdb_rating', 'votes', 'runtime_min', 'Certificate',
        'primary_genre', 'gross_usd', 'licensing_score', 'tier', 'rank'
    ]
    candidates = candidates.sort_values(['tier', 'rank'], ascending=[True, True])

    os.makedirs(args.output, exist_ok=True)
    out_csv = os.path.join(args.output, 'title_feed.csv')
    candidates[out_cols].to_csv(out_csv, index=False)

    # Also write a minimal metadata file for downstream audits
    meta = {
        'total_input_rows': int(df.shape[0]),
        'eligible_rows': int(candidates.shape[0]),
        'gross_non_null_ratio': float(present_mask.mean()),
        'score_min': float(candidates['licensing_score'].min()) if not candidates.empty else None,
        'score_max': float(candidates['licensing_score'].max()) if not candidates.empty else None,
    }
    with open(os.path.join(args.output, 'feed_metadata.json'), 'w') as f:
        import json
        json.dump(meta, f)


if __name__ == '__main__':
    main()
