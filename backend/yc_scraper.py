import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from backend.logs import log
from backend import db

def scrape_yc_startup_jobs():
    url = "https://www.workatastartup.com/companies?demographic=any&hasEquity=any&hasSalary=any&industry=any&interviewProcess=any&jobType=fulltime&layout=list-compact&sortBy=created_desc&tab=any&usVisaNotRequired=any"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    log("Fetching Y Combinator Work at a Startup page...")
    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=20)
        if response.status_code != 200:
            log(f"Failed to fetch YC page: HTTP {response.status_code}")
            return 0
            
        soup = BeautifulSoup(response.text, "html.parser")
        div = soup.find("div", attrs={"data-page": True})
        if not div:
            log("Could not find data-page div in YC page HTML.")
            return 0
            
        data_str = div["data-page"]
        data = json.loads(data_str)
        
        props = data.get("props", {})
        jobs = props.get("jobs", [])
        
        if not jobs:
            log("No jobs array found in YC page props.")
            return 0
            
        log(f"Found {len(jobs)} jobs on YC page. Matching against profile...")
        
        experience_limit = int(db.get_config("filter_max_experience", "2"))
        
        added_count = 0
        for job in jobs:
            job_id = f"yc_{job.get('id')}"
            title = job.get("title")
            company = job.get("companyName")
            location = job.get("location")
            salary = job.get("salary") or "Not specified"
            
            company_slug = job.get("companySlug")
            one_liner = job.get("companyOneLiner") or ""
            
            # Experience and tech checks
            from backend.scraper import extract_experience, extract_tech_stack
            
            full_text = f"{title or ''} {one_liner}"
            job_exp_str = extract_experience(full_text)
            job_tech_list = extract_tech_stack(full_text)
            
            job_data = {
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "description": f"{one_liner}\n\nApply via YC Work at a Startup.\nRole Type: {job.get('roleType', '')}\nBatch: {job.get('companyBatch', '') or 'N/A'}\nLast Active: {job.get('companyLastActiveAt', '') or 'N/A'}",
                "experience": job_exp_str,
                "tech_stack": job_tech_list,
                "salary": salary,
                "apply_url": f"https://www.workatastartup.com/jobs/{job.get('id')}" if job.get('id') else "https://www.workatastartup.com/companies",
                "source": "Y Combinator",
                "date_posted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_targeted": 0,
                "portal_type": "YC"
            }
            
            is_new = db.add_job(job_data)
            if is_new:
                added_count += 1
                
        log(f"YC scrape completed. Added {added_count} new YC jobs matching settings.")
        return added_count
        
    except Exception as e:
        log(f"Error scraping YC: {e}")
        return 0
