import os
import json
from datetime import date

import pandas as pd
from flask import Flask, render_template, request, jsonify

from database import (
    check_plate,
    get_dashboard_data,
    get_traffic_analytics
)


# --------------------------------------------------
# FLASK APP
# --------------------------------------------------

app = Flask(__name__, template_folder="Frontend")


# --------------------------------------------------
# FILE PATHS
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_DIR = os.path.join(BASE_DIR, "logs")

EXCEL_FILE = os.path.join(
    LOG_DIR,
    "records.xlsx"
)

DEFAULT_COLUMNS = [
    "Plate",
    "First Seen",
    "Last Seen"
]


# --------------------------------------------------
# CREATE EXCEL FILE IF NOT EXISTS
# --------------------------------------------------

def ensure_excel_file():

    os.makedirs(
        LOG_DIR,
        exist_ok=True
    )

    if not os.path.exists(EXCEL_FILE):

        df = pd.DataFrame(
            columns=DEFAULT_COLUMNS
        )

        df.to_excel(
            EXCEL_FILE,
            index=False
        )


# Create Excel file when application starts
ensure_excel_file()


# --------------------------------------------------
# JSON ENCODER
# --------------------------------------------------

class CustomJSONEncoder(json.JSONEncoder):

    def default(self, obj):

        if isinstance(obj, date):
            return obj.isoformat()

        return super().default(obj)


app.json_encoder = CustomJSONEncoder


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/", methods=["GET"])
def index():

    ensure_excel_file()

    try:

        total, new, returning, recent = (
            get_dashboard_data()
        )

        hourly, daily, anomaly = (
            get_traffic_analytics()
        )

    except Exception as e:

        print(
            "DASHBOARD ERROR:",
            repr(e)
        )

        total = 0
        new = 0
        returning = 0
        recent = []
        hourly = {}
        daily = {}
        anomaly = None

    # Convert daily dictionary keys to strings
    if daily and isinstance(daily, dict):

        daily = {
            str(k): v
            for k, v in daily.items()
        }

    return render_template(
        "index.html",
        result=None,
        total=total,
        new=new,
        returning=returning,
        recent=recent,
        hourly=hourly,
        daily=daily,
        anomaly=anomaly
    )


# --------------------------------------------------
# SEARCH VEHICLE
# --------------------------------------------------

@app.route("/api/search", methods=["POST"])
def api_search():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "error": "Invalid JSON data"
            })

        plate = data.get(
            "plate",
            ""
        ).strip()

        if not plate:

            return jsonify({
                "success": False,
                "error": "No plate number provided"
            })

        result = check_plate(plate)

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as e:

        print(
            "SEARCH ERROR:",
            repr(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        })


# --------------------------------------------------
# PREDICTED PEAK HOUR
# --------------------------------------------------

@app.route("/api/peak-hour", methods=["GET"])
def api_peak_hour():

    try:

        ensure_excel_file()

        # Read Excel file
        df = pd.read_excel(
            EXCEL_FILE
        )

        # Check if Excel is empty
        if df.empty:

            return jsonify({
                "ok": False,
                "message": "No traffic data available."
            })

        # --------------------------------------------------
        # SUPPORT BOTH COLUMN NAMES
        # --------------------------------------------------

        if (
            "Plate" in df.columns
            and "Car Number" not in df.columns
        ):

            df.rename(
                columns={
                    "Plate": "Car Number"
                },
                inplace=True
            )

        # --------------------------------------------------
        # GET TIMESTAMP
        # --------------------------------------------------

        if "Last Seen" in df.columns:

            ts = pd.to_datetime(
                df["Last Seen"],
                errors="coerce"
            )

            # If Last Seen is missing,
            # use First Seen
            if "First Seen" in df.columns:

                first_ts = pd.to_datetime(
                    df["First Seen"],
                    errors="coerce"
                )

                ts = ts.fillna(
                    first_ts
                )

        elif "First Seen" in df.columns:

            ts = pd.to_datetime(
                df["First Seen"],
                errors="coerce"
            )

        else:

            return jsonify({
                "ok": False,
                "message": "No timestamp column found."
            })

        # Remove invalid timestamps
        ts = ts.dropna()

        if ts.empty:

            return jsonify({
                "ok": False,
                "message": "No valid traffic timestamps found."
            })

        # --------------------------------------------------
        # COUNT VEHICLES BY HOUR
        # --------------------------------------------------

        hourly_counts = (
            ts.dt.hour
            .value_counts()
            .sort_index()
        )

        if hourly_counts.empty:

            return jsonify({
                "ok": False,
                "message": "No hourly traffic data found."
            })

        # --------------------------------------------------
        # FIND BUSIEST HOUR
        # --------------------------------------------------

        peak_hour = int(
            hourly_counts.idxmax()
        )

        peak_count = int(
            hourly_counts.max()
        )

        next_hour = (
            peak_hour + 1
        ) % 24

        print(
            "Predicted Peak Hour:",
            peak_hour
        )

        print(
            "Vehicle Count:",
            peak_count
        )

        # --------------------------------------------------
        # SEND RESULT TO WEBSITE
        # --------------------------------------------------

        return jsonify({

            "ok": True,

            "method":
                "traffic_frequency",

            "predicted_peak_hour":
                peak_hour,

            "peak_count":
                peak_count,

            "window":
                f"{peak_hour:02d}:00 - "
                f"{next_hour:02d}:00"
        })

    except Exception as e:

        print(
            "PEAK HOUR ERROR:",
            repr(e)
        )

        return jsonify({

            "ok": False,

            "message":
                str(e)
        })


# --------------------------------------------------
# RUN FLASK APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )