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
        "api_credentials": {
            "api_key": "",
            "facility_id": "",
            "username": "",
            "password": ""
        },
        "location": {
            "city": "Cedar Rapids",
            "state": "IA",
            "zip": "52402"
        },
        "hours": {
            "open": "06:00",
            "close": "20:00"
        },
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
            "Restaurant and bar",
            "Golf lessons available"
        ]
    }
}

TIMEZONE = "America/Chicago"

@app.route('/get_current_datetime', methods=['POST'])
def get_current_datetime():
    try:
        data = request.json or {}
        course_id = data.get('course_id', '')
        
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        
        course_name = GOLF_COURSES.get(course_id, {}).get('name', 'Golf Course')
        
        response = {
            'current_date': now.strftime('%Y-%m-%d'),
            'current_time': now.strftime('%H:%M'),
            'day_of_week': now.strftime('%A'),
            'display_time': now.strftime('%I:%M %p'),
            'display_date': now.strftime('%B %d, %Y'),
            'timezone': TIMEZONE
        }
        
        print(f"✓ [{course_name}] Current time: {response['display_time']} on {response['day_of_week']}")
        return jsonify(response)
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/check_tee_times', methods=['POST'])
def check_tee_times():
    try:
        data = request.json or {}
        course_id = data.get('course_id', '')
        course = GOLF_COURSES.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 400
        
        date = data.get('date')
        time_preference = data.get('time_preference', '')
        number_of_players = data.get('number_of_players', 4)
        
        print(f"✓ [{course['name']}] Checking tee times for {date}")
        
        available_times = generate_demo_times(course, date, time_preference)
        
        if not available_times:
            return jsonify({
                'date': date,
                'available_times': [],
                'message': 'No tee times available for that date'
            })
        
        if len(available_times) >= 2:
            message = f"Next available times are {available_times[0]['display_time']} and {available_times[1]['display_time']}"
        elif len(available_times) == 1:
            message = f"We have {available_times[0]['display_time']} available"
        else:
            message = "Let me check with the pro shop"
        
        return jsonify({
            'date': date,
            'available_times': available_times[:5],
            'message': message
        })
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return jsonify({
            'date': date if 'date' in locals() else '',
            'available_times': [],
            'message': 'Having trouble checking availability right now'
        }), 500

@app.route('/book_tee_time', methods=['POST'])
def book_tee_time():
    try:
        data = request.json or {}
        course_id = data.get('course_id', '')
        course = GOLF_COURSES.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 400
        
        date = data.get('date')
        time = data.get('time')
        player_name = data.get('player_name')
        phone_number = data.get('phone_number')
        number_of_players = data.get('number_of_players', 1)
        
        print(f"✓ [{course['name']}] Booking: {player_name}, {number_of_players}p on {date} at {time}")
        
        confirmation_number = f"{course['name'][:2].upper()}-{datetime.now().strftime('%y%m%d%H%M')}"
        display_time = format_time(time)
        
        return jsonify({
            'success': True,
            'confirmation_number': confirmation_number,
            'date': date,
            'time': time,
            'display_time': display_time,
            'player_name': player_name,
            'phone_number': phone_number,
            'number_of_players': number_of_players,
            'course_name': course['name'],
            'message': f'Tee time booked for {player_name}'
        })
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Unable to complete booking'
        }), 500

@app.route('/get_course_info', methods=['POST'])
def get_course_info():
    try:
        data = request.json or {}
        course_id = data.get('course_id', '')
        course = GOLF_COURSES.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 400
        
        print(f"✓ [{course['name']}] Getting course info")
        
        return jsonify({
            'course_name': course['name'],
            'phone': course['phone'],
            'hours': course['hours'],
            'rates': course['rates'],
            'features': course['features'],
            'location': course['location']
        })
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_weather_conditions', methods=['POST'])
def get_weather_conditions():
    try:
        data = request.json or {}
        course_id = data.get('course_id', '')
        course = GOLF_COURSES.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 400
        
        tz = pytz.timezone(TIMEZONE)
        current_hour = datetime.now(tz).hour
        
        if 6 <= current_hour < 12:
            temp = 68
            conditions = "Clear"
        elif 12 <= current_hour < 18:
            temp = 75
            conditions = "Partly Cloudy"
        else:
            temp = 62
            conditions = "Clear"
        
        print(f"✓ [{course['name']}] Weather: {temp}°F, {conditions}")
        
        return jsonify({
            'temperature': temp,
            'conditions': conditions,
            'wind_speed': 8,
            'course_status': 'Open - Excellent Conditions',
            'cart_path_only': False,
            'message': f"It's {temp} degrees with {conditions.lower()} skies. Course is in great shape!"
        })
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_demo_times(course, date, preference=''):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    request_date = datetime.strptime(date, '%Y-%m-%d')
    
    open_hour = int(course['hours']['open'].split(':')[0])
    close_hour = int(course['hours']['close'].split(':')[0])
    
    if preference == 'morning':
        start, end = open_hour, 12
    elif preference == 'afternoon':
        start, end = 12, 17
    elif preference == 'evening':
        start, end = 17, close_hour
    else:
        start = now.hour + 1 if request_date.date() == now.date() else open_hour
        end = close_hour
    
    times = []
    for hour in range(max(start, open_hour), min(end, close_hour)):
        for minute in [0, 10, 20, 30, 40, 50]:
            time_24 = f"{hour:02d}:{minute:02d}"
            times.append({
                'time': time_24,
                'display_time': format_time(time_24),
                'available_slots': 4
            })
    
    return times[:5]

def format_time(time_24hr):
    hour, minute = map(int, time_24hr.split(':'))
    period = 'AM' if hour < 12 else 'PM'
    display_hour = hour if hour <= 12 else hour - 12
    display_hour = 12 if display_hour == 0 else display_hour
    return f"{display_hour}:{minute:02d} {period}"

@app.route('/admin/courses', methods=['GET'])
def list_courses():
    courses = []
    for course_id, course_data in GOLF_COURSES.items():
        courses.append({
            'id': course_id,
            'name': course_data['name'],
            'phone': course_data['phone'],
            'booking_system': course_data['booking_system']
        })
    return jsonify({'courses': courses})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'TeeTalk AI Central Time',
        'timezone': TIMEZONE,
        'courses': len(GOLF_COURSES),
        'timestamp': datetime.now(pytz.timezone(TIMEZONE)).isoformat()
    })

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'TeeTalk AI - Central Time Webhook Server',
        'timezone': TIMEZONE,
        'courses_configured': len(GOLF_COURSES),
        'endpoints': [
            '/get_current_datetime',
            '/check_tee_times',
            '/book_tee_time',
            '/get_course_info',
            '/get_weather_conditions',
            '/admin/courses',
            '/health'
        ],
        'status': 'active'
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
```

6. Scroll down and click **"Commit changes"**

Render will automatically redeploy with the clean code!

---

**Wait 2 minutes, then test:**
```
https://teetalk-webhook.onrender.com/health
