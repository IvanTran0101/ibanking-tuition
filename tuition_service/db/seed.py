from __future__ import annotations

"""
Seed data for Tuition Service.

Adds two students (John Smith, William Clinton) and 8 tuition terms each
with amount_due = 1,000,000 VND, status UNLOCKED.

Run inside the container:
  docker compose exec tuition_service python tuition_service/db/seed.py
"""

import uuid
from datetime import datetime

from sqlalchemy import text

from tuition_service.app.db import session_scope


STUDENTS = [
    {"full_name": "John Smith", "student_id": "523K0017"},
    {"full_name": "William Clinton", "student_id": "523K0018"},
]

TERMS = list(range(1, 9))  # 8 terms: 1..8
AMOUNT_VND = 1_000_000


def seed() -> None:
    with session_scope() as db:
        # Insert students using provided student_id (text id)
        for s in STUDENTS:
            sid = s["student_id"]
            db.execute(
                text(
                    """
                    INSERT INTO students (student_id, full_name)
                    VALUES (:sid, :name)
                    ON CONFLICT (student_id) DO NOTHING
                    """
                ),
                {"sid": sid, "name": s["full_name"]},
            )

            # Insert 8 terms for each student
            for term_no in TERMS:
                tid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{sid}-{term_no}"))  # deterministic UUID per student/term
                pid = str(uuid.uuid4())  # placeholder payment_id (will be overwritten on lock)
                db.execute(
                    text(
                        """
                        INSERT INTO tuitions (tuition_id, student_id, term_no, amount_due, status, expires_at, payment_id)
                        VALUES (:tuition_id, :student_id, :term_no, :amount_due, 'UNLOCKED', :expires_at, :payment_id)
                        ON CONFLICT (student_id, term_no) DO NOTHING
                        """
                    ),
                    {
                        "tuition_id": tid,
                        "student_id": sid,
                        "term_no": int(term_no),
                        "amount_due": float(AMOUNT_VND),
                        "expires_at": datetime.utcnow(),
                        "payment_id": pid,
                    },
                )


if __name__ == "__main__":
    seed()
    for s in STUDENTS:
        print(f"seeded student_id (code): {s['student_id']}")
    print("Tuition seed completed.")
