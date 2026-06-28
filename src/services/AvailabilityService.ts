import type {
  PMSRoom,
  BookingRecord,
  MaintenanceBlock,
  HousekeepingTask,
  CalendarStatus,
} from "../data/operationsData";

// ─────────────────────────────────────────────────────────────────────────────
// SINGLE SOURCE OF TRUTH for availability logic.
// Every component (Customer Calendar, Admin Calendar, Booking Validation)
// must call ONLY these functions — never calculate availability independently.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Safely extract YYYY-MM-DD from any date input (string, object, timestamp).
 */
const toDateStr = (val: any): string => {
  if (!val) return "";
  const s = typeof val.toDate === "function" ? val.toDate().toISOString() : String(val);
  return s.substring(0, 10);
};

/**
 * Returns true if `date` falls within [start, end).
 * Check-OUT date is considered available for new check-ins (half-open interval).
 */
const isWithin = (date: any, start: any, end: any): boolean => {
  const d = toDateStr(date);
  return d >= toDateStr(start) && d < toDateStr(end);
};

/**
 * Returns true if [checkIn, checkOut) overlaps with [bStart, bEnd).
 * This is the canonical overlap test used for conflict detection.
 */
const overlaps = (checkIn: any, checkOut: any, bStart: any, bEnd: any): boolean => {
  const inStr = toDateStr(checkIn);
  const outStr = toDateStr(checkOut);
  return inStr < toDateStr(bEnd) && outStr > toDateStr(bStart);
};

/** Normalize room number to string for safe comparison */
const roomStr = (v: unknown): string => String(v ?? "").trim();

// ─────────────────────────────────────────────────────────────────────────────
// BLOCK HELPERS
// ─────────────────────────────────────────────────────────────────────────────

export const getBlockForRoomDate = (
  roomNumber: string,
  date: string,
  blocks: MaintenanceBlock[] = []
) =>
  blocks.find(
    (block) =>
      roomStr(block.roomNumber) === roomStr(roomNumber) &&
      block.status !== "Completed" &&
      isWithin(date, block.startDate, block.endDate)
  );

// ─────────────────────────────────────────────────────────────────────────────
// BOOKING HELPERS
// ─────────────────────────────────────────────────────────────────────────────

/** Returns true if this booking status actively blocks the room */
const isActiveStatus = (status: string): boolean => {
  const s = (status || "").toLowerCase().trim();
  // Only "cancelled" releases the room; everything else (pending, confirmed,
  // reserved, checked-in, etc.) keeps it blocked.
  return s !== "cancelled";
};

export const getBookingForRoomDate = (
  roomNumber: string,
  date: string,
  bookings: BookingRecord[] = []
) =>
  bookings.find((booking) => {
    const bookingRoom =
      roomStr(booking.assignedRoom) ||
      roomStr((booking as any).roomNumber) ||
      roomStr((booking as any).room_number) ||
      roomStr((booking as any).room_id);

    const checkIn = booking.checkIn || (booking as any).check_in || "";
    const checkOut = booking.checkOut || (booking as any).check_out || "";

    return (
      bookingRoom === roomStr(roomNumber) &&
      isActiveStatus(booking.status) &&
      isWithin(date, checkIn, checkOut)
    );
  });

// ─────────────────────────────────────────────────────────────────────────────
// CALENDAR STATUS — called per-cell in every calendar component
// ─────────────────────────────────────────────────────────────────────────────

export const getCalendarStatus = (
  room: PMSRoom,
  date: string,
  bookings: BookingRecord[] = [],
  blocks: MaintenanceBlock[] = [],
  tasks: HousekeepingTask[] = []
): CalendarStatus => {
  // Hard-disabled rooms always show as out-of-service
  if (room.status === "out-of-service") return "out-of-service";

  // Maintenance blocks have highest priority after hard-disabled
  if (getBlockForRoomDate(room.roomNumber, date, blocks)) return "maintenance";

  const booking = getBookingForRoomDate(room.roomNumber, date, bookings);

  // Active housekeeping task (not completed) marks the room as cleaning
  const hasActiveTask = tasks.some(
    (t) => roomStr(t.roomNumber) === roomStr(room.roomNumber) && t.status !== "Completed"
  );

  if (booking) {
    const s = (booking.status || "").toLowerCase();
    // Checked-out + active housekeeping task = cleaning
    if ((s === "checked-out") && hasActiveTask) return "cleaning";
    // "Pending" / "reserved" from backend = reserved (yellow/blue)
    if (s === "pending") return "reserved";
    // All other active statuses = booked (red)
    return "booked";
  }

  if (hasActiveTask) return "cleaning";
  return "available";
};

// ─────────────────────────────────────────────────────────────────────────────
// CONFLICT DETECTION — used by BookingPanel to prevent double-bookings
// ─────────────────────────────────────────────────────────────────────────────

export const hasRoomConflict = (
  roomNumber: string,
  checkIn: string,
  checkOut: string,
  bookings: BookingRecord[] = [],
  blocks: MaintenanceBlock[] = [],
  roomsList: PMSRoom[] = []
): boolean => {
  const room = roomsList.find((item) => roomStr(item.roomNumber) === roomStr(roomNumber));
  if (!room || room.status === "out-of-service") return true;

  const hasBookingConflict = bookings.some((booking) => {
    const bookingRoom =
      roomStr(booking.assignedRoom) ||
      roomStr((booking as any).roomNumber) ||
      roomStr((booking as any).room_number) ||
      roomStr((booking as any).room_id);

    const bIn = booking.checkIn || (booking as any).check_in || "";
    const bOut = booking.checkOut || (booking as any).check_out || "";

    return (
      bookingRoom === roomStr(roomNumber) &&
      isActiveStatus(booking.status) &&
      overlaps(checkIn, checkOut, bIn, bOut)
    );
  });

  const hasBlockConflict = blocks.some(
    (block) =>
      roomStr(block.roomNumber) === roomStr(roomNumber) &&
      block.status !== "Completed" &&
      overlaps(checkIn, checkOut, block.startDate, block.endDate)
  );

  return hasBookingConflict || hasBlockConflict;
};
