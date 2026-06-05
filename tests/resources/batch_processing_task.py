"""Batch processing task: Send discount confirmation emails to completed bookings."""
import polars as pl


def send_discount_confirmation_mail(email, discount):
    if pd.isna(email):
        raise RuntimeError("Error: No email to send to!")
    else:
        print(email, discount)


def batch_processing_task(df):
    import polars as pl
    discount_per_category = [5, 10, 25, 500]
    df = df.with_columns(
        pl.col("guest_category_idx")
        .map_elements(lambda x: discount_per_category[x], return_dtype=pl.Int64)
        .alias("discount")
    )
    completed_bookings = df.filter(pl.col("booking_status") == "COMPLETED")
    for booking in completed_bookings.iter_rows(named=True):
        send_discount_confirmation_mail(booking["email"], booking["discount"])
