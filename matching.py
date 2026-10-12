"""Transparent skill matching calculations."""
def match_skills(resume_skills: list[str], job_skills: list[str]) -> dict:
    resume = {skill.lower() for skill in resume_skills}
    required = {skill.lower() for skill in job_skills}
    matched = sorted(resume & required)
    missing = sorted(required - resume)
    score = round((len(matched) / len(required)) * 100) if required else 0
    return {"score": score, "matched": matched, "missing": missing}
