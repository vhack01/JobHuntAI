from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend import db, scraper
from backend.logs import log
from datetime import datetime
import json

scheduler = BackgroundScheduler()

def run_background_scrape():
    try:
        log("Triggering scheduled background job scrape...")
        new_jobs, total = scraper.run_job_search()
        log(f"Scheduled background scrape complete. Added {new_jobs} new jobs (Scraped: {total}).")
    except Exception as e:
        log(f"Error in background scrape: {e}")
    finally:
        update_next_run_time()

def update_next_run_time():
    next_runs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        if next_run:
            next_runs.append(next_run.strftime("%Y-%m-%d %H:%M:%S"))
    if next_runs:
        db.set_config("next_run", ", ".join(next_runs))
    else:
        db.set_config("next_run", "Not scheduled")

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
    reschedule_jobs()
    log("Background scheduler started successfully.")

def reschedule_jobs():
    for job in list(scheduler.get_jobs()):
        scheduler.remove_job(job.id)
        
    morning_time = db.get_config("schedule_morning", "09:00")
    evening_time = db.get_config("schedule_evening", "18:00")
    
    try:
        m_hour, m_minute = map(int, morning_time.split(":"))
        scheduler.add_job(
            run_background_scrape, 
            CronTrigger(hour=m_hour, minute=m_minute), 
            id="morning_scrape"
        )
        log(f"Scheduled morning scrape for {morning_time}")
    except Exception as e:
        log(f"Failed to schedule morning job for {morning_time}: {e}")
        
    try:
        e_hour, e_minute = map(int, evening_time.split(":"))
        scheduler.add_job(
            run_background_scrape, 
            CronTrigger(hour=e_hour, minute=e_minute), 
            id="evening_scrape"
        )
        log(f"Scheduled evening scrape for {evening_time}")
    except Exception as e:
        log(f"Failed to schedule evening job for {evening_time}: {e}")
        
    update_next_run_time()
