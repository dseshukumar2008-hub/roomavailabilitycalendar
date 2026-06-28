from services.firestore_client import get_db, server_timestamp

# Room seed data — room_type MUST match PMSRoomType values used in the frontend:
# "Single" | "Double" | "Deluxe" | "Suite" | "Executive Suite"
#
# Frontend hotelData.ts category mapping:
#   "Deluxe Rooms"       → rooms 101-105  → room_type = "Deluxe"
#   "Executive Rooms"    → rooms 201-205  → room_type = "Executive Suite"
#   "Family Rooms"       → rooms 301-305  → room_type = "Double"
#   "Suite Rooms"        → rooms 401-405  → room_type = "Suite"
#   "Presidential Suites"→ rooms 501-505  → room_type = "Executive Suite"

ROOM_SEEDS = [
    # Deluxe Rooms (101-105) — all "Deluxe" so they appear in Deluxe filter
    ("101", "Deluxe", "Floor 1", 2, 7500),
    ("102", "Deluxe", "Floor 1", 2, 8150),
    ("103", "Deluxe", "Floor 1", 2, 8800),
    ("104", "Deluxe", "Floor 1", 2, 9450),
    ("105", "Deluxe", "Floor 1", 2, 10100),
    # Executive Rooms (201-205)
    ("201", "Executive Suite", "Floor 2", 2, 10500),
    ("202", "Executive Suite", "Floor 2", 2, 11150),
    ("203", "Executive Suite", "Floor 2", 2, 11800),
    ("204", "Executive Suite", "Floor 2", 2, 12450),
    ("205", "Executive Suite", "Floor 2", 2, 13100),
    # Family Rooms (301-305)
    ("301", "Double", "Floor 3", 4, 13500),
    ("302", "Double", "Floor 3", 4, 14150),
    ("303", "Double", "Floor 3", 4, 14800),
    ("304", "Double", "Floor 3", 4, 15450),
    ("305", "Double", "Floor 3", 4, 16100),
    # Suite Rooms (401-405)
    ("401", "Suite", "Floor 4", 3, 18500),
    ("402", "Suite", "Floor 4", 3, 19150),
    ("403", "Suite", "Floor 4", 3, 19800),
    ("404", "Suite", "Floor 4", 3, 20450),
    ("405", "Suite", "Floor 4", 3, 21100),
    # Presidential Suites (501-505)
    ("501", "Executive Suite", "Floor 5", 5, 36000),
    ("502", "Executive Suite", "Floor 5", 5, 36650),
    ("503", "Executive Suite", "Floor 5", 5, 37300),
    ("504", "Executive Suite", "Floor 5", 5, 37950),
    ("505", "Executive Suite", "Floor 5", 5, 38600),
]


def ensure_seed_rooms():
    db = get_db()
    first_room = next(db.collection("rooms").limit(1).stream(), None)
    if first_room:
        return

    batch = db.batch()
    for room_number, room_type, floor, capacity, price in ROOM_SEEDS:
        ref = db.collection("rooms").document(room_number)
        batch.set(
            ref,
            {
                "room_number": room_number,
                "room_type": room_type,
                "category": room_type,
                "floor": floor,
                "capacity": capacity,
                "price": price,
                "status": "available",
                "booked_dates": [],
                "blocked_dates": [],
                "created_at": server_timestamp(),
                "updated_at": server_timestamp(),
            },
        )
    batch.commit()


def reseed_room_types():
    """
    Force-update all existing room documents to fix room_type mismatches.
    Call this once via Flask shell or a one-off admin route if rooms already exist
    with wrong room_type values.
    """
    db = get_db()
    seed_map = {room_number: (room_type, floor, capacity, price) for room_number, room_type, floor, capacity, price in ROOM_SEEDS}
    batch = db.batch()
    updated = 0
    for doc in db.collection("rooms").stream():
        data = doc.to_dict() or {}
        room_number = data.get("room_number", doc.id)
        if room_number in seed_map:
            room_type, floor, capacity, price = seed_map[room_number]
            current_type = data.get("room_type", "")
            if current_type != room_type:
                batch.update(doc.reference, {
                    "room_type": room_type,
                    "category": room_type,
                    "floor": floor,
                    "capacity": capacity,
                    "updated_at": server_timestamp(),
                })
                updated += 1
    if updated:
        batch.commit()
    return updated