#!/usr/bin/env python3
"""
OTSUKA Auto-Booker
Automatically books a slot on Zenchef using Playwright.
"""

import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

RESTAURANT_ID = 365906
BOOKING_BASE = "https://bookings.zenchef.com/results"
SCREENSHOTS_DIR = "screenshots"

PREFERRED_SLOTS = ["19:00", "20:00"]
CIVILITY = "Herr"


def get_booking_details() -> dict:
    details = {
        "firstname": os.environ.get("BOOKING_FIRSTNAME", ""),
        "lastname": os.environ.get("BOOKING_LASTNAME", ""),
        "email": os.environ.get("BOOKING_EMAIL", ""),
        "phone": os.environ.get("BOOKING_PHONE", ""),
    }
    missing = [k for k, v in details.items() if not v]
    if missing:
        print(f"  [!] Missing booking env vars: {', '.join(missing)}")
        print("      Set BOOKING_FIRSTNAME, BOOKING_LASTNAME, BOOKING_EMAIL, BOOKING_PHONE in env.sh")
        return {}
    return details


def build_booking_url(day: str, slot: str, details: dict, pax: int = 2) -> str:
    phone = details["phone"].replace("+", "%2B")
    return (
        f"{BOOKING_BASE}?rid={RESTAURANT_ID}"
        f"&pax={pax}&day={day}&slot={slot}&lang=de"
        f"&firstname={details['firstname']}"
        f"&lastname={details['lastname']}"
        f"&email={details['email']}"
        f"&phone={phone}"
    )


def screenshot(page, name: str):
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOTS_DIR, f"{ts}_{name}.png")
    page.screenshot(path=path, full_page=True)
    print(f"  [screenshot] {path}")


def pick_best_slot(available_times: list[str]) -> str | None:
    """Pick the best slot from available times based on preference order."""
    for pref in PREFERRED_SLOTS:
        if pref in available_times:
            return pref
    return available_times[0] if available_times else None


def attempt_booking(day: str, slot: str, details: dict, pax: int = 2, headless: bool = True) -> bool:
    """
    Attempt to book a slot. Returns True if booking was submitted successfully.
    """
    url = build_booking_url(day, slot, details, pax)
    print(f"  [booker] Attempting: {day} {slot} for {pax} guests")
    print(f"  [booker] URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 430, "height": 932})

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            screenshot(page, "01_landing")

            # Check if slot is still available (not "Ausgebucht")
            body_text = page.inner_text("body")
            if "Ausgebucht" in body_text or "voll" in body_text.lower():
                print(f"  [booker] Slot already taken or fully booked")
                screenshot(page, "01_sold_out")
                browser.close()
                return False

            # Verify the time slot is visible/selected
            slot_visible = page.query_selector(f'text="{slot}"')
            if not slot_visible:
                # Try clicking the time dropdown to find our slot
                time_dropdown = page.query_selector('[class*="slot"], [class*="time"]')
                if time_dropdown:
                    time_dropdown.click()
                    time.sleep(1)
                    slot_btn = page.query_selector(f'button:has-text("{slot}")')
                    if slot_btn:
                        slot_btn.click()
                        time.sleep(1)

            screenshot(page, "02_slot_selected")

            # Click "Reservieren" to go to the form
            reserve_btn = page.query_selector('button:has-text("Reservieren")')
            if not reserve_btn:
                print("  [booker] Could not find Reservieren button")
                screenshot(page, "02_no_reserve_btn")
                browser.close()
                return False

            reserve_btn.click()
            time.sleep(3)
            screenshot(page, "03_form_page")

            # Handle offer selection if present (OTSUKA requires Sushi Omakase)
            body_text = page.inner_text("body")
            if "Omakase" in body_text or "Erlebnis" in body_text or "Angebot" in body_text:
                print("  [booker] Offer selection detected")
                # Try to click the offer
                offer_btn = page.query_selector('button:has-text("Omakase")')
                if not offer_btn:
                    offer_btn = page.query_selector('[class*="offer"], [data-testid*="offer"]')
                if offer_btn:
                    offer_btn.click()
                    time.sleep(2)
                    screenshot(page, "03b_offer_selected")

                    # May need to click Reservieren/Continue again
                    next_btn = page.query_selector('button:has-text("Reservieren"), button:has-text("Weiter"), button:has-text("Bestätigen")')
                    if next_btn:
                        next_btn.click()
                        time.sleep(2)
                        screenshot(page, "03c_after_offer")

            # Now on the contact form — fields should be pre-filled via URL params
            # Select civility (Herr)
            herr_radio = page.query_selector(f'text="{CIVILITY}"')
            if herr_radio:
                herr_radio.click()
                time.sleep(0.5)

            # Verify fields are filled
            fname = page.input_value('input[name="firstname"]') if page.query_selector('input[name="firstname"]') else ""
            lname = page.input_value('input[name="lastname"]') if page.query_selector('input[name="lastname"]') else ""
            email = page.input_value('input[name="email"]') if page.query_selector('input[name="email"]') else ""
            phone = page.input_value('input[name="phone_number"]') if page.query_selector('input[name="phone_number"]') else ""

            print(f"  [booker] Form: {fname} {lname}, {email}, {phone}")

            # Fill any empty fields manually
            if not fname and page.query_selector('input[name="firstname"]'):
                page.fill('input[name="firstname"]', details["firstname"])
            if not lname and page.query_selector('input[name="lastname"]'):
                page.fill('input[name="lastname"]', details["lastname"])
            if not email and page.query_selector('input[name="email"]'):
                page.fill('input[name="email"]', details["email"])
            if not phone and page.query_selector('input[name="phone_number"]'):
                page.fill('input[name="phone_number"]', details["phone"])

            # Accept terms (required checkbox)
            eula_checkbox = page.query_selector('input#eula_accepted')
            if eula_checkbox and not eula_checkbox.is_checked():
                eula_checkbox.click()
                time.sleep(0.3)

            screenshot(page, "04_form_filled")

            # Submit the booking
            submit_btn = page.query_selector('button:has-text("Reservieren")')
            if not submit_btn:
                print("  [booker] Could not find submit button")
                screenshot(page, "04_no_submit")
                browser.close()
                return False

            print("  [booker] Submitting booking...")
            submit_btn.click()
            time.sleep(5)
            screenshot(page, "05_after_submit")

            # Check result
            body_text = page.inner_text("body")
            success_keywords = ["bestätigt", "Bestätigung", "Vielen Dank", "Reservierung", "erhalten"]
            failure_keywords = ["Fehler", "error", "nicht verfügbar", "Ausgebucht"]

            is_success = any(kw.lower() in body_text.lower() for kw in success_keywords)
            is_failure = any(kw.lower() in body_text.lower() for kw in failure_keywords)

            if is_success and not is_failure:
                print("  [booker] *** BOOKING SUBMITTED SUCCESSFULLY! ***")
                screenshot(page, "06_success")
                browser.close()
                return True
            else:
                print(f"  [booker] Booking result unclear. Check screenshots.")
                screenshot(page, "06_result_unclear")
                browser.close()
                return False

        except PlaywrightTimeout as e:
            print(f"  [booker] Timeout: {e}")
            screenshot(page, "error_timeout")
            browser.close()
            return False
        except Exception as e:
            print(f"  [booker] Error: {e}")
            try:
                screenshot(page, "error_exception")
            except Exception:
                pass
            browser.close()
            return False


def auto_book(available: dict, pax: int = 2, min_date: str = "") -> bool:
    """
    Given available slots dict from checker, attempt to book the best one.
    Returns True if booking was submitted.
    """
    details = get_booking_details()
    if not details:
        return False

    for day in sorted(available.keys()):
        if min_date and day < min_date:
            continue
        for shift_entry in available[day]:
            best_slot = pick_best_slot(shift_entry["times"])
            if best_slot:
                success = attempt_booking(day, best_slot, details, pax)
                if success:
                    return True
                print(f"  [booker] Failed for {day} {best_slot}, trying next...")

    print("  [booker] All booking attempts failed.")
    return False


if __name__ == "__main__":
    details = get_booking_details()
    if not details:
        print("Set BOOKING_* env vars (source env.sh) and retry.")
        sys.exit(1)

    day = sys.argv[1] if len(sys.argv) > 1 else "2026-03-25"
    slot = sys.argv[2] if len(sys.argv) > 2 else "19:00"
    print(f"Test booking: {day} at {slot}")
    attempt_booking(day, slot, details, headless=False)
