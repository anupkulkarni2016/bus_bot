import os
import sys
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # pip install tzdata on Windows
from urllib.parse import quote_plus

import pandas as pd
import googlemaps
from dotenv import load_dotenv
from email.mime.text import MIMEText
import smtplib

# -------------------- Config & Logging --------------------

LONDON_TZ = ZoneInfo("Europe/London")

logging.basicConfig(
    filename="bus_bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def load_config():
    load_dotenv()
    cfg = {
        "api_key": os.getenv("GOOGLE_MAPS_API_KEY", "").strip(),
        "home": os.getenv("HOME_ADDRESS", "").strip(),
        "default_work": os.getenv("DEFAULT_WORK_ADDRESS", "").strip(),
        "buffer": int(os.getenv("BUFFER_MINUTES", "10")),
        "email_enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
        "smtp_server": os.getenv("SMTP_SERVER", "").strip(),
        "smtp_port": int(os.getenv("SMTP_PORT", "465")),
        "smtp_user": os.getenv("SMTP_USER", "").strip(),
        "smtp_pass": os.getenv("SMTP_PASS", "").strip(),
        "email_to": os.getenv("EMAIL_TO", "").strip(),
    }
    if not cfg["api_key"] or not cfg["home"] or not cfg["default_work"]:
        print("Config error: Ensure GOOGLE_MAPS_API_KEY, HOME_ADDRESS, DEFAULT_WORK_ADDRESS are set in .env")
        sys.exit(1)
    return cfg

# -------------------- Shift Loading --------------------

def load_shifts_for_date(csv_path: str, target_date, tz=LONDON_TZ):
    if not os.path.exists(csv_path):
        print(f"Missing {csv_path}. Create it with headers: date,start_time,location")
        sys.exit(1)
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    shifts = df[df["date"] == target_date].copy()
    return shifts

def load_tomorrows_shifts(csv_path: str, tz=LONDON_TZ):
    tomorrow = (datetime.now(tz).date() + timedelta(days=1))
    return load_shifts_for_date(csv_path, tomorrow, tz), tomorrow

# -------------------- Routing Helpers --------------------

def build_arrival_dt(date_obj, time_str, tz=LONDON_TZ, buffer_min=10):
    # time_str: "HH:MM"
    hh, mm = map(int, time_str.split(":"))
    shift_start = datetime(date_obj.year, date_obj.month, date_obj.day, hh, mm, tzinfo=tz)
    arrive_by = shift_start - timedelta(minutes=buffer_min)
    return arrive_by, shift_start

def fetch_bus_route(gmaps_client, origin, destination, arrival_dt):
    """Try bus-only first; if none, fall back to mixed transit."""
    try:
        routes = gmaps_client.directions(
            origin,
            destination,
            mode="transit",
            transit_mode="bus",
            arrival_time=int(arrival_dt.timestamp()),
            alternatives=False
        )
        if routes:
            return routes[0], "bus_only"
        routes = gmaps_client.directions(
            origin,
            destination,
            mode="transit",
            arrival_time=int(arrival_dt.timestamp()),
            alternatives=False
        )
        if routes:
            return routes[0], "mixed_transit"
        return None, "no_route"
    except Exception as e:
        logging.exception("Directions API error")
        return None, "error"

def format_route(route):
    leg = route["legs"][0]
    lines = []
    arrive_txt = leg.get("arrival_time", {}).get("text", "—")
    lines.append(f"Total: {leg['duration']['text']} (arrive {arrive_txt})")
    for step in leg["steps"]:
        mode = step["travel_mode"]
        if mode == "WALKING":
            lines.append(f"Walk: {step['duration']['text']}")
        elif mode == "TRANSIT":
            td = step.get("transit_details", {})
            line = td.get("line", {})
            vehicle = line.get("vehicle", {}).get("type", "TRANSIT")
            bus_no = line.get("short_name") or line.get("name", "Transit")
            dep_stop = td.get("departure_stop", {}).get("name", "?")
            arr_stop = td.get("arrival_stop", {}).get("name", "?")
            dep_time = td.get("departure_time", {}).get("text", "?")
            arr_time = td.get("arrival_time", {}).get("text", "?")
            lines.append(f"{vehicle} {bus_no}: {dep_stop} {dep_time} → {arr_stop} {arr_time}")
    return "\n".join(lines)

def compute_leave_by(route):
    """Compute 'leave home by' as first transit departure minus initial walk."""
    leg = route["legs"][0]
    first_dep_epoch = None
    walk_secs = 0
    for step in leg["steps"]:
        if step["travel_mode"] == "TRANSIT" and first_dep_epoch is None:
            td = step.get("transit_details", {})
            first_dep_epoch = td.get("departure_time", {}).get("value")  # epoch seconds
            break
        elif step["travel_mode"] == "WALKING":
            walk_secs += step.get("duration", {}).get("value", 0)
    if first_dep_epoch:
        leave_dt = datetime.fromtimestamp(first_dep_epoch - walk_secs, tz=LONDON_TZ)
        # Windows-safe: %I has leading zero; strip it
        return leave_dt.strftime("%I:%M %p").lstrip("0")
    return None

def maps_link(origin, dest, arrival_dt):
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}"
        f"&destination={quote_plus(dest)}"
        f"&travelmode=transit"
        f"&arrival_time={int(arrival_dt.timestamp())}"
    )

# -------------------- Notifications --------------------

def send_email(cfg, subject, body):
    if not cfg["email_enabled"]:
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = cfg["smtp_user"]
    msg["To"] = cfg["email_to"]
    with smtplib.SMTP_SSL(cfg["smtp_server"], cfg["smtp_port"]) as s:
        s.login(cfg["smtp_user"], cfg["smtp_pass"])
        s.send_message(msg)

# -------------------- Main --------------------

def main():
    cfg = load_config()
    gmaps_client = googlemaps.Client(key=cfg["api_key"])

    # CLI date override: python bus_bot.py 2025-08-31
    if len(sys.argv) > 1:
        try:
            target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD.")
            sys.exit(1)
        shifts = load_shifts_for_date("shifts.csv", target_date, LONDON_TZ)
        report_date = target_date
    else:
        shifts, report_date = load_tomorrows_shifts("shifts.csv", LONDON_TZ)

    logging.info(f"Planning for {report_date}; shifts found: {len(shifts)}")

    if shifts.empty:
        print(f"No shifts found for {report_date}.")
        return

    report_lines = [f"🚌 Bus plan for {report_date} (buffer {cfg['buffer']} min)"]
    for _, row in shifts.iterrows():
        time_str = str(row["start_time"]).strip()
        loc_raw = str(row.get("location", "DEFAULT")).strip()
        destination = cfg["default_work"] if (loc_raw.upper() == "DEFAULT" or not loc_raw) else loc_raw

        arrive_by, _ = build_arrival_dt(row["date"], time_str, LONDON_TZ, cfg["buffer"])
        route, mode = fetch_bus_route(gmaps_client, cfg["home"], destination, arrive_by)

        header = f"\n=== Shift {time_str} @ {destination} ==="
        report_lines.append(header)

        if route:
            leave_by_txt = compute_leave_by(route)
            if leave_by_txt:
                report_lines.append(f"Leave home by: {leave_by_txt}")

            report_lines.append(format_route(route))

            link = maps_link(cfg["home"], destination, arrive_by)
            report_lines.append(f"Open in Maps: {link}")

            if mode == "mixed_transit":
                report_lines.append("(No bus-only route, showing best transit mix.)")
        else:
            report_lines.append("No transit route found for the arrival time. Try an earlier arrival or another mode.")

    report = "\n".join(report_lines)
    print(report)

    with open("tomorrow_bus_plan.txt", "w", encoding="utf-8") as f:
        f.write(report)

    if cfg["email_enabled"]:
        send_email(cfg, f"Bus Plan – {report_date}", report)
        print("Email sent.")

if __name__ == "__main__":
    main()
