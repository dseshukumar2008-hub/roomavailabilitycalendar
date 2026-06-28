import { useEffect, useState } from "react";
import { collection, onSnapshot, query } from "firebase/firestore";
import { db } from "../services/firebase";
import type { HousekeepingTask } from "../data/operationsData";

export function useRealtimeHousekeeping() {
  const [tasks, setTasks] = useState<HousekeepingTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const q = query(collection(db, "housekeeping_tasks"));
    
    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        const tasksData: HousekeepingTask[] = [];
        snapshot.forEach((doc) => {
          const data = doc.data();
          tasksData.push({
            id: doc.id,
            roomNumber: data.room_number || data.room_id || "",
            task: data.task || data.task_type || "Cleaning",
            priority: data.priority || "Medium",
            assignedStaff: data.assigned_staff || data.assigned_to || "",
            status: data.status || "Pending",
            remarks: data.remarks || data.notes || "",
          });
        });
        setTasks(tasksData);
        setLoading(false);
      },
      (err) => {
        console.error("Error listening to housekeeping tasks:", err);
        setError(err);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  return { tasks, loading, error };
}
