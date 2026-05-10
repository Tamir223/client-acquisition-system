import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from werkzeug.security import generate_password_hash
from database import DB_PATH


def create_client(name, business_name, email, password, sheet_id, niche):
    db = sqlite3.connect(DB_PATH)
    try:
        db.execute(
            "INSERT INTO clients (name, business_name, email, password_hash, google_sheet_id, niche) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, business_name, email.strip().lower(), generate_password_hash(password), sheet_id, niche)
        )
        db.commit()
        print(f"Client created: {business_name} ({email})")
    except sqlite3.IntegrityError:
        print(f"Error: A client with email '{email}' already exists.")
    finally:
        db.close()


if __name__ == "__main__":
    print("=== Create Client Account ===")
    create_client(
        name=input("Client name: "),
        business_name=input("Business name: "),
        email=input("Email: "),
        password=input("Password: "),
        sheet_id=input("Google Sheet ID (leave blank to skip): "),
        niche=input("Niche (e.g. plumbing, trucking): "),
    )
