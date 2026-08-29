"""Practice content for the RBI English Descriptive timed-writing simulator.

Small hand-authored starter set, not a real-PYQ bank (RBI Grade B's English
descriptive paper has no public official archive of past prompts/passages the
way the MCQ side does). Expand this list over time; the blueprint picks
randomly among available entries so repeats are avoided until the set is
exhausted for a session.
"""

ESSAY_PROMPTS = [
    {
        "id": "essay_01",
        "prompt": "Financial inclusion is a necessary but not sufficient condition for inclusive growth in India. Discuss.",
    },
    {
        "id": "essay_02",
        "prompt": "Digital lending platforms have expanded access to credit but also created new risks for unsophisticated borrowers. Examine the regulatory challenges this poses for the RBI.",
    },
    {
        "id": "essay_03",
        "prompt": "Central bank independence is essential for effective monetary policy, but complete independence from elected governments is neither feasible nor desirable. Comment.",
    },
]

PRECIS_PASSAGES = [
    {
        "id": "precis_01",
        "text": (
            "The Reserve Bank of India's regulatory sandbox framework allows fintech firms to test "
            "innovative products in a controlled environment before a full-scale launch, under relaxed "
            "regulatory requirements and close supervisory oversight. The stated objective is to foster "
            "responsible innovation in financial services while ensuring that consumer protection and "
            "systemic stability are not compromised in the process. Since its introduction, several "
            "cohorts have been run on themes ranging from retail payments to cross-border remittances, "
            "with participating entities required to report outcomes and risks observed during the test "
            "phase. Critics argue that the sandbox's limited scale means findings may not generalise to "
            "full-market conditions, while supporters point to it as a pragmatic middle path between "
            "unchecked innovation and regulatory paralysis in a fast-moving sector."
        ),
        "target_words": 100,
    },
    {
        "id": "precis_02",
        "text": (
            "Non-performing assets in the banking sector rose sharply in the years following the global "
            "financial crisis, driven in large part by stressed lending to infrastructure and corporate "
            "borrowers whose projects faced cost overruns and delayed cash flows. The Insolvency and "
            "Bankruptcy Code, introduced as a time-bound resolution mechanism, shifted bargaining power "
            "from defaulting promoters toward creditors and established a market-driven process for "
            "resolving distressed assets. While recovery rates and resolution timelines have improved "
            "compared to the earlier regime of restructuring schemes, a meaningful share of cases still "
            "exceed the code's mandated timelines, raising questions about judicial capacity and the "
            "adequacy of the current framework for very large or legally complex cases."
        ),
        "target_words": 100,
    },
]

RC_PASSAGES = [
    {
        "id": "rc_01",
        "text": (
            "Inflation targeting, adopted formally by India in 2016 through an amendment to the RBI Act, "
            "commits the central bank to keeping consumer price inflation within a band around a numerical "
            "target, currently 4% with a tolerance of plus or minus 2 percentage points. The framework is "
            "operated through a Monetary Policy Committee, a majority of whose members are external "
            "appointees, intended to bring diverse expertise and reduce the perception that policy is set "
            "unilaterally by the central bank governor. Supporters argue the framework has anchored "
            "inflation expectations more credibly than the earlier multiple-indicator approach, while "
            "critics contend that a single-minded focus on headline inflation can conflict with growth "
            "and financial-stability objectives, particularly during supply-side shocks that monetary "
            "policy is poorly equipped to address."
        ),
        "questions": [
            "What committee structure was introduced to operationalise inflation targeting in India, and why?",
            "According to the passage, what is the main criticism of a single-minded inflation-targeting framework?",
            "In your own words, summarise the passage's central argument in 2-3 sentences.",
        ],
    },
    {
        "id": "rc_02",
        "text": (
            "Central bank digital currencies have moved from theoretical proposals to active pilots in a "
            "number of jurisdictions, including India's e-rupee. Proponents frame CBDCs as a way to "
            "preserve the role of public money in an increasingly digital payments landscape, reduce the "
            "cost of currency management, and improve the efficiency of cross-border settlement. Sceptics "
            "raise concerns about disintermediation of commercial banks if retail depositors shift funds "
            "into central-bank-issued digital money during periods of stress, and about the privacy "
            "implications of a payment instrument that is, by design, traceable by the issuing authority. "
            "Design choices around whether a CBDC is token-based or account-based, and whether it bears "
            "interest, materially affect how these risks play out in practice."
        ),
        "questions": [
            "What is the main concern raised about commercial banks in the context of retail CBDCs?",
            "Name two design choices mentioned that affect how CBDC risks materialise.",
            "In your own words, summarise the passage's central argument in 2-3 sentences.",
        ],
    },
]


def pick_content(session_id: str) -> dict:
    """Deterministic-per-session pick so a refreshed page doesn't reshuffle content mid-attempt."""
    import hashlib
    h = int(hashlib.sha256(session_id.encode()).hexdigest(), 16)
    return {
        "essay": ESSAY_PROMPTS[h % len(ESSAY_PROMPTS)],
        "precis": PRECIS_PASSAGES[h % len(PRECIS_PASSAGES)],
        "rc": RC_PASSAGES[h % len(RC_PASSAGES)],
    }
