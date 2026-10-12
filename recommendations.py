"""Curated, explainable learning recommendations for missing skills."""
from urllib.parse import quote_plus

RESOURCES = {
    "python": ("Python documentation", "https://docs.python.org/3/tutorial/"),
    "sql": ("SQLBolt", "https://sqlbolt.com/"),
    "javascript": ("MDN JavaScript Guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide"),
    "react": ("React Learn", "https://react.dev/learn"),
    "aws": ("AWS Skill Builder", "https://skillbuilder.aws/"),
    "docker": ("Docker Get Started", "https://docs.docker.com/get-started/"),
    "machine learning": ("Google ML Crash Course", "https://developers.google.com/machine-learning/crash-course"),
    "git": ("Atlassian Git tutorials", "https://www.atlassian.com/git/tutorials"),
}


def recommend_resources(missing_skills: list[str]) -> list[dict]:
    return [
        {
            "skill": skill,
            "title": RESOURCES.get(skill, (f"Learn {skill.title()}", f"https://www.coursera.org/search?query={quote_plus(skill)}"))[0],
            "url": RESOURCES.get(skill, ("", f"https://www.coursera.org/search?query={quote_plus(skill)}"))[1],
            "youtube_url": f"https://www.youtube.com/results?search_query={quote_plus(skill + ' tutorial')}",
        }
        for skill in missing_skills
    ]
