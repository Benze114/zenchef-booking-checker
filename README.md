# Zenchef Booking Checker

A lightweight Python script that monitors a [Zenchef](https://www.zenchef.com/) restaurant booking page for newly available slots and sends macOS notifications when they appear.

Built for restaurants with limited seating that release reservations on a rolling basis with no fixed schedule.

## Features

- Polls the Zenchef availability API at a configurable interval
- Detects **new** slots (ignores already-known availability)
- **Auto-booking** — automatically submits a reservation via browser automation (Playwright)
- macOS native notification with sound
- Text-to-speech announcement
- Automatically opens the booking page in your browser
- Optional: WhatsApp notifications via CallMeBot
- JSON logging of all check results

## Usage

```bash
source env.sh && python3 checker.py
```

To run in the background (keeps running after closing the terminal):

```bash
source env.sh && caffeinate -i nohup python3 checker.py > checker.log 2>&1 &
```

Stop with `Ctrl+C` (foreground) or `pkill -f "python3 checker.py"` (background).

### Preventing sleep

The script checks every few seconds during the 11:30–13:30 release window. If your Mac sleeps, it will miss new slots.

- **`caffeinate -i`** prevents idle sleep while the script runs. Add `-d` to also keep the display awake: `caffeinate -di`.
- **Screen lock** does not affect the script — only sleep does.
- **Closing the lid** will sleep the Mac regardless. Keep it open or use `pmset` to disable lid sleep.
- **macOS settings**: System Settings → Battery → Options → Enable "Prevent automatic sleeping when the display is off".
- Make sure your MacBook is **plugged in** so it doesn't die mid-check.

## Configuration

Edit the constants at the top of `checker.py`:


| Setting                  | Default  | Description                                                   |
| ------------------------ | -------- | ------------------------------------------------------------- |
| `RESTAURANT_ID`          | `365906` | Zenchef restaurant ID (from the booking URL `rid=` parameter) |
| `GUESTS`                 | `2`      | Number of guests to search for                                |
| `CHECK_INTERVAL_MINUTES` | `5`      | Minutes between each check (1 min during 11:30–13:30)         |
| `LOOKAHEAD_DAYS`         | `14`     | How many days ahead to search                                 |


To monitor a different restaurant, find the `rid` value in its Zenchef booking URL:
`https://bookings.zenchef.com/results?rid=<RESTAURANT_ID>`

### Optional: WhatsApp notifications

Uses [CallMeBot](https://www.callmebot.com/blog/free-api-whatsapp-messages/) (free):

1. Send `I allow callmebot to send me messages` to +34 644 71 76 18 on WhatsApp
2. You'll receive an API key

**Option A — In the script:** Edit the constants at the top of `checker.py`:

```python
CALLMEBOT_PHONE = "491234567890"   # Your phone, international format (no +)
CALLMEBOT_API_KEY = "your-api-key"
```

**Option B — Separate file:** Create `env.sh` with:

```bash
export CALLMEBOT_PHONE=491234567890
export CALLMEBOT_API_KEY=your-api-key
```

Then run: `source env.sh && python3 checker.py`

### Auto-booking

When `AUTO_BOOK = True` in `checker.py`, the script will automatically attempt to book a slot using Playwright when one becomes available.

Add your booking details to `env.sh`:

```bash
export BOOKING_FIRSTNAME=YourFirstName
export BOOKING_LASTNAME=YourLastName
export BOOKING_EMAIL=your@email.com
export BOOKING_PHONE=+49123456789
```

Configure in `checker.py`:

| Setting | Default | Description |
|---|---|---|
| `AUTO_BOOK` | `True` | Enable auto-booking |
| `MIN_BOOKING_DATE` | `2026-03-25` | Only book dates from this date onwards |

Configure in `auto_booker.py`:

| Setting | Default | Description |
|---|---|---|
| `PREFERRED_SLOTS` | `["19:00", "19:30", "20:00", ...]` | Time slots in order of preference |
| `CIVILITY` | `"Herr"` | Salutation (`Frau`, `Herr`, `Mx.`) |

Screenshots of each booking attempt are saved to `screenshots/`.

To test the auto-booker standalone:

```bash
source env.sh && python3 auto_booker.py 2026-03-25 19:00
```

## Requirements

- Python 3.9+
- macOS (for notifications, `say`, and `open` commands)
- Playwright (`pip3 install playwright && python3 -m playwright install chromium`)

## License

MIT