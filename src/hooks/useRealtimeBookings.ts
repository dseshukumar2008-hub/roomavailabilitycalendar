import { useEffect, useState } from "react";
import { collection, onSnapshot, query } from "firebase/firestore";
import { db } from "../services/firebase";
import type { BookingRecord, BookingStatus } from "../data/operationsData";

/** Normalize any status string from Firestore/backend into our frontend BookingStatus union */
function normalizeBookingStatus(raw: string | undefined): BookingStatus {
  if (!raw) return "Pending";
  const s = raw.toLowerCase().trim();
  if (s === "confirmed" || s === "confirm") return "Confirmed";
  if (s === "checked-in" || s === "checked_in" || s === "checkin") return "Checked-In";
  if (s === "checked-out" || s === "checked_out" || s === "checkout") return "Checked-Out";
  if (s === "cancelled" || s === "canceled") return "Cancelled";
  // "reserved", "pending", "reserved" and any other status treated as Pending (active booking)
  return "Pending";
}

export function useRealtimeBookings() {
  const [bookings, setBookings] = useState<BookingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const q = query(collection(db, "bookings"));
    
    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        const bookingsData: BookingRecord[] = [];
        snapshot.forEach((doc) => {
          const data = doc.data();
          const rawStatus = String(data.status || "");
          // Only skip truly cancelled bookings — ALL others (reserved, confirmed, pending) block the room
          bookingsData.push({
            id: doc.id,
            guestName: data.guest_name || data.guestName || "Guest",
            phone: data.phone || "",
            email: data.email || "",
            idProof: (data.guest_details && data.guest_details[0]?.idNumber) || "",
            checkIn: data.check_in || data.checkIn || "",
            checkOut: data.check_out || data.checkOut || "",
            guests: Number(data.guests || 1),
            maxOccupancy: Number(data.max_occupancy || data.maxOccupancy || 2),
            guestDetails: data.guest_details || data.guestDetails || [],
            roomType: data.room_type || data.roomType || "Single",
            // assignedRoom maps from room_number OR room_id (room number string like "101")
            assignedRoom: data.room_number || data.roomNumber || data.room_id || data.roomId || "",
            status: normalizeBookingStatus(rawStatus),
            amount: Number(data.total_amount || data.amount || 0),
          });
        });
        setBookings(bookingsData);
        setLoading(false);
      },
      (err) => {
        console.error("Error listening to bookings:", err);
        setError(err);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  return { bookings, loading, error };
}
