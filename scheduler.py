import time
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from database import init_db, get_active_publishers
from engine import run_refresh

scheduler = BlockingScheduler()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def run_publisher_job(publisher):
    log(f"Scheduler tetikledi: {publisher['name']}")
    run_refresh(publisher, dry_run=False)

def setup_jobs():
    publishers = get_active_publishers()
    if not publishers:
        log("Aktif publisher yok.")
        return

    for publisher in publishers:
        job_id = f"publisher_{publisher['id']}"
        interval_days = publisher.get("frequency_days", 2)

        scheduler.add_job(
            run_publisher_job,
            trigger="interval",
            days=interval_days,
            args=[publisher],
            id=job_id,
            name=publisher["name"],
            next_run_time=datetime.now() + timedelta(seconds=10)
        )
        log(f"Job eklendi: {publisher['name']} — her {interval_days} günde bir")

def main():
    init_db()
    log("=== Adsyield Scheduler basliyor ===")
    setup_jobs()

    if not scheduler.get_jobs():
        log("Hic job yok, cikiyor.")
        return

    log("Scheduler calisiyor. Durdurmak icin Ctrl+C")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log("Scheduler durduruldu.")

if __name__ == "__main__":
    main()