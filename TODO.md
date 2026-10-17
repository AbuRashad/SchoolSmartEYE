# Student Profile Page — Implementation Status

## Backend
- [x] Add `GET /students/{student_id}/profile` endpoint in `app/api/v1/endpoints/students.py`
  - Aggregate: student info, assigned bracelet, today's attendance, 7-day attendance,
    monthly attendance %, streak, notifications, safety status, last-seen zone label.

## Frontend
- [x] Add `StudentProfile` + `StudentProfileAttendanceDay` + related types in `frontend/src/types.ts`
- [x] Create `frontend/src/components/control/StudentProfileModal.tsx` with tabs:
  - Overview / Attendance / Bracelet / Notifications / Edit
- [x] Update `frontend/src/components/control/StudentsTab.tsx`:
  - Add search + grade/section filters
  - Add "View" (eye) action opening profile modal
  - Make student name clickable
  - Collapse Add Student form into a toggleable drawer

## Follow-up
- [x] Run dev server & verify profile loads for each seeded student
- [x] Verify edit / activate-toggle / delete flow refreshes table
- [x] Verify modal closes cleanly and does not leak state
