#!/usr/bin/env python3
"""
OTSUKA Booking Availability Checker
Monitors Zenchef for new booking slots and sends macOS notifications.
"""

import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta

RESTAURANT_ID = 365906
RESTAURANT_NAME = "OTSUKA"
BOOKING_URL = f"https://bookings.zenchef.com/results?rid={RESTAURANT_ID}"
API_URL = "https://bookings-middleware.zenchef.com/getAvailabilities"

CHECK_INTERVAL_MINUTES = 5
GUESTS = 2
LOOKAHEAD_DAYS = 14


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
    print(f"  Check interval: every {CHECK_INTERVAL_MINUTES} min")
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

                notify(
                    f"NEW slots at {RESTAURANT_NAME}!",
                    f"{len(new_slots)} new time slot(s) available — click to book!",
                )
                speak(f"New booking slots available at {RESTAURANT_NAME}!")
                open_url()
            elif new_slots and first_run:
                print(f"  Currently available slots (baseline):")
                print(format_slots(available))
                print()
            else:
                print(f"  No new slots (still {len(known_slots)} known).")
        else:
            print(f"  No available slots found.")
            if not first_run and known_slots:
                known_slots.clear()
                print(f"  (Previously known slots cleared — they were taken.)")

        first_run = False

        next_check = datetime.now() + timedelta(minutes=CHECK_INTERVAL_MINUTES)
        print(f"  Next check at {next_check.strftime('%H:%M:%S')}")
        print()

        try:
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\nStopped by user. Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
