"""
availability_engine.py — Single Source of Truth for room availability.

Every backend route that needs to know if a room/date is available
must call this module. Never duplicate this logic.
"""

from datetime import date, timedelta
from services.firestore_client import get_db


def _parse_date(iso: str) -> date:
    return date.fromisoformat(iso[:10])


def date_range(check_in: str, check_out: str) -> list[str]:
    """Return a list of ISO date strings for [check_in, check_out) — i.e. each night."""
    start = _parse_date(check_in)
    end = _parse_date(check_out)
    result = []
    current = start
    while current < end:
        result.append(current.isoformat())
        current += timedelta(days=1)
    return result


def _active_booking_status(status: str) -> bool:
    """Return True if this booking status means the room is occupied/blocked."""
    return (status or "").lower().strip() not in ("cancelled", "canceled", "checked-out", "checked_out")


def get_room_status_for_date(room_number: str, iso_date: str, db=None) -> str:
    """
    Calculate the canonical status for a specific room on a specific date.
    Returns one of: 'available', 'booked', 'reserved', 'maintenance', 'out-of-service', 'cleaning'
    """
    if db is None:
        db = get_db()

    # 1. Check room-level status (out-of-service overrides everything)
    room_query = db.collection("rooms").where("room_number", "==", str(room_number)).limit(1).stream()
    room_doc = next(room_query, None)
    room_data = room_doc.to_dict() if room_doc else {}
    room_status = (room_data.get("status") or "available").lower()

    if room_status == "out-of-service":
        return "out-of-service"

    # 2. Check maintenance blocks
    blocks = db.collection("maintenance_blocks").where("room_number", "==", str(room_number)).stream()
    for block in blocks:
        bd = block.to_dict() or {}
        if bd.get("status") == "Completed":
            continue
        start = bd.get("start_date") or bd.get("startDate") or ""
        end = bd.get("end_date") or bd.get("endDate") or ""
        if start and end and start <= iso_date < end:
            return "maintenance"

    if room_status == "maintenance":
        return "maintenance"

    # 3. Check active bookings that overlap with this date
    booking_status = None
    bookings = db.collection("bookings").where("room_number", "==", str(room_number)).stream()
    for bk in bookings:
        bd = bk.to_dict() or {}
        status = bd.get("status", "")
        if not _active_booking_status(status):
            continue
        check_in = bd.get("check_in") or bd.get("checkIn") or ""
        check_out = bd.get("check_out") or bd.get("checkOut") or ""
        if check_in and check_out and check_in <= iso_date < check_out:
            booking_status = (status or "").lower()
            break

    if booking_status:
        if booking_status in ("pending", "reserved"):
            return "reserved"
        return "booked"

    # 4. Check housekeeping tasks (cleaning)
    tasks = db.collection("housekeeping_tasks").where("room_number", "==", str(room_number)).stream()
    for task in tasks:
        td = task.to_dict() or {}
        if td.get("status") != "Completed":
            return "cleaning"

    return "available"


def get_room_availability_range(room_number: str, check_in: str, check_out: str, db=None) -> list[dict]:
    """
    Return a list of {date, status} dicts for every night in [check_in, check_out).
    Uses the same logic as the frontend AvailabilityService.ts.
    """
    if db is None:
        db = get_db()

    nights = date_range(check_in, check_out)
    return [
        {"date": night, "status": get_room_status_for_date(room_number, night, db)}
        for night in nights
    ]


def has_conflict(room_number: str, check_in: str, check_out: str, db=None) -> bool:
    """
    Return True if any night in [check_in, check_out) is NOT available.
    Called by the booking API before creating a new booking.
    """
    if db is None:
        db = get_db()

    # Check maintenance blocks
    blocks = db.collection("maintenance_blocks").where("room_number", "==", str(room_number)).stream()
    for block in blocks:
        bd = block.to_dict() or {}
        if bd.get("status") == "Completed":
            continue
        b_start = bd.get("start_date") or bd.get("startDate") or ""
        b_end = bd.get("end_date") or bd.get("endDate") or ""
        if b_start and b_end and check_in < b_end and check_out > b_start:
            return True

    # Check active bookings
    bookings = db.collection("bookings").where("room_number", "==", str(room_number)).stream()
    for bk in bookings:
        bd = bk.to_dict() or {}
        status = bd.get("status", "")
        if not _active_booking_status(status):
            continue
        b_in = bd.get("check_in") or bd.get("checkIn") or ""
        b_out = bd.get("check_out") or bd.get("checkOut") or ""
        if b_in and b_out and check_in < b_out and check_out > b_in:
            return True

    return False
