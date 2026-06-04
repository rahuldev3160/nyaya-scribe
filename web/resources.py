"""
External study resources for the onboarding planner.
Update this file as new content is uploaded to @rahuldev0108.
"""

_CHANNEL = "https://www.youtube.com/@rahuldev0108"
_IES_PLAYLIST = "https://www.youtube.com/playlist?list=PLG8cSH86vt8YyNB-tJPdFkp59B33ZFoRj"
_RBI_PLAYLIST = "https://www.youtube.com/playlist?list=PLG8cSH86vt8b8JDlHZMxMS5c0pIuLn-Li"

# YouTube resources per exam.
YOUTUBE: dict[str, list[dict]] = {
    "ies": [
        {
            "title": "IES Economics Prep — Audio Series (24 episodes)",
            "channel": "@rahuldev0108",
            "url": _IES_PLAYLIST,
            "note": "Topic-by-topic audio summaries for IES Economics. Best for commute or passive review after reading.",
        },
        {
            "title": "UPSC Economics Optional (IES-level theory)",
            "channel": "Sanjay Kathuria",
            "url": "https://www.youtube.com/@SanjayKathuria",
            "note": "Macro theory at IES depth — IS-LM, AD-AS, Growth models. Substantial syllabus overlap.",
        },
        {
            "title": "Indian Economy for Exams",
            "channel": "Mrunal Patel",
            "url": "https://www.youtube.com/@MrunalPatel0",
            "note": "Indian Economy topics. Use for IES Paper II — Indian economic policy and data.",
        },
    ],
    "rbi": [
        {
            "title": "RBI Grade B DEPR — Audio Series (6 episodes)",
            "channel": "@rahuldev0108",
            "url": _RBI_PLAYLIST,
            "note": "RBI DEPR-focused audio guides. IS-LM and monetary policy episodes are the priority.",
        },
        {
            "title": "RBI Grade B Prep",
            "channel": "Oliveboard",
            "url": "https://www.youtube.com/@OliveBoardExams",
            "note": "Use for regulatory updates and current affairs only — not for theory.",
        },
    ],
    "upsc": [
        {
            "title": "UPSC Economics Optional — Full Course",
            "channel": "Sanjay Kathuria",
            "url": "https://www.youtube.com/@SanjayKathuria",
            "note": "Essential for Paper I theory and Paper II Indian Economy. Deep coverage.",
        },
        {
            "title": "IES Audio Series (theory overlap)",
            "channel": "@rahuldev0108",
            "url": _CHANNEL,
            "note": "IES and UPSC Eco Optional share most macro theory — same audio applies to both.",
        },
    ],
}

AI_TOOLS = {
    "theory_check": (
        "Ask Gemini: 'Explain [concept] in 3 sentences suitable for a competitive economics exam answer.'"
    ),
    "answer_drill": (
        "Ask Gemini: 'Give me 5 IES/RBI-style questions on [topic] with brief model answers.'"
    ),
    "answer_review": (
        "Ask Claude: 'I wrote this answer for [question]. Score it against an IES examiner rubric "
        "and tell me exactly what is missing.' Paste your full answer. One call per practice session."
    ),
}


def resources_summary(exam_focus: list[str]) -> str:
    """Return a plain-text summary of resources for use in AI prompts."""
    lines = []
    seen = set()
    for exam in exam_focus:
        for r in YOUTUBE.get(exam, []):
            if r["title"] not in seen:
                seen.add(r["title"])
                lines.append(f"- {r['title']} by {r['channel']}: {r['note']}")
    return "\n".join(lines) if lines else "No specific resources configured."
