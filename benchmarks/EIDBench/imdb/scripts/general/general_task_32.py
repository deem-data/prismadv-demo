import argparse
import os
import re
import json
import pandas as pd
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True)
parser.add_argument('--output', type=str, required=True)
args = parser.parse_args()

input_csv = os.path.join(args.input, 'new_data.csv')
os.makedirs(args.output, exist_ok=True)

df = pd.read_csv(input_csv)

# Basic dtype normalization used by ranking and rendering
df['IMDB_Rating'] = pd.to_numeric(df['IMDB_Rating'], errors='coerce')
df['No_of_Votes'] = pd.to_numeric(df['No_of_Votes'], errors='coerce')
# ASSERTION_START
rating_ok = df['IMDB_Rating'].notna() & df['IMDB_Rating'].between(0.0, 10.0, inclusive='both')
votes_ok = df['No_of_Votes'].notna() & (df['No_of_Votes'] >= 0)
assert rating_ok.all() and votes_ok.all()
# ASSERTION_END
# Compute a weighted ranking using a Bayesian-style formula
v = df['No_of_Votes']
r = df['IMDB_Rating']
C = r.mean()
m = float(v.quantile(0.60))
if not np.isfinite(m) or m <= 0:
    m = 1000.0

score = (v / (v + m)) * r + (m / (v + m)) * C
df['ranking_score'] = score

# Pick weekly featured titles
TOP_N = 12
featured = df.sort_values(['ranking_score', 'IMDB_Rating', 'No_of_Votes'], ascending=[False, False, False]).head(TOP_N).copy()
# ASSERTION_START
assert featured['Poster_Link'].astype(str).str.match(r'^https?://.+', na=False).all()
# ASSERTION_END
# ASSERTION_START
assert featured['Runtime'].str.contains(r'\d+').all()
# ASSERTION_END
# Parse runtime minutes for display and layout
featured['runtime_minutes'] = featured['Runtime'].str.extract(r'(\d+)')[0].astype(int)

# Prepare rendering data
def slugify(text: str) -> str:
    base = re.sub(r'[^a-zA-Z0-9]+', '-', text.strip()).strip('-')
    return base.lower()

cards = []
for row in featured.itertuples(index=False):
    title = str(getattr(row, 'Series_Title'))
    year = int(getattr(row, 'Released_Year')) if pd.notna(getattr(row, 'Released_Year')) else None
    poster = str(getattr(row, 'Poster_Link'))
    runtime_min = int(getattr(row, 'runtime_minutes'))
    certificate = getattr(row, 'Certificate')
    certificate_display = 'NR' if pd.isna(certificate) or str(certificate).strip() == '' else str(certificate)
    rating_val = float(getattr(row, 'IMDB_Rating'))
    votes_val = int(getattr(row, 'No_of_Votes'))
    score_val = float(getattr(row, 'ranking_score'))
    slug = slugify(f"{title}-{year}")
    star_fill_pct = max(0.0, min(100.0, rating_val * 10.0))

    cards.append({
        'id': slug,
        'title': title,
        'year': year,
        'poster': poster,
        'runtime_minutes': runtime_min,
        'certificate': certificate_display,
        'imdb_rating': rating_val,
        'votes': votes_val,
        'score': score_val,
        'genre': str(getattr(row, 'Genre')),
        'star_fill_pct': star_fill_pct
    })

# Render a simple HTML page with cards
style = """
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #0f1115; color: #e6e8eb; }
    h1 { margin: 0 0 16px 0; font-size: 24px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
    .card { background: #171a21; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
    .poster { width: 100%; height: 360px; object-fit: cover; background: #0b0d12; }
    .content { padding: 12px; }
    .title { font-weight: 600; font-size: 15px; line-height: 1.25; margin: 0 0 4px 0; }
    .meta { font-size: 12px; color: #aab2bd; margin-bottom: 6px; }
    .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px; background: #2a2f3a; color: #c8d1dc; }
    .rating { position: relative; display: inline-block; width: 100px; height: 16px; background: #2a2f3a; border-radius: 8px; overflow: hidden; vertical-align: middle; }
    .rating-fill { position: absolute; left: 0; top: 0; bottom: 0; background: linear-gradient(90deg, #ffd54f, #ffb300); }
    .rating-text { font-size: 12px; margin-left: 8px; color: #c8d1dc; }
  </style>
"""

cards_html_parts = []
for c in cards:
    card_html = f"""
      <div class=\"card\" id=\"{c['id']}\">
        <img class=\"poster\" src=\"{c['poster']}\" alt=\"{c['title']} poster\"/>
        <div class=\"content\">
          <div class=\"title\">{c['title']} ({c['year']})</div>
          <div class=\"meta\">{c['genre']}</div>
          <span class=\"badge\">{c['runtime_minutes']} min</span>
          <span class=\"badge\">{c['certificate']}</span>
          <div style=\"margin-top:8px;\">
            <div class=\"rating\"><div class=\"rating-fill\" style=\"width:{c['star_fill_pct']}%;\"></div></div>
            <span class=\"rating-text\">{c['imdb_rating']:.1f} • {c['votes']:,} votes</span>
          </div>
        </div>
      </div>
    """
    cards_html_parts.append(card_html)

html = f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\"/>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
    <title>Weekly Featured Films</title>
    {style}
  </head>
  <body>
    <h1>Weekly Featured Films</h1>
    <div class=\"grid\">
      {''.join(cards_html_parts)}
    </div>
  </body>
</html>
"""

with open(os.path.join(args.output, 'featured_cards.html'), 'w', encoding='utf-8') as f:
    f.write(html)

with open(os.path.join(args.output, 'featured_cards.json'), 'w', encoding='utf-8') as f:
    json.dump({'generated_by': 'curation_pipeline', 'count': len(cards), 'items': cards}, f, ensure_ascii=False, indent=2)
