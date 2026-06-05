"""Analytics task: Generate report of active bookings by guest category."""
from datetime import datetime


def save_to_s3(report, date):
    print(date)
    print(report)


def analytics_task(df):
    import duckdb

    report = duckdb.sql(
        """
      SELECT guest_category_idx, COUNT(*) as active_bookings FROM df
       WHERE booking_status = 'IN_PROGRESS'
    GROUP BY guest_category_idx
    ORDER BY guest_category_idx
    """
    ).df()
    save_to_s3(report, datetime.today())
