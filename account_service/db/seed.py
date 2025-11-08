from __future__ import annotations

"""
Seed data for Account Service.

Creates two users with predefined IDs, hashed passwords (as provided),
and initial balance = 100,000,000 VND.

Run:
  docker compose exec account_service python account_service/db/seed.py
"""

from sqlalchemy import text
from account_service.app.db import session_scope


USERS = [
    {
        # UUIDs with trailing ...0001 and ...0002 to conceptually match 1, 2
        "user_id": "00000000-0000-0000-0000-000000000001",
        "username": "anhminh",  # you can login with this username
        "password_hash": "d48cb882ca5db13885c5d8f644904ba552b2218d1f808632a7a218b3053ea087",
        "full_name": "Tran Anh Minh",
        "phone_number": "0776966302",
        "email": "anhminht68@gmail.com",
        "balance": 100_000_000,
    },
    {
        "user_id": "00000000-0000-0000-0000-000000000002",
        "username": "thanhvu",
        "password_hash": "d48cb882ca5db13885c5d8f644904ba552b2218d1f808632a7a218b3053ea087",
        "full_name": "Chau Thanh Vu",
        "phone_number": "0776966301",
        "email": "chauthanhvu24122007@gmail.com",
        "balance": 100_000_000,
    },
]


def seed() -> None:
    with session_scope() as db:
        for u in USERS:
            db.execute(
                text(
                    """
                    INSERT INTO accounts (user_id, username, password_hash, full_name, phone_number, email, balance)
                    VALUES (:user_id, :username, :password_hash, :full_name, :phone_number, :email, :balance)
                    ON CONFLICT (username) DO NOTHING
                    """
                ),
                {
                    "user_id": u["user_id"],
                    "username": u["username"],
                    "password_hash": u["password_hash"],
                    "full_name": u["full_name"],
                    "phone_number": u["phone_number"],
                    "email": u["email"],
                    "balance": float(u["balance"]),
                },
            )


if __name__ == "__main__":
    seed()
    print("Account seed completed.")
