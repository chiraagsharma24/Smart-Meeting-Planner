# Smart Meeting Planner

A Flask-based meeting scheduler that finds optimal meeting times by analyzing users' busy intervals and suggesting available windows.

## Video Demo
Watch the application in action: [Smart Meeting Planner Demo](https://drive.google.com/drive/folders/1hTr07PDYqnLjMkttlTi6A94rNeAMKA89?usp=sharing)

## Features

- **POST /slots**: Accept JSON list of users with their busy intervals
- **GET /suggest**: Return first three available time windows for a given meeting duration
- **GET /calendar/:userId**: Show individual user's busy slots and booked meetings
- **Web Interface**: Simple HTML interface to test all functionality
- **In-memory Storage**: No database required, uses Python dictionaries
- **Time Format Support**: Handles both ISO-8601 and HH:MM time formats
- **Working Hours**: Constrains suggestions to 09:00-18:00 IST
- **Booking Feature**: Optional ability to book suggested time slots

## API Endpoints

### POST /slots
```json
{
  "users": [
    { "id": 1, "busy": [["09:00","10:30"], ["13:00","14:00"]] },
    { "id": 2, "busy": [["11:00","12:00"], ["15:00","16:00"]] }
  ]
}
```

### GET /suggest?duration=30
Returns:
```json
[["10:30","11:00"], ["12:00","13:00"], ["14:00","15:00"]]
```

## Local Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd smart-meeting-planner
```
2. Install dependencies:
```bash
# Make sure you're in the project directory
pip install flask flask-cors python-dateutil
```
3. Start the Flask server:
```bash
python app.py
```

4. Open your web browser and navigate to:
```
http://localhost:5000
```


## Project Reflection

### AI Usage in Development
During the development of this project, I primarily used Cursor IDE for initial HTML structure generation and basic code scaffolding. This helped me get started quickly with the frontend layout. However, I wrote all the Python backend logic, API endpoints, and time slot calculation algorithms myself. I found that while AI tools were helpful for boilerplate code, the core business logic and complex time-slot calculations required careful manual implementation to ensure accuracy and efficiency.

### Future Improvements
Given two more days, I would focus on adding these exciting features:

First, I'd add a calendar integration feature that lets users sync their Google calendars. This would make it super easy for users to automatically block their busy slots instead of manually entering them.

Next, I'd implement a meeting preferences system where users can set their preferred meeting times and durations. For example, someone might prefer morning meetings or have a maximum meeting duration they're comfortable with.

I'd also add a recurring meetings feature. Right now, users can only schedule one-time meetings, but it would be really useful to set up weekly team syncs or monthly reviews that automatically find the best recurring time slot.

Finally, I'd add a meeting room booking system. When suggesting time slots, the app would also check room availability and include that in the suggestions. This would be especially helpful for hybrid teams who need both virtual and physical meeting spaces.

These features would make the app much more practical for real-world team collaboration and scheduling needs.