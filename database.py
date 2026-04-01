import sqlite3
import json
from datetime import datetime

DB_PATH = "adsyield.db"

def init_db():
    """Veritabanını ve tabloları oluştur"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Publisher tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS publishers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            management_key  TEXT NOT NULL,
            publisher_tag   TEXT NOT NULL,
            find_string     TEXT NOT NULL,
            replace_string  TEXT NOT NULL,
            frequency_days  INTEGER DEFAULT 2,
            current_version INTEGER DEFAULT 1,
            active          INTEGER DEFAULT 1,
            last_run        TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Job log tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            publisher_id    INTEGER,
            publisher_name  TEXT,
            ad_unit_id      TEXT,
            ad_unit_name    TEXT,
            old_value       TEXT,
            new_value       TEXT,
            status          TEXT,
            error_message   TEXT,
            ran_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (publisher_id) REFERENCES publishers(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Veritabanı hazır")

def add_publisher(name, management_key, publisher_tag, find_string, replace_string, frequency_days=2):
    """Yeni publisher ekle"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO publishers 
        (name, management_key, publisher_tag, find_string, replace_string, frequency_days)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, management_key, publisher_tag, find_string, replace_string, frequency_days))
    conn.commit()
    publisher_id = c.lastrowid
    conn.close()
    print(f"[DB] Publisher eklendi: {name} (id={publisher_id})")
    return publisher_id

def get_active_publishers():
    """Aktif publisher'ları getir"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM publishers WHERE active = 1")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_publishers():
    """Tüm publisher'ları getir"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM publishers ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_publisher_version(publisher_id, new_find, new_replace, new_version):
    """Publisher'ın versiyon bilgisini güncelle"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE publishers 
        SET find_string = ?, replace_string = ?, current_version = ?, last_run = ?
        WHERE id = ?
    ''', (new_find, new_replace, new_version, datetime.now().isoformat(), publisher_id))
    conn.commit()
    conn.close()

def update_last_run(publisher_id):
    """Son çalışma zamanını güncelle"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE publishers SET last_run = ? WHERE id = ?",
        (datetime.now().isoformat(), publisher_id)
    )
    conn.commit()
    conn.close()

def log_operation(publisher_id, publisher_name, ad_unit_id, ad_unit_name, old_value, new_value, status, error_message=""):
    """Her ad unit operasyonunu logla"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO job_logs 
        (publisher_id, publisher_name, ad_unit_id, ad_unit_name, old_value, new_value, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (publisher_id, publisher_name, ad_unit_id, ad_unit_name, old_value, new_value, status, error_message))
    conn.commit()
    conn.close()

def get_job_logs(publisher_id=None, limit=100):
    """Job loglarını getir"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if publisher_id:
        c.execute(
            "SELECT * FROM job_logs WHERE publisher_id = ? ORDER BY ran_at DESC LIMIT ?",
            (publisher_id, limit)
        )
    else:
        c.execute("SELECT * FROM job_logs ORDER BY ran_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    init_db()
    
    add_publisher(
        name           = "TheGameOps Test",
        management_key = "e0757bd737fa69c9d7c8dea73f3e4d57bc403d2a557073180b8e3a938d773465e7759b6c89fb89297e66d2",
        publisher_tag  = "thegameops",
        find_string    = "_0_",
        replace_string = "_TEST_",
        frequency_days = 2
    )
    
    publishers = get_all_publishers()
    for p in publishers:
        print(f"  - {p['name']} | tag: {p['publisher_tag']} | find: {p['find_string']}")