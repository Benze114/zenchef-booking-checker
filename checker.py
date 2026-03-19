#!/usr/bin/env python3
"""
OTSUKA Booking Availability Checker
Monitors Zenchef for new booking slots and sends macOS notifications.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

RESTAURANT_ID = 365906
RESTAURANT_NAME = "OTSUKA"
BOOKING_URL = f"https://bookings.zenchef.com/results?rid={RESTAURANT_ID}"
API_URL = "https://bookings-middleware.zenchef.com/getAvailabilities"

CHECK_INTERVAL_MINUTES = 5
CHECK_INTERVAL_PEAK_MINUTES = 0.1  # During release window
PEAK_START = (11, 30)  # 11:30
PEAK_END = (13, 30)    # 13:30
GUESTS = 2
LOOKAHEAD_DAYS = 14

# WhatsApp (CallMeBot) — set here or via env vars CALLMEBOT_PHONE, CALLMEBOT_API_KEY
CALLMEBOT_PHONE = ""  # e.g. "491234567890" (international format, no +)
CALLMEBOT_API_KEY = ""  # Get from: send "I allow callmebot to send me messages" to +34 644 71 76 18

LOG_FILE = "checker_log.json"


def append_log(timestamp: str, available: dict, status: str, new_slots_count: int = 0):
    """Append a log entry to the JSON log file."""
    entry = {
        "timestamp": timestamp,
        "available": available,
        "status": status,
        "new_slots_count": new_slots_count,
    }
    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        logs.append(entry)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except (OSError, json.JSONDecodeError) as e:
        print(f"  [!] Log write failed: {e}")


def get_check_interval_minutes() -> int:
    """Return 1 min during 11:30–13:30 (release window), else 5 min."""
    now = datetime.now()
    start = now.replace(hour=PEAK_START[0], minute=PEAK_START[1], second=0, microsecond=0)
    end = now.replace(hour=PEAK_END[0], minute=PEAK_END[1], second=0, microsecond=0)
    if start <= now <= end:
        return CHECK_INTERVAL_PEAK_MINUTES
    return CHECK_INTERVAL_MINUTES


def notify(title: str, message: str, url: str = BOOKING_URL, sound: str = "Hero"):
    """Send a macOS notification with sound. Clicking opens the booking URL."""
    script = (
        f'display notification "{message}" '
        f'with title "{title}" '
        f'sound name "{sound}"'
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)


def speak(text: str):
    """Use macOS text-to-speech as an extra alert."""
    subprocess.Popen(["say", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_url(url: str = BOOKING_URL):
    """Open the booking page in the default browser."""
    subprocess.run(["open", url], capture_output=True)


def notify_whatsapp(message: str):
    """Send WhatsApp via CallMeBot. Set CALLMEBOT_PHONE and CALLMEBOT_API_KEY in script or env."""
    phone = (CALLMEBOT_PHONE or os.environ.get("CALLMEBOT_PHONE") or "").replace("+", "")
    apikey = CALLMEBOT_API_KEY or os.environ.get("CALLMEBOT_API_KEY")
    if not phone or not apikey:
        return
    try:
        text = urllib.parse.quote(message)
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={text}&apikey={apikey}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"  [✓] WhatsApp sent")
            else:
                print(f"  [!] WhatsApp failed: status {resp.status}")
    except Exception as e:
        print(f"  [!] WhatsApp failed: {e}")


def fetch_availabilities(date_begin: str, date_end: str) -> list:
    params = (
        f"?restaurantId={RESTAURANT_ID}"
        f"&date_begin={date_begin}"
        f"&date_end={date_end}"
    )
    url = API_URL + params

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  [!] API error: {e}")
        return []

    if not isinstance(data, list):
        print(f"  [!] Unexpected API response format")
        return []

    return data


def find_available_slots(guests: int) -> dict:
    """
    Returns a dict: { "YYYY-MM-DD": [ {"shift": str, "times": [str]} ] }
    for dates with available slots matching the guest count.
    Uses possible_guests — the only reliable bookability signal from Zenchef API.
    When possible_guests is empty, the slot is not bookable (even if occupation suggests capacity).
    """
    today = date.today()
    end = today + timedelta(days=LOOKAHEAD_DAYS)

    raw = fetch_availabilities(today.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    available = {}
    for day_entry in raw:
        day_str = day_entry.get("date", "")
        for shift in day_entry.get("shifts", []):
            shift_name = shift.get("name", "")
            matching_times = []
            for slot in shift.get("shift_slots", []):
                if guests in slot.get("possible_guests", []):
                    matching_times.append(slot.get("name", ""))

            if matching_times:
                if day_str not in available:
                    available[day_str] = []
                available[day_str].append({
                    "shift": shift_name,
                    "times": matching_times,
                })

    return available


def format_slots(available: dict) -> str:
    lines = []
    for day_str in sorted(available.keys()):
        try:
            nice_date = datetime.strptime(day_str, "%Y-%m-%d").strftime("%a %d %b")
        except ValueError:
            nice_date = day_str
        for entry in available[day_str]:
            times = ", ".join(entry["times"])
            lines.append(f"  {nice_date}  {entry['shift']:>10s}:  {times}")
    return "\n".join(lines)


def main():
    print(f"{'=' * 60}")
    print(f"  OTSUKA Booking Checker")
    print(f"  Restaurant ID : {RESTAURANT_ID}")
    print(f"  Guests        : {GUESTS}")
    print(f"  Lookahead     : {LOOKAHEAD_DAYS} days")
    print(f"  Check interval: every {CHECK_INTERVAL_MINUTES} min (every {CHECK_INTERVAL_PEAK_MINUTES} min 11:30–13:30)")
    print(f"  Booking URL   : {BOOKING_URL}")
    print(f"{'=' * 60}")
    print()

    known_slots: dict = {}
    first_run = True

    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Checking availability...")

        available = find_available_slots(GUESTS)

        if available:
            new_slots = {}
            for day, shifts in available.items():
                for shift_entry in shifts:
                    for t in shift_entry["times"]:
                        key = (day, shift_entry["shift"], t)
                        if key not in known_slots:
                            new_slots[key] = True
                            known_slots[key] = True

            if new_slots and not first_run:
                print(f"\n  *** NEW SLOTS FOUND! ***")
                print(format_slots(available))
                print()
                append_log(now, available, "new_slots", len(new_slots))

                notify(
                    f"NEW slots at {RESTAURANT_NAME}!",
                    f"{len(new_slots)} new time slot(s) available — click to book!",
                )
                speak(f"New booking slots available at {RESTAURANT_NAME}!")
                open_url()
                notify_whatsapp(
                    f"OTSUKA: {len(new_slots)} new booking slot(s) available! Book now: {BOOKING_URL}",
                )
            elif new_slots and first_run:
                print(f"  Currently available slots (baseline):")
                print(format_slots(available))
                print()
                append_log(now, available, "baseline")
            else:
                print(f"  No new slots (still {len(known_slots)} known).")
                append_log(now, available, "no_change")
        else:
            print(f"  No available slots found.")
            if not first_run and known_slots:
                known_slots.clear()
                print(f"  (Previously known slots cleared — they were taken.)")
                append_log(now, {}, "slots_cleared")
            else:
                append_log(now, {}, "no_slots")

        first_run = False

        interval = get_check_interval_minutes()
        next_check = datetime.now() + timedelta(minutes=interval)
        print(f"  Next check at {next_check.strftime('%H:%M:%S')} (interval: {interval} min)")
        print()

        try:
            time.sleep(interval * 60)
        except KeyboardInterrupt:
            print("\nStopped by user. Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
