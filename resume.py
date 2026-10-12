"""Resume text extraction and lightweight skill discovery."""
import re
from pypdf import PdfReader

SKILL_CATALOG = {
    "python", "java", "javascript", "Machine Learning", "Data Analysis", 
    "typescript", "sql", "html", "css", "react",
    "streamlit", "flask", "deep learning", "pandas",
    "communication", "leadership",
    "project management", "figma", "tableau", "power bi", "excel", "rest api",
}


def extract_pdf_text(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_skills(text: str) -> list[str]:
    normalized = text.lower()
    return sorted(skill for skill in SKILL_CATALOG if re.search(r"(?<![a-z])" + re.escape(skill) + r"(?![a-z])", normalized))
