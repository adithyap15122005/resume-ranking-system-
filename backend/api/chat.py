"""
AI Recruiter Chat Assistant — rule-based intelligent responses over resume/job data.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.core.database import get_db
from backend.models.job import JobDescription
from backend.models.ranking import RankingResult
from backend.models.resume import Resume
from backend.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["AI Assistant"])

# Session-level chat history (use Redis in production)
_chat_history: Dict[str, List[Dict]] = {}


class ChatRequest(BaseModel):
    message: str
    job_id: Optional[str] = None
    resume_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    suggestions: List[str] = []
    data: Optional[Dict] = None
    timestamp: datetime


# ── Intent Matching ───────────────────────────────────────────────────────────

def _detect_intent(msg: str) -> str:
    m = msg.lower()
    if any(kw in m for kw in ("best", "top", "highest", "top candidate", "number 1")):
        return "best_candidate"
    if any(kw in m for kw in ("compare", "vs", "versus", "difference between")):
        return "compare"
    if any(kw in m for kw in ("summarize", "summary", "about this", "tell me about")):
        return "summarize"
    if any(kw in m for kw in ("interview question", "questions to ask", "interview prep")):
        return "interview_questions"
    if any(kw in m for kw in ("skill gap", "missing skill", "what skill", "lacking")):
        return "skill_gaps"
    if any(kw in m for kw in ("rejection", "reject email", "decline", "not selected")):
        return "rejection_email"
    if any(kw in m for kw in ("offer letter", "job offer", "congratulation email")):
        return "offer_letter"
    if any(kw in m for kw in ("how many", "count", "total")):
        return "stats"
    if any(kw in m for kw in ("shortlist", "recommend", "who should i")):
        return "recommend"
    if any(kw in m for kw in ("explain", "why", "reason", "score")):
        return "explain_score"
    return "general"


# ── Response Generators ───────────────────────────────────────────────────────

async def _handle_best_candidate(db: AsyncSession, job_id: Optional[str], org_id: Optional[str]) -> str:
    q = select(RankingResult).order_by(RankingResult.similarity_score.desc()).limit(1)
    if job_id:
        q = q.where(RankingResult.job_id == job_id)
    if org_id:
        q = q.where(RankingResult.organization_id == org_id)
    res = await db.execute(q)
    rr = res.scalar_one_or_none()
    if not rr:
        return "I don't have any ranking results yet. Please run the ranking pipeline first by going to a job and clicking 'Rank Candidates'."

    resume_res = await db.execute(select(Resume).where(Resume.id == rr.resume_id))
    resume = resume_res.scalar_one_or_none()

    name = resume.candidate_name if resume else "Unknown"
    skills = ", ".join((resume.skills or [])[:5]) if resume else ""
    return (
        f"**{name}** is currently the top-ranked candidate with a match score of **{rr.similarity_score:.1f}%**.\n\n"
        f"**Recommendation:** {rr.recommendation}\n"
        f"**Matched Skills:** {', '.join(rr.matched_skills or [])[:100]}\n"
        f"**Missing Skills:** {', '.join(rr.missing_skills or [])[:100]}\n"
        f"**Experience:** {rr.experience_years:.1f} years\n"
        f"**Hiring Probability:** {rr.hiring_probability*100:.1f}%\n\n"
        f"Top skills: {skills}"
    )


async def _handle_stats(db: AsyncSession, org_id: Optional[str]) -> str:
    from sqlalchemy import func

    resume_q = select(func.count(Resume.id))
    job_q = select(func.count(JobDescription.id))
    ranking_q = select(func.count(RankingResult.id))

    if org_id:
        resume_q = resume_q.where(Resume.organization_id == org_id)
        job_q = job_q.where(JobDescription.organization_id == org_id)
        ranking_q = ranking_q.where(RankingResult.organization_id == org_id)

    total_r = (await db.execute(resume_q)).scalar_one()
    total_j = (await db.execute(job_q)).scalar_one()
    total_rk = (await db.execute(ranking_q)).scalar_one()

    return (
        f"Here's your current hiring snapshot:\n\n"
        f"- **Total Resumes:** {total_r}\n"
        f"- **Active Jobs:** {total_j}\n"
        f"- **Ranking Results:** {total_rk}\n\n"
        f"You can view detailed analytics on the Analytics dashboard."
    )


async def _handle_skill_gaps(db: AsyncSession, job_id: Optional[str], org_id: Optional[str]) -> str:
    q = select(RankingResult)
    if job_id:
        q = q.where(RankingResult.job_id == job_id)
    if org_id:
        q = q.where(RankingResult.organization_id == org_id)
    res = await db.execute(q)
    rankings = res.scalars().all()

    if not rankings:
        return "No ranking data found. Run the ranking pipeline first."

    gap_freq: Dict[str, int] = {}
    for rr in rankings:
        for s in (rr.missing_skills or []):
            gap_freq[s] = gap_freq.get(s, 0) + 1

    top_gaps = sorted(gap_freq.items(), key=lambda x: x[1], reverse=True)[:8]
    gap_lines = "\n".join(f"  - **{s}** (missing in {c}/{len(rankings)} candidates)" for s, c in top_gaps)

    return (
        f"**Top Skill Gaps Across {len(rankings)} Candidates:**\n\n"
        f"{gap_lines}\n\n"
        f"Consider candidates who are willing to learn these skills, or adjust job requirements accordingly."
    )


def _generate_rejection_email(candidate_name: str = "the candidate", job_title: str = "the position") -> str:
    return f"""**Rejection Email Template:**

---

Subject: Update on Your Application — {job_title}

Dear {candidate_name},

Thank you for taking the time to apply for the {job_title} position and for your interest in joining our team.

After careful consideration, we have decided to move forward with other candidates whose experience more closely aligns with our current requirements. This was a difficult decision given the competitive pool of applicants.

We genuinely appreciate the effort you put into your application and encourage you to apply for future openings that match your skills and experience. We will keep your profile on file.

We wish you all the best in your job search and future endeavors.

Warm regards,
[Recruiter Name]
[Company Name]

---"""


def _generate_offer_letter(candidate_name: str = "Candidate Name", job_title: str = "Position", salary: str = "TBD") -> str:
    return f"""**Offer Letter Template:**

---

Subject: Job Offer — {job_title}

Dear {candidate_name},

We are thrilled to offer you the position of **{job_title}** at [Company Name], effective [Start Date].

**Offer Details:**
- **Position:** {job_title}
- **Start Date:** [Date]
- **Compensation:** {salary} per annum
- **Benefits:** [Benefits package]
- **Location:** [Office / Remote]

This offer is contingent upon satisfactory reference and background checks.

Please confirm your acceptance by [Acceptance Deadline].

We look forward to you joining our team!

Best regards,
[HR Manager Name]
[Company Name]

---"""


async def _handle_recommend(db: AsyncSession, job_id: Optional[str], org_id: Optional[str]) -> str:
    q = select(RankingResult).order_by(RankingResult.similarity_score.desc()).limit(5)
    if job_id:
        q = q.where(RankingResult.job_id == job_id)
    if org_id:
        q = q.where(RankingResult.organization_id == org_id)
    res = await db.execute(q)
    top = res.scalars().all()

    if not top:
        return "No rankings found. Please rank candidates against a job first."

    lines = []
    for i, rr in enumerate(top, 1):
        resume_res = await db.execute(select(Resume).where(Resume.id == rr.resume_id))
        resume = resume_res.scalar_one_or_none()
        name = resume.candidate_name if resume else "Unknown"
        lines.append(
            f"{i}. **{name}** — Score: {rr.similarity_score:.1f}% | {rr.recommendation} | "
            f"Matched skills: {len(rr.matched_skills or [])}"
        )

    return (
        f"**My Top Recommendations:**\n\n" + "\n".join(lines) +
        "\n\nI recommend starting with shortlisting candidates 1-3 for technical interviews."
    )


# ── Main Endpoint ─────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    session_id = body.session_id or str(uuid.uuid4())[:8]
    intent = _detect_intent(body.message)
    org_id = current_user.organization_id

    suggestions = [
        "Who is the best candidate?",
        "Show me the skill gaps",
        "How many resumes do we have?",
        "Generate rejection email",
        "Recommend top candidates",
    ]

    # Route to handler
    if intent == "best_candidate":
        response = await _handle_best_candidate(db, body.job_id, org_id)
    elif intent == "stats":
        response = await _handle_stats(db, org_id)
    elif intent == "skill_gaps":
        response = await _handle_skill_gaps(db, body.job_id, org_id)
    elif intent == "rejection_email":
        response = _generate_rejection_email()
    elif intent == "offer_letter":
        response = _generate_offer_letter()
    elif intent == "recommend":
        response = await _handle_recommend(db, body.job_id, org_id)
    elif intent == "interview_questions":
        response = (
            "**Suggested Technical Interview Questions:**\n\n"
            "1. Walk me through your most complex system design.\n"
            "2. How do you approach debugging a production incident?\n"
            "3. Describe your experience with CI/CD pipelines.\n"
            "4. How do you ensure code quality in a fast-moving team?\n"
            "5. What's your approach to technical debt?\n\n"
            "View candidate-specific questions in the Candidate Intelligence tab."
        )
    elif intent == "explain_score":
        response = (
            "**How Scores Are Calculated:**\n\n"
            "- **50%** — Semantic similarity (SBERT embedding cosine similarity)\n"
            "- **30%** — Skill match (required + preferred skills overlap)\n"
            "- **20%** — Experience match (years vs. requirement)\n\n"
            "Each candidate's score is then broken down into SHAP-style contributions "
            "showing which factors helped or hurt their ranking. View these in the Rankings page."
        )
    else:
        response = (
            f"I'm your AI recruiting assistant. You asked: **\"{body.message}\"**\n\n"
            f"I can help you with:\n"
            f"- Finding the best candidates\n"
            f"- Analyzing skill gaps\n"
            f"- Generating interview questions\n"
            f"- Writing rejection or offer emails\n"
            f"- Explaining candidate scores\n\n"
            f"Try asking one of the suggested questions below!"
        )

    # Store in history
    if session_id not in _chat_history:
        _chat_history[session_id] = []
    _chat_history[session_id].append({
        "role": "user",
        "content": body.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _chat_history[session_id].append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return ChatResponse(
        session_id=session_id,
        message=response,
        suggestions=suggestions,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/history")
async def chat_history(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    return {"session_id": session_id, "messages": _chat_history.get(session_id, [])}
