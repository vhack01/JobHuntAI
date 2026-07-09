// Global State
let jobsData = [];
let configData = {};
let activePanel = "dashboard";
let activeJob = null;
let isSyncing = false;
let logInterval = null;
let parsedResumeData = {
    experience: 2,
    skills: [],
    suggested_keywords: []
};

// DOM Elements
const elements = {
    sunIcon: document.querySelector(".sun-icon"),
    moonIcon: document.querySelector(".moon-icon"),
    themeToggleBtn: document.getElementById("themeToggleBtn"),
    navButtons: document.querySelectorAll(".nav-btn"),
    panels: document.querySelectorAll(".panel"),
    viewTitle: document.getElementById("viewTitle"),
    viewSub: document.getElementById("viewSub"),
    syncStatus: document.getElementById("syncStatus"),
    syncText: document.getElementById("syncText"),
    syncNowBtn: document.getElementById("syncNowBtn"),
    exportBtn: document.getElementById("exportBtn"),
    toastContainer: document.getElementById("toastContainer"),
    
    // Stats
    statTotal: document.getElementById("statTotal"),
    statInterested: document.getElementById("statInterested"),
    statApplied: document.getElementById("statApplied"),
    statInterviewing: document.getElementById("statInterviewing"),
    legendNew: document.getElementById("legendNew"),
    legendInterested: document.getElementById("legendInterested"),
    legendApplied: document.getElementById("legendApplied"),
    legendInterviewing: document.getElementById("legendInterviewing"),
    pipelineProgressCircle: document.getElementById("pipelineProgressCircle"),
    pipelineProgressPercent: document.getElementById("pipelineProgressPercent"),
    
    // Scheduler Display
    lblMorningTime: document.getElementById("lblMorningTime"),
    lblEveningTime: document.getElementById("lblEveningTime"),
    statLastRun: document.getElementById("statLastRun"),
    statNextRun: document.getElementById("statNextRun"),
    lblActiveProfile: document.getElementById("lblActiveProfile"),
    
    // Tables
    mainJobsTable: document.getElementById("mainJobsTable"),
    recentJobsTableBody: document.getElementById("recentJobsTableBody"),
    jobsTableBody: document.getElementById("jobsTableBody"),
    jobsEmptyState: document.getElementById("jobsEmptyState"),
    viewAllJobsBtn: document.getElementById("viewAllJobsBtn"),
    
    // Filters
    jobsSearchInput: document.getElementById("jobsSearchInput"),
    filterStatus: document.getElementById("filterStatus"),
    filterExperience: document.getElementById("filterExperience"),
    filterSalary: document.getElementById("filterSalary"),
    filterLocation: document.getElementById("filterLocation"),
    filterRecency: document.getElementById("filterRecency"),
    filterMatchType: document.getElementById("filterMatchType"),
    filterSource: document.getElementById("filterSource"),
    
    // Settings
    keywordsTagsWrapper: document.getElementById("keywordsTagsWrapper"),
    locationsTagsWrapper: document.getElementById("locationsTagsWrapper"),
    keywordInput: document.getElementById("keywordInput"),
    locationInput: document.getElementById("locationInput"),
    addKeywordBtn: document.getElementById("addKeywordBtn"),
    addLocationBtn: document.getElementById("addLocationBtn"),
    morningTime: document.getElementById("morningTime"),
    eveningTime: document.getElementById("eveningTime"),
    prefMaxExperience: document.getElementById("prefMaxExperience"),
    prefShowUnspecified: document.getElementById("prefShowUnspecified"),
    prefMinSalary: document.getElementById("prefMinSalary"),
    companiesTagsWrapper: document.getElementById("companiesTagsWrapper"),
    companyInput: document.getElementById("companyInput"),
    addCompanyBtn: document.getElementById("addCompanyBtn"),
    scanCompanyInput: document.getElementById("scanCompanyInput"),
    triggerScanCompanyBtn: document.getElementById("triggerScanCompanyBtn"),
    companyListFile: document.getElementById("companyListFile"),
    uploadFileName: document.getElementById("uploadFileName"),
    triggerBulkUploadBtn: document.getElementById("triggerBulkUploadBtn"),
    saveSettingsBtn: document.getElementById("saveSettingsBtn"),
    
    // Resume Sync
    resumeDropZone: document.getElementById("resumeDropZone"),
    resumeFileInput: document.getElementById("resumeFileInput"),
    chooseResumeBtn: document.getElementById("chooseResumeBtn"),
    resumeFileNameDisplay: document.getElementById("resumeFileNameDisplay"),
    resumeModalOverlay: document.getElementById("resumeModalOverlay"),
    closeResumeModalBtn: document.getElementById("closeResumeModalBtn"),
    resumeExpInput: document.getElementById("resumeExpInput"),
    resumeSkillsWrapper: document.getElementById("resumeSkillsWrapper"),
    resumeSkillInput: document.getElementById("resumeSkillInput"),
    addResumeSkillBtn: document.getElementById("addResumeSkillBtn"),
    resumeKeywordsList: document.getElementById("resumeKeywordsList"),
    cancelResumeBtn: document.getElementById("cancelResumeBtn"),
    applyResumeBtn: document.getElementById("applyResumeBtn"),
    
    // Drawer
    drawerOverlay: document.getElementById("drawerOverlay"),
    jobDrawer: document.getElementById("jobDrawer"),
    closeDrawerBtn: document.getElementById("closeDrawerBtn"),
    drawerSource: document.getElementById("drawerSource"),
    drawerTitle: document.getElementById("drawerTitle"),
    drawerCompany: document.getElementById("drawerCompany"),
    drawerMeta: document.getElementById("drawerMeta"),
    drawerTechStack: document.getElementById("drawerTechStack"),
    drawerStatus: document.getElementById("drawerStatus"),
    drawerApplyBtn: document.getElementById("drawerApplyBtn"),
    drawerNotes: document.getElementById("drawerNotes"),
    saveJobNotesBtn: document.getElementById("saveJobNotesBtn"),
    drawerDescription: document.getElementById("drawerDescription"),
    
    // Logs
    consoleLogsBox: document.getElementById("consoleLogsBox"),
    clearLogsBtn: document.getElementById("clearLogsBtn")
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
    initTheme();
    setupEventListeners();
    await fetchConfig();
    await fetchJobs();
    startLoggingPoll();
});

// Theme Management
function initTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
    updateThemeUI(currentTheme);
}

function updateThemeUI(theme) {
    if (theme === "dark") {
        elements.sunIcon.style.display = "block";
        elements.moonIcon.style.display = "none";
    } else {
        elements.sunIcon.style.display = "none";
        elements.moonIcon.style.display = "block";
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    updateThemeUI(newTheme);
    showToast("Theme switched to " + newTheme + " mode.", "info");
}

// Navigation & Routing
function setupEventListeners() {
    // Theme Button
    elements.themeToggleBtn.addEventListener("click", toggleTheme);
    
    // Sidebar Tabs
    elements.navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-target");
            switchTab(target);
        });
    });
    
    // Dashboard redirection to Board
    elements.viewAllJobsBtn.addEventListener("click", () => {
        switchTab("jobs");
    });
    
    // Sync Button
    elements.syncNowBtn.addEventListener("click", triggerScrape);
    
    // Export Button
    elements.exportBtn.addEventListener("click", exportToExcel);
    
    // Filters Event
    elements.jobsSearchInput.addEventListener("input", filterAndRenderJobs);
    elements.filterStatus.addEventListener("change", filterAndRenderJobs);
    elements.filterExperience.addEventListener("change", filterAndRenderJobs);
    elements.filterSalary.addEventListener("change", filterAndRenderJobs);
    elements.filterLocation.addEventListener("change", filterAndRenderJobs);
    elements.filterRecency.addEventListener("change", filterAndRenderJobs);
    elements.filterMatchType.addEventListener("change", filterAndRenderJobs);
    elements.filterSource.addEventListener("change", filterAndRenderJobs);
    
    // Drawer Closing
    elements.closeDrawerBtn.addEventListener("click", closeDrawer);
    elements.drawerOverlay.addEventListener("click", closeDrawer);
    
    // Job Note Update
    elements.saveJobNotesBtn.addEventListener("click", saveJobNotes);
    
    // Settings tag helpers
    elements.addKeywordBtn.addEventListener("click", () => addTag("keyword"));
    elements.addLocationBtn.addEventListener("click", () => addTag("location"));
    elements.addCompanyBtn.addEventListener("click", () => addTag("company"));
    elements.keywordInput.addEventListener("keypress", (e) => { if (e.key === "Enter") { e.preventDefault(); addTag("keyword"); } });
    elements.locationInput.addEventListener("keypress", (e) => { if (e.key === "Enter") { e.preventDefault(); addTag("location"); } });
    elements.companyInput.addEventListener("keypress", (e) => { if (e.key === "Enter") { e.preventDefault(); addTag("company"); } });
    
    // Quick Company Scan Event
    elements.triggerScanCompanyBtn.addEventListener("click", triggerCompanyScrape);
    elements.scanCompanyInput.addEventListener("keypress", (e) => { if (e.key === "Enter") { e.preventDefault(); triggerCompanyScrape(); } });
    
    // Bulk Upload Events
    elements.companyListFile.addEventListener("change", (e) => {
        const file = e.target.files[0];
        elements.uploadFileName.innerText = file ? file.name : "Choose File";
    });
    elements.triggerBulkUploadBtn.addEventListener("click", uploadAndScanCompanyList);
    
    // Settings Saving
    elements.saveSettingsBtn.addEventListener("click", saveSettings);
    
    // Resume Dropzone & File Input triggers
    elements.chooseResumeBtn.addEventListener("click", () => elements.resumeFileInput.click());
    elements.resumeDropZone.addEventListener("click", (e) => {
        if (e.target !== elements.chooseResumeBtn) {
            elements.resumeFileInput.click();
        }
    });
    
    // Drag & Drop handlers
    elements.resumeDropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        elements.resumeDropZone.style.background = "rgba(255, 255, 255, 0.05)";
    });
    elements.resumeDropZone.addEventListener("dragleave", () => {
        elements.resumeDropZone.style.background = "none";
    });
    elements.resumeDropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        elements.resumeDropZone.style.background = "none";
        const file = e.dataTransfer.files[0];
        if (file) {
            handleResumeUpload(file);
        }
    });
    
    // File change handler
    elements.resumeFileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (file) {
            handleResumeUpload(file);
        }
    });

    // Resume Modal handlers
    elements.closeResumeModalBtn.addEventListener("click", closeResumeModal);
    elements.cancelResumeBtn.addEventListener("click", closeResumeModal);
    elements.addResumeSkillBtn.addEventListener("click", addResumeSkillFromInput);
    elements.resumeSkillInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            addResumeSkillFromInput();
        }
    });
    elements.applyResumeBtn.addEventListener("click", applyResumeProfileSettings);
    
    // Logs Clear
    elements.clearLogsBtn.addEventListener("click", clearLogs);
}

function switchTab(tabId) {
    activePanel = tabId;
    
    // Update active tab buttons
    elements.navButtons.forEach(btn => {
        if (btn.getAttribute("data-target") === tabId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
    
    // Switch active panel visibility
    elements.panels.forEach(panel => {
        if (panel.id === `${tabId}Panel`) {
            panel.classList.add("active");
        } else {
            panel.classList.remove("active");
        }
    });
    
    // Update Header Text
    const headers = {
        dashboard: { title: "Dashboard", sub: "Overview of job listings and matching analytics" },
        jobs: { title: "Jobs Board", sub: "Search, filter, and track discovered job postings" },
        settings: { title: "Settings", sub: "Configure keywords, locations, and automated schedules" },
        logs: { title: "Console Logs", sub: "Real-time scraper activities and server logs" }
    };
    
    elements.viewTitle.innerText = headers[tabId].title;
    elements.viewSub.innerText = headers[tabId].sub;
}

// Fetch Configurations
async function fetchConfig() {
    try {
        const response = await fetch("/api/config");
        configData = await response.json();
        renderSettings();
        
        // Populate scheduler status labels in dashboard
        elements.lblMorningTime.innerText = configData.schedule_morning || "09:00";
        elements.lblEveningTime.innerText = configData.schedule_evening || "18:00";
        elements.statLastRun.innerText = formatRelativeTime(configData.last_run);
        elements.statNextRun.innerText = configData.next_run || "Pending scheduler";
        
        // Active profiles chips on dashboard
        elements.lblActiveProfile.innerHTML = "";
        const keywords = configData.search_keywords || [];
        keywords.forEach(kw => {
            const chip = document.createElement("span");
            chip.className = "chip";
            chip.innerText = kw;
            elements.lblActiveProfile.appendChild(chip);
        });
    } catch (error) {
        console.error("Error fetching config:", error);
        showToast("Failed to fetch settings config.", "error");
    }
}

// Dynamic location populater
function populateLocationsDropdown() {
    const select = elements.filterLocation;
    if (!select) return;
    select.innerHTML = `
        <option value="">All Locations</option>
        <option value="remote_only">Remote Only</option>
        <option value="india_only">India (All Cities)</option>
    `;
    
    const uniqueLocs = [...new Set(jobsData.map(j => j.location).filter(Boolean))]
        .filter(loc => !/remote/i.test(loc))
        .sort();
    uniqueLocs.forEach(loc => {
        const opt = document.createElement("option");
        opt.value = loc;
        opt.innerText = loc;
        select.appendChild(opt);
    });
}

// Fetch Jobs Data
async function fetchJobs() {
    try {
        const response = await fetch("/api/jobs");
        jobsData = await response.json();
        populateLocationsDropdown();
        updateDashboardMetrics();
        filterAndRenderJobs();
        renderRecentJobs();
    } catch (error) {
        console.error("Error fetching jobs:", error);
        showToast("Error loading job postings database.", "error");
    }
}

// Render Dashboard Metrics and Graph
function updateDashboardMetrics() {
    const matchedJobs = jobsData.filter(matchesProfile);
    const total = matchedJobs.length;
    const interested = matchedJobs.filter(j => j.status === "Interested").length;
    const applied = matchedJobs.filter(j => j.status === "Applied").length;
    const interviewing = matchedJobs.filter(j => j.status === "Interviewing").length;
    const rejected = matchedJobs.filter(j => j.status === "Rejected").length;
    const newList = matchedJobs.filter(j => j.status === "New").length;
    
    elements.statTotal.innerText = total;
    elements.statInterested.innerText = interested;
    elements.statApplied.innerText = applied;
    elements.statInterviewing.innerText = interviewing;
    
    // Legend counts
    elements.legendNew.innerText = newList;
    elements.legendInterested.innerText = interested;
    elements.legendApplied.innerText = applied;
    elements.legendInterviewing.innerText = interviewing;
    
    // Progress calculation: Applied rate = (Applied / Total) * 100
    const percent = total > 0 ? Math.round((applied / total) * 100) : 0;
    elements.pipelineProgressPercent.innerText = `${percent}%`;
    
    // Stroke calculation (circle radius is 70, circumference is 2 * pi * r = 439.8)
    const offset = 439.8 - (percent * 4.398);
    elements.pipelineProgressCircle.style.strokeDashoffset = offset;
}

// Render Recent Jobs list in Dashboard
function renderRecentJobs() {
    elements.recentJobsTableBody.innerHTML = "";
    
    // Apply profile matching filter first, then take the 5 most recently found jobs
    const recentJobs = jobsData.filter(matchesProfile).slice(0, 5);
    
    if (recentJobs.length === 0) {
        elements.recentJobsTableBody.innerHTML = `<tr><td colspan="8" class="text-center" style="color:var(--text-muted); padding: 2rem;">No jobs found matching your profile yet. Click 'Search Jobs Now' to start scanning.</td></tr>`;
        return;
    }
    
    recentJobs.forEach(job => {
        const row = createJobRow(job);
        elements.recentJobsTableBody.appendChild(row);
    });
}

function getExperienceNumber(expText) {
    if (!expText || expText === "Not specified") return null;
    const match = expText.match(/(\d+)/);
    return match ? parseInt(match[1], 10) : null;
}

function getSalaryNumericValue(salText) {
    if (!salText || salText === "Not specified") return null;
    const isUsd = /\$|usd|k\b/i.test(salText);
    const numbers = salText.match(/\d+/g);
    if (!numbers) return null;
    const values = numbers.map(n => parseInt(n, 10));
    const avgVal = values.reduce((a, b) => a + b, 0) / values.length;
    return { value: avgVal, isUsd: isUsd };
}

// Helper: Check if a job matches the user's active profile settings
function matchesProfile(job) {
    const defaultMaxExp = configData.filter_max_experience ? parseInt(configData.filter_max_experience, 10) : null;
    const showUnspecified = configData.filter_show_unspecified_exp !== undefined ? (configData.filter_show_unspecified_exp === "true") : true;
    const minSalConfig = configData.filter_min_salary ? parseInt(configData.filter_min_salary, 10) : null;

    // Experience checks
    const matchesExperience = (() => {
        if (job.experience === "Not specified") {
            return showUnspecified;
        }
        const expVal = getExperienceNumber(job.experience);
        if (expVal === null) return showUnspecified;
        
        if (defaultMaxExp !== null) {
            return expVal <= defaultMaxExp;
        }
        return true;
    })();

    // Salary checks
    const matchesSalary = (() => {
        if (minSalConfig && (!job.salary || job.salary === "Not specified")) {
            return false;
        }
        if (minSalConfig) {
            const salObj = getSalaryNumericValue(job.salary);
            if (salObj === null) return false;
            if (salObj.isUsd) {
                const usdLimit = minSalConfig === 6 ? 50 : minSalConfig === 10 ? 80 : minSalConfig === 15 ? 120 : minSalConfig === 20 ? 150 : 250;
                return salObj.value >= usdLimit;
            } else {
                return salObj.value >= minSalConfig;
            }
        }
        return true;
    })();

    return matchesExperience && matchesSalary;
}

// Render Jobs in Main Board with Filters
function filterAndRenderJobs() {
    if (!elements.jobsSearchInput) return; // Prevent runs before initial DOM load
    
    const searchQuery = elements.jobsSearchInput.value.toLowerCase();
    const statusFilter = elements.filterStatus.value;
    const sourceFilter = elements.filterSource.value;
    
    const maxExpLimit = elements.filterExperience.value !== "" ? parseInt(elements.filterExperience.value, 10) : null;
    
    // Preferences from config (fallbacks)
    const showUnspecified = elements.prefShowUnspecified ? elements.prefShowUnspecified.checked : true;
    const defaultMaxExp = (maxExpLimit === null && elements.prefMaxExperience && elements.prefMaxExperience.value !== "") ? parseInt(elements.prefMaxExperience.value, 10) : null;
    const minSalConfig = elements.prefMinSalary && elements.prefMinSalary.value ? elements.prefMinSalary.value.toLowerCase().trim() : "";
    
    const filteredJobs = jobsData.filter(job => {
        const matchesSearch = 
            (job.title && job.title.toLowerCase().includes(searchQuery)) ||
            (job.company && job.company.toLowerCase().includes(searchQuery)) ||
            (job.tech_stack && job.tech_stack.toLowerCase().includes(searchQuery)) ||
            (job.location && job.location.toLowerCase().includes(searchQuery));
            
        const matchesStatus = !statusFilter || job.status === statusFilter;
        const matchesSource = !sourceFilter || job.source === sourceFilter;
        
        // Experience Filter logic
        const matchesExperience = (() => {
            if (job.experience === "Not specified") {
                return showUnspecified;
            }
            const expVal = getExperienceNumber(job.experience);
            if (expVal === null) return showUnspecified;
            
            if (maxExpLimit !== null) {
                return expVal <= maxExpLimit;
            } else if (defaultMaxExp !== null) {
                return expVal <= defaultMaxExp;
            }
            return true;
        })();
        
        // Salary Filter logic
        const matchesSalary = (() => {
            const salFilter = elements.filterSalary.value;
            if (!salFilter) {
                if (minSalConfig && (!job.salary || job.salary === "Not specified")) {
                    return false;
                }
                return true;
            }
            
            if (salFilter === "specified") {
                return job.salary && job.salary !== "Not specified";
            }
            
            const minLimit = parseInt(salFilter, 10);
            const salObj = getSalaryNumericValue(job.salary);
            if (salObj === null) return false;
            
            if (salObj.isUsd) {
                const usdLimit = minLimit === 6 ? 50 : minLimit === 10 ? 80 : minLimit === 15 ? 120 : minLimit === 20 ? 150 : 250;
                return salObj.value >= usdLimit;
            } else {
                return salObj.value >= minLimit;
            }
        })();
        
        // Location Filter logic
        const matchesLocation = (() => {
            const locFilter = elements.filterLocation.value;
            if (!locFilter) return true;
            if (locFilter === "remote_only") {
                return job.location && /remote/i.test(job.location);
            }
            if (locFilter === "india_only") {
                return job.location && /india/i.test(job.location);
            }
            return job.location === locFilter;
        })();
        
        // Recency Filter logic
        const matchesRecency = (() => {
            if (!elements.filterRecency) return true;
            const recency = elements.filterRecency.value;
            if (!recency) return true;
            
            const dateStr = job.date_posted || job.date_found;
            if (!dateStr || dateStr === "Not specified" || dateStr === "None") return false;
            
            const postedDate = new Date(dateStr);
            const now = new Date();
            const diffMs = now - postedDate;
            const diffHours = diffMs / 3600000;
            
            if (recency === "24h") return diffHours <= 24;
            if (recency === "48h") return diffHours <= 48;
            if (recency === "7d") return diffHours <= 168; // 24 * 7
            if (recency === "30d") return diffHours <= 720; // 24 * 30
            return true;
        })();
        
        // Match Type Filter logic
        const matchesMatchType = (() => {
            if (!elements.filterMatchType) return true;
            const matchFilter = elements.filterMatchType.value;
            if (!matchFilter) return true;
            if (matchFilter === "targeted") {
                return job.is_targeted === 1;
            } else if (matchFilter === "organic") {
                return !job.is_targeted || job.is_targeted === 0;
            }
            return true;
        })();
        
        return matchesSearch && matchesStatus && matchesSource && matchesExperience && matchesSalary && matchesLocation && matchesRecency && matchesMatchType;
    });
    
    elements.jobsTableBody.innerHTML = "";
    
    if (filteredJobs.length === 0) {
        elements.jobsEmptyState.style.display = "flex";
        elements.mainJobsTable.style.display = "none";
    } else {
        elements.jobsEmptyState.style.display = "none";
        elements.mainJobsTable.style.display = "table";
        
        filteredJobs.forEach(job => {
            const row = createJobRow(job);
            elements.jobsTableBody.appendChild(row);
        });
    }
}

// Helper: Create Row Element
function createJobRow(job) {
    const tr = document.createElement("tr");
    
    // Job Title
    const tdTitle = document.createElement("td");
    tdTitle.style.fontWeight = "600";
    tdTitle.innerText = job.title || "Untitled Position";
    
    // Company
    const tdCompany = document.createElement("td");
    tdCompany.innerText = job.company || "Unknown Company";
    if (job.is_targeted === 1) {
        const targetBadge = document.createElement("span");
        targetBadge.className = "target-company-badge";
        targetBadge.innerHTML = "🎯 Target";
        tdCompany.appendChild(targetBadge);
    }
    
    // Location
    const tdLoc = document.createElement("td");
    tdLoc.innerText = job.location || "Remote";
    
    // Tech stack (show max 3 badges)
    const tdTech = document.createElement("td");
    const stack = job.tech_stack ? job.tech_stack.split(", ").slice(0, 3) : [];
    stack.forEach(tech => {
        const tag = document.createElement("span");
        tag.className = "tech-tag";
        tag.innerText = tech;
        tdTech.appendChild(tag);
    });
    if (job.tech_stack && job.tech_stack.split(", ").length > 3) {
        const moreTag = document.createElement("span");
        moreTag.className = "tech-tag";
        moreTag.innerText = `+${job.tech_stack.split(", ").length - 3}`;
        tdTech.appendChild(moreTag);
    }
    
    // Experience
    const tdExp = document.createElement("td");
    tdExp.innerText = job.experience || "Not specified";
    
    // Salary
    const tdSal = document.createElement("td");
    if (job.salary && job.salary !== "Not specified") {
        const pill = document.createElement("span");
        pill.className = "salary-pill";
        pill.innerText = job.salary;
        tdSal.appendChild(pill);
    } else {
        tdSal.innerText = "Not specified";
        tdSal.style.color = "var(--text-muted)";
    }
    
    // Posted Date
    const tdPosted = document.createElement("td");
    const cleanDate = job.date_posted && job.date_posted !== "None" ? job.date_posted : "";
    if (cleanDate) {
        tdPosted.innerText = formatRelativeTime(cleanDate) || cleanDate;
    } else {
        tdPosted.innerText = "Recently";
        tdPosted.style.color = "var(--text-muted)";
    }
    
    // Source
    const tdSource = document.createElement("td");
    tdSource.innerHTML = `<span class="source-tag">${job.source || "Web"}</span>`;
    
    // Status Badge
    const tdStatus = document.createElement("td");
    const badge = document.createElement("span");
    const statusClass = (job.status || "New").toLowerCase().replace(" ", "-");
    badge.className = `badge ${statusClass}`;
    badge.innerText = job.status || "New";
    tdStatus.appendChild(badge);
    
    tr.appendChild(tdTitle);
    tr.appendChild(tdCompany);
    tr.appendChild(tdLoc);
    tr.appendChild(tdTech);
    tr.appendChild(tdExp);
    tr.appendChild(tdSal);
    tr.appendChild(tdPosted);
    tr.appendChild(tdSource);
    tr.appendChild(tdStatus);
    
    tr.addEventListener("click", () => openDrawer(job));
    
    return tr;
}

// Side Drawer Detail View
function openDrawer(job) {
    activeJob = job;
    
    // Set text contents
    elements.drawerTitle.innerText = job.title;
    elements.drawerCompany.innerText = job.company;
    elements.drawerSource.innerText = job.source;
    
    const salaryText = job.salary && job.salary !== "Not specified" ? ` | Salary: ${job.salary}` : "";
    elements.drawerMeta.innerText = `${job.location || 'Remote'} | Exp: ${job.experience || 'Not specified'}${salaryText}`;
    
    // Set Status dropdown
    elements.drawerStatus.value = job.status || "New";
    
    // Set Notes
    elements.drawerNotes.value = job.notes || "";
    
    // Render Tech Stack chips
    elements.drawerTechStack.innerHTML = "";
    if (job.tech_stack) {
        job.tech_stack.split(", ").forEach(tech => {
            const span = document.createElement("span");
            span.className = "tech-tag";
            span.innerText = tech;
            elements.drawerTechStack.appendChild(span);
        });
    }
    
    // Direct Apply Link
    if (job.apply_url) {
        elements.drawerApplyBtn.href = job.apply_url;
        elements.drawerApplyBtn.style.display = "flex";
    } else {
        elements.drawerApplyBtn.style.display = "none";
    }
    
    // Render Description HTML/Text
    elements.drawerDescription.innerText = job.description || "No description available.";
    
    // Display elements
    elements.drawerOverlay.classList.add("active");
    elements.jobDrawer.classList.add("active");
}

function closeDrawer() {
    elements.drawerOverlay.classList.remove("active");
    elements.jobDrawer.classList.remove("active");
    activeJob = null;
}

// Save Job updates from Drawer
async function saveJobNotes() {
    if (!activeJob) return;
    
    const newStatus = elements.drawerStatus.value;
    const newNotes = elements.drawerNotes.value;
    
    try {
        // 1. Update status
        await fetch(`/api/jobs/${activeJob.job_id}/status`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        
        // 2. Update notes
        await fetch(`/api/jobs/${activeJob.job_id}/notes`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: newNotes })
        });
        
        showToast("Job status and notes saved.", "success");
        closeDrawer();
        fetchJobs(); // Refresh grid
    } catch (error) {
        console.error("Error saving job details:", error);
        showToast("Failed to save changes.", "error");
    }
}

// Sync / Scrape Triggering
async function triggerScrape() {
    if (isSyncing) return;
    
    isSyncing = true;
    elements.syncNowBtn.disabled = true;
    document.querySelector(".spin-icon").classList.add("spinning");
    elements.syncStatus.querySelector(".status-indicator").className = "status-indicator syncing";
    elements.syncText.innerText = "Syncing Jobs...";
    
    showToast("Starting job scrape in background...", "info");
    
    // Switch to logs view so user can watch output progress
    switchTab("logs");
    
    try {
        const response = await fetch("/api/jobs/scrape", { method: "POST" });
        const data = await response.json();
        
        // Poll logs aggressively while running
        let pollCount = 0;
        const syncCheckInterval = setInterval(async () => {
            pollCount++;
            const logRes = await fetch("/api/logs");
            const logData = await logRes.json();
            renderLogs(logData.logs);
            
            // Check if final finished log is present
            const lastLog = logData.logs[logData.logs.length - 1] || "";
            if (lastLog.includes("Job search finished") || pollCount > 120) { // Limit to 2 minutes
                clearInterval(syncCheckInterval);
                isSyncing = false;
                elements.syncNowBtn.disabled = false;
                document.querySelector(".spin-icon").classList.remove("spinning");
                elements.syncStatus.querySelector(".status-indicator").className = "status-indicator idle";
                elements.syncText.innerText = "System Idle";
                
                showToast("Job scraping sync complete!", "success");
                fetchJobs(); // Refresh jobs database
                fetchConfig(); // Update next runs
            }
        }, 1500);
        
    } catch (error) {
        console.error("Scraping trigger error:", error);
        showToast("Failed to initiate search job.", "error");
        isSyncing = false;
        elements.syncNowBtn.disabled = false;
        document.querySelector(".spin-icon").classList.remove("spinning");
        elements.syncStatus.querySelector(".status-indicator").className = "status-indicator idle";
        elements.syncText.innerText = "System Idle";
    }
}

// Targeted single-company scrape trigger
async function triggerCompanyScrape() {
    if (isSyncing) return;
    
    const companyName = elements.scanCompanyInput.value.trim();
    if (!companyName) {
        showToast("Please enter a company name to scan.", "warning");
        return;
    }
    
    isSyncing = true;
    elements.triggerScanCompanyBtn.disabled = true;
    elements.triggerScanCompanyBtn.innerText = "Scanning...";
    elements.syncNowBtn.disabled = true;
    document.querySelector(".spin-icon").classList.add("spinning");
    elements.syncStatus.querySelector(".status-indicator").className = "status-indicator syncing";
    elements.syncText.innerText = "Scanning Employer...";
    
    showToast(`Initiating targeted scan for '${companyName}'...`, "info");
    
    // Switch to logs view so user can watch progress
    switchTab("logs");
    
    try {
        const response = await fetch("/api/jobs/scrape-company", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ company: companyName })
        });
        
        const data = await response.json();
        elements.scanCompanyInput.value = "";
        
        // Poll logs aggressively while running
        let pollCount = 0;
        const syncCheckInterval = setInterval(async () => {
            pollCount++;
            const logRes = await fetch("/api/logs");
            const logData = await logRes.json();
            renderLogs(logData.logs);
            
            // Check if final finished log is present
            const lastLog = logData.logs[logData.logs.length - 1] || "";
            if (lastLog.includes("Targeted single-company scan finished") || pollCount > 100) { // Limit to ~2.5 minutes
                clearInterval(syncCheckInterval);
                isSyncing = false;
                elements.triggerScanCompanyBtn.disabled = false;
                elements.triggerScanCompanyBtn.innerText = "Scan Company";
                elements.syncNowBtn.disabled = false;
                document.querySelector(".spin-icon").classList.remove("spinning");
                elements.syncStatus.querySelector(".status-indicator").className = "status-indicator idle";
                elements.syncText.innerText = "System Idle";
                
                showToast(`Scrape sync for '${companyName}' complete!`, "success");
                fetchJobs(); // Refresh jobs database
                fetchConfig(); // Update next runs
            }
        }, 1500);
        
    } catch (error) {
        console.error("Company scraping trigger error:", error);
        showToast("Failed to initiate company scan.", "error");
        isSyncing = false;
        elements.triggerScanCompanyBtn.disabled = false;
        elements.triggerScanCompanyBtn.innerText = "Scan Company";
        elements.syncNowBtn.disabled = false;
        document.querySelector(".spin-icon").classList.remove("spinning");
        elements.syncStatus.querySelector(".status-indicator").className = "status-indicator idle";
        elements.syncText.innerText = "System Idle";
    }
}

// Bulk Upload & Scan File Handler
async function uploadAndScanCompanyList() {
    if (isSyncing) return;
    
    const fileInput = elements.companyListFile;
    if (!fileInput || fileInput.files.length === 0) {
        showToast("Please choose a company list file (.txt, .csv) first.", "warning");
        return;
    }
    
    const file = fileInput.files[0];
    isSyncing = true;
    elements.triggerBulkUploadBtn.disabled = true;
    elements.triggerBulkUploadBtn.innerText = "Uploading...";
    elements.syncNowBtn.disabled = true;
    document.querySelector(".spin-icon").classList.add("spinning");
    elements.syncStatus.querySelector(".status-indicator").className = "status-indicator syncing";
    elements.syncText.innerText = "Scanning Bulk List...";
    
    showToast(`Uploading '${file.name}' and starting bulk scan...`, "info");
    
    // Switch to logs view so user can watch progress
    switchTab("logs");
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
        const response = await fetch("/api/jobs/upload-companies", {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Upload failed");
        }
        
        const data = await response.json();
        
        // Clear file input display
        fileInput.value = "";
        elements.uploadFileName.innerText = "Choose File";
        
        // Poll logs aggressively while running
        let pollCount = 0;
        const syncCheckInterval = setInterval(async () => {
            pollCount++;
            const logRes = await fetch("/api/logs");
            const logData = await logRes.json();
            renderLogs(logData.logs);
            
            const lastLog = logData.logs[logData.logs.length - 1] || "";
            if (lastLog.includes("Bulk uploaded companies scan finished") || pollCount > 150) { // Limit to ~3.75 minutes
                clearInterval(syncCheckInterval);
                isSyncing = false;
                elements.triggerBulkUploadBtn.disabled = false;
                elements.triggerBulkUploadBtn.innerText = "Scan List";
                elements.syncNowBtn.disabled = false;
                document.querySelector(".spin-icon").classList.remove("spinning");
                elements.syncStatus.querySelector(".status-indicator").className = "status-indicator idle";
                elements.syncText.innerText = "System Idle";
                
                showToast("Bulk scan of company list complete!", "success");
                fetchJobs(); // Refresh jobs database
                fetchConfig(); // Reload preferences config (which contains the updated companies)
            }
        }, 1500);
        
    } catch (error) {
        console.error("Bulk upload scan error:", error);
        showToast(error.message || "Failed to parse and scan company list.", "error");
        isSyncing = false;
        elements.triggerBulkUploadBtn.disabled = false;
        elements.triggerBulkUploadBtn.innerText = "Scan List";
        elements.syncNowBtn.disabled = false;
        document.querySelector(".spin-icon").classList.remove("spinning");
        elements.syncStatus.querySelector(".status-indicator").className = "status-indicator idle";
        elements.syncText.innerText = "System Idle";
    }
}

// Settings Views Rendering and Configs saving
function renderSettings() {
    // Keywords tags
    elements.keywordsTagsWrapper.innerHTML = "";
    const keywords = configData.search_keywords || [];
    keywords.forEach((kw, index) => {
        elements.keywordsTagsWrapper.appendChild(createTagElement(kw, index, "keyword"));
    });
    
    // Locations tags
    elements.locationsTagsWrapper.innerHTML = "";
    const locations = configData.search_locations || [];
    locations.forEach((loc, index) => {
        elements.locationsTagsWrapper.appendChild(createTagElement(loc, index, "location"));
    });
    
    // Companies tags
    if (elements.companiesTagsWrapper) {
        elements.companiesTagsWrapper.innerHTML = "";
        const companies = configData.target_companies || [];
        companies.forEach((co, index) => {
            elements.companiesTagsWrapper.appendChild(createTagElement(co, index, "company"));
        });
    }
    
    // Schedule times
    elements.morningTime.value = configData.schedule_morning || "09:00";
    elements.eveningTime.value = configData.schedule_evening || "18:00";
    
    // Preference filters
    if (elements.prefMaxExperience) {
        elements.prefMaxExperience.value = configData.filter_max_experience !== undefined ? configData.filter_max_experience : "2";
    }
    if (elements.prefShowUnspecified) {
        elements.prefShowUnspecified.checked = configData.filter_show_unspecified_exp !== undefined ? (configData.filter_show_unspecified_exp === "true") : true;
    }
    if (elements.prefMinSalary) {
        elements.prefMinSalary.value = configData.filter_min_salary !== undefined ? configData.filter_min_salary : "";
    }
}

function createTagElement(text, index, type) {
    const span = document.createElement("span");
    span.className = "form-tag";
    span.innerHTML = `${text} <button type="button">&times;</button>`;
    
    span.querySelector("button").addEventListener("click", () => {
        removeTag(index, type);
    });
    
    return span;
}

function addTag(type) {
    if (type === "keyword") {
        const val = elements.keywordInput.value.trim();
        if (val) {
            if (!configData.search_keywords) configData.search_keywords = [];
            configData.search_keywords.push(val);
            elements.keywordInput.value = "";
            renderSettings();
        }
    } else if (type === "location") {
        const val = elements.locationInput.value.trim();
        if (val) {
            if (!configData.search_locations) configData.search_locations = [];
            configData.search_locations.push(val);
            elements.locationInput.value = "";
            renderSettings();
        }
    } else if (type === "company") {
        const val = elements.companyInput.value.trim();
        if (val) {
            if (!configData.target_companies) configData.target_companies = [];
            configData.target_companies.push(val);
            elements.companyInput.value = "";
            renderSettings();
        }
    }
}

function removeTag(index, type) {
    if (type === "keyword") {
        configData.search_keywords.splice(index, 1);
    } else if (type === "location") {
        configData.search_locations.splice(index, 1);
    } else if (type === "company") {
        configData.target_companies.splice(index, 1);
    }
    renderSettings();
}

async function saveSettings() {
    const morning = elements.morningTime.value;
    const evening = elements.eveningTime.value;
    const maxExp = elements.prefMaxExperience ? elements.prefMaxExperience.value : "2";
    const showUnspecified = (elements.prefShowUnspecified && elements.prefShowUnspecified.checked) ? "true" : "false";
    const minSal = elements.prefMinSalary ? elements.prefMinSalary.value : "";
    
    const payload = {
        search_keywords: configData.search_keywords || [],
        search_locations: configData.search_locations || [],
        target_companies: configData.target_companies || [],
        schedule_morning: morning,
        schedule_evening: evening,
        filter_max_experience: maxExp,
        filter_show_unspecified_exp: showUnspecified,
        filter_min_salary: minSal
    };
    
    try {
        const response = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        await response.json();
        showToast("Scraper configurations saved successfully.", "success");
        fetchConfig(); // Reload display
    } catch (error) {
        console.error("Save config error:", error);
        showToast("Failed to save settings configurations.", "error");
    }
}

// Resume Parsing API Client & UI Helpers
async function handleResumeUpload(file) {
    if (isSyncing) return;
    
    // Check file type
    const filename = file.name.toLowerCase();
    if (!filename.endsWith(".pdf") && !filename.endsWith(".txt")) {
        showToast("Please select a PDF or Plain Text (.txt) resume.", "warning");
        return;
    }
    
    isSyncing = true;
    elements.chooseResumeBtn.disabled = true;
    elements.chooseResumeBtn.innerText = "Parsing Resume...";
    
    showToast(`Uploading and parsing '${file.name}'...`, "info");
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
        const response = await fetch("/api/resume/parse", {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Failed to parse resume.");
        }
        
        const data = await response.json();
        
        // Save parsed data locally
        parsedResumeData = {
            experience: data.experience,
            skills: data.skills || [],
            suggested_keywords: data.suggested_keywords || []
        };
        
        // Show review modal
        openResumeModal();
        showToast("Resume parsed successfully! Please review the extracted settings.", "success");
        
    } catch (error) {
        console.error("Resume upload error:", error);
        showToast(error.message || "Error parsing your resume file.", "error");
    } finally {
        isSyncing = false;
        elements.chooseResumeBtn.disabled = false;
        elements.chooseResumeBtn.innerText = "Choose File";
        elements.resumeFileInput.value = ""; // Reset
    }
}

function openResumeModal() {
    elements.resumeModalOverlay.style.display = "flex";
    elements.resumeExpInput.value = parsedResumeData.experience;
    renderResumeSkills();
    renderResumeKeywords();
}

function closeResumeModal() {
    elements.resumeModalOverlay.style.display = "none";
}

function renderResumeSkills() {
    elements.resumeSkillsWrapper.innerHTML = "";
    parsedResumeData.skills.forEach((skill, index) => {
        const badge = document.createElement("span");
        badge.className = "tag-badge";
        badge.style.cssText = "display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.8rem; background: var(--border-glass); border: 1px solid var(--border-glass-focus); color: var(--text-color); padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 500;";
        badge.innerHTML = `
            ${skill}
            <span style="cursor:pointer; font-weight: bold; margin-left: 2px; color: var(--text-muted);" onclick="removeResumeSkill(${index})">&times;</span>
        `;
        elements.resumeSkillsWrapper.appendChild(badge);
    });
}

// Make globally accessible so the inline onclick works
window.removeResumeSkill = function(index) {
    parsedResumeData.skills.splice(index, 1);
    renderResumeSkills();
};

function addResumeSkillFromInput() {
    const val = elements.resumeSkillInput.value.trim();
    if (val) {
        // Capitalize nicely if it's not present
        if (!parsedResumeData.skills.some(s => s.toLowerCase() === val.toLowerCase())) {
            parsedResumeData.skills.push(val);
            renderResumeSkills();
        }
        elements.resumeSkillInput.value = "";
    }
}

function renderResumeKeywords() {
    elements.resumeKeywordsList.innerHTML = "";
    if (parsedResumeData.suggested_keywords.length === 0) {
        elements.resumeKeywordsList.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 0.5rem 0;">No query suggestions found.</div>`;
        return;
    }
    
    parsedResumeData.suggested_keywords.forEach((kw, index) => {
        const item = document.createElement("label");
        item.style.cssText = "display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; cursor: pointer; color: var(--text-color); margin: 0;";
        item.innerHTML = `
            <input type="checkbox" value="${kw}" checked style="width: 15px; height: 15px; cursor: pointer;">
            <span>${kw}</span>
        `;
        elements.resumeKeywordsList.appendChild(item);
    });
}

async function applyResumeProfileSettings() {
    const selectedKeywords = Array.from(elements.resumeKeywordsList.querySelectorAll("input[type='checkbox']:checked")).map(el => el.value);
    const expValue = parseInt(elements.resumeExpInput.value, 10);
    
    if (isNaN(expValue) || expValue < 0) {
        showToast("Please enter a valid experience year count.", "warning");
        return;
    }
    
    if (selectedKeywords.length === 0) {
        showToast("Please select at least one search query to continue.", "warning");
        return;
    }
    
    elements.applyResumeBtn.disabled = true;
    elements.applyResumeBtn.innerText = "Applying...";
    
    const payload = {
        experience: expValue,
        skills: parsedResumeData.skills,
        keywords: selectedKeywords
    };
    
    try {
        const response = await fetch("/api/resume/apply", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error("Failed to apply resume settings.");
        }
        
        showToast("Search profile synced with resume!", "success");
        closeResumeModal();
        
        // Reload all data in the UI
        fetchConfig();
        fetchJobs();
        
    } catch (error) {
        console.error("Apply resume settings error:", error);
        showToast("Error updating configurations.", "error");
    } finally {
        elements.applyResumeBtn.disabled = false;
        elements.applyResumeBtn.innerText = "Apply to Search Profile";
    }
}

// Log Polling & Console Box rendering
function startLoggingPoll() {
    fetchLogs();
    logInterval = setInterval(fetchLogs, 5000); // Poll logs every 5 seconds
}

async function fetchLogs() {
    // If user is currently running a scraper, we bypass standard interval because triggerScrape handles it faster.
    if (isSyncing) return;
    
    try {
        const response = await fetch("/api/logs");
        const data = await response.json();
        renderLogs(data.logs);
    } catch (error) {
        console.error("Error reading logs:", error);
    }
}

function renderLogs(logs) {
    const isAtBottom = elements.consoleLogsBox.scrollHeight - elements.consoleLogsBox.clientHeight <= elements.consoleLogsBox.scrollTop + 20;
    
    elements.consoleLogsBox.innerHTML = "";
    if (logs.length === 0) {
        elements.consoleLogsBox.innerHTML = `<div class="console-line text-muted">Console output is clear. No background jobs logged.</div>`;
        return;
    }
    
    logs.forEach(line => {
        const div = document.createElement("div");
        div.className = "console-line";
        
        // Style depending on log content
        if (line.toLowerCase().includes("error") || line.toLowerCase().includes("fail")) {
            div.classList.add("error");
        } else if (line.includes("complete") || line.includes("finished") || line.includes("started successfully")) {
            div.classList.add("success");
        } else if (line.includes("Starting") || line.includes("Manual scrape") || line.includes("Triggering")) {
            div.classList.add("info");
        } else if (line.includes("Scraping") || line.includes("Scheduled")) {
            div.classList.add("warning");
        }
        
        div.innerText = line;
        elements.consoleLogsBox.appendChild(div);
    });
    
    // Auto scroll if user hasn't scrolled up
    if (isAtBottom) {
        elements.consoleLogsBox.scrollTop = elements.consoleLogsBox.scrollHeight;
    }
}

async function clearLogs() {
    try {
        await fetch("/api/logs/clear", { method: "POST" });
        showToast("Console activity logs cleared.", "info");
        renderLogs([]);
    } catch (error) {
        console.error("Error clearing logs:", error);
    }
}

// Excel Export Trigger
function exportToExcel() {
    showToast("Preparing Excel sheets export...", "info");
    window.location.href = "/api/jobs/export";
}

// Utility: Toast notifications
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    // Icon selection
    let icon = "";
    if (type === "success") icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    else if (type === "error") icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    else if (type === "warning") icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
    else icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    
    toast.innerHTML = `${icon} <span>${message}</span>`;
    elements.toastContainer.appendChild(toast);
    
    // Fade out and remove
    setTimeout(() => {
        toast.style.transition = "opacity 0.5s ease-out, transform 0.5s ease-out";
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-10px)";
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

// Utility: Relative time formatter
function formatRelativeTime(isoString) {
    if (!isoString || isoString === "Never") return "Never";
    
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return "Just now";
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        return date.toLocaleDateString();
    } catch (e) {
        return isoString;
    }
}
