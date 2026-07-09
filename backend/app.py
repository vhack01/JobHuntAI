import os
import io
import json
import re
from fastapi import FastAPI, BackgroundTasks, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import pandas as pd
from pydantic import BaseModel

from backend import db, scraper, scheduler, logs

app = FastAPI(title="Job Tracker & Scraper API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to initialize DB and Scheduler (serverless-aware)
@app.on_event("startup")
def startup_event():
    try:
        db.init_db()
        logs.log("Database initialized successfully.")
    except Exception as e:
        logs.log(f"WARNING: Database initialization failed: {e}")
        
    # Disable APScheduler in Vercel serverless functions to avoid blockages
    if os.environ.get("VERCEL"):
        logs.log("FastAPI backend started in serverless mode (Vercel). Scheduler thread disabled.")
    else:
        try:
            scheduler.start_scheduler()
            logs.log("FastAPI backend started. Database and scheduler initialized.")
        except Exception as e:
            logs.log(f"WARNING: Scheduler startup failed: {e}")

# Job Status update model
class StatusUpdate(BaseModel):
    status: str

# Job Notes update model
class NotesUpdate(BaseModel):
    notes: str

@app.get("/api/jobs")
def get_jobs(status: str = None, search: str = None):
    try:
        return db.get_jobs(status=status, search=search)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/jobs/{job_id}/status")
def update_job_status(job_id: str, body: StatusUpdate):
    try:
        db.update_job_status(job_id, body.status)
        logs.log(f"Updated status of job '{job_id}' to '{body.status}'")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/jobs/{job_id}/notes")
def update_job_notes(job_id: str, body: NotesUpdate):
    try:
        db.update_job_notes(job_id, body.notes)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    try:
        # Check if already running or just trigger in background
        background_tasks.add_task(scheduler.run_background_scrape)
        logs.log("Manual scrape triggered by user.")
        return {"status": "started", "message": "Scrape task initiated in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CompanyScrapeRequest(BaseModel):
    company: str

@app.post("/api/jobs/scrape-company")
def trigger_company_scrape(body: CompanyScrapeRequest, background_tasks: BackgroundTasks):
    try:
        if not body.company or not body.company.strip():
            raise HTTPException(status_code=400, detail="Company name is required.")
        background_tasks.add_task(scraper.run_company_search, body.company.strip())
        logs.log(f"Manual single-company scan triggered for: '{body.company}'")
        return {"status": "started", "message": f"Scan for '{body.company}' initiated in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/upload-companies")
def upload_companies(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    try:
        content_bytes = file.file.read()
        content = content_bytes.decode("utf-8")
        companies = []
        filename = file.filename.lower()
        
        if filename.endswith(".txt"):
            for line in content.splitlines():
                name = line.strip()
                if name:
                    companies.append(name)
        elif filename.endswith(".csv"):
            import csv
            import io
            f = io.StringIO(content)
            reader = csv.reader(f)
            for row in reader:
                if row:
                    name = row[0].strip()
                    if name and name.lower() not in ["company", "company name", "employer", "employer name", "companies"]:
                        companies.append(name)
        else:
            raise HTTPException(status_code=400, detail="Only .txt and .csv files are supported.")
            
        if not companies:
            raise HTTPException(status_code=400, detail="No valid company names found in the uploaded file.")
            
        # Add to target companies config
        target_companies_raw = db.get_config("target_companies", "[]")
        try:
            target_companies = json.loads(target_companies_raw)
        except:
            target_companies = []
            
        # Merge lists and deduplicate
        updated_companies = list(set(target_companies + companies))
        db.set_config("target_companies", json.dumps(updated_companies))
        
        # Trigger background scanning for these specific companies
        def run_bulk_scan(companies_list):
            logs.log(f"Starting bulk company scan for uploaded list: {companies_list}")
            for company in companies_list:
                try:
                    scraper.run_company_search(company)
                except Exception as e:
                    logs.log(f"Error scanning company '{company}': {e}")
            logs.log("Bulk uploaded companies scan finished.")
            
        background_tasks.add_task(run_bulk_scan, companies)
        logs.log(f"Uploaded company file '{file.filename}'. Found {len(companies)} companies.")
        
        return {
            "status": "success", 
            "companies_added": companies, 
            "message": f"Successfully loaded {len(companies)} companies and initiated scan."
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
def get_config():
    try:
        raw_config = db.get_all_config()
        # Parse JSON fields
        config = {}
        for k, v in raw_config.items():
            if k in ["search_keywords", "search_locations", "target_companies"]:
                try:
                    config[k] = json.loads(v)
                except:
                    config[k] = []
            else:
                config[k] = v
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
def update_config(config_data: dict = Body(...)):
    try:
        for k, v in config_data.items():
            if k in ["search_keywords", "search_locations", "target_companies"]:
                db.set_config(k, json.dumps(v))
            else:
                db.set_config(k, str(v))
        
        # Reschedule jobs with new timings
        scheduler.reschedule_jobs()
        logs.log("Scheduler configuration updated and jobs rescheduled.")
        return {"status": "success", "message": "Configuration updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
def get_app_logs():
    return {"logs": logs.get_logs()}

@app.post("/api/logs/clear")
def clear_app_logs():
    logs.clear_logs()
    return {"status": "success"}

@app.get("/api/jobs/export")
def export_jobs_excel():
    try:
        jobs = db.get_jobs()
        if not jobs:
            # Return empty excel
            df = pd.DataFrame(columns=["job_id", "title", "company", "location", "experience", "tech_stack", "salary", "apply_url", "source", "date_posted", "date_found", "status", "notes"])
        else:
            df = pd.DataFrame(jobs)
            
            # Apply configuration preference filters to Excel output
            import re
            max_exp_str = db.get_config("filter_max_experience")
            show_unspecified_str = db.get_config("filter_show_unspecified_exp", "true")
            min_sal_str = db.get_config("filter_min_salary", "")
            
            if max_exp_str and "experience" in df.columns:
                try:
                    max_exp = int(max_exp_str)
                    show_unspecified = show_unspecified_str == "true"
                    
                    def match_experience(exp):
                        if not exp or str(exp) == "Not specified":
                            return show_unspecified
                        num_match = re.search(r'(\d+)', str(exp))
                        if num_match:
                            return int(num_match.group(1)) <= max_exp
                        return show_unspecified
                        
                    df = df[df['experience'].apply(match_experience)]
                except Exception as ex:
                    logs.log(f"Excel experience filtering error: {ex}")
                    
            if min_sal_str and "salary" in df.columns:
                def match_salary(sal):
                    if not sal or str(sal) == "Not specified":
                        return False
                    return True
                df = df[df['salary'].apply(match_salary)]
            
        # Reorder columns for readability and drop descriptions to keep sheet light
        cols = ["title", "company", "location", "experience", "tech_stack", "salary", "status", "source", "date_posted", "apply_url", "notes", "job_id"]
        # Ensure columns exist before filtering
        existing_cols = [c for c in cols if c in df.columns]
        df = df[existing_cols]
        
        # Rename columns to proper headers
        column_mapping = {
            "title": "Job Title",
            "company": "Company Name",
            "location": "Location",
            "experience": "Experience Required",
            "tech_stack": "Tech Stack",
            "salary": "Salary",
            "status": "Tracking Status",
            "source": "Platform Source",
            "date_posted": "Posted Date",
            "apply_url": "Direct Apply Link",
            "notes": "My Notes",
            "job_id": "Job ID"
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write 'All Jobs' sheet
            df.to_excel(writer, sheet_name='All Jobs', index=False)
            
            # Write status-based sheets
            status_col = "Tracking Status"
            if status_col in df.columns:
                statuses = ['New', 'Interested', 'Applied', 'Interviewing', 'Rejected']
                for status in statuses:
                    status_df = df[df[status_col] == status]
                    status_df.to_excel(writer, sheet_name=status, index=False)
            
            # Apply styling to columns in openpyxl
            workbook = writer.book
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                # Auto-fit columns
                for col in sheet.columns:
                    max_len = 0
                    col_letter = col[0].column_letter
                    for cell in col:
                        if cell.value:
                            max_len = max(max_len, len(str(cell.value)))
                    sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 50)
                
                # Format header row
                for cell in sheet[1]:
                    cell.font = cell.font.copy(bold=True)
                    
            workbook.save(filename=None) # Keep raw bytes stream
            
        output.seek(0)
        
        headers = {
            'Content-Disposition': 'attachment; filename="job_tracking_list.xlsx"'
        }
        return StreamingResponse(
            output, 
            headers=headers, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Master tech keywords list for resume matching
MASTER_SKILLS = [
    # Languages
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Golang", "Rust", "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala",
    # Backend Frameworks
    "Spring Boot", "Spring", "FastAPI", "Django", "Flask", "Express", "Node.js", "NestJS", "Ruby on Rails", "Laravel", "ASP.NET",
    # Frontend
    "React", "Angular", "Vue", "Svelte", "Next.js", "Nuxt.js", "Redux", "HTML5", "CSS3", "Tailwind",
    # Databases & Cache
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Cassandra", "DynamoDB", "Elasticsearch", "Oracle",
    # Cloud & DevOps
    "AWS", "Google Cloud", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible", "CI/CD", "Jenkins", "GitLab", "GitHub Actions",
    # AI & Messaging
    "LangGraph", "LangChain", "OpenAI", "PyTorch", "TensorFlow", "Pandas", "NumPy", "Apache Spark", "Kafka", "REST API", "GraphQL", "Microservices"
]

COMMON_TITLES = [
    "Software Engineer", "Software Developer", "Full Stack Developer", "Full Stack Engineer", 
    "Backend Engineer", "Backend Developer", "Frontend Engineer", "Frontend Developer", 
    "Data Engineer", "Data Scientist", "AI Engineer", "Machine Learning Engineer", 
    "DevOps Engineer", "Cloud Engineer", "Android Developer", "iOS Developer"
]

class ResumeApplyModel(BaseModel):
    experience: int
    skills: list
    keywords: list

@app.post("/api/resume/parse")
async def parse_resume(file: UploadFile = File(...)):
    filename = file.filename.lower()
    
    if not (filename.endswith(".pdf") or filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")
        
    try:
        # Read raw bytes
        file_bytes = await file.read()
        
        # Extract text content
        if filename.endswith(".pdf"):
            pdf_file = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
            
        if not text.strip():
            raise HTTPException(status_code=400, detail="No readable text found in the uploaded file.")
            
        # Parse Experience level
        experience_years = 2 # Default fallback
        exp_patterns = [
            r'(\d+)\s*\+\s*years?\s*(?:of)?\s*experience',
            r'experience\s*(?:of|:)?\s*(\d+)\s*(?:\+)?\s*years?',
            r'(\d+)\s*(?:to|-)\s*(\d+)\s*years?\s*(?:of)?\s*experience',
            r'(\d+)\s*years?\s*experience',
            r'(\d+)\s*yrs?\s*experience'
        ]
        for pattern in exp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                experience_years = int(groups[0])
                break
        else:
            # Fallback search
            match = re.search(r'\bexperience\b.{0,30}\b(\d+)\b', text, re.IGNORECASE | re.DOTALL)
            if match:
                experience_years = int(match.group(1))
                
        # Bound experience to reasonable developer limits (0 to 15)
        experience_years = max(0, min(15, experience_years))
        
        # Extract skills
        extracted_skills = []
        text_lower = text.lower()
        for skill in MASTER_SKILLS:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if "ci/cd" in skill.lower() or "/" in skill:
                pattern = re.escape(skill.lower())
            if re.search(pattern, text_lower):
                extracted_skills.append(skill)
                
        # Fallback if no skills matched
        if not extracted_skills:
            extracted_skills = ["Java", "Spring Boot", "React", "Python"]
            
        # Extract Job Titles to suggest search keywords
        detected_titles = []
        for title in COMMON_TITLES:
            pattern = r'\b' + re.escape(title.lower()) + r'\b'
            if re.search(pattern, text_lower):
                detected_titles.append(title)
                
        # Suggest Search Keywords based on titles and primary skills
        suggestions = []
        primary_skills = [s for s in extracted_skills if s in ["Java", "Python", "React", "TypeScript", "Go", "AWS", "Rust", "Node.js"]][:3]
        if not detected_titles:
            detected_titles = ["Software Engineer", "Backend Developer"]
            
        for title in detected_titles[:2]:
            suggestions.append(title)
            for skill in primary_skills:
                suggestions.append(f"{title} {skill}")
                
        # Add tech combos
        if "Java" in extracted_skills and "Spring Boot" in extracted_skills:
            suggestions.append("Java Spring Boot Developer")
        if "Python" in extracted_skills and "FastAPI" in extracted_skills:
            suggestions.append("FastAPI Python Backend")
        if "React" in extracted_skills and "TypeScript" in extracted_skills:
            suggestions.append("React TypeScript Developer")
            
        # Deduplicate suggestions
        seen = set()
        deduped_suggestions = []
        for s in suggestions:
            if s.lower() not in seen:
                seen.add(s.lower())
                deduped_suggestions.append(s)
                
        return {
            "status": "success",
            "experience": experience_years,
            "skills": extracted_skills,
            "suggested_keywords": deduped_suggestions[:6],
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")

@app.post("/api/resume/apply")
async def apply_resume_profile(data: ResumeApplyModel):
    try:
        # Update database configs
        db.set_config("filter_max_experience", str(data.experience))
        db.set_config("tech_keywords", json.dumps(data.skills))
        db.set_config("search_keywords", json.dumps(data.keywords))
        
        # Reschedule scraping runs with new keywords
        try:
            scheduler.reschedule_jobs()
        except Exception as se:
            logs.log(f"Rescheduling failed on resume sync: {se}")
            
        logs.log(f"Synced job hunt search profile with uploaded resume data. Active experience limit set to <= {data.experience} years.")
        
        return {
            "status": "success",
            "message": "Successfully applied resume settings to search profile."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serving static frontend folder
# Ensure folder exists first
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
