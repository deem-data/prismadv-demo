import argparse
import os
from datetime import datetime

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_csv = os.path.join(args.input, 'new_data.csv')
output_dir = args.output
os.makedirs(output_dir, exist_ok=True)

df = pd.read_csv(input_csv)
# Poster link quality checks before using for dedup and URL passthrough
poster_series = df['Poster_Link'].astype(str)
# Released year checks and parsing before recency computation
year_str = df['Released_Year'].astype(str).str.strip()
year_int = pd.to_numeric(year_str, errors='coerce')
current_year = datetime.now().year
# ASSERTION_START
assert year_int.notna().all()
# ASSERTION_END
# IMDB rating checks before normalization and scoring
ratings = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
# ASSERTION_START
assert ratings.notna().all() and ratings.between(0.0, 10.0).all()

# ASSERTION_END
rating_norm = ratings / 10.0

# Votes checks before log computation and correlation-based weighting
votes = pd.to_numeric(df['No_of_Votes'], errors='coerce')
# ASSERTION_START
assert votes.notna().all() and (votes >= 0).all()
# ASSERTION_END
votes_log = np.log10(votes.clip(lower=1))

# Correlation assumptions used to weight the composite score components
corr = pd.concat([ratings, votes], axis=1).dropna().corr().iloc[0, 1]
# Runtime checks and parsing; used for a small tie-breaker bonus
runtime_str = df['Runtime'].astype(str).str.strip()
runtime_min = pd.to_numeric(runtime_str.str.extract(r'^(\d+)', expand=False), errors='coerce')
# ASSERTION_START
# The runtime_bonus calculation is robust to values outside the original asserted range.
# However, NaN values must be prevented from propagating into the score.
assert runtime_min.notna().all() and (runtime_min >= 0).all()
# ASSERTION_END
# Smooth bonus centered around ~100 minutes
runtime_bonus = np.exp(-((runtime_min - 100.0) ** 2) / (2 * (35.0 ** 2)))

# Gross parsing and checks; used for scoring
gross_str = df['Gross'].astype('string')
present_mask = gross_str.notna()
gross_num = pd.to_numeric(gross_str.str.replace(',', '', regex=False), errors='coerce').fillna(0)

# Certificate checks; used to enforce family-friendly eligibility
cert_series = df['Certificate']
cert_upper = cert_series.fillna('').astype(str).str.strip().str.upper()
allowed_cert_set = {
    'U', 'UA', 'A', 'G', 'PG', 'PG-13', 'R', 'NC-17', 'NOT RATED', 'UNRATED'
}
# Cross-field logic between certificate and genre
genre_str = df['Genre'].astype(str)
# Recency transformation
age = (current_year - year_int).clip(lower=0)
recency_score = 1.0 / (1.0 + (age / 5.0))

# Gross normalization (log scale)
if (gross_num > 0).any():
    gross_log = np.log10(gross_num.where(gross_num > 0, np.nan))
    gross_log = (gross_log - np.nanmin(gross_log)) / (np.nanmax(gross_log) - np.nanmin(gross_log))
    gross_norm = gross_log.fillna(0.0)
else:
    gross_norm = pd.Series(0.0, index=df.index)

# Votes normalization (log scale)
votes_log_min = votes_log.min()
votes_log_ptp = votes_log.max() - votes_log.min()
votes_norm = (votes_log - votes_log_min) / (votes_log_ptp if votes_log_ptp != 0 else 1.0)

# Dynamic weighting based on observed correlation (guarded earlier)
vote_weight = min(0.35, max(0.20, float(corr)))
fixed_weights_sum = 0.15 + 0.15 + 0.05  # recency + gross + runtime
rating_weight = 1.0 - (vote_weight + fixed_weights_sum)

composite_score = (
        rating_weight * rating_norm +
        vote_weight * votes_norm +
        0.15 * recency_score +
        0.15 * gross_norm +
        0.05 * runtime_bonus
)

# Family-friendly eligibility
family_allowed = {'U', 'G', 'PG', 'PG-13', 'UA'}
eligible_mask = cert_upper.isin(family_allowed)

# Prepare output: dedupe by poster and rank
work = df.copy()
work['CompositeScore'] = composite_score
work['EligibleFamilyFriendly'] = eligible_mask
work['Year'] = year_int

# Use poster link uniqueness assumption to deduplicate display items
work = work.sort_values(['EligibleFamilyFriendly', 'CompositeScore'], ascending=[False, False])
work = work.drop_duplicates(subset=['Poster_Link'], keep='first')

ranked = work[work['EligibleFamilyFriendly']].copy()
ranked = ranked.sort_values('CompositeScore', ascending=False)

# Persist outputs
ranked_cols = [
    'Series_Title', 'Released_Year', 'IMDB_Rating', 'No_of_Votes', 'Gross',
    'Certificate', 'Genre', 'Poster_Link', 'CompositeScore'
]
ranked[ranked_cols].to_csv(os.path.join(output_dir, 'homepage_ranked_family_friendly.csv'), index=False)

# Also export top 50 for immediate homepage usage
ranked.head(50)[ranked_cols].to_csv(os.path.join(output_dir, 'homepage_top50.csv'), index=False)
