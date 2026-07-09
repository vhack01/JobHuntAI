import re
import time
import json
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from jobspy import scrape_jobs
from backend import db
from backend.logs import log

def extract_tech_stack(text):
    if not text:
        return ""
        
    # Load tech keywords dynamically from the database config
    tech_keywords_str = db.get_config("tech_keywords")
    if tech_keywords_str:
        try:
            tech_keywords = json.loads(tech_keywords_str)
        except Exception:
            tech_keywords = [
                "Java", "Spring Boot", "Spring", "Hibernate", "JPA", "Hibernate/JPA",
                "React", "ReactJS", "Redux", "TypeScript", "JavaScript", "HTML5", "CSS3",
                "LangChain", "LangGraph", "Python", "FastAPI", "REST API", "Microservices",
                "MySQL", "PostgreSQL", "Redis", "Apache Kafka", "Kafka", "Apache Spark", "Spark",
                "AWS", "Docker", "Kubernetes", "Terraform", "GitLab CI/CD", "Git", "Datadog", "Grafana", "K6"
            ]
    else:
        tech_keywords = [
            "Java", "Spring Boot", "Spring", "Hibernate", "JPA", "Hibernate/JPA",
            "React", "ReactJS", "Redux", "TypeScript", "JavaScript", "HTML5", "CSS3",
            "LangChain", "LangGraph", "Python", "FastAPI", "REST API", "Microservices",
            "MySQL", "PostgreSQL", "Redis", "Apache Kafka", "Kafka", "Apache Spark", "Spark",
            "AWS", "Docker", "Kubernetes", "Terraform", "GitLab CI/CD", "Git", "Datadog", "Grafana", "K6"
        ]
        
    matched = []
    text_lower = text.lower()
    for tech in tech_keywords:
        pattern = r'\b' + re.escape(tech.lower()) + r'\b'
        if "ci/cd" in tech.lower() or "hibernate/jpa" in tech.lower() or "/" in tech:
            pattern = re.escape(tech.lower())
        
        if re.search(pattern, text_lower):
            matched.append(tech)
            
    return ", ".join(matched)

def extract_experience(text):
    if not text:
        return "Not specified"
        
    patterns = [
        r'(\d+)\s*(?:to|-)\s*(\d+)\s*years?',
        r'(\d+)\s*\+\s*years?',
        r'experience\s*of\s*(\d+)\s*years?',
        r'(\d+)\s*years?\s*\+?',
        r'(\d+)\s*yrs?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                return f"{groups[0]}-{groups[1]} years"
            else:
                return f"{groups[0]}+ years"
                
    return "Not specified"

def extract_salary(row, text):
    min_amt = row.get("min_amount")
    max_amt = row.get("max_amount")
    currency = row.get("currency") or ""
    interval = row.get("interval") or ""
    
    if min_amt is not None and max_amt is not None:
        return f"{currency} {min_amt} - {max_amt} ({interval})".strip()
    elif min_amt is not None:
        return f"{currency} {min_amt}+ ({interval})".strip()
        
    if not text:
        return "Not specified"
        
    salary_patterns = [
        r'(\d+\s*-\s*\d+\s*(?:LPA|Lakhs?|L))',
        r'(\d+\s*(?:LPA|Lakhs?|L))',
        r'(\$\s*\d+k\s*-\s*\$\s*\d+k)',
        r'(?:salary|package|compensation)\s*(?:of|is|range)?\s*([^,\.\n\(\)]+)'
    ]
    
    for pattern in salary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            if len(val) < 40 and any(char.isdigit() for char in val):
                return val
                
    return "Not specified"

def fetch_linkedin_description(job_id):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            desc_div = soup.find("div", class_="description__text") or soup.find("div", class_="show-more-less-html__markup")
            if desc_div:
                return desc_div.get_text(separator="\n", strip=True)
    except Exception as e:
        log(f"Error fetching description for LI job {job_id}: {e}")
    return None

def scrape_query(keyword, location, company_name=None):
    new_jobs_count = 0
    total_scraped_count = 0
    
    search_term = keyword
    if company_name:
        search_term = f"{company_name} {keyword}"
        log(f"Scraping company '{company_name}' for '{keyword}' in '{location}'...")
    else:
        log(f"Scraping '{keyword}' in '{location}'...")
        
    try:
        jobs_df = scrape_jobs(
            site_name=["linkedin", "google"],
            search_term=search_term,
            location=location,
            results_wanted=10,
            hours_old=48
        )
        
        if jobs_df is None or jobs_df.empty:
            log(f"No jobs found for search '{search_term}' in '{location}'")
            return 0, 0
            
        total_scraped_count = len(jobs_df)
        
        for _, row in jobs_df.iterrows():
            raw_id = row.get("id")
            if not raw_id:
                continue
                
            site = row.get("site", "unknown")
            title = row.get("title")
            company = row.get("company")
            job_loc = row.get("location")
            job_url = row.get("job_url_direct") or row.get("job_url")
            date_posted = str(row.get("date_posted") or "")
            
            # Filter matches by target company if company_name is specified (avoids loose match pollution)
            if company_name and company:
                if company_name.lower() not in company.lower():
                    continue
            
            description = row.get("description")
            
            if site == "linkedin" and not description:
                li_match = re.search(r'\b(\d+)\b', raw_id)
                if li_match:
                    li_id = li_match.group(1)
                    time.sleep(random.uniform(1.0, 2.0))
                    description = fetch_linkedin_description(li_id)
                    
            full_text = f"{title or ''} {description or ''}"
            tech_stack = extract_tech_stack(full_text)
            experience = extract_experience(full_text)
            salary = extract_salary(row, description)
            
            job_data = {
                "job_id": raw_id,
                "title": title,
                "company": company,
                "location": job_loc,
                "description": description or "No description available",
                "experience": experience,
                "tech_stack": tech_stack,
                "salary": salary,
                "apply_url": job_url,
                "source": site.capitalize(),
                "date_posted": date_posted,
                "is_targeted": 1 if company_name else 0
            }
            
            is_new = db.add_job(job_data)
            if is_new:
                new_jobs_count += 1
                
    except Exception as e:
        log(f"Scraper error for search '{search_term}' in '{location}': {e}")
        
    return new_jobs_count, total_scraped_count

def run_job_search():
    log("Starting job search scrape...")
    
    keywords_raw = db.get_config("search_keywords", "[]")
    locations_raw = db.get_config("search_locations", "[]")
    target_companies_raw = db.get_config("target_companies", "[]")
    
    try:
        keywords = json.loads(keywords_raw)
        locations = json.loads(locations_raw)
        target_companies = json.loads(target_companies_raw)
    except Exception as e:
        log(f"Error reading config JSON: {e}. Using defaults.")
        keywords = ["Java Spring Boot Kafka", "LangGraph AI Agent", "FastAPI Python Backend"]
        locations = ["Hyderabad", "India", "Remote"]
        target_companies = []
        
    db.set_config("last_run", datetime.now().isoformat())
    
    new_jobs_count = 0
    total_scraped_count = 0
    
    # 1. Run general searches
    for location in locations:
        for keyword in keywords:
            new_c, total_c = scrape_query(keyword, location)
            new_jobs_count += new_c
            total_scraped_count += total_c
            time.sleep(random.uniform(1.0, 2.5))
            
    # 2. Run target companies searches if configured
    if target_companies:
        log(f"Starting target companies scraping for: {target_companies}")
        for company in target_companies:
            for location in locations:
                for keyword in keywords:
                    new_c, total_c = scrape_query(keyword, location, company_name=company)
                    new_jobs_count += new_c
                    total_scraped_count += total_c
                    time.sleep(random.uniform(1.0, 2.5))
            
    log(f"Job search finished. Scraped: {total_scraped_count}, New added: {new_jobs_count}")
    return new_jobs_count, total_scraped_count

def run_company_search(company_name):
    log(f"Starting targeted single-company scan for: '{company_name}'...")
    
    keywords_raw = db.get_config("search_keywords", "[]")
    locations_raw = db.get_config("search_locations", "[]")
    
    try:
        keywords = json.loads(keywords_raw)
        locations = json.loads(locations_raw)
    except Exception as e:
        log(f"Error reading config JSON: {e}. Using defaults.")
        keywords = ["Java Spring Boot Kafka", "LangGraph AI Agent", "FastAPI Python Backend"]
        locations = ["Hyderabad", "India", "Remote"]
        
    new_jobs_count = 0
    total_scraped_count = 0
    
    for location in locations:
        for keyword in keywords:
            new_c, total_c = scrape_query(keyword, location, company_name=company_name)
            new_jobs_count += new_c
            total_scraped_count += total_c
            time.sleep(random.uniform(1.0, 2.0))
            
    log(f"Targeted single-company scan finished. Scraped: {total_scraped_count}, New added: {new_jobs_count}")
    return new_jobs_count, total_scraped_count
