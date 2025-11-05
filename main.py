from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__)

GOLF_COURSES = {
    "cedar-ridge": {
        "name": "Cedar Ridge Golf Club",
        "phone": "+13193641111",
        "booking_system": "call_for_details",
        "location": {"city": "Cedar Rapids", "state": "IA", "zip": "52402"},
        "hours": {"open": "06:00", "close": "20:00"},
        "rates": {
            "weekday_18": "$42",
            "weekend_18": "$52",
            "weekday_9": "$24",
            "weekend_9": "$32"
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


def format_time(time_24hr: str) -> str:
    """Convert 'HH:MM' to 'H:MM AM/PM'."""
    hour, minute = map(int, time_24hr.split(':'))
    period = 'AM' if hour < 12 else 'PM'
    display_hour = 12 if hour == 0 or hour == 12 else (hour - 12 if hour > 12 else hour)
    return f"{display_hour}:{minute:02d} {period}"


def generate_demo_times(course: dict, date_str: str):
    """
    Generate a small list of plausible tee times for demo purposes.
    Uses course open/close hours and clusters near the current time.
    """
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    # Parse date_str if you want future/next-day demos; fall back to today on error
    try:
        q_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        q_date = now.date()

    open_hour = int(course["hours"]["open"].split(':')[0])
    close_hour = int(course["hours"]["close"].split(':')[0])

    # Build a window from next upcoming 30-min slot forward
    base_hour = now.hour if q_date == now.date() else open_hour
    start_hour = max(open_hour, base_hour)
    end_hour = min(close_hour, start_hour + 10)

    times = []
    for hour in range(start_hour, end_hour):
        for minute in (0, 10, 20, 30, 40, 50):
            t_24 = f"{hour:02d}:{minute:02d}"
            times.append({
                "time": t_24,
                "display_time": format_time(t_24),
                "available_slots": 4
            })

    # Trim to a handful for the demo
    return times[:12]


@app.route("/get_current_datetime", methods=["POST"])
def get_current_datetime():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return jsonify({
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M"),
        "day_of_week": now.strftime("%A"),
        "display_time": now.strftime("%I:%M %p"),
        "display_date": now.strftime("%B %d, %Y"),
        "timezone": TIMEZONE
    })


@app.route("/check_tee_times", methods=["POST"])
def check_tee_times():
    data = request.get_json(silent=True) or {}
    course_id = data.get("course_id", "cedar-ridge")
    course = GOLF_COURSES.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 400

    # If no date provided, use today in local tz
    tz = pytz.timezone(TIMEZONE)
    date_str = data.get("date") or datetime.now(tz).strftime("%Y-%m-%d")

    available = generate_demo_times(course, date_str)
    if len(available) >= 2:
        msg = f"Next available times are {available[0]['display_time']} and {available[1]['display_time']}"
    elif available:
        msg = f"Next available time is {available[0]['display_time']}"
    else:
        msg = "Let me check with the pro shop."

    return jsonify({
        "date": date_str,
        "available_times": available[:5],
        "message": msg
    })


@app.route("/book_tee_time", methods=["POST"])
def book_tee_time():
    data = request.get_json(silent=True) or {}
    course_id = data.get("course_id", "cedar-ridge")
    course = GOLF_COURSES.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 400

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    confirmation_number = f"{course['name'][:2].upper()}-{now.strftime('%y%m%d%H%M')}"

    return jsonify({
        "success": True,
        "confirmation_number": confirmation_number,
        "date": data.get("date"),
        "time": data.get("time"),
        "display_time": format_time(data.get("time")) if data.get("time") else None,
        "player_name": data.get("player_name"),
        "phone_number": data.get("phone_number"),
        "number_of_players": data.get("number_of_players", 1),
        "course_name": course["name"]
    })


@app.route("/get_course_info", methods=["POST"])
def get_course_info():
    data = request.get_json(silent=True) or {}
    course = GOLF_COURSES.get(data.get("course_id", "cedar-ridge"))
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
    course = GOLF_COURSES.get(data.get("course_id", "cedar-ridge"))
    if not course:
        return jsonify({"error": "Course not found"}), 400

    tz = pytz.timezone(TIMEZONE)
    hour = datetime.now(tz).hour
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


# Local dev runner (Render will use Gunicorn via Procfile)
if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
