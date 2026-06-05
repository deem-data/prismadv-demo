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

    input_csv = os.path.join(args.input, 'new_data.csv')
    df = pd.read_csv(input_csv)

    # Basic normalization of relevant fields
    df['IMDB_Rating'] = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
    df['Released_Year'] = pd.to_numeric(df['Released_Year'], errors='coerce')
    df['Runtime'] = df['Runtime'].astype(str).str.strip()
    # Normalize Gross to have NaN for missing/blank
    if 'Gross' in df.columns:
        gross_raw = df['Gross'].astype(str)
        gross_raw = gross_raw.replace({
            '': np.nan,
            'nan': np.nan,
            'None': np.nan,
            'NaN': np.nan
        })
        df['Gross'] = gross_raw
    else:
        df['Gross'] = np.nan

    # Score components configuration
    current_year = int(pd.Timestamp.today().year)
    min_year = 1900
    min_runtime = 60
    max_runtime = 240
    ideal_runtime = 110
    target_runtime_low = 80
    target_runtime_high = 140

    # ASSERTION_START
    # Use IMDB rating (quality)
    assert df['IMDB_Rating'].notna().all()
    # ASSERTION_END
    rating_score = df['IMDB_Rating'] / 10.0

    # ASSERTION_START
    # Use recency (newer is better)
    assert df['Released_Year'].notna().all()
    # ASSERTION_END
    year_span = float(current_year - min_year) if current_year > min_year else 1.0
    recency_score = (df['Released_Year'] - min_year) / year_span

    # ASSERTION_START
    # Runtime suitability
    runtime_extracted = df['Runtime'].str.extract(r'^(\d+) min$')[0]
    assert runtime_extracted.notna().all(), "Runtime format must be '<number> min'"
    assert pd.to_numeric(runtime_extracted).gt(0).all(), "Runtime minutes must be positive"
    # ASSERTION_END
    runtime_min = df['Runtime'].str.extract(r'^([1-9][0-9]{1,2}) min$')[0].astype(int)
    runtime_deviation = (runtime_min - ideal_runtime).abs()
    # Linearly decay from ideal with tolerance window; negative clipped at 0
    tolerance = 50.0
    runtime_suitability = 1.0 - (runtime_deviation / tolerance)
    runtime_suitability = runtime_suitability.clip(lower=0.0, upper=1.0)

    present_mask = df['Gross'].notna() & (df['Gross'].astype(str).str.strip() != '')
    # ASSERTION_START
    # Revenue proxy from Gross
    gross_num_check = pd.to_numeric(
        df['Gross'].astype(str).str.replace(',', '', regex=False),
        errors='coerce'
    )
    assert gross_num_check.dropna().gt(-1).all()
    # ASSERTION_END
    gross_num = pd.to_numeric(df['Gross'].astype(str).str.replace(',', '', regex=False), errors='coerce')
    # Impute missing revenue proxy with median to avoid biasing scores where Gross is absent
    gross_filled = gross_num.fillna(gross_num.median())
    if np.isfinite(gross_filled.max()) and gross_filled.max() > 0:
        revenue_score = np.log1p(gross_filled) / np.log1p(gross_filled.max())
    else:
        revenue_score = pd.Series(0.0, index=df.index)

    # Composite score assembly
    # Weights tuned to favor quality and recency for licensing
    w_rating = 0.4
    w_recency = 0.3
    w_runtime = 0.15
    w_revenue = 0.15
    composite_score = (
            w_rating * rating_score +
            w_recency * recency_score +
            w_runtime * runtime_suitability +
            w_revenue * revenue_score
    )

    # Suitability filters for shortlist (keep code behavior dependent on valid assumptions)
    runtime_in_target = runtime_min.between(target_runtime_low, target_runtime_high, inclusive='both')
    quality_filter = df['IMDB_Rating'] >= 7.0
    filtered = df[quality_filter & runtime_in_target].copy()

    # Attach computed fields for ranking and auditing
    filtered['runtime_min'] = runtime_min.loc[filtered.index]
    filtered['rating_score'] = rating_score.loc[filtered.index]
    filtered['recency_score'] = recency_score.loc[filtered.index]
    filtered['revenue_score'] = revenue_score.loc[filtered.index]
    filtered['composite_score'] = composite_score.loc[filtered.index]

    # ASSERTION_START
    # Uniqueness of (Series_Title, Released_Year) is required to construct a reliable mapping
    assert not filtered.duplicated(['Series_Title', 'Released_Year']).any()
    # ASSERTION_END
    # Rank and produce a mapping keyed by (title, year)
    filtered['shortlist_rank'] = filtered['composite_score'].rank(method='dense', ascending=False).astype(int)
    filtered.sort_values(['composite_score', 'No_of_Votes'], ascending=[False, False], inplace=True)

    # Build a dict for downstream contracts that rely on unique keys
    key_tuples = list(zip(filtered['Series_Title'].astype(str), filtered['Released_Year'].astype(int)))
    score_map = dict(zip(key_tuples, filtered['composite_score'].round(6)))

    # Outputs
    shortlist_cols = [
        'Series_Title', 'Released_Year', 'IMDB_Rating', 'Runtime', 'runtime_min',
        'Gross', 'composite_score', 'shortlist_rank', 'No_of_Votes', 'Genre', 'Director'
    ]
    shortlist_path = os.path.join(args.output, 'licensing_shortlist.csv')
    filtered[shortlist_cols].to_csv(shortlist_path, index=False)

    scores_path = os.path.join(args.output, 'title_scores.csv')
    scored_df = df.copy()
    scored_df['runtime_min'] = runtime_min
    scored_df['rating_score'] = rating_score
    scored_df['recency_score'] = recency_score
    scored_df['revenue_score'] = revenue_score
    scored_df['composite_score'] = composite_score
    scored_df.to_csv(scores_path, index=False)

    mapping_path = os.path.join(args.output, 'score_map.json')
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump({f"{k[0]} ({k[1]})": float(v) for k, v in score_map.items()}, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
