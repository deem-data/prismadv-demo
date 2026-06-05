import argparse
import os

import numpy as np
import pandas as pd


def assign_salary_slab(income):
    if pd.isna(income):
        return np.nan
    v = float(income)
    if v <= 5000:
        return "Upto 5k"
    elif v <= 10000:
        return "5k-10k"
    elif v <= 15000:
        return "10k-15k"
    else:
        return "15k+"


def get_band_midpoints(df):
    mid = {
        "Upto 5k": 2500.0,
        "5k-10k": 7500.0,
        "10k-15k": 12500.0,
        "15k+": df.loc[df["SalarySlab"] == "15k+", "MonthlyIncome"].median(),
    }
    if pd.isna(mid["15k+"]):
        mid["15k+"] = 17500.0
    return mid


def next_band_lower_bound(slab):
    if slab == "Upto 5k":
        return 5001
    if slab == "5k-10k":
        return 10001
    if slab == "10k-15k":
        return 15001
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    input_file = os.path.join(args.input, 'new_data.csv')
    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(input_file)

    # Coerce types that are required for analytics
    for col in [
        "MonthlyIncome",
        "JobLevel",
        "PerformanceRating",
        "YearsAtCompany",
        "TotalWorkingYears",
        "YearsSinceLastPromotion",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Guard use of band logic against invalid slab-income alignments
    # ASSERTION_START
    valid_rows_df = df.dropna(subset=["SalarySlab", "MonthlyIncome"])
    assert (valid_rows_df["MonthlyIncome"] > 0).all()
    _mask = (
            ((valid_rows_df["SalarySlab"] == "Upto 5k") & (valid_rows_df["MonthlyIncome"] <= 5000)) |
            ((valid_rows_df["SalarySlab"] == "5k-10k") & (valid_rows_df["MonthlyIncome"] > 5000) & (
                    valid_rows_df["MonthlyIncome"] <= 10000)) |
            ((valid_rows_df["SalarySlab"] == "10k-15k") & (valid_rows_df["MonthlyIncome"] > 10000) & (
                    valid_rows_df["MonthlyIncome"] <= 15000)) |
            ((valid_rows_df["SalarySlab"] == "15k+") & (valid_rows_df["MonthlyIncome"] > 15000))
    )
    assert _mask.all()
    # ASSERTION_END
    band_mid = get_band_midpoints(df)
    df["BandMidpoint"] = df["SalarySlab"].map(band_mid)
    df["CompaRatio"] = df["MonthlyIncome"] / df["BandMidpoint"]

    rating_raise = {3: 0.03, 4: 0.08}
    df["BaseRaisePct"] = df["PerformanceRating"].map(rating_raise).fillna(0.0)

    df["MarketAdjPct"] = np.where(
        df["CompaRatio"] < 0.90, 0.02,
        np.where(df["CompaRatio"] > 1.10, -0.01, 0.0)
    )

    # Tenure-derived calculations rely on hierarchical year consistency
    # ASSERTION_START
    TENURE_COLS = ["YearsAtCompany", "YearsSinceLastPromotion"]
    valid_rows_df = df.dropna(subset=TENURE_COLS)
    assert (valid_rows_df["YearsAtCompany"] >= 0).all()
    assert (valid_rows_df["YearsSinceLastPromotion"] >= 0).all()
    # ASSERTION_END
    df["TenureRatio"] = np.where(df["YearsAtCompany"] > 0,
                                 df["YearsSinceLastPromotion"] / df["YearsAtCompany"],
                                 0.0)
    df["TenureAdjPct"] = np.minimum(0.02, 0.02 * df["TenureRatio"])

    # Level-salary relationship sanity prior to percentile-based promotion gating
    df["LevelPercentile"] = df.groupby("JobLevel")["MonthlyIncome"].rank(pct=True, method="average")

    # High-level compensation tiering alignment before using level-based logic
    df["PromotionRecommended"] = (
            (df["PerformanceRating"] >= 4) &
            (df["YearsSinceLastPromotion"] >= 2) &
            (df["LevelPercentile"] >= 0.85) &
            (df["JobLevel"] < df["JobLevel"].max())
    )

    df["RecommendedRaisePct"] = df[["BaseRaisePct", "MarketAdjPct", "TenureAdjPct"]].sum(axis=1)
    df["PromoKickerPct"] = np.where(df["PromotionRecommended"], 0.10, 0.0)
    df["TotalRaisePct"] = (df["RecommendedRaisePct"] + df["PromoKickerPct"]).clip(lower=0.0, upper=0.20)

    df["NextBandMin"] = df["SalarySlab"].map(next_band_lower_bound)

    new_income = (df["MonthlyIncome"] * (1.0 + df["TotalRaisePct"]))
    new_income = new_income.round(0).astype("Int64")

    promo_mask = df["PromotionRecommended"] & df["NextBandMin"].notna()
    if promo_mask.any():
        nbmin = df.loc[promo_mask, "NextBandMin"].astype(int)
        boosted = np.maximum(new_income.loc[promo_mask].astype(int).values, nbmin.values)
        new_income.loc[promo_mask] = boosted

    df["NewMonthlyIncome"] = new_income.astype(int)
    df["NewSalarySlab"] = df["NewMonthlyIncome"].apply(assign_salary_slab)
    df["NewJobLevel"] = np.where(df["PromotionRecommended"], df["JobLevel"] + 1, df["JobLevel"])

    out_cols = [
        "EmpID",
        "JobLevel",
        "SalarySlab",
        "MonthlyIncome",
        "PerformanceRating",
        "YearsAtCompany",
        "TotalWorkingYears",
        "YearsSinceLastPromotion",
        "PromotionRecommended",
        "NewJobLevel",
        "RecommendedRaisePct",
        "PromoKickerPct",
        "TotalRaisePct",
        "NewMonthlyIncome",
        "NewSalarySlab",
    ]
    existing_cols = [c for c in out_cols if c in df.columns]
    df_out = df[existing_cols]

    out_path = os.path.join(args.output, 'compensation_recommendations.csv')
    df_out.to_csv(out_path, index=False)


if __name__ == '__main__':
    main()
