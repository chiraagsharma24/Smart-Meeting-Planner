import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Set up logging to help debug production issues
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
CORS(app)

# Store user data and bookings in memory since we don't need persistence
users_data = {}
bookings = []

# Business hours in IST - adjust these if your team works different hours
WORK_START = "09:00"
WORK_END = "18:00"

def parse_time(time_str):
    """Handles both ISO-8601 and HH:MM time formats, converting to minutes since midnight.
    This makes it easier to do time arithmetic and comparisons."""
    try:
        # Strip timezone and date info from ISO format if present
        if 'T' in time_str:
            time_str = time_str.split('T')[1].split('.')[0].split('+')[0].split('Z')[0]
        
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    except (ValueError, IndexError) as e:
        logging.error(f"Error parsing time '{time_str}': {e}")
        raise ValueError(f"Invalid time format: {time_str}")

def minutes_to_time(minutes):
    """Converts minutes since midnight back to HH:MM format for API responses"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def get_busy_intervals_for_all_users():
    """Aggregates all busy intervals across users and existing bookings.
    Used to find truly free time slots that work for everyone."""
    all_busy = []
    
    # Include both user-defined busy times and existing bookings
    for user_id, user_data in users_data.items():
        for interval in user_data.get('busy', []):
            start_minutes = parse_time(interval[0])
            end_minutes = parse_time(interval[1])
            all_busy.append((start_minutes, end_minutes))
    
    for booking in bookings:
        start_minutes = parse_time(booking['start'])
        end_minutes = parse_time(booking['end'])
        all_busy.append((start_minutes, end_minutes))
    
    return all_busy

def merge_overlapping_intervals(intervals):
    """Merges overlapping time intervals to simplify availability calculation.
    For example, [(9:00, 10:00), (9:30, 10:30)] becomes [(9:00, 10:30)]"""
    if not intervals:
        return []
    
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    
    for current in intervals[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    
    return merged

def find_free_windows(duration_minutes):
    """Finds available time slots that work for everyone.
    Returns up to 3 slots to avoid overwhelming the user with options."""
    work_start_minutes = parse_time(WORK_START)
    work_end_minutes = parse_time(WORK_END)
    
    busy_intervals = get_busy_intervals_for_all_users()
    merged_busy = merge_overlapping_intervals(busy_intervals)
    
    free_windows = []
    current_time = work_start_minutes
    
    # Find gaps between busy periods
    for busy_start, busy_end in merged_busy:
        if current_time < busy_start:
            gap_duration = busy_start - current_time
            if gap_duration >= duration_minutes:
                free_windows.append((current_time, busy_start))
        current_time = max(current_time, busy_end)
    
    # Check for available time after the last busy period
    if current_time < work_end_minutes:
        gap_duration = work_end_minutes - current_time
        if gap_duration >= duration_minutes:
            free_windows.append((current_time, work_end_minutes))
    
    # Split free windows into slots of the requested duration
    available_slots = []
    for start, end in free_windows:
        slot_start = start
        while slot_start + duration_minutes <= end:
            slot_end = slot_start + duration_minutes
            available_slots.append([minutes_to_time(slot_start), minutes_to_time(slot_end)])
            slot_start += duration_minutes
            if len(available_slots) >= 3:  # Limit to 3 slots for better UX
                break
        if len(available_slots) >= 3:
            break
    
    return available_slots[:3]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/slots', methods=['POST'])
def set_slots():
    """Accepts and validates user busy intervals.
    Expects a list of users, each with an ID and list of busy time ranges."""
    try:
        data = request.get_json()
        if not data or 'users' not in data:
            return jsonify({'error': 'Invalid JSON format. Expected "users" field.'}), 400
        
        users = data['users']
        if not isinstance(users, list):
            return jsonify({'error': 'Users must be a list'}), 400
        
        users_data.clear()
        
        for user in users:
            if 'id' not in user:
                return jsonify({'error': 'Each user must have an "id" field'}), 400
            
            user_id = user['id']
            busy_intervals = user.get('busy', [])
            
            processed_busy = []
            for interval in busy_intervals:
                if not isinstance(interval, list) or len(interval) != 2:
                    return jsonify({'error': f'Invalid busy interval format for user {user_id}'}), 400
                
                try:
                    start_time = interval[0]
                    end_time = interval[1]
                    parse_time(start_time)
                    parse_time(end_time)
                    processed_busy.append([start_time, end_time])
                except ValueError as e:
                    return jsonify({'error': f'Invalid time format for user {user_id}: {str(e)}'}), 400
            
            users_data[user_id] = {
                'busy': processed_busy
            }
        
        logging.info(f"Stored data for {len(users_data)} users")
        return jsonify({'message': f'Successfully stored busy intervals for {len(users_data)} users'}), 200
        
    except Exception as e:
        logging.error(f"Error in set_slots: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/suggest', methods=['GET'])
def suggest_meeting_times():
    """Suggests available meeting times based on everyone's busy slots.
    Duration parameter determines how long each suggested slot should be."""
    try:
        duration = request.args.get('duration', '30')
        try:
            duration_minutes = int(duration)
            if duration_minutes <= 0:
                return jsonify({'error': 'Duration must be a positive integer'}), 400
        except ValueError:
            return jsonify({'error': 'Duration must be a valid integer'}), 400
        
        if not users_data:
            return jsonify({'error': 'No user data available. Please post to /slots first.'}), 400
        
        available_slots = find_free_windows(duration_minutes)
        
        if not available_slots:
            return jsonify([]), 200
        
        logging.info(f"Found {len(available_slots)} available slots for {duration_minutes} minutes")
        return jsonify(available_slots), 200
        
    except Exception as e:
        logging.error(f"Error in suggest_meeting_times: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/calendar/<int:user_id>', methods=['GET'])
def get_user_calendar(user_id):
    """Returns a user's calendar showing both their busy slots and booked meetings.
    Useful for displaying a complete view of someone's schedule."""
    try:
        if user_id not in users_data:
            return jsonify({'error': f'User {user_id} not found'}), 404
        
        user_data = users_data[user_id]
        
        calendar_data = {
            'user_id': user_id,
            'busy_slots': user_data.get('busy', []),
            'booked_meetings': []
        }
        
        for booking in bookings:
            calendar_data['booked_meetings'].append({
                'start': booking['start'],
                'end': booking['end'],
                'meeting_id': booking.get('id', 'unknown')
            })
        
        return jsonify(calendar_data), 200
        
    except Exception as e:
        logging.error(f"Error in get_user_calendar: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/book', methods=['POST'])
def book_meeting():
    """Books a meeting slot. Note: This is a simple implementation that doesn't
    check for conflicts - in a real app, you'd want to validate the slot is still free."""
    try:
        data = request.get_json()
        if not data or 'start' not in data or 'end' not in data:
            return jsonify({'error': 'Missing start or end time'}), 400
        
        start_time = data['start']
        end_time = data['end']
        
        try:
            parse_time(start_time)
            parse_time(end_time)
        except ValueError as e:
            return jsonify({'error': f'Invalid time format: {str(e)}'}), 400
        
        booking_id = len(bookings) + 1
        booking = {
            'id': booking_id,
            'start': start_time,
            'end': end_time
        }
        
        bookings.append(booking)
        
        logging.info(f"Booked meeting from {start_time} to {end_time}")
        return jsonify({'message': 'Meeting booked successfully', 'booking': booking}), 200
        
    except Exception as e:
        logging.error(f"Error in book_meeting: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/reset', methods=['POST'])
def reset_data():
    """Clears all stored data. Useful for testing and development."""
    users_data.clear()
    bookings.clear()
    return jsonify({'message': 'All data cleared'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
