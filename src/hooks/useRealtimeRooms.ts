import { useEffect, useState } from "react";
import { collection, onSnapshot, query } from "firebase/firestore";
import { db } from "../services/firebase";
import { pmsRooms, type PMSRoom } from "../data/operationsData";

export function useRealtimeRooms() {
  const [rooms, setRooms] = useState<PMSRoom[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const q = query(collection(db, "rooms"));
    
    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        const roomsData: PMSRoom[] = [];
        snapshot.forEach((doc) => {
          const data = doc.data();
          roomsData.push({
            id: doc.id,
            roomNumber: data.room_number || data.roomNumber || doc.id,
            roomType: data.room_type || data.roomType || data.category || "Single",
            floor: data.floor || "Floor 1",
            capacity: Number(data.capacity || data.max_occupancy || 2),
            price: Number(data.price || 0),
            status: data.status || "available",
          });
        });
        roomsData.sort((a, b) => String(a.roomNumber).localeCompare(String(b.roomNumber), undefined, { numeric: true }));
        setRooms(roomsData.length > 0 ? roomsData : pmsRooms);
        setLoading(false);
      },
      (err) => {
        console.error("Error listening to rooms:", err);
        setError(err);
        setRooms(pmsRooms);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  return { rooms, loading, error };
}
