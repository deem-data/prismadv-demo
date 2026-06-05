import argparse
import os

import numpy as np
import pandas as pd


def robust_minmax(s: pd.Series, low_q: float = 0.05, high_q: float = 0.95) -> pd.Series:
    s = s.astype(float)
    lo, hi = s.quantile(low_q), s.quantile(high_q)
    denom = (hi - lo)
    if pd.notna(denom) and denom != 0:
        return ((s.clip(lo, hi) - lo) / denom).fillna(0.5)
    else:
        return pd.Series(0.5, index=s.index)


def runtime_factor(minutes: pd.Series) -> pd.Series:
    min_minutes = 45
    low_opt = 90
    high_opt = 150
    max_minutes = 240
    min_factor = 0.8
    factor = np.ones(len(minutes), dtype=float)
    left = minutes < low_opt
    right = minutes > high_opt
    factor[left] = min_factor + (minutes[left] - min_minutes) / (low_opt - min_minutes) * (1 - min_factor)
    factor[right] = min_factor + (max_minutes - minutes[right]) / (max_minutes - high_opt) * (1 - min_factor)
    factor = np.clip(factor, min_factor, 1.0)
    return pd.Series(factor, index=minutes.index)


parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

input_file = os.path.join(args.input, 'new_data.csv')
df = pd.read_csv(input_file)

# Rating is used to normalize and to fit a calibration with Meta_score
# ASSERTION_START
rating = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
assert rating.notna().all()
assert rating.between(0, 10).all()
# ASSERTION_END
rating_norm = df['IMDB_Rating'].astype(float) / 10.0

# Votes power part of the popularity model through a log transform
# ASSERTION_START
votes_series = pd.to_numeric(df['No_of_Votes'], errors='coerce')
assert votes_series.notna().all()
assert (votes_series > -1).all()
# ASSERTION_END
votes_log = np.log1p(df['No_of_Votes'].astype(float))
votes_norm = robust_minmax(votes_log)

# Runtime shapes the final score via a factor so its format and bounds must be consistent
# ASSERTION_START
extracted_runtime = df['Runtime'].astype(str).str.extract(r'([0-9]{2,3})')[0]
assert extracted_runtime.notna().all()
# ASSERTION_END
runtime_minutes = df['Runtime'].astype(str).str.extract(r'([0-9]{2,3})')[0].astype(int)
runtime_adj = runtime_factor(runtime_minutes)

# Gross contributes a smaller boost; ensure parsable for all present values
df['Gross_USD'] = pd.to_numeric(df['Gross'].astype(str).str.replace(',', '', regex=False), errors='coerce')
# Use a robust normalization on log gross; fill missing with median to avoid penalizing titles without data
_gross_for_norm = df['Gross_USD'].copy()
if _gross_for_norm.notna().any():
    median_g = _gross_for_norm.median(skipna=True)
    _gross_for_norm = _gross_for_norm.fillna(median_g)
else:
    _gross_for_norm = pd.Series(np.zeros(len(df)), index=df.index)

gross_norm = robust_minmax(np.log1p(_gross_for_norm))

# Correlation between IMDB_Rating and Meta_score is used to calibrate blending weight and for regression-based imputation
meta_valid_mask = df['Meta_score'].notna() & df['IMDB_Rating'].notna()
if meta_valid_mask.sum() > 1:
    r = df.loc[meta_valid_mask, 'IMDB_Rating'].astype(float).corr(df.loc[meta_valid_mask, 'Meta_score'].astype(float))
else:
    r = np.nan
# ASSERTION_START
assert np.isfinite(r)
# ASSERTION_END
# Fit a simple linear model Meta_score ~ a * IMDB_Rating + b to impute missing Meta_score
slope, intercept = np.polyfit(
    df.loc[meta_valid_mask, 'IMDB_Rating'].astype(float).values,
    df.loc[meta_valid_mask, 'Meta_score'].astype(float).values,
    1
)

meta_filled = df['Meta_score'].astype(float).copy()
missing_meta = meta_filled.isna()
if missing_meta.any():
    meta_filled.loc[missing_meta] = np.clip(slope * df.loc[missing_meta, 'IMDB_Rating'].astype(float) + intercept, 0,
                                            100)

meta_norm = meta_filled / 100.0

# Blend rating and metascore with correlation-aware weights
r_norm = float(np.clip((r - 0.2) / 0.8, 0.0, 1.0))
w_rating = 0.5 + 0.2 * r_norm
w_meta = 1.0 - w_rating

content_quality = w_rating * rating_norm + w_meta * meta_norm

# Ensure Series_Title + Released_Year uniquely identifies a title row used for ranking and output publishing keys
popularity_index_base = 0.6 * content_quality + 0.3 * votes_norm + 0.1 * gross_norm
popularity_index = popularity_index_base * runtime_adj

df['PopularityIndex'] = popularity_index

# Set a MultiIndex for downstream publishing keyed by title-year
_ = df.set_index(['Series_Title', 'Released_Year'], inplace=False)

df_sorted = df.sort_values('PopularityIndex', ascending=False).copy()
df_sorted['Rank'] = np.arange(1, len(df_sorted) + 1)

all_out = df_sorted[[
    'Series_Title', 'Released_Year', 'IMDB_Rating', 'Meta_score', 'No_of_Votes', 'Runtime', 'Gross',
    'PopularityIndex', 'Rank'
]]

top_n = min(100, len(all_out))
top_out = all_out.head(top_n)

all_out.to_csv(os.path.join(args.output, 'movie_popularity_ranking.csv'), index=False)
top_out.to_csv(os.path.join(args.output, 'movie_popularity_top100.csv'), index=False)
