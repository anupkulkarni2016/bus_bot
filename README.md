# 🚌 Bus Commute Planner

A Python automation project that reads my work shift schedule, fetches real-time bus routes from the **Google Maps API**, and emails me a full travel plan every evening.

## 🚀 Features
- Reads shifts from a simple **CSV file** (`date,start_time,location`)
- Fetches real-time **bus routes** with Google Maps Directions API
- Calculates **"Leave Home By"** time
- Generates step-by-step commute instructions
- Adds a **Google Maps clickable link** for one-tap navigation
- Sends the plan via **email** (SMTP)
- Automates daily runs with **Windows Task Scheduler**

## 🛠️ Tech Stack
- **Python 3.10+**
- **Google Maps API** (`googlemaps` library)
- **pandas** for CSV handling
- **dotenv** for environment configuration
- **smtplib** for email notifications
- **tzdata / zoneinfo** for timezone handling

## ⚙️ Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/bus-commute-planner.git
   cd bus-commute-planner
Create a virtual environment:

bash
Copy code
python -m venv venv
venv\Scripts\activate
Install dependencies:

bash
Copy code
pip install -r requirements.txt
Create a .env file with your details:

ini
Copy code
GOOGLE_MAPS_API_KEY=your_api_key_here
HOME_ADDRESS="Your Home Address"
DEFAULT_WORK_ADDRESS="Default Work Address"
BUFFER_MINUTES=10

EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
EMAIL_TO=recipient_email@gmail.com
Add your shift schedule in shifts.csv:

csv
Copy code
date,start_time,location
2025-08-28,09:00,DEFAULT
2025-08-29,10:00,123 Oxford Street, London, UK
▶️ Usage
Run for tomorrow:

bash
Copy code
python bus_bot.py
Run for a specific date:

bash
Copy code
python bus_bot.py 2025-08-28
Output is saved in:

tomorrow_bus_plan.txt (text file)

Console (printed)

Email (if enabled)

📅 Automation
Add a Windows Task Scheduler job to run:

bat
Copy code
run_bus_bot.bat
every evening (e.g. 8:00 PM).
