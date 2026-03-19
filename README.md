# Zenchef Booking Checker

A lightweight Python script that monitors a [Zenchef](https://www.zenchef.com/) restaurant booking page for newly available slots and sends macOS notifications when they appear.

Built for restaurants with limited seating that release reservations on a rolling basis with no fixed schedule.

## Features

- Polls the Zenchef availability API at a configurable interval
- Detects **new** slots (ignores already-known availability)
- macOS native notification with sound
- Text-to-speech announcement
- Automatically opens the booking page in your browser
- Zero dependencies — uses only Python standard library + macOS built-ins
- Optional: WhatsApp notifications via CallMeBot

## Usage

```bash
python3 checker.py
```

To run in the background:

```bash
nohup python3 checker.py > checker.log 2>&1 &
```

Stop with `Ctrl+C` (foreground) or `kill %1` (background).

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

## Requirements

- Python 3.6+
- macOS (for notifications, `say`, and `open` commands)

## License

MIT