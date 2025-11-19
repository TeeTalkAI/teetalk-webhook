from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz
import os
import re

app = Flask(__name__)

# -------------------------------
# Config / Mock Data
# -------------------------------
TIMEZONE = "America/Chicago"
TZ = pytz.timezone(TIMEZONE)

GOLF_COURSES = {
    "cedar-ridge": {
        "name": "Cedar Ridge Golf Club",
        "phone": "+13193641111",
        "booking_system": "call_for_details",
        "location": {"city": "Cedar Rapids", "state": "IA", "zip": "52402"},
        "hours": {"open": "06:00", "close": "20:00"},  # 24h format
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

# -------------------------------
# Helpers
# -------------------------------
def now_local():
    return datetime.now(TZ)

def parse_hhmm(hhmm: str):
    h, m = map(int, hhmm.split(":"))
    return h, m

def hhmm_to_minutes(hhmm: str) -> int:
    h, m = parse_hhmm(hhmm)
    return h * 60 + m

def minutes_to_hhmm(total: int) -> str:
    h = total // 60
    m = total % 60
    return f"{h:02d}:{m:02d}"

def format_time_12h(time_24hr: str) -> str:
    hour, minute = map(int, time_24hr.split(":"))
    period = "AM" if hour < 12 else "PM"
    display_hour = 12 if hour % 12 == 0 else hour % 12
    return f"{display_hour}:{minute:02d} {period}"

def is_today(date_str: str) -> bool:
    today = now_local().strftime("%Y-%m-%d")
    return date_str == today

def clamp_start_to_next_slot(current_minutes: int, slot_minutes: int = 10) -> int:
    # e.g., if now is 11:21 → next slot 11:30 (round up to next 10-min multiple)
    remainder = current_minutes % slot_minutes
    return current_minutes if remainder == 0 else current_minutes + (slot_minutes - remainder)

def validate_course(course_id: str):
    course = GOLF_COURSES.get(course_id)
    if not course:
        return None, {"error": "Course not found"}, 400
    return course, None, None

# -------------------------------
# Core generators
# -------------------------------
def generate_demo_times(course: dict, date: str):
    """
    Generates on-interval (10-min) tee-times between course opening and last tee time.
    If date is today, excludes times earlier than 'now' (rounded up to next slot).
    Returns a list of {time: 'HH:MM', display_time: 'H:MM AM/PM', available_slots: 4}
    """
    open_min = hhmm_to_minutes(course["hours"]["open"])
    close_min = hhmm_to_minutes(course["hours"]["close"])
    slot = 10
    
    # Last tee time is 4:00 PM (16:00 = 960 minutes)
    last_tee_time = 16 * 60  # 4:00 PM in minutes
    
    start_min = open_min
    if is_today(date):
        now = now_local()
        now_minutes = now.hour * 60 + now.minute
        start_min = max(open_min, clamp_start_to_next_slot(now_minutes, slot))

    # Don't generate past last tee time
    if start_min >= last_tee_time:
        return []

    times = []
    t = start_min

    while t <= last_tee_time:  # Changed to <= so 4:00 PM is included
        hhmm = minutes_to_hhmm(t)
        times.append({
            "time": hhmm,
            "display_time": format_time_12h(hhmm),
            "available_slots": 4
        })
        t += slot

    return times

# -------------------------------
# Routes
# -------------------------------
@app.route("/get_current_datetime", methods=["POST"])
def get_current_datetime():
    # Retell sends: {"call": {...}, "name": "get_current_datetime", "args": {...}}
    data = request.get_json(silent=True) or {}
    args = data.get("args", data)  # Support both Retell format and direct calls
    
    now = now_local()
    return jsonify({
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M"),
        "day_of_week": now.strftime("%A"),
        "display_time": now.strftime("%I:%M %p").lstrip("0"),
        "display_date": now.strftime("%B %d, %Y"),
        "timezone": TIMEZONE
    })

@app.route("/check_tee_times", methods=["POST"])
def check_tee_times():
    # Retell sends: {"call": {...}, "name": "check_tee_times", "args": {...}}
    data = request.get_json(silent=True) or {}
    args = data.get("args", data)  # Support both Retell format and direct calls
    
    course_id = args.get("course_id", "cedar-ridge")
    course, err_dict, err_code = validate_course(course_id)
    if err_dict:
        return jsonify(err_dict), err_code

    # date default = today
    date = args.get("date")
    if not date:
        date = now_local().strftime("%Y-%m-%d")

    slots = generate_demo_times(course, date)
    if len(slots) >= 2:
        msg = f"Next available times are {slots[0]['display_time']} and {slots[1]['display_time']}."
    elif len(slots) == 1:
        msg = f"Next available time is {slots[0]['display_time']}."
    else:
        # If no slots remain today, offer tomorrow's daybreak
        tomorrow = (now_local() + timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_slots = generate_demo_times(course, tomorrow)
        if tomorrow_slots:
            msg = f"No more times today. Earliest tomorrow is {tomorrow_slots[0]['display_time']}."
        else:
            msg = "No available times right now. Please try again later."

    return jsonify({
        "course_id": course_id,
        "date": date,
        "available_times": slots[:5],
        "message": msg
    })

@app.route("/book_tee_time", methods=["POST"])
def book_tee_time():
    # Retell sends: {"call": {...}, "name": "book_tee_time", "args": {...}}
    data = request.get_json(silent=True) or {}
    args = data.get("args", data)  # Support both Retell format and direct calls
    
    print("=" * 50)
    print("BOOKING REQUEST RECEIVED")
    print(f"Full data: {data}")
    print(f"Args extracted: {args}")
    print("=" * 50)

    course_id = args.get("course_id", "")
    course, err_dict, err_code = validate_course(course_id)
    if err_dict:
        print(f"ERROR: Course validation failed - {err_dict}")
        return jsonify(err_dict), err_code

    date = args.get("date")
    time_24 = args.get("time")
    player_name = args.get("player_name")
    phone_number = args.get("phone_number") or args.get("phone")  # Support both field names
    num_players_raw = args.get("number_of_players") or args.get("num_players", 1)
    
    try:
        number_of_players = int(num_players_raw)
    except (ValueError, TypeError):
        number_of_players = 1

    # Basic validations
    if not date or not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        print(f"ERROR: Invalid date format: {date}")
        return jsonify({"error": f"Invalid or missing 'date' (expected YYYY-MM-DD, got {date})"}), 400
    if not time_24 or not re.match(r"^\d{2}:\d{2}$", time_24):
        print(f"ERROR: Invalid time format: {time_24}")
        return jsonify({"error": f"Invalid or missing 'time' (expected HH:MM 24h, got {time_24})"}), 400
    if not player_name:
        print(f"ERROR: Missing player_name")
        return jsonify({"error": "Missing player_name"}), 400
    if not phone_number:
        print(f"ERROR: Missing phone_number")
        return jsonify({"error": "Missing phone_number"}), 400
    if number_of_players < 1 or number_of_players > 4:
        print(f"ERROR: Invalid number_of_players: {number_of_players}")
        return jsonify({"error": "number_of_players must be between 1 and 4"}), 400

    # Time window checks (no past bookings today, honor open/close)
    req_min = hhmm_to_minutes(time_24)
    open_min = hhmm_to_minutes(course["hours"]["open"])
    close_min = hhmm_to_minutes(course["hours"]["close"])

    if req_min < open_min or req_min >= close_min:
        print(f"ERROR: Time outside operating hours")
        return jsonify({"error": "Requested time is outside operating hours"}), 400

    if is_today(date):
        now = now_local()
        now_min = now.hour * 60 + now.minute
        # round now up to next 10-min slot for fairness
        now_min_rounded = clamp_start_to_next_slot(now_min, 10)
        if req_min < now_min_rounded:
            print(f"ERROR: Requested time has passed")
            return jsonify({"error": "Requested time has already passed"}), 400

    # Fake confirmation number
    confirmation_number = f"{course['name'][:2].upper()}-{now_local().strftime('%y%m%d%H%M')}"

    print(f"SUCCESS: Booking confirmed - {confirmation_number}")
    
    return jsonify({
        "success": True,
        "confirmation_number": confirmation_number,
        "date": date,
        "time": time_24,
        "display_time": format_time_12h(time_24),
        "player_name": player_name,
        "phone_number": phone_number,
        "number_of_players": number_of_players,
        "course_name": course["name"]
    })

@app.route("/get_course_info", methods=["POST"])
def get_course_info():
    # Retell sends: {"call": {...}, "name": "get_course_info", "args": {...}}
    data = request.get_json(silent=True) or {}
    args = data.get("args", data)  # Support both Retell format and direct calls
    
    course_id = args.get("course_id", "")
    course, err_dict, err_code = validate_course(course_id)
    if err_dict:
        return jsonify(err_dict), err_code

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
    # Retell sends: {"call": {...}, "name": "get_weather_conditions", "args": {...}}
    data = request.get_json(silent=True) or {}
    args = data.get("args", data)  # Support both Retell format and direct calls
    
    course_id = args.get("course_id", "")
    course, err_dict, err_code = validate_course(course_id)
    if err_dict:
        return jsonify(err_dict), err_code

    hour = now_local().hour
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

@app.get("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "TeeTalk AI Central Time",
        "timezone": TIMEZONE,
        "courses": len(GOLF_COURSES)
    })

@app.get("/")
def root():
    return jsonify({"service": "TeeTalk AI", "status": "active"})

if __name__ == "__main__":
    # Render launches via gunicorn, but this lets you run locally too.
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=True)
