import os
import re
import json
import requests
from datetime import datetime
from backend import db, logs, scraper

def get_company_slugs(company_name):
    name = company_name.lower().strip()
    slugs = []
    
    # Strip common business suffixes
    name = re.sub(r'\b(inc|corp|labs|ltd|co|software|technologies|solutions|group|cloud)\b', '', name).strip()
    
    # Strip non-alphanumeric characters except spaces
    clean_name = re.sub(r'[^a-z0-9\s-]', '', name)
    
    # Generate variations
    slugs.append(clean_name.replace(" ", ""))
    slugs.append(clean_name.replace(" ", "-"))
    
    # Deduplicate
    return list(set([s for s in slugs if len(s) > 1]))

def check_resume_match(title, description, tech_keywords, max_exp, show_unspecified):
    full_text = f"{title}\n{description}".lower()
    
    # 1. Tech keywords match: must match at least one tech stack keyword
    matched_skills = []
    for skill in tech_keywords:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if "ci/cd" in skill.lower() or "/" in skill:
            pattern = re.escape(skill.lower())
        if re.search(pattern, full_text):
            matched_skills.append(skill)
            
    if not matched_skills:
        return False, [], "Not specified"
        
    # 2. Experience limit check
    exp_str = scraper.extract_experience(full_text)
    exp_years = None
    if exp_str != "Not specified":
        match = re.search(r'(\d+)', exp_str)
        if match:
            exp_years = int(match.group(1))
            
    if exp_years is not None:
        if exp_years > max_exp:
            return False, [], "Not specified"
    else:
        if not show_unspecified:
            return False, [], "Not specified"
            
    return True, matched_skills, exp_str

def scrape_greenhouse_company(company_name, slug, tech_keywords, max_exp, show_unspecified):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        response = requests.get(url, timeout=12)
        if response.status_code != 200:
            return []
            
        data = response.json()
        jobs = data.get("jobs", [])
        matched_jobs = []
        
        for job in jobs:
            title = job.get("title", "")
            description_html = job.get("content", "")
            description_text = re.sub(r'<[^>]*>', ' ', description_html)
            
            is_match, matched_skills, exp_str = check_resume_match(
                title, description_text, tech_keywords, max_exp, show_unspecified
            )
            
            if is_match:
                salary_str = scraper.extract_salary({}, description_text)
                location = job.get("location", {}).get("name", "Remote")
                job_id = f"career-gh-{slug}-{job.get('id')}"
                
                job_entry = {
                    "job_id": job_id,
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "description": description_html,
                    "experience": exp_str,
                    "tech_stack": ", ".join(matched_skills),
                    "salary": salary_str,
                    "apply_url": job.get("absolute_url"),
                    "source": "Greenhouse",
                    "date_posted": job.get("updated_at", datetime.now().isoformat()),
                    "is_targeted": 1,
                    "portal_type": "Career"
                }
                matched_jobs.append(job_entry)
        return matched_jobs
    except Exception as e:
        logs.log(f"Greenhouse crawl exception for {company_name} ({slug}): {e}")
        return []

def scrape_lever_company(company_name, slug, tech_keywords, max_exp, show_unspecified):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        response = requests.get(url, timeout=12)
        if response.status_code != 200:
            return []
            
        jobs = response.json()
        if not isinstance(jobs, list):
            return []
            
        matched_jobs = []
        for job in jobs:
            title = job.get("text", "")
            description = job.get("description", "")
            desc_body = job.get("descriptionBody", "")
            
            # Combine content lists
            lists_html = ""
            for item in job.get("lists", []):
                lists_html += f"<h3>{item.get('text', '')}</h3><ul>{item.get('content', '')}</ul>"
                
            full_description_html = f"<div>{description}</div>{lists_html}<div>{job.get('additional', '')}</div>"
            description_text = re.sub(r'<[^>]*>', ' ', full_description_html) + f"\n{desc_body}"
            
            is_match, matched_skills, exp_str = check_resume_match(
                title, description_text, tech_keywords, max_exp, show_unspecified
            )
            
            if is_match:
                salary_str = scraper.extract_salary({}, description_text)
                location = job.get("categories", {}).get("location", "Remote")
                job_id = f"career-lv-{slug}-{job.get('id')}"
                
                job_entry = {
                    "job_id": job_id,
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "description": full_description_html,
                    "experience": exp_str,
                    "tech_stack": ", ".join(matched_skills),
                    "salary": salary_str,
                    "apply_url": job.get("hostedUrl"),
                    "source": "Lever",
                    "date_posted": datetime.now().isoformat(),
                    "is_targeted": 1,
                    "portal_type": "Career"
                }
                matched_jobs.append(job_entry)
        return matched_jobs
    except Exception as e:
        logs.log(f"Lever crawl exception for {company_name} ({slug}): {e}")
        return []

def scrape_all_careers():
    logs.log("Starting targeted company career pages scraping job...")
    
    companies_str = db.get_config("target_companies", "[]")
    try:
        companies = json.loads(companies_str)
    except Exception:
        companies = []
        
    tech_keywords_str = db.get_config("tech_keywords", "[]")
    try:
        tech_keywords = json.loads(tech_keywords_str)
    except Exception:
        tech_keywords = []
        
    max_exp_str = db.get_config("filter_max_experience", "2")
    try:
        max_exp = int(max_exp_str)
    except ValueError:
        max_exp = 2
        
    show_unspecified = db.get_config("filter_show_unspecified_exp", "true").lower() == "true"
    
    if not companies:
        logs.log("No target companies configured. Career page scraper aborted.")
        return 0
        
    new_jobs_count = 0
    total_processed = 0
    
    logs.log(f"Scanning boards for {len(companies)} target companies against {len(tech_keywords)} technologies...")
    
    for company in companies:
        slugs = get_company_slugs(company)
        company_jobs = []
        
        for slug in slugs:
            gh_jobs = scrape_greenhouse_company(company, slug, tech_keywords, max_exp, show_unspecified)
            if gh_jobs:
                company_jobs.extend(gh_jobs)
                logs.log(f"Discovered {len(gh_jobs)} postings for {company} on Greenhouse board '{slug}'")
                
            lv_jobs = scrape_lever_company(company, slug, tech_keywords, max_exp, show_unspecified)
            if lv_jobs:
                company_jobs.extend(lv_jobs)
                logs.log(f"Discovered {len(lv_jobs)} postings for {company} on Lever board '{slug}'")
                
        # Deduplicate jobs parsed from multiple slug tries
        seen_job_ids = set()
        unique_jobs = []
        for j in company_jobs:
            if j["job_id"] not in seen_job_ids:
                seen_job_ids.add(j["job_id"])
                unique_jobs.append(j)
                
        # Insert unique matched postings
        for job in unique_jobs:
            try:
                is_new = db.add_job(job)
                if is_new:
                    new_jobs_count += 1
                total_processed += 1
            except Exception as e:
                logs.log(f"Error inserting career job {job.get('title')} ({company}): {e}")
                
    logs.log(f"Target company careers scrape completed. Processed {total_processed} matching jobs. Added {new_jobs_count} new listings.")
    return new_jobs_count
