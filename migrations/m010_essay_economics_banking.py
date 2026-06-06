"""Add 3 open-ended UPSC-style essay questions on economics and banking themes."""

DB = "ies"

_ESSAYS = [
    {
        "question_id": "eng_essay_006",
        "exam_id": "english_practice",
        "type_id": "essay",
        "marks": 20,
        "word_count_target": 500,
        "source_exam": "upsc_style",
        "difficulty": "hard",
        "prompt_text": (
            "The invisible hand of the market needs the visible hand of regulation.\n\n"
            "Write an essay of approximately 500 words. A clear title is required.\n"
            "(UPSC / IES General English — Essay)"
        ),
        "intro_text": (
            "Order and Freedom: The Case for Regulation in a Market Economy\n\n"
            "The invisible hand — Adam Smith's metaphor for how individual self-interest "
            "aggregates into collective welfare without central direction — is among the "
            "most influential ideas in the history of economics. Yet its most ardent "
            "proponents have often overlooked what Smith himself understood: the mechanism "
            "functions only within a framework of laws, institutions, and enforced norms "
            "that markets cannot spontaneously generate. The invisible hand is not a "
            "self-sufficient system; it is a conditional one. The visible hand of "
            "regulation is not its opponent — it is its operating system."
        ),
        "body_text": (
            "The case for unregulated markets rests on the theoretical efficiency of "
            "price signals: when buyers and sellers are free to transact, prices aggregate "
            "dispersed information and direct resources to their highest-value uses. This "
            "logic is powerful, and the evidence that markets outperform central planning "
            "as an allocative mechanism is overwhelming. But the theory assumes conditions "
            "that real markets routinely violate: perfect information, the absence of "
            "externalities, competitive structure, and the impossibility of one party "
            "acquiring enough power to distort the terms of exchange.\n\n"
            "Where these conditions fail, unregulated markets produce not efficiency but "
            "market failure — a phenomenon with real and measurable human costs. The 2008 "
            "global financial crisis was not an act of nature; it was the consequence of "
            "mortgage markets in which originators had every incentive to issue loans they "
            "knew were unsound, because risk had been securitised and distributed to "
            "investors who could not evaluate it. Deregulation had removed the friction "
            "that would have checked this behaviour. The invisible hand, left alone, "
            "built a system that enriched its participants until it collapsed on the "
            "taxpayers who had not been consulted.\n\n"
            "In India, the relevance is immediate. The telecom sector's spectrum allocation "
            "disorders, the banking sector's NPA crisis — driven in part by connected "
            "lending and evergreening that weak regulatory oversight permitted — and the "
            "consumer internet sector's data monopolies are not stories of government "
            "overreach but of regulatory absence or capture. Markets in these sectors "
            "produced outcomes that served concentrated interests at the expense of "
            "consumers, taxpayers, and competitors.\n\n"
            "The productive relationship between markets and regulation is not adversarial "
            "but constitutive. Property rights must be defined and enforced for markets to "
            "exist. Contracts must be honoured, or exchange collapses. Fraud must be "
            "prosecuted, or price signals are corrupted. Environmental costs must be "
            "internalised — whether through taxation or standards — or markets will "
            "systematically overproduce pollution. Financial leverage must be bounded, or "
            "private risk-taking becomes a claim on public resources.\n\n"
            "The argument is not for maximum regulation but for appropriately calibrated "
            "regulation: rules designed with enough knowledge of market structure to "
            "address real failures without introducing new ones. Regulatory capacity — "
            "technical expertise, independence from capture, and accountability to the "
            "public — is therefore as important an investment as market development itself."
        ),
        "conclusion_text": (
            "The debate between markets and regulation is often framed as a choice between "
            "freedom and control. It is more accurately a question of design: what "
            "institutional architecture produces markets that generate broad welfare rather "
            "than concentrated rents? The invisible hand is a genuine discovery — but it "
            "was never meant to operate in a vacuum. The visible hand of well-designed "
            "regulation is not the enemy of the market; it is the condition of its "
            "legitimacy."
        ),
    },
    {
        "question_id": "eng_essay_007",
        "exam_id": "english_practice",
        "type_id": "essay",
        "marks": 20,
        "word_count_target": 500,
        "source_exam": "upsc_style",
        "difficulty": "medium",
        "prompt_text": (
            "A bank is not merely a custodian of money — it is a custodian of public trust.\n\n"
            "Write an essay of approximately 500 words. A clear title is required.\n"
            "(UPSC / IES General English — Essay)"
        ),
        "intro_text": (
            "The Architecture of Trust: Why Banking Is Different\n\n"
            "Most businesses fail their customers in ways that are costly but recoverable: "
            "a faulty product can be returned, a bad service provider replaced, a "
            "misdirected investment written off. A bank failure is categorically different. "
            "When a bank fails, the savings of depositors — accumulated across lifetimes, "
            "representing security for retirement, illness, or a child's education — can "
            "vanish in days. This asymmetry explains why banking has always been treated "
            "differently from other industries, and why the proposition that a bank is "
            "a custodian of public trust is not metaphor but institutional reality."
        ),
        "body_text": (
            "The economic function of banking rests entirely on trust. Banks are fundamentally "
            "in the business of borrowing short and lending long: they accept deposits "
            "repayable on demand and deploy them in loans that mature over years. This "
            "maturity transformation is the source of banking's economic value — it channels "
            "idle savings into productive investment — and also its inherent fragility. If "
            "depositors lose confidence and withdraw simultaneously, even a solvent bank "
            "can fail, because no bank holds enough liquid assets to meet all its liabilities "
            "at once. A bank run is not caused by insolvency; it is caused by the loss of "
            "trust. This is why trust is not a soft corporate value in banking — it is the "
            "load-bearing structure.\n\n"
            "India's banking history is punctuated by episodes in which this trust was "
            "violated and the consequences were severe. The Punjab and Maharashtra Co-operative "
            "Bank collapse in 2019 trapped the savings of 900,000 depositors. The IL&FS "
            "crisis of 2018 revealed how systemic risk can accumulate invisibly when "
            "governance is poor and regulators are slow to act. The banking sector's NPA "
            "crisis — which saw gross non-performing assets exceed ₹10 lakh crore by 2018 "
            "— was not only a balance-sheet problem; it was a governance crisis that "
            "revealed the fragility of the trust relationship between public sector banks, "
            "their borrowers, and the depositing public.\n\n"
            "The custodianship of public trust imposes obligations that go beyond prudent "
            "balance-sheet management. It demands transparency: depositors and investors "
            "must be able to assess the health of the institutions to which they have "
            "entrusted their savings. It demands independence: bank boards and management "
            "must be insulated from political pressure to lend for non-commercial purposes. "
            "It demands proportionate regulation: capital adequacy requirements, stress "
            "testing, and resolution frameworks exist not to constrain banks but to "
            "protect the public that stands behind them.\n\n"
            "The Reserve Bank of India's evolution as a regulator reflects this logic. "
            "The Prompt Corrective Action framework, the Asset Quality Review of 2015–16 "
            "that forced recognition of hidden NPAs, and the move toward risk-based "
            "supervision are all institutional expressions of the principle that banking "
            "must be held to a standard of trust that other industries are not."
        ),
        "conclusion_text": (
            "When a bank fails, the depositor who loses savings does not care about "
            "capital ratios or provisioning norms — they care about whether the "
            "institution they trusted behaved honestly and was properly supervised. "
            "The entire architecture of banking regulation exists to make the answer "
            "to that question reliably 'yes'. A bank that treats itself as merely a "
            "profit-maximising business among others has misunderstood its own nature. "
            "It exists because the public trusted it with their money — and that trust "
            "is the only true capital that cannot be replenished once spent."
        ),
    },
    {
        "question_id": "eng_essay_008",
        "exam_id": "english_practice",
        "type_id": "essay",
        "marks": 20,
        "word_count_target": 500,
        "source_exam": "upsc_style",
        "difficulty": "medium",
        "prompt_text": (
            "Financial inclusion is the unfinished agenda of Indian independence.\n\n"
            "Write an essay of approximately 500 words. A clear title is required.\n"
            "(UPSC / IES General English — Essay)"
        ),
        "intro_text": (
            "The Excluded Majority: India's Long Road to Financial Inclusion\n\n"
            "When India gained independence in 1947, the formal financial system served "
            "a narrow colonial economy. Banks were urban, English-speaking institutions "
            "whose services were inaccessible to the rural majority. Seventy-five years "
            "later, the arithmetic has shifted dramatically — yet the promise of a "
            "financial system that genuinely serves every citizen remains incompletely "
            "fulfilled. Financial inclusion — the ability of every individual and "
            "enterprise to access useful and affordable financial services — is not a "
            "technical banking objective; it is a dimension of the democratic and "
            "economic citizenship that independence promised and has only partially delivered."
        ),
        "body_text": (
            "The scale of historical exclusion shaped the political choices of independent "
            "India's early decades. Bank nationalisation in 1969 — the takeover of 14 major "
            "private banks — was driven explicitly by the argument that credit was flowing "
            "to industry and commerce while agriculture and the rural poor were left to "
            "the mercy of moneylenders charging rates of 30–100% annually. Priority sector "
            "lending norms, the expansion of the branch network into rural areas, and the "
            "establishment of Regional Rural Banks were all instruments of the same "
            "intention: to make the formal financial system serve the majority, not just "
            "the elite.\n\n"
            "The results were mixed. Nationalisation expanded the branch network and "
            "rural credit flows, but it also created public sector banks whose credit "
            "allocation was too often driven by political rather than commercial logic, "
            "generating the bad loan cycles that have repeatedly required taxpayer-funded "
            "recapitalisation. The informal moneylender was not replaced — rural "
            "households continued to rely on informal credit for emergencies, weddings, "
            "and agricultural inputs. Financial inclusion as lived experience remained "
            "elusive for hundreds of millions.\n\n"
            "India's digital public infrastructure has created new possibilities that "
            "could not have been imagined in 1969. The Jan Dhan Yojana opened 500 million "
            "basic bank accounts between 2014 and 2023. Aadhaar-based eKYC reduced the "
            "cost of account opening from hundreds of rupees to single digits. UPI enabled "
            "seamless peer-to-peer and merchant payments for anyone with a smartphone "
            "and a bank account. Direct Benefit Transfer delivered welfare payments "
            "directly to the accounts of beneficiaries, bypassing the intermediaries "
            "who historically captured a significant share.\n\n"
            "Yet account ownership and financial inclusion are not the same. The "
            "World Bank's Global Findex data shows that a significant proportion of "
            "Jan Dhan accounts remain dormant. Access to credit — working capital for "
            "small enterprises, consumption smoothing for households facing income "
            "shocks — remains constrained for those without formal income documentation "
            "or collateral. Insurance penetration among the poor is minimal. Financial "
            "literacy gaps mean that those who most need financial services often lack "
            "the knowledge to use them safely. The infrastructure has been built; the "
            "superstructure of genuine usage remains under construction."
        ),
        "conclusion_text": (
            "Financial inclusion is not complete when a bank account is opened. It is "
            "complete when a farmer in Vidarbha can access crop insurance without a "
            "week of paperwork, when a street vendor in Chennai can borrow working "
            "capital based on her UPI transaction history, and when a migrant worker "
            "in Delhi can remit money home without surrendering 10% to a corridor "
            "operator. These are not distant ambitions — they are the logical destination "
            "of the infrastructure already in place. The unfinished agenda of independence "
            "is within reach; closing it requires moving from access to active, "
            "affordable usage for the hundreds of millions who were excluded for "
            "most of the republic's history."
        ),
    },
]


def run(conn):
    for q in _ESSAYS:
        conn.execute(
            """INSERT OR IGNORE INTO english_questions
               (question_id, exam_id, type_id, marks, word_count_target,
                source_exam, difficulty, prompt_text, intro_text, body_text, conclusion_text)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                q["question_id"], q["exam_id"], q["type_id"],
                q["marks"], q["word_count_target"],
                q["source_exam"], q["difficulty"],
                q["prompt_text"], q["intro_text"], q["body_text"], q["conclusion_text"],
            ),
        )
    conn.commit()
