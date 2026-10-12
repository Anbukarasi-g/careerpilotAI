"""CareerPilot - AI Placement Agent Streamlit entry point."""
import html
import logging
import sqlite3
import streamlit as st

from auth import login, register
from db import init_db
from services.ai import analyze_resume, interview_reply_stream, review_interview_response
from services.jobs import COMPANY_OPTIONS, ROLE_OPTIONS, search_jobs
from services.matching import match_skills
from services.recommendations import recommend_resources
from services.resume import extract_pdf_text, extract_skills

logger = logging.getLogger(__name__)

st.set_page_config(page_title="CareerPilot", page_icon="CP", layout="wide", initial_sidebar_state="expanded")
try:
    init_db()
except (sqlite3.Error, OSError):
    logger.exception("Could not initialize the CareerPilot database.")
    st.error("CareerPilot could not open its database. Check the database path and permissions, then restart the app.")
    st.stop()


def inject_styles() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#FFFFFF; --purple:#F4B6CF; --accent:#F4B6CF; --paper:#101014; --card:#211E24; --line:#493640; --mint:#F4B6CF; --blush:#FBEAF1; --button-ink:#21141B; }
    .stApp { background:var(--paper); color:var(--ink); }
    [data-testid='stHeader'] { background:var(--paper); }
    h1,h2,h3 { font-family:'Space Grotesk', sans-serif; color:#FFFFFF; }
    p, label, .stMarkdown { font-family:'DM Sans', sans-serif; }
    [data-testid='stSidebar'] { background:#211E24; }
    [data-testid='stSidebar'] * { color:#FFFFFF; }
    [data-testid='stSidebar'] svg { color:var(--accent); fill:currentColor; }
    [data-testid='stSidebar'] [role='radiogroup'] label:has(input:checked) { color:#F4B6CF !important; }
    [data-testid='stSidebar'] [role='radiogroup'] label:has(input:checked) p { color:#F4B6CF !important; }
    .hero { padding:3rem 0 2rem; border-bottom:1px solid var(--line); }
    .eyebrow { color:var(--purple); font-weight:700; text-transform:uppercase; letter-spacing:.12em; font-size:.75rem; }
    .hero h1 { font-size:clamp(2.5rem, 5vw, 5rem); line-height:.98; margin:.4rem 0 1rem; max-width:850px; }
    .hero p { font-size:1.15rem; max-width:650px; color:#FFFFFF; }
    .metric { background:var(--card); border:1px solid var(--line); padding:1rem; border-radius:16px; text-align:center; min-height:112px; display:flex; flex-direction:column; justify-content:center; }
    .metric strong { font-family:'Space Grotesk'; font-size:2rem; color:var(--accent); display:block; }
    .welcome-title { text-align:center; color:#FFFFFF; font-family:'Space Grotesk', sans-serif; font-size:2.2rem; margin:1.5rem 0 .4rem; }
    .welcome-slogan { text-align:center; color:#FFFFFF; font-size:1.15rem; font-weight:600; margin:1.4rem 0 2rem; }
    .welcome-quote { max-width:900px; margin:2.2rem auto 2rem; padding:1.5rem 2rem; text-align:center; color:#21141B; background:var(--blush); border:1px solid var(--line); border-radius:20px; box-shadow:0 10px 30px #00000030; font-family:'Space Grotesk', sans-serif; font-size:clamp(1.3rem, 2.4vw, 2rem); font-weight:600; line-height:1.45; }
    .feature-card { height:100%; min-height:180px; box-sizing:border-box; padding:1.5rem; text-align:center; background:var(--blush); color:#000000; border:1px solid var(--line); border-radius:18px; box-shadow:0 8px 24px #00000030; }
    .feature-card .feature-icon { font-size:2rem; margin-bottom:.55rem; }
    .feature-card h3 { margin:.2rem 0 .55rem; font-size:1.15rem; color:#000000; }
    .feature-card p { margin:0; color:#000000; line-height:1.55; }
    .journey-points { max-width:900px; margin:1.5rem auto; display:grid; gap:.8rem; }
    .journey-point { display:flex; align-items:center; gap:1rem; padding:1rem 1.2rem; background:var(--blush); color:#000000; border:1px solid var(--line); border-radius:14px; box-shadow:0 5px 18px #00000030; }
    .journey-number { flex:0 0 2.6rem; height:2.6rem; display:grid; place-items:center; border-radius:50%; color:var(--button-ink); background:var(--accent); font-family:'Space Grotesk', sans-serif; font-weight:700; }
    .journey-point strong { color:#21141B; }
    .journey-point p { margin:.15rem 0 0; color:#000000; }
    .dashboard-hint { max-width:900px; margin:1.5rem auto 0; padding:1rem 1.2rem; text-align:center; color:#000000; background:var(--blush); border-radius:14px; font-weight:600; }
    .auth-heading { text-align:center; color:#FFFFFF; font-family:'Space Grotesk', sans-serif; }
    .auth-subtitle { text-align:center; color:var(--ink); margin-bottom:1.2rem; }
    .job { background:var(--card); border-left:4px solid var(--accent); padding:1.1rem 1.25rem; margin:.75rem 0; border-radius:8px; box-shadow:0 5px 20px #6C4AB61A; }
    .job h3 { margin:0; font-size:1.1rem; }
    .muted { color:#FFFFFF; opacity:.72; }
    .score-wrap { display:flex; justify-content:center; margin:1rem 0 1.5rem; }
    .score-ring { width:180px; height:180px; border-radius:50%; display:grid; place-items:center; position:relative; }
    .score-ring::after { content:''; position:absolute; inset:14px; border-radius:50%; background:#211E24; }
    .score-value { position:relative; z-index:1; text-align:center; font-family:'Space Grotesk'; font-size:2rem; font-weight:700; color:var(--accent); }
    .score-value small { display:block; font-family:'DM Sans'; font-size:.8rem; font-weight:500; color:#FFFFFF; }
    .stButton > button[kind='primary'] { background:var(--accent); border-color:var(--accent); color:var(--button-ink); }
    .stButton > button:hover { border-color:var(--accent); color:var(--accent); }
    .stTextInput input, .stTextArea textarea, [data-baseweb='select'] > div { background:var(--card); border-color:var(--line); color:#FFFFFF; }
    [data-testid='stChatInput'] textarea { background:var(--card); color:var(--ink) !important; caret-color:var(--accent); }
    [data-testid='stChatInput'] textarea::placeholder { color:#C9C1C6 !important; opacity:1; }
    [data-testid='stChatInput'] button { color:var(--accent); }
    [data-testid='stChatMessage'] { color:#FFFFFF !important; }
    [data-testid='stChatMessage'] p, [data-testid='stChatMessage'] div { color:#FFFFFF !important; }
    [data-testid='stChatMessage']:has([data-testid='chatAvatarIcon-assistant']) { background:#211E24; border:1px solid var(--line); border-radius:12px; }
    [data-testid='stChatMessage']:has([data-testid='chatAvatarIcon-user']) { background:#FBEAF1; border:1px solid #F4B6CF; border-radius:12px; }
    [data-testid='stChatMessage']:has([data-testid='chatAvatarIcon-user']) p, [data-testid='stChatMessage']:has([data-testid='chatAvatarIcon-user']) div { color:#000000 !important; }
    [data-baseweb='tab-list'] { gap:.5rem; background:#211E24; padding:.35rem; border-radius:12px; border:1px solid var(--line); }
    [data-baseweb='tab'] { color:var(--accent) !important; background:#211E24; font-weight:700; padding:.7rem 1rem; border-radius:8px; }
    [data-baseweb='tab'][aria-selected='true'] { color:var(--button-ink) !important; background:var(--accent) !important; border-radius:8px; }
    [data-baseweb='tab-highlight'] { background:var(--accent) !important; }
    @media (max-width: 640px) {
        .hero { padding:1.5rem 0 1rem; }
        .hero h1 { font-size:2.35rem; }
        .welcome-title { font-size:1.7rem; }
        .welcome-slogan { font-size:1rem; }
        .welcome-quote { padding:1.2rem; }
        .feature-card { min-height:150px; margin-bottom:.75rem; }
        .journey-point { align-items:flex-start; padding:.85rem; }
        .metric { min-height:92px; padding:.75rem; }
        .job { padding:1rem; }
        .score-ring { width:150px; height:150px; }
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_state() -> None:
    defaults = {"user": None, "resume_text": "", "resume_skills": [], "selected_role": "Python Developer", "selected_company": "Google", "messages": [], "workspace_page": "Overview"}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def welcome_page() -> None:
    st.markdown(
        '<div class="welcome-title">Welcome to CareerPilot</div>'
        '<div class="welcome-quote">“Your next opportunity begins with one brave step, one skill sharpened, and one conversation practiced.”</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(3)
    cards = [
        ("🔎", "Find roles", "Explore opportunities and choose a direction that fits your goals."),
        ("📄", "Improve your skills", "See your strengths, spot skill gaps, and plan what to learn next."),
        ("🎤", "Practice interviews", "Build confidence by practicing answers before the real conversation."),
    ]
    for column, (icon, title, description) in zip(columns, cards):
        with column:
            st.markdown(
                f'<div class="feature-card"><div class="feature-icon">{icon}</div>'
                f'<h3>{title}</h3><p>{description}</p></div>',
                unsafe_allow_html=True,
            )
    st.write("")
    _, action_column, _ = st.columns([1, 2, 1])
    with action_column:
        start_journey = st.button(
            "Begin My CareerPilot Journey",
            type="primary",
            use_container_width=True,
        )
    if start_journey:
        st.session_state["show_auth"] = True
        st.rerun()


def auth_page() -> None:
    st.markdown("<h2 class='auth-heading'>Welcome to CareerPilot</h2>", unsafe_allow_html=True)
    st.markdown("<p class='auth-subtitle'>Choose an option to begin your career journey</p>", unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["Log in", "Create account"])
    with tab_login:
        with st.form("login_form"):
            st.markdown("### Log in")
            email = st.text_input("Email", placeholder="Enter your email", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", help="Password must contain at least 8 characters.", key="login_password")
            st.caption("Password must contain at least 8 characters.")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            try:
                user = login(email, password)
            except (sqlite3.Error, OSError):
                logger.exception("Could not log in because the database is unavailable.")
                st.error("Login is temporarily unavailable because the database could not be opened.")
                return
            if user:
                st.session_state["user"] = user
                st.rerun()
            st.error("Email or password not recognized.")
    with tab_register:
        with st.form("register_form"):
            st.markdown("### Create account")
            name = st.text_input("Name", placeholder="Enter your name")
            email = st.text_input("Email", placeholder="Enter your email", key="register_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", help="Password must contain at least 8 characters.")
            st.caption("Password must contain at least 8 characters.")
            submitted = st.form_submit_button("Create account", type="primary")
        if submitted:
            try:
                success, message = register(name, email, password)
            except (sqlite3.Error, OSError):
                logger.exception("Could not register because the database is unavailable.")
                st.error("Account creation is temporarily unavailable because the database could not be opened.")
                return
            if success:
                try:
                    st.session_state["user"] = login(email, password)
                except (sqlite3.Error, OSError):
                    logger.exception("The account was created, but automatic login failed.")
                    st.error("Your account was created, but automatic login failed. Please log in.")
                    return
                st.rerun()
            st.error(message)


def dashboard() -> None:
    with st.sidebar:
        st.markdown("## CareerPilot")
        st.caption(f"Signed in as {st.session_state['user']['name']}")
        page = st.radio("Dashboard", ["Overview", "Find roles", "Resume lab", "Interview coach"], key="workspace_page")
        st.divider()
        if st.button("Log out"):
            st.session_state["user"] = None
            st.rerun()

    if page == "Overview":
        overview_page()
    elif page == "Find roles":
        jobs_page()
    elif page == "Resume lab":
        resume_page()
    else:
        interview_page()


def overview_page() -> None:
    first_name = html.escape(st.session_state["user"]["name"].strip().split()[0])
    st.markdown("<div class='welcome-title'>Welcome to CareerPilot ✨</div>", unsafe_allow_html=True)
    st.markdown(
        f"<h1 style='text-align:center'>Good to see you, {first_name}.</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='welcome-slogan'>Every small step you take today moves your career forward.</p>",
        unsafe_allow_html=True,
    )
    points = [
        ("Choose your direction", "Explore opportunities that connect with your interests and goals."),
        ("Show what you can do", "Use your resume to highlight your experience and discover skill gaps."),
        ("Learn with purpose", "Turn missing skills into clear, manageable next steps."),
        ("Practice with confidence", "Prepare for interviews one thoughtful answer at a time."),
        ("Keep moving forward", "Progress comes from consistent effort, not having everything figured out at once."),
    ]
    point_cards = "".join(
        f'<div class="journey-point"><div class="journey-number">{number:02}</div>'
        f'<div><strong>{title}</strong><p>{description}</p></div></div>'
        for number, (title, description) in enumerate(points, start=1)
    )
    st.markdown(f'<div class="journey-points">{point_cards}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-hint">Your dashboard is on the left. Choose Find roles, Resume lab, '
        'or Interview coach to start your journey.</div>',
        unsafe_allow_html=True,
    )


def jobs_page() -> None:
    st.markdown('<div class="eyebrow">01 / Role discovery</div><h1>Choose a direction.</h1>', unsafe_allow_html=True)
    left, right = st.columns([1, 1])
    with left:
        company = st.selectbox("Company", COMPANY_OPTIONS)
    with right:
        role = st.selectbox("Job role", ROLE_OPTIONS)
    if st.button("Find current openings", type="primary"):
        jobs, demo_mode = search_jobs(company, role)
        st.session_state["jobs"] = jobs
        st.session_state["jobs_demo"] = demo_mode
        st.session_state["selected_company"] = company
        st.session_state["selected_role"] = role
    jobs = st.session_state.get("jobs", [])
    if jobs:
        for job in jobs:
            st.markdown(f'<div class="job"><h3>{job["title"]}</h3><b>{job["company"]}</b><span class="muted"> · {job["location"]}</span><p class="muted">Skills: {", ".join(job["skills"])}</p></div>', unsafe_allow_html=True)
            st.link_button("Apply now", job["url"], use_container_width=False)
    elif "jobs" in st.session_state:
        st.info("No jobs matched those filters. Try Any role or clear the company field.")


def resume_page() -> None:
    st.markdown('<div class="eyebrow">02 / Resume lab</div><h1>Make your experience legible.</h1>', unsafe_allow_html=True)
    selected_company = st.session_state.get("selected_company", "Google")
    selected_role = st.session_state.get("selected_role", "Python Developer")
    st.info(f"Matching your resume for **{selected_role}** at **{selected_company}**. Select a company and role in Find roles first to change this target.")
    upload = st.file_uploader("Upload a PDF resume", type=["pdf"])
    if upload and st.button("Extract and analyze", type="primary"):
        st.session_state["resume_text"] = ""
        st.session_state["resume_skills"] = []
        st.session_state["analysis"] = {}
        try:
            resume_text = extract_pdf_text(upload)
            if not resume_text:
                st.warning("No readable text was found in this PDF. Upload a text-based PDF resume.")
            else:
                resume_skills = extract_skills(resume_text)
                analysis = analyze_resume(resume_text, selected_role, resume_skills)
                st.session_state["resume_text"] = resume_text
                st.session_state["resume_skills"] = resume_skills
                st.session_state["analysis"] = analysis
        except Exception as error:
            logger.exception("Could not extract or analyze the uploaded resume.")
            st.error(f"Could not read this PDF: {error}")
    if st.session_state.get("resume_text"):
        skills = st.session_state["resume_skills"]
        st.markdown(f"**Detected skills:** {', '.join(skills) if skills else 'No catalogued skills detected yet.'}")
        analysis = st.session_state.get("analysis", {})
        st.subheader("Resume readout")
        st.write(analysis.get("summary", ""))
        if analysis.get("strengths"):
            st.write("Strengths: " + "; ".join(analysis["strengths"]))
        st.write("Next edit: " + analysis.get("advice", "Add measurable outcomes to your strongest experience."))
        st.divider()
        st.subheader(f"Role fit: {selected_role} at {selected_company}")
        jobs, _ = search_jobs(company=selected_company, role=selected_role)
        target = jobs[0] if jobs else {"skills": []}
        result = match_skills(skills, target["skills"])
        score = max(0, min(100, result["score"]))
        score_degrees = score * 3.6
        st.markdown(
            f'<div class="score-wrap"><div class="score-ring" role="img" aria-label="Role match score: {score} percent" style="background:conic-gradient(from -90deg, var(--accent) 0deg {score_degrees}deg, #211E24 {score_degrees}deg 360deg)"><div class="score-value">{score}%<small>role match</small></div></div></div>',
            unsafe_allow_html=True,
        )
        match_column, missing_column = st.columns(2)
        with match_column:
            st.subheader("Matching skills")
            if result["matched"]:
                for skill in result["matched"]:
                    st.success(skill.title())
            else:
                st.info("No matching skills detected yet.")
        missing = result["missing"]
        with missing_column:
            st.subheader("Missing skills")
            if missing:
                for skill in missing:
                    st.warning(skill.title())
            else:
                st.success("None identified")
        if missing:
            st.subheader("Learn the missing skills")
            for resource in recommend_resources(missing):
                st.markdown(f"**{resource['skill'].title()}**")
                website, youtube = st.columns(2)
                with website:
                    st.link_button("Open website course", resource["url"], use_container_width=True)
                with youtube:
                    st.link_button("Watch YouTube tutorials", resource["youtube_url"], use_container_width=True)
        else:
            st.success("No missing skills identified for this role.")


def interview_page() -> None:
    st.markdown('<div class="eyebrow">03 / Interview coach</div><h1>Practice the answer before the pressure.</h1>', unsafe_allow_html=True)
    role = st.selectbox("Practice role", ROLE_OPTIONS, key="interview_role")
    if st.session_state.get("interview_active_role") != role:
        st.session_state["messages"] = []
        st.session_state["interview_active_role"] = role
    practice_mode = "Interview chatbot"

    if practice_mode == "Self intro":
        st.subheader("Build a confident introduction")
        with st.form("self_intro_form"):
            candidate_name = st.text_input("Your name", key="intro_name")
            experience = st.text_input("Experience or current status", placeholder="Final-year student / 2 years in backend development", key="intro_experience")
            strengths = st.text_input("Top skills", placeholder="Python, SQL, APIs", key="intro_skills")
            project = st.text_area("Project or achievement", placeholder="What you built, your contribution, and the result", key="intro_project")
            goal = st.text_input("Why this role?", placeholder="What interests you about this role", key="intro_goal")
            build_intro = st.form_submit_button("Prepare my introduction", type="primary")
        if build_intro:
            if not all([candidate_name.strip(), experience.strip(), strengths.strip(), project.strip(), goal.strip()]):
                st.session_state["intro_draft"] = ""
                st.warning("Fill in each field to build a complete introduction.")
            else:
                st.session_state["intro_draft"] = (
                    f"Hi, I'm {candidate_name.strip()}. I'm a {experience.strip()} with strengths in {strengths.strip()}. "
                    f"One project I'm proud of is {project.strip()}. It helped me develop practical problem-solving and collaboration skills. "
                    f"I'm interested in this {role} opportunity because {goal.strip()}, and I'm excited to contribute while continuing to grow."
                )
        if st.session_state.get("intro_draft"):
            st.text_area("Your practice version", value=st.session_state["intro_draft"], height=170, key="intro_draft_output")
            st.caption("Keep it natural: practice the key points, not every word.")

    if practice_mode == "Technical Q&A":
        st.subheader(f"Technical questions for {role}")
        technical_sets = {
            "Python": [
                ("What is the difference between a list and a tuple?", "Lists are mutable; tuples are immutable. Choose based on whether the collection should change, and mention common use cases."),
                ("How does a Python dictionary work?", "Explain key-value storage, hashing, average lookup complexity, and that keys must be hashable."),
                ("What are generators, and when would you use one?", "Describe lazy iteration with yield, lower memory use for large streams, and one practical use."),
            ],
            "Data": [
                ("How do you handle missing values in a dataset?", "First measure and understand why values are missing; then justify dropping, imputing, or flagging them and validate the impact."),
                ("Explain the difference between WHERE and HAVING in SQL.", "WHERE filters rows before grouping; HAVING filters groups after aggregation. Give a short grouped-query example."),
                ("How would you explain a model or analysis result to a non-technical stakeholder?", "Lead with the decision and impact, use plain language and a simple visual, then state assumptions and uncertainty."),
            ],
            "Web": [
                ("What happens when a browser requests a web page?", "Cover DNS, connection/TLS, HTTP request and response, server processing, and browser rendering at an appropriate level."),
                ("How do you design a REST API endpoint?", "Discuss resource naming, HTTP methods/status codes, validation, error shape, pagination, and authentication."),
                ("How do you debug a slow web application?", "Reproduce and measure first; inspect browser/network and server metrics; isolate bottlenecks; verify the fix with measurements."),
            ],
            "DevOps": [
                ("What problem do containers solve?", "Explain packaging an application with dependencies for consistent environments, while distinguishing containers from virtual machines."),
                ("What stages belong in a reliable CI/CD pipeline?", "Mention lint/tests, build, security checks, deploy to a safe environment, health checks, and rollback."),
                ("How would you investigate a production outage?", "Prioritize impact and mitigation, inspect logs/metrics/traces, communicate status, restore service, then document root cause and prevention."),
            ],
            "QA": [
                ("What is the difference between unit, integration, and end-to-end tests?", "Explain their scope, dependencies, speed, and where each catches failures in the system."),
                ("How do you decide what to test first?", "Prioritize user impact, failure likelihood, critical paths, boundary cases, and recent changes."),
                ("How would you report a useful bug?", "Include environment, clear reproduction steps, expected versus actual behavior, evidence, and severity/impact."),
            ],
        }
        if "Data" in role or "Machine Learning" in role:
            question_set = technical_sets["Data"]
        elif "Frontend" in role or "Full Stack" in role or "Backend" in role:
            question_set = technical_sets["Web"]
        elif "DevOps" in role or "Cloud" in role:
            question_set = technical_sets["DevOps"]
        elif "QA" in role:
            question_set = technical_sets["QA"]
        else:
            question_set = technical_sets["Python"]
        selected_question = st.selectbox("Choose a question", [item[0] for item in question_set], key="technical_question")
        technical_context = (role, selected_question)
        if st.session_state.get("technical_context") != technical_context:
            st.session_state["technical_context"] = technical_context
            st.session_state["technical_answer"] = ""
            st.session_state["technical_review"] = ""
        answer_outline = dict(question_set)[selected_question]
        with st.expander("Answer points to cover"):
            st.write(answer_outline)
        technical_answer = st.text_area("Your answer", placeholder="Write your answer as if you were speaking to the interviewer...", key="technical_answer")
        if st.button("Review technical answer", key="review_technical", type="primary"):
            if not technical_answer.strip():
                st.warning("Write an answer first so the coach can review it.")
            else:
                st.session_state["technical_review"] = review_interview_response(selected_question, technical_answer, role, "technical")
        if st.session_state.get("technical_review"):
            st.markdown("**Coach feedback**")
            st.write(st.session_state["technical_review"])

    if practice_mode == "Coding mock":
        st.subheader("Coding practice")
        challenges = {
            "Two Sum": "Given a list of integers and a target, return the indices of two distinct values that add up to the target. Assume exactly one solution.",
            "First Unique Character": "Given a string, return the index of its first non-repeating character. Return -1 if every character repeats.",
            "Merge Overlapping Intervals": "Given a list of [start, end] intervals, merge every overlapping interval and return the remaining intervals in sorted order.",
        }
        challenge = st.selectbox("Challenge", list(challenges), key="coding_challenge")
        language = st.selectbox("Language", ["Python", "JavaScript", "Java", "SQL"], key="coding_language")
        coding_context = (role, challenge, language)
        if st.session_state.get("coding_context") != coding_context:
            st.session_state["coding_context"] = coding_context
            st.session_state["coding_answer"] = ""
            st.session_state["coding_review"] = ""
        st.markdown(f"**Problem**\n\n{challenges[challenge]}")
        st.caption("Suggested time: 20 minutes. Test normal input, edge cases, and explain complexity.")
        code_answer = st.text_area("Your solution", height=220, placeholder=f"Write your {language} solution here...", key="coding_answer")
        if st.button("Submit for code review", key="review_code", type="primary"):
            if not code_answer.strip():
                st.warning("Write a solution first so the coach can review it.")
            else:
                st.session_state["coding_review"] = review_interview_response(challenges[challenge], code_answer, role, "code")
        if st.session_state.get("coding_review"):
            st.markdown("**Code review**")
            st.write(st.session_state["coding_review"])

    if practice_mode == "Interview chatbot":
        st.subheader("CareerPilot AI")
        if not st.session_state["messages"]:
            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": "Hi! I'm CareerPilot AI. Ask me anything, or we can practice for your interview.",
                }
            )
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        prompt = st.chat_input("Ask me anything...")
        if prompt:
            st.session_state["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = st.write_stream(interview_reply_stream(st.session_state["messages"], role))
            st.session_state["messages"].append({"role": "assistant", "content": reply})


initialize_state()
inject_styles()
if st.session_state["user"]:
    dashboard()
elif st.session_state.get("show_auth"):
    auth_page()
else:
    welcome_page()
