from flask import Flask, request, jsonify
from datetime import datetime
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
        "rates": {"weekday_18": "$42", "weekend_18": "$52", "weekday_9": "$24", "weekend_9": "$32"},
        "features": ["18-hole championship course", "Full driving range", "Pro shop", "Restaurant and bar"]
    }
}

TIMEZONE = "America/Chicago"

@app.route('/get_current_datetime', methods=['POST'])
def get_current_datetime():
    data = request.json or {}
    course_id = data.get('course_id', '')
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return jsonify({
        'current_date': now.strftime('%Y-%m-%d'),
        'current_time': now.strftime('%H:%M'),
        'day_of_week': now.strftime('%A'),
        'display_time': now.strftime('%I:%M %p'),
        'display_date': now.strftime('%B %d, %Y'),
        'timezone': TIMEZONE
    })

@app.route('/check_tee_times', methods=['POST'])
def check_tee_times():
    data = request.json or {}
    course_id = data.get('course_id', '')
    course = GOLF_COURSES.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 400
    date = data.get('date')
    available_times = generate_demo_times(course, date)
    message = f"Next available times are {available_times[0]['display_time']} and {available_times[1]['display_time']}" if len(available_times) >= 2 else "Let me check with the pro shop"
    return jsonify({'date': date, 'available_times': available_times[:5], 'message': message})

@app.route('/book_tee_time', methods=['POST'])
def book_tee_time():
    data = request.json or {}
    course_id = data.get('course_id', '')
    course = GOLF_COURSES.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 400
    confirmation_number = f"{course['name'][:2].upper()}-{datetime.now().strftime('%y%m%d%H%M')}"
    return jsonify({
        'success': True,
        'confirmation_number': confirmation_number,
        'date': data.get('date'),
        'time': data.get('time'),
        'display_time': format_time(data.get('time')),
        'player_name': data.get('player_name'),
        'phone_number': data.get('phone_number'),
        'number_of_players': data.get('number_of_players', 1),
        'course_name': course['name']
    })

@app.route('/get_course_info', methods=['POST'])
def get_course_info():
    data = request.json or {}
    course = GOLF_COURSES.get(data.get('course_id', ''))
    if not course:
        return jsonify({'error': 'Course not found'}), 400
    return jsonify({
        'course_name': course['name'],
        'phone': course['phone'],
        'hours': course['hours'],
        'rates': course['rates'],
        'features': course['features'],
        'location': course['location']
    })

@app.route('/get_weather_conditions', methods=['POST'])
def get_weather_conditions():
    data = request.json or {}
    course = GOLF_COURSES.get(data.get('course_id', ''))
    if not course:
        return jsonify({'error': 'Course not found'}), 400
    tz = pytz.timezone(TIMEZONE)
    hour = datetime.now(tz).hour
    temp = 68 if 6 <= hour < 12 else 75 if 12 <= hour < 18 else 62
    conditions = "Clear" if hour < 12 or hour >= 18 else "Partly Cloudy"
    return jsonify({
        'temperature': temp,
        'conditions': conditions,
        'wind_speed': 8,
        'course_status': 'Open - Excellent Conditions',
        'cart_path_only': False,
        'message': f"It's {temp} degrees with {conditions.lower()} skies. Course is in great shape!"
    })

def generate_demo_times(course, date):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    open_hour = int(course['hours']['open'].split(':')[0])
    close_hour = int(course['hours']['close'].split(':')[0])
    times = []
    for hour in range(open_hour, min(close_hour, now.hour + 10)):
        for minute in [0, 10, 20, 30, 40, 50]:
            times.append({'time': f"{hour:02d}:{minute:02d}", 'display_time': format_time(f"{hour:02d}:{minute:02d}"), 'available_slots': 4})
    return times[:5]

def format_time(time_24hr):
    hour, minute = map(int, time_24hr.split(':'))
    period = 'AM' if hour < 12 else 'PM'
    display_hour = 12 if hour == 0 else hour if hour <= 12 else hour - 12
    return f"{display_hour}:{minute:02d} {period}"

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'TeeTalk AI Central Time', 'timezone': TIMEZONE, 'courses': len(GOLF_COURSES)})

@app.route('/', methods=['GET'])
def root():
    return jsonify({'service': 'TeeTalk AI', 'status': 'active'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
