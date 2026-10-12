"""Hirebase job search adapter with a local demo fallback."""
import logging

import requests

from config import HIREBASE_API_KEY, HIREBASE_API_URL

logger = logging.getLogger(__name__)

COMPANY_CAREER_SITES = {
    "Google": "https://careers.google.com/jobs/results/",
    "Microsoft": "https://jobs.careers.microsoft.com/global/en/search",
    "Amazon": "https://www.amazon.jobs/en/search",
    "Apple": "https://jobs.apple.com/en-us/search",
    "Meta": "https://www.metacareers.com/jobs",
    "Netflix": "https://jobs.netflix.com/search",
    "IBM": "https://www.ibm.com/careers/search",
    "Infosys": "https://career.infosys.com/joblist",
    "TCS": "https://www.tcs.com/careers",
    "Wipro": "https://careers.wipro.com/",
}

COMPANY_OPTIONS = list(COMPANY_CAREER_SITES)
ROLE_OPTIONS = [
    "Python Developer",
    "Data Analyst",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Data Scientist",
    "Machine Learning Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "QA Engineer",
]

ROLE_SKILLS = {
    "Python Developer": ["python", "sql", "git"],
    "Data Analyst": ["python", "sql", "excel"],
    "Frontend Developer": ["javascript", "react", "css"],
    "Backend Developer": ["python", "sql", "rest api"],
    "Full Stack Developer": ["javascript", "react", "sql"],
    "Data Scientist": ["python", "sql", "machine learning"],
    "Machine Learning Engineer": ["python", "machine learning", "docker"],
    "DevOps Engineer": ["docker", "aws", "git"],
    "Cloud Engineer": ["aws", "docker", "linux"],
    "QA Engineer": ["python", "git", "sql"],
}

OPENING_LOCATIONS = [
    "Bengaluru, India",
    "Chennai, India",
    "Hyderabad, India",
    "Pune, India",
    "Mumbai, India",
    "New Delhi, India",
    "Gurugram, India",
    "Noida, India",
    "Remote - India",
    "Remote - Worldwide",
]

DEMO_JOBS = [
    {
        "title": role,
        "company": company,
        "location": location,
        "skills": ROLE_SKILLS[role],
        "url": COMPANY_CAREER_SITES[company],
    }
    for company in COMPANY_OPTIONS
    for role in ROLE_OPTIONS
    for location in OPENING_LOCATIONS
]


def search_jobs(company: str = "", role: str = "") -> tuple[list[dict], bool]:
    if not HIREBASE_API_KEY:
        return _filter_demo(company, role), True
    try:
        response = requests.get(
            HIREBASE_API_URL,
            params={"company": company, "role": role},
            headers={"Authorization": HIREBASE_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else payload
        if not isinstance(jobs, list):
            raise ValueError("Job API response must contain a list of jobs.")
        normalized_jobs = [_normalize_job(job) for job in jobs]
        if normalized_jobs:
            return normalized_jobs, False
        return _filter_demo(company, role), True
    except (requests.RequestException, ValueError, TypeError) as error:
        logger.warning("Job search failed; using demo results: %s", error)
        return _filter_demo(company, role), True


def _normalize_job(job: object) -> dict:
    if not isinstance(job, dict):
        raise ValueError("Each job API result must be an object.")

    company = job.get("company", job.get("company_name", "Unknown company"))
    if not isinstance(company, str) or not company.strip():
        company = "Unknown company"
    title = job.get("title", job.get("job_title", "Untitled role"))
    if not isinstance(title, str) or not title.strip():
        title = "Untitled role"
    location = job.get("location", "Not specified")
    if not isinstance(location, str) or not location.strip():
        location = "Not specified"
    skills = job.get("skills", [])
    if isinstance(skills, str):
        skills = [skills]
    if not isinstance(skills, list):
        skills = []
    url = job.get("url", job.get("apply_url", COMPANY_CAREER_SITES.get(company, "#")))
    if not isinstance(url, str) or not url.strip():
        url = COMPANY_CAREER_SITES.get(company, "#")

    return {
        "title": title,
        "company": company,
        "location": location,
        "skills": [str(skill).lower() for skill in skills if skill is not None],
        "url": url,
    }


def _filter_demo(company: str, role: str) -> list[dict]:
    company_query = company.strip().lower()
    role_query = role.strip().lower()
    return [
        job for job in DEMO_JOBS
        if (not company_query or company_query in job["company"].lower())
        and (not role_query or role_query in job["title"].lower())
    ]
