import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2
from werkzeug.security import generate_password_hash

DATABASE_URL = os.environ.get("DATABASE_URL")


def create_client(name, business_name, email, password, sheet_id, niche):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clients (name, business_name, email, password_hash, google_sheet_id, niche) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (name, business_name, email.strip().lower(), generate_password_hash(password), sheet_id, niche)
        )
        conn.commit()
        print(f"Client created: {business_name} ({email})")
    except psycopg2.errors.UniqueViolation:
        print(f"Error: A client with email '{email}' already exists.")
    finally:
        conn.close()


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
