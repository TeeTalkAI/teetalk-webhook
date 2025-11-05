from flask import Flask, request, jsonify
from datetime import datetime, date, time as dtime
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

def filter_past_if_today(slots, target_date: date, now_dt: datetime):
    if target_date != now_dt.date():
        return slots
    now_t = now_dt.time()
    return [s for s in slots if parse_hhmm(s["time"]) and parse_hhmm(s["time"]) > now_t]

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
def get_current_datetime():
    now = tz_now()
    return jsonify({
        "current_date":  now.strftime("%Y-%m-%d"),
        "current_time":  now.strftime("%H:%M"),
        "day_of_week":   now.strftime("%A"),
        "display_time":  now.strftime("%I:%M %p").lstrip("0"),
        "display_date":  now.strftime("%B %d, %Y"),
        "timezone":      TIMEZONE
    })

@app.route("/check_tee_times", methods=["POST"])
def check_tee_times():
    data = request.get_json(silent=True) or {}
    course_id = data.get("course_id", "cedar-ridge")
    course = GOLF_COURSES.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 400

    now = tz_now()
    date_str = data.get("date") or now.strftime("%Y-%m-%d")
    target = parse_ymd(date_str)
    if not target:
        return jsonify({"error": "Invalid date format (use YYYY-MM-DD)"}), 400

    all_slots = next_slots_for_date(course, target)
    available = filter_past_if_today(all_slots, target, now)

    message = "Let me check with the pro shop."
    if len(available) >= 2:
        message = f"Next available times are {available[0]['display_time']} and {available[1]['display_time']}"

    return jsonify({
        "date": date_str,
        "available_times": available[:5],
        "message": message
    })

@app.route("/book_tee_time", methods=["POST"])
def book_tee_time():
    data = request.get_json(silent=True) or {}
    course_id = data.get("course_id", "")
    course = GOLF_COURSES.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 400

    # Required fields
    date_str = data.get("date")
    time_str = data.get("time")
    player_name = data.get("player_name")
    phone_number = data.get("phone_number")
    num_players = int(data.get("number_of_players", 1))

    if not all([date_str, time_str, player_name, phone_number]):
        return jsonify({"error": "Missing required booking fields"}), 400

    target_date = parse_ymd(date_str)
    target_time = parse_hhmm(time_str)
    if not target_date or not target_time:
        return jsonify({"error": "Invalid date/time format"}), 400

    now = tz_now()
    # Block booking in the past (today)
    if target_date == now.date() and target_time <= now.time():
        return jsonify({"error": "Requested time has already passed"}), 400
    # Optional: block booking for any past date
    if target_date < now.date():
        return jsonify({"error": "Requested date has already passed"}), 400
    # Ensure within hours
    if not within_hours(course, target_time):
        return jsonify({"error": "Requested time is outside of course hours"}), 400
    # Ensure valid step
    if target_time.minute not in STEP_MINUTES:
        return jsonify({"error": "Please choose a time on a 10-minute step"}), 400

    confirmation_number = f"{course['name'][:2].upper()}-{now.strftime('%y%m%d%H%M')}"
    return jsonify({
        "success": True,
        "confirmation_number": confirmation_number,
        "date": date_str,
        "time": time_str,
        "display_time": format_time(time_str),
        "display_date": display_date(date_str),
        "player_name": player_name,
        "phone_number": phone_number,
        "number_of_players": num_players,
        "course_name": course["name"]
    })

@app.route("/get_course_info", methods=["POST"])
def get_course_info():
    data = request.get_json(silent=True) or {}
    course = GOLF_COURSES.get(data.get("course_id", ""))
    if not course:
        return jsonify({"error": "Course not found"}), 400
    return jsonify({
        "course_name": course["name"],
        "phone": course["phone"],
        "hours": course["hours"],
        "rates": course["rates"],
        "features": course["features"],
        "location": course["location"]
    })

@app.route("/get_weather_conditions", methods=["POST"])
def get_weather_conditions():
    data = request.get_json(silent=True) or {}
    course = GOLF_COURSES.get(data.get("course_id", ""))
    if not course:
        return jsonify({"error": "Course not found"}), 400

    now = tz_now()
    hour = now.hour
    temp = 68 if 6 <= hour < 12 else 75 if 12 <= hour < 18 else 62
    conditions = "Clear" if hour < 12 or hour >= 18 else "Partly Cloudy"

    return jsonify({
        "temperature": temp,
        "conditions": conditions,
        "wind_speed": 8,
        "course_status": "Open - Excellent Conditions",
        "cart_path_only": False,
        "message": f"It's {temp} degrees with {conditions.lower()} skies. Course is in great shape!"
    })

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "TeeTalk AI Central Time",
        "timezone": TIMEZONE,
        "courses": len(GOLF_COURSES)
    })

@app.route("/", methods=["GET"])
def root():
    return jsonify({"service": "TeeTalk AI", "status": "active"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
