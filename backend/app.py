from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

from config import Config
from routes import register_blueprints
from services.firestore_client import init_firestore
from services.notification_scheduler import start_notification_scheduler


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, origins=[app.config["FRONTEND_URL"]], supports_credentials=True)
    init_firestore(app)
    JWTManager(app)
    register_blueprints(app)
    start_notification_scheduler(app)

    @app.get("/api/health")
    def health_check():
        return jsonify({"status": "ok", "service": "Room Availability Calendar API"})

    @app.post("/api/admin/reseed-room-types")
    def reseed_room_types_route():
        """
        One-time admin endpoint: fixes room_type mismatches in already-seeded Firestore rooms.
        Call once after deploying this fix if rooms were previously seeded with wrong types.
        E.g. rooms 101-102 were "Single" but should be "Deluxe".
        """
        from services.default_data import reseed_room_types
        updated = reseed_room_types()
        return jsonify({"updated": updated, "message": f"Fixed room_type for {updated} rooms."})

    # Auto-fix room types on startup (safe no-op if already correct)
    with app.app_context():
        try:
            from services.default_data import reseed_room_types
            fixed = reseed_room_types()
            if fixed:
                app.logger.info(f"[startup] Fixed room_type for {fixed} Firestore room documents.")
        except Exception as exc:
            app.logger.warning(f"[startup] reseed_room_types skipped: {exc}")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)