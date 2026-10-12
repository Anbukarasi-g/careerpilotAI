"""Gemini integration with useful deterministic fallbacks for local development."""
import json
import logging
import re
from collections.abc import Iterator
from google import genai
from google.genai.errors import APIError
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

TECHNICAL_QUESTION_BANKS = {
    "Python": [
        ("What is the difference between a list and a tuple?", (("mutable", "changeable"), ("immutable", "unchangeable"))),
        ("How does a Python dictionary work?", (("key-value", "key value", "keys and values"), ("hash",), ("lookup", "search"))),
        ("What is a generator, and when would you use one?", (("yield",), ("lazy", "on demand"), ("memory",))),
    ],
    "Data": [
        ("How would you handle missing values in a dataset?", (("investigate", "understand", "analyze"), ("impute", "fill", "drop", "remove"), ("validate", "impact", "bias"))),
        ("What is the difference between WHERE and HAVING in SQL?", (("before", "row"), ("after", "group", "aggregate"))),
        ("How would you explain an analysis result to a non-technical stakeholder?", (("impact", "decision", "result"), ("plain language", "simple", "clear"), ("assumption", "uncertainty", "limitation"))),
    ],
    "Web": [
        ("What makes an API RESTful?", (("resource",), ("http", "method"), ("stateless", "statelessness"))),
        ("How would you debug a slow web application?", (("measure", "reproduce", "profile"), ("bottleneck", "trace", "inspect"), ("verify", "measure again", "test"))),
        ("How do you handle errors in a web API?", (("status code", "http code"), ("message", "error response"), ("log", "logging"))),
    ],
    "DevOps": [
        ("What problem do containers solve?", (("package", "package application", "dependencies"), ("consistent", "reproducible"), ("isolat",))),
        ("What stages belong in a reliable CI/CD pipeline?", (("test",), ("build",), ("deploy", "release"), ("rollback", "health check", "monitor"))),
        ("How would you respond to a production outage?", (("impact", "prioritize", "mitigate"), ("logs", "metrics", "traces"), ("communicate", "status"), ("root cause", "postmortem"))),
    ],
    "QA": [
        ("What is the difference between unit, integration, and end-to-end tests?", (("unit",), ("integration",), ("end-to-end", "e2e"), ("scope", "system"))),
        ("How do you decide what to test first?", (("impact", "risk", "critical"), ("likelihood", "probability"), ("boundary", "edge case"))),
        ("What should a useful bug report include?", (("steps", "reproduce"), ("expected",), ("actual",), ("environment", "evidence"))),
    ],
}

def _model():
    if not GEMINI_API_KEY:
        return None
    return genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=20000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def analyze_resume(resume_text: str, target_role: str, target_skills: list[str]) -> dict:
    try:
        model = _model()
        if not model:
            return {"summary": f"Your resume is being evaluated for {target_role}.", "strengths": ["Relevant experience detected from your resume"], "advice": "Add measurable outcomes and tailor keywords to the target role."}
        prompt = f"Return only valid JSON with keys summary, strengths (array), advice. Analyze this resume for {target_role} requiring {target_skills}:\n{resume_text[:12000]}"
        response = model.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        response_text = (getattr(response, "text", "") or "").strip()
        result = json.loads(response_text.replace("```json", "").replace("```", "").strip())
        if not isinstance(result, dict):
            raise ValueError("Resume analysis must be a JSON object.")

        summary = result.get("summary", "The AI response could not be read.")
        if not isinstance(summary, str):
            summary = "The AI response could not be read."

        strengths = result.get("strengths", [])
        if isinstance(strengths, str):
            strengths = [strengths]
        if not isinstance(strengths, list):
            strengths = []

        advice = result.get("advice", "Review the resume manually and try again.")
        if isinstance(advice, list):
            advice = "; ".join(str(item) for item in advice)
        elif not isinstance(advice, str):
            advice = "Review the resume manually and try again."

        return {
            "summary": summary,
            "strengths": [str(item) for item in strengths if item is not None],
            "advice": advice,
        }
    except (ValueError, TypeError, json.JSONDecodeError):
        return {"summary": "The AI response could not be read.", "strengths": [], "advice": "Review the resume manually and try again."}
    except Exception:
        logger.exception("AI resume analysis failed.")
        return {
            "summary": f"AI analysis is temporarily unavailable for the {target_role} role.",
            "strengths": [],
            "advice": "Your resume was uploaded successfully. You can still review the role match and skill gaps below.",
        }


def _greeting_reply(messages: list[dict]) -> str | None:
    latest = messages[-1].get("content", "").strip() if messages else ""
    greeting = re.fullmatch(
        r"(?:hi+|hello+|hey+|vanakkam)(?:[,!\s]+(?:i'?m|my name is)\s+([A-Za-z][A-Za-z -]*))?[.!?\s]*",
        latest,
        re.IGNORECASE,
    )
    if greeting:
        name = greeting.group(1).strip().title() if greeting.group(1) else ""
        return (
            f"Hi {name}! Nice to meet you. We can chat about anything or work on interview prep. "
            "What would you like to start with?"
        )
    return None


def _interview_prompt(messages: list[dict], role: str) -> str:
    transcript = "\n".join(f"{item['role']}: {item['content']}" for item in messages[-20:])
    instructions = (
        f"You are CareerPilot AI, a helpful general-purpose assistant with particular expertise in career and interview preparation "
        f"for a {role} candidate. Answer the latest user message directly and specifically, whatever the topic; do not assume every message is "
        "about interviews, force unrelated questions back to career advice, or restrict answers to a menu of features. Explain concepts, "
        "solve problems, help with writing, and have natural follow-up conversation like a capable general AI assistant. Use the full "
        "conversation context and keep relevant details in mind. Do not repeat an earlier assistant answer unless the user asks you to "
        "repeat or summarize it; make every reply relevant to the newest message. Treat each conversation as a separate person: use only details that "
        "this user shares in this conversation, never assume their name or background, and never carry another user's identity or "
        "details into this chat. Adapt the explanation to this user's apparent experience level and request. Match their language, "
        "writing style, and tone, including Tamil-English/Tanglish or Tamil script when appropriate. Be accurate, clear, and "
        "appropriately detailed; say when uncertain instead of inventing facts.\n\n"
        "When the user does ask for interview practice: for self-introductions, offer useful tips and a tailored draft from their "
        "details; for technical or coding practice, ask one question at a time, review the answer, explain gaps, then continue; for "
        "aptitude/reasoning, offer a question set and validate their answers with explanations. Never claim submitted code was executed. "
        "Do not add an interview follow-up to unrelated general questions."
    )
    return (
        f"{instructions}\n\nConversation:\n"
        f"{transcript or 'No messages yet. Greet the user and briefly explain that you can help with general questions as well as interview practice.'}"
    )


def _generate_interview_reply(model, messages: list[dict], role: str) -> str:
    prompt = _interview_prompt(messages, role)
    response = model.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "thinking_config": {"thinking_level": "MINIMAL"},
            "max_output_tokens": 1024,
        },
    )
    reply = (getattr(response, "text", "") or "").strip()
    if not reply:
        return _offline_interview_reply(messages, role)

    previous_replies = {
        item.get("content", "").strip()
        for item in messages[:-1]
        if item.get("role") == "assistant" and isinstance(item.get("content"), str)
    }
    if reply in previous_replies:
        retry_prompt = (
            prompt
            + "\n\nYour draft exactly repeats an earlier assistant response. Reply to the newest user message "
            "with fresh, directly relevant information and different wording. Do not repeat that earlier response."
        )
        response = model.models.generate_content(
            model=GEMINI_MODEL,
            contents=retry_prompt,
            config={
                "thinking_config": {"thinking_level": "MINIMAL"},
                "max_output_tokens": 1024,
            },
        )
        retry_reply = (getattr(response, "text", "") or "").strip()
        if retry_reply:
            reply = retry_reply
        if reply in previous_replies:
            return _offline_interview_reply(messages, role)
    return reply


def interview_reply(messages: list[dict], role: str) -> str:
    try:
        model = _model()
        if not model:
            return _offline_interview_reply(messages, role)
        return _generate_interview_reply(model, messages, role)
    except APIError as error:
        logger.warning("AI interview reply failed with API status %s: %s", error.code, error)
        return _interview_api_fallback(messages, role, error)
    except Exception as error:
        logger.exception("AI interview reply failed.")
        return _interview_api_fallback(messages, role, error)


def interview_reply_stream(messages: list[dict], role: str) -> Iterator[str]:
    try:
        model = _model()
        if not model:
            yield _offline_interview_reply(messages, role)
            return
        yield _generate_interview_reply(model, messages, role)
    except APIError as error:
        logger.warning("Streaming AI interview reply failed with API status %s: %s", error.code, error)
        yield _interview_api_fallback(messages, role, error)
    except Exception as error:
        logger.exception("Streaming AI interview reply failed.")
        yield _interview_api_fallback(messages, role, error)


def _interview_api_fallback(messages: list[dict], role: str, error: Exception) -> str:
    fallback_reply = _offline_interview_reply(messages, role)
    if isinstance(error, APIError) and error.code == 429:
        notice = (
            "Gemini's request quota is exhausted, so I can't answer this open-ended question reliably "
            "right now. Check your Google AI Studio quota and billing, or try again after the quota resets."
        )
    elif isinstance(error, APIError) and error.code == 403:
        notice = (
            "Gemini denied access to this project (403). Check that this API key belongs to a Google AI "
            "Studio project allowed to use the Gemini API and selected model. If access is still denied, "
            "contact Google AI Studio support; changing the key alone may not fix a project-level restriction."
        )
    elif isinstance(error, APIError) and error.code == 401:
        notice = (
            "Gemini rejected the API key (401). Check GEMINI_API_KEY in your .env file, save it, "
            "and restart Streamlit."
        )
    else:
        notice = (
            "Gemini is temporarily unavailable, so I can't answer this open-ended question reliably "
            "right now. Please try again later."
        )
    if fallback_reply.startswith(("I understand you're asking:", "நீங்கள் கேட்டது:")):
        return notice
    return f"{fallback_reply}\n\n{notice}"


def _technical_questions(role: str) -> list[tuple[str, tuple[tuple[str, ...], ...]]]:
    if "data" in role.lower() or "machine learning" in role.lower():
        return TECHNICAL_QUESTION_BANKS["Data"]
    if any(keyword in role.lower() for keyword in ("frontend", "full stack", "backend")):
        return TECHNICAL_QUESTION_BANKS["Web"]
    if any(keyword in role.lower() for keyword in ("devops", "cloud")):
        return TECHNICAL_QUESTION_BANKS["DevOps"]
    if "qa" in role.lower():
        return TECHNICAL_QUESTION_BANKS["QA"]
    return TECHNICAL_QUESTION_BANKS["Python"]


def _offline_interview_reply(messages: list[dict], role: str) -> str:
    latest = next(
        (
            item.get("content", "").strip()
            for item in reversed(messages)
            if item.get("role") == "user" and isinstance(item.get("content"), str)
        ),
        "",
    )
    prior_replies = {
        item.get("content", "").strip()
        for item in messages
        if item.get("role") == "assistant" and isinstance(item.get("content"), str)
    }
    is_tamil = any("\u0b80" <= character <= "\u0bff" for character in latest)
    lowered = latest.lower()

    if not latest:
        reply = f"வணக்கம்! எந்தக் கேள்வியாக இருந்தாலும் கேளுங்கள்; முடிந்தவரை நேரடியாகவும் தெளிவாகவும் உதவுகிறேன்." if is_tamil else (
            f"Hi! Ask me anything, and I'll do my best to give you a clear, useful answer."
        )
    else:
        greeting = _greeting_reply([{"role": "user", "content": latest}])
        if greeting:
            reply = greeting
        elif any(term in lowered for term in ("thank you", "thanks", "ரொம்ப நன்றி", "நன்றி")):
            reply = "மகிழ்ச்சி! இன்னும் ஏதாவது உதவி வேண்டும்னா கேளுங்கள்." if is_tamil else (
                "You're welcome! What would you like to explore next?"
            )
        elif match := re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:of|ஐ)\s*(\d+(?:\.\d+)?)", lowered):
            percentage, value = (float(number) for number in match.groups())
            result = percentage * value / 100
            formatted_result = str(int(result)) if result.is_integer() else f"{result:.2f}".rstrip("0").rstrip(".")
            reply = f"{percentage:g}% of {value:g} = {formatted_result}." if not is_tamil else (
                f"{value:g}-இல் {percentage:g}% = {formatted_result}."
            )
        elif (
            any(term in lowered for term in ("what is", "what's", "define ", "meaning of", "என்றால் என்ன"))
            or lowered.strip(" .!?") in {
                "python", "sql", "api", "git", "html", "css", "machine learning",
                "recursion", "database", "streamlit", "artificial intelligence",
            }
        ):
            definitions = {
                "python": "Python is a general-purpose programming language known for readable syntax and a large ecosystem of libraries.",
                "sql": "SQL is the language used to query and manage data in relational databases.",
                "api": "An API is a defined way for software systems to request data or actions from one another.",
                "git": "Git is a version-control system that records changes to files and helps people collaborate on code.",
                "html": "HTML describes the structure and content of a web page.",
                "css": "CSS controls how web content is styled and laid out.",
                "machine learning": "Machine learning is a way to build systems that learn patterns from data to make predictions or decisions.",
                "recursion": "Recursion is when a function solves a problem by calling itself on a smaller version of that problem, with a base case to stop.",
                "database": "A database is an organized system for storing, finding, and updating information.",
                "streamlit": "Streamlit is a Python framework for building interactive data and AI apps with simple scripts.",
                "artificial intelligence": "Artificial intelligence is the broad field of building systems that perform tasks associated with human reasoning, perception, or language.",
            }
            topic = next((term for term in sorted(definitions, key=len, reverse=True) if term in lowered), None)
            if topic:
                reply = definitions[topic]
            else:
                reply = (
                    f"“{latest}” asks for a definition. In simple terms, what specific word or concept would you like me to define?"
                    if not is_tamil else
                    f"“{latest}” என்பதில் எந்தச் சொல் அல்லது கருத்தின் அர்த்தம் வேண்டும் என்று குறிப்பிட்டால், எளிமையாக விளக்குகிறேன்."
                )
        elif any(term in lowered for term in ("self intro", "introduce myself", "tell me about yourself")):
            reply = (
                "உங்கள் அறிமுகத்தை 45–60 விநாடிக்குள் சொல்லுங்கள்: தற்போதைய நிலை/அனுபவம், முக்கிய திறன்கள், "
                "ஒரு project-ல் உங்கள் பங்கு மற்றும் அதன் முடிவு, இந்த role ஏன் பிடித்திருக்கிறது. "
                "உங்கள் விவரங்களை அனுப்பினால், இயல்பான அறிமுகமாக எழுதித் தருகிறேன்."
                if is_tamil else
                f"For a {role} self-introduction, briefly cover your current experience, two relevant skills, "
                "one project with your contribution and result, and why this role interests you. Share those details "
                "and I'll help shape them into a natural introduction."
            )
        elif any(term in lowered for term in ("weakness", "weak point")):
            reply = (
                "உண்மையான, மேம்படுத்திக் கொண்டிருக்கும் ஒரு திறனைத் தேர்வு செய்து, அதை மேம்படுத்த நீங்கள் எடுத்துவரும் "
                "நடவடிக்கையையும் சொல்லுங்கள். ஒரு குறிப்பிட்ட உதாரணம் சேர்த்தால் பதில் நம்பகமாக இருக்கும்."
                if is_tamil else
                "Choose a genuine skill you're improving, explain the action you're taking, and give one example "
                "of your progress. That keeps the answer honest and shows growth."
            )
        elif any(term in lowered for term in ("strength", "strengths", "பலங்கள்")):
            reply = (
                f"{role} பணிக்கு பொருந்தும் இரண்டு பலங்களைத் தேர்வு செய்து, ஒவ்வொன்றுக்கும் நீங்கள் செய்த வேலை மற்றும் "
                "கிடைத்த முடிவைச் சொல்லுங்கள். முடிந்தால் எண்ணிக்கையால் அதன் தாக்கத்தைக் காட்டுங்கள்."
                if is_tamil else
                f"Pick two strengths relevant to {role}. For each, give a brief example of what you did and the result; "
                "a measurable outcome makes the answer more convincing."
            )
        elif any(term in lowered for term in ("behavioral", "tell me about a time", "hr interview", "star method")):
            reply = (
                "STAR முறையைப் பயன்படுத்துங்கள்: Situation (சூழல்), Task (உங்கள் பொறுப்பு), Action (நீங்கள் செய்தது), "
                "Result (முடிவு). Action பகுதியைத் தெளிவாகச் சொல்லி, முடிந்தால் அதன் தாக்கத்தையும் அளவிடுங்கள்."
                if is_tamil else
                "Use STAR: briefly explain the Situation and Task, focus most on the Action you personally took, "
                "then finish with the Result and what you learned."
            )
        elif any(term in lowered for term in ("technical practice", "practice technical", "technical question")):
            question = _technical_questions(role)[0][0]
            reply = (
                f"{role}க்கு ஒரு technical practice கேள்வி: {question} உங்கள் சொற்களில் பதில் சொல்லுங்கள்; "
                "அதில் சரியாக உள்ளவை, மேம்படுத்த வேண்டியவை என்று குறிப்பிட்டு உதவுகிறேன்."
                if is_tamil else
                f"Let's practise one {role} question: {question} Answer in your own words, and I'll point out "
                "what is strong and what could be clearer."
            )
        elif any(term in lowered for term in ("coding practice", "coding question", "code challenge", "dsa practice")):
            reply = (
                "எந்த language-ல் code வேண்டும், எந்த input/output எதிர்பார்க்கிறீர்கள் என்று சொல்லுங்கள்; "
                "அதன்படி உதவுகிறேன். ஏற்கெனவே code இருந்தால், அதைச் சேர்த்து error அல்லது எதிர்பார்த்த முடிவையும் எழுதுங்கள்."
                if is_tamil else
                "Tell me the language, expected input/output, and any constraints. If you already have code, paste it "
                "with the error or result you expected, and I'll work through it with you."
            )
        else:
            excerpt = latest if len(latest) <= 180 else latest[:177].rstrip() + "..."
            if is_tamil:
                reply = (
                    f"நீங்கள் கேட்டது: “{excerpt}”. இதற்கு ஊகித்து பதில் சொல்லாமல் சரியாக உதவ விரும்புகிறேன். "
                    "இது எந்தச் சூழலைப் பற்றியது, அல்லது நீங்கள் எதிர்பார்க்கும் முடிவு என்ன என்பதைச் சுருக்கமாகச் சொல்லுங்கள்; "
                    "அதன்படி நேரடியாகப் பதிலளிக்கிறேன்."
                )
            else:
                reply = (
                    f"I understand you're asking: “{excerpt}”. I want to answer the exact question rather than guess. "
                    "Could you share one detail about the context or the result you're looking for? I'll tailor the answer to that."
                )

    if reply in prior_replies:
        follow_ups = (
            [
                " வேறு கோணத்தில் பார்க்க வேண்டுமா?",
                " ஒரு உதாரணத்துடன் விளக்கட்டுமா?",
                " இதை இன்னும் எளிமையாகச் சொல்லட்டுமா?",
            ]
            if is_tamil else
            [
                " Would you like a practical example?",
                " Should I explain that step by step?",
                " Would a simpler explanation help?",
            ]
        )
        original_reply = reply
        repeat_number = 0
        while reply in prior_replies:
            suffix = (
                follow_ups[repeat_number]
                if repeat_number < len(follow_ups)
                else f" Follow-up {repeat_number + 1}: would you like an example?"
            )
            reply = original_reply + suffix
            repeat_number += 1
    return reply


def review_interview_response(question: str, answer: str, role: str, response_type: str) -> str:
    try:
        model = _model()
        if not model:
            if response_type == "code":
                return (
                    "Review your solution against the sample cases, empty input, and the largest expected input. "
                    "Explain the algorithm, time complexity, and space complexity before the interview. "
                    "Add tests for duplicates and boundary values where relevant."
                )
            return (
                "Use a clear structure: define the concept, explain why it matters for the role, and support it "
                "with a specific example. Mention trade-offs and edge cases, then finish with the result."
            )
        prompt = (
            f"You are an interview coach for a {role} candidate. Review this {response_type} response to the question below. "
            "Give concise, specific feedback with one strength, two improvements, and a stronger answer outline. "
            "For code, also assess correctness risks, edge cases, and time/space complexity. Do not claim code was executed.\n"
            f"Question: {question}\nResponse:\n{answer[:12000]}"
        )
        response = model.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return (getattr(response, "text", "") or "").strip() or "The review was empty. Try submitting a more complete response."
    except Exception:
        logger.exception("AI interview review failed.")
        return "The AI review is temporarily unavailable. Check correctness, edge cases, and complexity, then try again."
