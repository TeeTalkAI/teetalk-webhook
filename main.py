from flask import Flask, request, jsonify
from datetime import datetime, date, time as dtime, timedelta
import pytz
import os

app = Flask(__name__)

# --------------------------
# Demo data
# --------------------------
GOLF_COURSES = {
    "cedar-ridge": {
        "name": "Cedar Ridge Golf Club",
        "phone": "+13193641111",
        "booking_system": "call_for_details",
        "location": {"city": "Cedar Rapids", "state": "IA", "zip": "52402"},
        "hours": {"open": "06:00", "close": "20:00"},  # 24h HH:MM
        "rates": {
            "weekday_18": "$42",
            "weekend_18": "$52",
            "weekday_9":  "$24",
            "weekend_9":  "$32"
        },
        "features": [
            "18-hole championship course",
            "Full driving range",
            "Pro shop",
            "Restaurant and bar"
        ]
    }
}

TIMEZONE = "America/Chicago"
STEP_MINUTES = [0, 10, 20, 30, 40, 50]  # demo slot increments

# --------------------------
# Helpers
# --------------------------
def tz_now():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)

def parse_ymd(ymd_str):
    try:
        y, m, d = map(int, ymd_str.split("-"))
        return date(y, m, d)
    except Exception:
        return None

def parse_hhmm(hhmm_str):
    try:
        h, m = map(int, hhmm_str.split(":"))
        return dtime(hour=h, minute=m)
    except Exception:
        return None

def within_hours(course, t: dtime):
    open_t = parse_hhmm(course["hours"]["open"])
    close_t = parse_hhmm(course["hours"]["close"])
    if not open_t or not close_t:
        return True
    return open_t <= t <= close_t

def next_slots_for_date(course, target_date: date):
    open_t = parse_hhmm(course["hours"]["open"]) or dtime(6, 0)
    close_t = parse_hhmm(course["hours"]["close"]) or dtime(20, 0)
    slots = []
    for hour in range(open_t.hour, close_t.hour + 1):
        for minute in STEP_MINUTES:
            candidate = dtime(hour=hour, minute=minute)
            if candidate < open_t or candidate > close_t:
                continue
            slots.append({
                "time": candidate.strftime("%H:%M"),
                "display_time": format_time(candidate.strftime("%H:%M")),
                "available_slots": 4
            })
    return slots

def format_time(time_24hr):
    h, m = map(int, time_24hr.split(":"))
    period = "AM" if h < 12 else "PM"
    display_hour = 12 if h == 0 else (h if h <= 12 else h - 12)
    return f"{display_hour}:{m:02d} {period}"

def display_date(ymd_str):
    try:
        y, m, d = map(int, ymd_str.split("-"))
        return date(y, m, d).strftime("%B %d, %Y")
    except Exception:
        return ymd_str

# --------------------------
# Routes
# --------------------------
@app.route("/get_current_datetime", methods=["POST"])
def get_c
