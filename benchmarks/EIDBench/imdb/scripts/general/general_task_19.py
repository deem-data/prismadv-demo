import argparse
import os
from datetime import datetime
import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_file = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_file)

    # Basic type normalization for downstream logic
    df['IMDB_Rating'] = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
    df['Released_Year'] = pd.to_numeric(df['Released_Year'], errors='coerce').astype('Int64')
    df['No_of_Votes'] = pd.to_numeric(df['No_of_Votes'], errors='coerce').fillna(0).astype(int)

    current_year = datetime.now().year

    allowed_genres = {
        'Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family',
        'Fantasy', 'Film-Noir', 'History', 'Horror', 'Music', 'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Sport',
        'Thriller', 'War', 'Western'
    }
    allowed_certificates = {
        'U', 'UA', 'A', 'G', 'PG', 'PG-13', 'R', 'NC-17', 'Not Rated', 'Unrated', 'Passed', 'Approved'
    }

    # ASSERTION_START
    # 1) Uniqueness of (Series_Title, Released_Year)
    assert not df.duplicated(subset=['Series_Title', 'Released_Year']).any()
    # ASSERTION_END
    # Use the unique key as index for deterministic scoring and dedupe safety
    df = df.set_index(['Series_Title', 'Released_Year'], verify_integrity=True)

    # ASSERTION_START
    # 2) IMDB_Rating must be within [0, 10]
    assert df['IMDB_Rating'].notna().all()
    # ASSERTION_END
    # Quality component derived from rating; relies on bounded rating to keep scores in [0,1]
    rating_score = (df['IMDB_Rating'] / 10.0).clip(0, 1)

    # Popularity component (log-scaled votes); calibrated assuming high-rated entries have strong vote counts
    votes_log = np.log10(df['No_of_Votes'].clip(lower=1))
    pop_score = ((votes_log - 3.0) / (6.0 - 3.0)).clip(0, 1)  # 1k->0, 1M->1

    # ASSERTION_START
    # 4) Released_Year must be within [1920, current_year]
    years = df.reset_index()['Released_Year']
    assert years.notna().all()
    # ASSERTION_END
    # Freshness factor decaying after ~30 years
    age_years = (current_year - df.reset_index()['Released_Year']).astype(float)
    freshness = (1.0 - (age_years / 30.0)).clip(0, 1).values

    # ASSERTION_START
    # 5) Runtime format must match '<digits> min'
    # The subsequent .astype(int) call will fail if the extraction of digits
    # returns any null values. This assertion checks that requirement directly.
    assert df['Runtime'].str.extract(r'(\d+)', expand=False).notna().all()
    # ASSERTION_END
    # Parse runtime minutes for engagement modeling
    runtime_min = df['Runtime'].str.extract(r'(\d+)', expand=False).astype(int)

    runtime_diff = (runtime_min - 110).astype(float)
    engagement = np.exp(-((runtime_diff / 50.0) ** 2))

    genre_weights = {
        'Action': 1.1, 'Adventure': 1.05, 'Animation': 1.05, 'Biography': 1.0, 'Comedy': 1.0, 'Crime': 1.05,
        'Documentary': 0.85, 'Drama': 1.1, 'Family': 1.05, 'Fantasy': 1.0, 'Film-Noir': 1.0, 'History': 0.95,
        'Horror': 0.85, 'Music': 0.95, 'Musical': 0.90, 'Mystery': 1.0, 'Romance': 0.95, 'Sci-Fi': 1.0,
        'Sport': 0.95, 'Thriller': 1.05, 'War': 0.90, 'Western': 0.85
    }

    def avg_genre_weight(genre_str: str) -> float:
        parts = [p.strip() for p in str(genre_str).split(',') if p.strip()]
        weights = [genre_weights.get(p, 1.0) for p in parts]
        if not weights:
            return 1.0
        return float(np.mean(weights))

    genre_pref = df['Genre'].map(avg_genre_weight)

    cert_weights = {
        'U': 1.10, 'G': 1.10, 'PG': 1.05, 'PG-13': 1.00, 'UA': 1.00, 'Passed': 0.95, 'Approved': 0.95,
        'Not Rated': 0.95, 'Unrated': 0.90, 'R': 0.80, 'A': 0.75, 'NC-17': 0.00
    }
    cert_series = df['Certificate'].fillna('Not Rated').astype(str)
    suitability = cert_series.map(cert_weights).fillna(0.90)

    # Content suitability gating (e.g., avoid NC-17 for licensing)
    eligible_mask = suitability > 0.0

    # Combine signals into recommendation score
    # The weighting structure assumes all upstream fields adhere to the asserted contracts
    combined_score = (
        (0.55 * rating_score + 0.45 * pop_score)
        * (0.6 + 0.4 * freshness)
        * (0.6 + 0.4 * engagement)
        * (0.85 + 0.15 * genre_pref)
        * suitability
    )

    rec = df.copy()
    rec['rating_score'] = rating_score
    rec['pop_score'] = pop_score
    rec['freshness'] = freshness
    rec['engagement'] = engagement
    rec['genre_pref'] = genre_pref
    rec['suitability'] = suitability
    rec['priority_score'] = combined_score

    # Apply eligibility filter and minimum quality threshold for licensing
    quality_gate = rec['IMDB_Rating'] >= 6.5
    final = rec[eligible_mask & quality_gate].sort_values('priority_score', ascending=False)

    # Persist results
    out_cols = [
        'Poster_Link', 'Certificate', 'Runtime', 'Genre', 'IMDB_Rating', 'No_of_Votes',
        'Meta_score', 'Director', 'Star1', 'Star2', 'Star3', 'Star4', 'Gross',
        'rating_score', 'pop_score', 'freshness', 'engagement', 'genre_pref', 'suitability', 'priority_score'
    ]
    # Keep only columns that exist in the input plus derived metrics
    out_cols = [c for c in out_cols if c in final.columns]

    output_file = os.path.join(args.output, 'licensing_recommendations.csv')
    final.reset_index().to_csv(output_file, index=False, columns=['Series_Title', 'Released_Year'] + out_cols)


if __name__ == '__main__':
    main()
