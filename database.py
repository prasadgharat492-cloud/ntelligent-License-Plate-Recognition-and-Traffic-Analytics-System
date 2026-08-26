import pandas as pd
import os
from datetime import datetime, timedelta

# =========================================================
# PROJECT PATH
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
excel_file = os.path.join(LOG_DIR, "records.xlsx")

os.makedirs(LOG_DIR, exist_ok=True)


# =========================================================
# CREATE EXCEL FILE IF IT DOES NOT EXIST
# =========================================================

if not os.path.exists(excel_file):
    df = pd.DataFrame(
        columns=["Car Number", "First Seen", "Last Seen"]
    )
    df.to_excel(excel_file, index=False)


# =========================================================
# LOAD AND NORMALIZE DATA
# =========================================================

def load_data():
    df = pd.read_excel(excel_file)

    if df.empty:
        return df

    # Support both old column names
    if "Plate" in df.columns and "Car Number" not in df.columns:
        df.rename(columns={"Plate": "Car Number"}, inplace=True)

    # Make sure required columns exist
    if "Car Number" not in df.columns:
        df["Car Number"] = ""

    if "First Seen" not in df.columns:
        df["First Seen"] = None

    if "Last Seen" not in df.columns:
        df["Last Seen"] = None

    # Convert dates
    df["First Seen"] = pd.to_datetime(
        df["First Seen"], errors="coerce"
    )

    df["Last Seen"] = pd.to_datetime(
        df["Last Seen"], errors="coerce"
    )

    return df


# =========================================================
# CHECK PLATE
# =========================================================

def check_plate(plate_number):
    try:
        df = load_data()

        if df.empty:
            return "❌ Car not found!"

        plate = str(plate_number).strip().upper()

        records = df[
            df["Car Number"]
            .astype(str)
            .str.strip()
            .str.upper()
            == plate
        ]

        if records.empty:
            return "❌ Car not found!"

        history = records["Last Seen"].dropna().tolist()

        if not history:
            history = records["First Seen"].dropna().tolist()

        if not history:
            return f"✅ Car found: {plate_number}"

        history_str = "\n".join(
            [str(ts) for ts in history]
        )

        return (
            f"✅ Car found: {plate_number}\n"
            f"History:\n{history_str}"
        )

    except Exception as e:
        return f"Error: {e}"


# =========================================================
# DASHBOARD DATA
# =========================================================

def get_dashboard_data():
    try:
        df = load_data()

        if df.empty:
            return 0, 0, 0, []

        # Remove empty plate numbers
        df = df[
            df["Car Number"]
            .notna()
            & (df["Car Number"].astype(str).str.strip() != "")
        ]

        if df.empty:
            return 0, 0, 0, []

        # Group same vehicle
        unique_cars = (
            df.groupby("Car Number", as_index=False)
            .agg({
                "First Seen": "min",
                "Last Seen": "max"
            })
        )

        total_cars = len(unique_cars)

        new_cars = len(
            unique_cars[
                unique_cars["First Seen"]
                == unique_cars["Last Seen"]
            ]
        )

        returning_cars = total_cars - new_cars

        # Sort recent vehicles
        unique_cars["sort_date"] = (
            unique_cars["Last Seen"]
            .fillna(unique_cars["First Seen"])
        )

        recent_plates = (
            unique_cars
            .sort_values(
                "sort_date",
                ascending=False
            )
            .drop(columns=["sort_date"])
            .to_dict(orient="records")
        )

        return (
            total_cars,
            new_cars,
            returning_cars,
            recent_plates
        )

    except Exception as e:
        print("Dashboard error:", e)
        return 0, 0, 0, []


# =========================================================
# TRAFFIC ANALYTICS
# =========================================================
def get_traffic_analytics():
    try:
        df = load_data()

        if df.empty:
            return {}, {}, None

        # Make sure datetime columns are properly converted
        df["Last Seen"] = pd.to_datetime(df["Last Seen"], errors="coerce")
        df["First Seen"] = pd.to_datetime(df["First Seen"], errors="coerce")

        # Use Last Seen first
        ts = df["Last Seen"].copy()

        # If Last Seen is missing, use First Seen
        ts = ts.fillna(df["First Seen"])
        ts = ts.dropna()

        if ts.empty:
            return {}, {}, None

        # =================================================
        # HOURLY TRAFFIC - ALL 24 HOURS
        # =================================================

        today = datetime.now().date()

        today_data = ts[ts.dt.date == today]

        # During testing, if there is no data today,
        # use all available records.
        if today_data.empty:
            hourly_source = ts
        else:
            hourly_source = today_data

        hourly_counts = (
            hourly_source
            .dt.hour
            .value_counts()
            .to_dict()
        )

        # Create all 24 hours
        hourly = {
            hour: int(hourly_counts.get(hour, 0))
            for hour in range(24)
        }

        # =================================================
        # DAILY TRAFFIC - LAST 7 DAYS
        # =================================================

        daily_counts = (
            ts.dt.date
            .value_counts()
            .to_dict()
        )

        # Create last 7 dates
        daily = {}

        for i in range(6, -1, -1):
            day = today - timedelta(days=i)

            # If today has no data and old data exists,
            # use available dates for testing.
            daily[str(day)] = int(daily_counts.get(day, 0))

        # =================================================
        # SIMPLE ANOMALY DETECTION
        # =================================================

        per_day_counts = ts.dt.date.value_counts()

        avg_daily = (
            per_day_counts.mean()
            if not per_day_counts.empty
            else 0
        )

        anomaly = None

        if avg_daily > 0:

            if len(today_data) > avg_daily * 1.5:
                anomaly = "🚨 High traffic today!"

            elif (
                len(today_data) < avg_daily * 0.5
                and len(today_data) > 0
            ):
                anomaly = "⚠️ Low traffic today!"

        print("Hourly traffic:", hourly)
        print("Daily traffic:", daily)

        return hourly, daily, anomaly

    except Exception as e:

        print("Traffic analytics error:", e)

        return {}, {}, f"Error in analytics: {e}"