from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import init_db, get_all_publishers, add_publisher, get_job_logs
from engine import run_refresh
import threading
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

class PublisherCreate(BaseModel):
    name: str
    management_key: str
    publisher_tag: str
    find_string: str
    replace_string: str
    frequency_days: int = 2

class PublisherUpdate(BaseModel):
    find_string: str
    replace_string: str
    frequency_days: int
    active: int

@app.get("/publishers")
def list_publishers():
    return get_all_publishers()

@app.post("/publishers")
def create_publisher(p: PublisherCreate):
    publisher_id = add_publisher(
        p.name, p.management_key, p.publisher_tag,
        p.find_string, p.replace_string, p.frequency_days
    )
    return {"id": publisher_id, "status": "created"}

@app.put("/publishers/{publisher_id}")
def update_publisher(publisher_id: int, p: PublisherUpdate):
    conn = sqlite3.connect("adsyield.db")
    c = conn.cursor()
    c.execute('''
        UPDATE publishers 
        SET find_string = ?, replace_string = ?, frequency_days = ?, active = ?
        WHERE id = ?
    ''', (p.find_string, p.replace_string, p.frequency_days, p.active, publisher_id))
    conn.commit()
    conn.close()
    return {"status": "updated"}

@app.post("/publishers/{publisher_id}/run")
def run_publisher(publisher_id: int, dry_run: bool = True):
    publishers = get_all_publishers()
    publisher = next((p for p in publishers if p["id"] == publisher_id), None)
    if not publisher:
        return {"error": "Publisher not found"}
    
    success, failed, skipped = run_refresh(publisher, dry_run=dry_run)
    
    if success == 0 and failed == 0:
        return {
            "status": "no_match",
            "message": f"Eşleşme bulunamadı. Find string'i kontrol et: {publisher['find_string']}",
            "success": 0,
            "failed": 0,
            "skipped": skipped
        }
    
    return {
        "status": "done",
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "dry_run": dry_run
    }
@app.delete("/publishers/{publisher_id}")
def delete_publisher(publisher_id: int):
    conn = sqlite3.connect("adsyield.db")
    c = conn.cursor()
    c.execute("DELETE FROM publishers WHERE id = ?", (publisher_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}
@app.get("/logs")
def list_logs():
    return get_job_logs(limit=200)