from flask import Blueprint, jsonify, request

from services.date_utils import each_date_inclusive
from services.default_data import ensure_seed_rooms
from services.firestore_client import get_db
from services.availability_engine import get_room_availability_range, get_room_status_for_date

rooms_bp = Blueprint("rooms", __name__)


def room_to_dict(snapshot):
    data = snapshot.to_dict() or {}
    return {
        "id": snapshot.id,
        "roomNumber": data.get("room_number", snapshot.id),
        "category": data.get("category") or data.get("room_type"),
        "roomType": data.get("room_type") or data.get("category"),
        "floor": data.get("floor"),
        "capacity": data.get("capacity"),
        "price": data.get("price", 0),
        "status": data.get("status", "available"),
        "amenities": data.get("amenities", []),
        "images": data.get("images", []),
    }


@rooms_bp.get("/room-categories")
def room_categories():
    ensure_seed_rooms()
    categories = sorted({(room.to_dict() or {}).get("room_type") for room in get_db().collection("rooms").stream()})
    return jsonify({"categories": [category for category in categories if category]})


@rooms_bp.get("/rooms")
def list_rooms():
    ensure_seed_rooms()
    category = request.args.get("category")
    query = get_db().collection("rooms")
    if category:
        query = query.where("room_type", "==", category)
    rooms = sorted([room_to_dict(room) for room in query.stream()], key=lambda item: item["roomNumber"])
    return jsonify({"rooms": rooms})


@rooms_bp.get("/rooms/<room_id>")
def room_detail(room_id):
    ensure_seed_rooms()
    room = get_db().collection("rooms").document(str(room_id)).get()
    if not room.exists:
        return jsonify({"message": "Room not found"}), 404
    return jsonify(room_to_dict(room))


@rooms_bp.get("/rooms/<room_id>/availability")
def room_availability(room_id):
    """
    Returns dynamic availability for a room over a date range.
    Uses the centralized availability_engine — the single source of truth.
    Queries live Firestore bookings + maintenance_blocks, never static arrays.
    """
    ensure_seed_rooms()
    room = get_db().collection("rooms").document(str(room_id)).get()
    if not room.exists:
        return jsonify({"message": "Room not found"}), 404

    start = request.args.get("start")
    end = request.args.get("end")

    room_number = (room.to_dict() or {}).get("room_number", room_id)

    if start and end:
        dates = get_room_availability_range(room_number, start, end)
    else:
        # Default: return today's status only
        from datetime import date as dt
        today = dt.today().isoformat()
        dates = [{"date": today, "status": get_room_status_for_date(room_number, today)}]

    return jsonify({"roomId": room.id, "dates": dates})


@rooms_bp.put("/rooms/<room_id>")
def update_room(room_id):
    db = get_db()
    ref = db.collection("rooms").document(str(room_id))
    if not ref.get().exists:
        return jsonify({"message": "Room not found"}), 404
    payload = request.get_json() or {}
    allowed = {"status", "price", "capacity", "floor", "amenities", "notes"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if updates:
        from services.firestore_client import server_timestamp
        updates["updated_at"] = server_timestamp()
        ref.update(updates)
    data = ref.get().to_dict() or {}
    data["id"] = ref.id
    return jsonify({"room": data})