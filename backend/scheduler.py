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
        
        # 1. Scrape standard job portals
        new_jobs, total = scraper.run_job_search()
        log(f"Scheduled portal scrape complete. Added {new_jobs} new jobs (Scraped: {total}).")
        
        # 2. Scrape target company career boards
        from backend import career_scraper
        career_jobs = career_scraper.scrape_all_careers()
        log(f"Scheduled career pages scrape complete. Added {career_jobs} new jobs.")
        
    except Exception as e:
        log(f"Error in background scrape: {e}")
    finally:
        update_next_run_time()

def run_daily_active_check():
    try:
        log("Triggering daily active status verification check...")
        scraper.sync_active_status_job()
    except Exception as e:
        log(f"Error in daily active status check: {e}")
    finally:
        update_next_run_time()

def update_next_run_time():
    if not scheduler.running:
        db.set_config("next_run", "Disabled (Serverless Mode)")
        return
        
    next_runs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        if next_run:
            next_runs.append(f"{job.id}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    if next_runs:
        db.set_config("next_run", " | ".join(next_runs))
    else:
        db.set_config("next_run", "Not scheduled")

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
    reschedule_jobs()
    log("Background scheduler started successfully.")

def reschedule_jobs():
    if not scheduler.running:
        log("Scheduler is not running (serverless mode). Skipping reschedule_jobs.")
        return
        
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
        
    try:
        scheduler.add_job(
            run_daily_active_check,
            CronTrigger(hour=3, minute=0),
            id="daily_active_check"
        )
        log("Scheduled daily active status verification check for 03:00 AM")
    except Exception as e:
        log(f"Failed to schedule daily active check: {e}")
        
    update_next_run_time()
