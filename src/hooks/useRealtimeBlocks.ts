import { useEffect, useState } from "react";
import { collection, onSnapshot, query } from "firebase/firestore";
import { db } from "../services/firebase";
import type { MaintenanceBlock } from "../data/operationsData";

export function useRealtimeBlocks() {
  const [blocks, setBlocks] = useState<MaintenanceBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const q = query(collection(db, "maintenance_blocks"));
    
    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        const blocksData: MaintenanceBlock[] = [];
        snapshot.forEach((doc) => {
          const data = doc.data();
          blocksData.push({
            id: doc.id,
            roomNumber: data.room_number || data.room_id || "",
            startDate: data.start_date || "",
            endDate: data.end_date || "",
            reason: data.reason || "",
            description: data.description || "",
            priority: data.priority || "Medium",
            assignedStaff: data.assigned_staff || data.created_by || "System",
            expectedCompletionDate: data.expected_completion_date || data.end_date || "",
            status: data.status || "Active",
          });
        });
        setBlocks(blocksData);
        setLoading(false);
      },
      (err) => {
        console.error("Error listening to maintenance blocks:", err);
        setError(err);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  return { blocks, loading, error };
}
