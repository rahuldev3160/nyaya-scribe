"""
Seed GS4 thinkers (~15 rows) and gs4_keywords (~200 canonical ethics terms) into upsc_gs.db.
Run once after schema migrations are applied: python3.11 scripts/setup_upsc_gs.py
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "upsc_gs.db"


# ── GS4 Thinkers ──────────────────────────────────────────────────────────────

THINKERS = [
    {
        "thinker_id": "thinker_gandhi",
        "name": "Mahatma Gandhi",
        "era": "20th century",
        "school_of_thought": "Indian Political Philosophy / Non-violence",
        "key_works": json.dumps(["Hind Swaraj", "My Experiments with Truth", "Sarvodaya"]),
        "core_concepts": json.dumps(["Satyagraha", "Ahimsa", "Trusteeship", "means-ends inseparability", "Swaraj", "Gram Swaraj"]),
        "upsc_relevance_score": 0.97,
        "most_cited_quote": "The means are the end in miniature.",
        "typical_question_angle": "Means-ends inseparability; civil servant duty vs conscience; anti-corruption stance",
        "years_appeared": json.dumps([2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_integrity","gs4_c_honesty","gs4_c_public_service_values"]),
        "indian_governance_application": "Trusteeship model for public resources; non-violence in conflict resolution; panchayati raj foundations",
        "common_mistake": "Conflating Satyagraha with passive resistance — it is active moral resistance, not inaction",
    },
    {
        "thinker_id": "thinker_vivekananda",
        "name": "Swami Vivekananda",
        "era": "19th-20th century",
        "school_of_thought": "Vedanta / Indian Spirituality",
        "key_works": json.dumps(["Raja Yoga", "Karma Yoga", "Jnana Yoga", "Chicago Address 1893"]),
        "core_concepts": json.dumps(["service as worship (Daridra Narayana)", "character as foundation", "inner strength", "practical Vedanta", "strength-based ethics"]),
        "upsc_relevance_score": 0.93,
        "most_cited_quote": "Education is the manifestation of the perfection already in man.",
        "typical_question_angle": "Public service as worship; character-building for civil servants; human dignity",
        "years_appeared": json.dumps([2015,2016,2017,2018,2019,2020,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_empathy","gs4_c_public_service_values","gs4_c_compassion"]),
        "indian_governance_application": "Civil servant as servant-leader; RTE: education for character not just livelihood; welfare delivery with dignity",
        "common_mistake": "Treating him as only religious thinker — UPSC asks for governance/administrative ethics angle",
    },
    {
        "thinker_id": "thinker_kant",
        "name": "Immanuel Kant",
        "era": "18th century",
        "school_of_thought": "Deontological Ethics",
        "key_works": json.dumps(["Groundwork of the Metaphysics of Morals", "Critique of Pure Reason", "Critique of Practical Reason"]),
        "core_concepts": json.dumps(["Categorical Imperative", "duty-based ethics", "universalisability", "dignity of persons as ends", "good will"]),
        "upsc_relevance_score": 0.90,
        "most_cited_quote": "Act only according to that maxim whereby you can at the same time will that it should become a universal law.",
        "typical_question_angle": "Duty over consequences; rule-based decision making; civil servant as duty-bound agent",
        "years_appeared": json.dumps([2013,2014,2015,2016,2017,2018,2019,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_integrity","gs4_c_honesty","gs4_c_rule_of_law"]),
        "indian_governance_application": "Categorical Imperative as test for policy universalisation; treating citizens as ends (not means) in welfare delivery; Rule of Law",
        "common_mistake": "Stating Categorical Imperative without applying it — must demonstrate universalisation test in answer",
    },
    {
        "thinker_id": "thinker_aristotle",
        "name": "Aristotle",
        "era": "Ancient Greece (384-322 BCE)",
        "school_of_thought": "Virtue Ethics",
        "key_works": json.dumps(["Nicomachean Ethics", "Politics", "Rhetoric"]),
        "core_concepts": json.dumps(["Virtue Ethics", "eudaimonia (flourishing)", "phronesis (practical wisdom)", "the Golden Mean", "moral habituation"]),
        "upsc_relevance_score": 0.88,
        "most_cited_quote": "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
        "typical_question_angle": "Character formation; practical wisdom in decision-making; virtuous civil servant",
        "years_appeared": json.dumps([2014,2015,2016,2018,2019,2020,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_integrity","gs4_c_emotional_intelligence","gs4_c_compassion"]),
        "indian_governance_application": "Golden Mean in policy: balance development vs environment; Phronesis for IAS officer judgment in field; virtue habituation in training",
        "common_mistake": "Eudaimonia ≠ happiness — it is human flourishing through virtuous activity, not pleasure",
    },
    {
        "thinker_id": "thinker_ambedkar",
        "name": "B.R. Ambedkar",
        "era": "20th century",
        "school_of_thought": "Constitutional Morality / Social Justice",
        "key_works": json.dumps(["Annihilation of Caste", "The Buddha and His Dhamma", "Waiting for a Visa"]),
        "core_concepts": json.dumps(["Constitutional morality over social morality", "dignity of the individual", "social justice", "anti-caste ethics", "self-respect"]),
        "upsc_relevance_score": 0.88,
        "most_cited_quote": "Constitutional morality is not a natural sentiment. It has to be cultivated.",
        "typical_question_angle": "Constitutional morality vs prevailing social norms; dignity in welfare delivery; reservation ethics",
        "years_appeared": json.dumps([2015,2016,2017,2018,2019,2020,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_social_justice","gs4_c_human_rights","gs4_c_impartiality"]),
        "indian_governance_application": "Civil servant duty to uphold constitutional morality even against local social pressure; SC/ST atrocity cases; welfare delivery with dignity",
        "common_mistake": "Limiting him to reservation debate — his constitutional morality concept applies to all governance ethics questions",
    },
    {
        "thinker_id": "thinker_bentham",
        "name": "Jeremy Bentham",
        "era": "18th-19th century",
        "school_of_thought": "Utilitarianism",
        "key_works": json.dumps(["Introduction to Principles of Morals and Legislation", "The Panopticon Writings"]),
        "core_concepts": json.dumps(["Utility principle", "felicific calculus", "greatest happiness of greatest number", "hedonistic calculus"]),
        "upsc_relevance_score": 0.82,
        "most_cited_quote": "The greatest good for the greatest number.",
        "typical_question_angle": "Consequentialist policy justification; welfare maximisation; trolley-problem type dilemmas",
        "years_appeared": json.dumps([2014,2016,2017,2019,2020,2021,2022,2023]),
        "concept_links": json.dumps(["gs4_c_utilitarian_ethics","gs4_c_public_interest","gs4_c_welfare"]),
        "indian_governance_application": "GDP growth vs inequality trade-offs; displacement for development projects; drug policy harm reduction",
        "common_mistake": "Ignoring minority rights — UPSC cases often test limits of majority utility; must flag this limitation",
    },
    {
        "thinker_id": "thinker_mill",
        "name": "John Stuart Mill",
        "era": "19th century",
        "school_of_thought": "Liberal Utilitarianism",
        "key_works": json.dumps(["Utilitarianism", "On Liberty", "The Subjection of Women"]),
        "core_concepts": json.dumps(["higher and lower pleasures", "harm principle", "individual liberty", "representative government", "quality over quantity of pleasure"]),
        "upsc_relevance_score": 0.80,
        "most_cited_quote": "The liberty of the individual must be thus far limited; he must not make himself a nuisance to other people.",
        "typical_question_angle": "Harm principle in regulatory ethics; civil servant intervention boundaries; press freedom",
        "years_appeared": json.dumps([2015,2017,2018,2020,2021,2022,2023]),
        "concept_links": json.dumps(["gs4_c_utilitarian_ethics","gs4_c_human_rights","gs4_c_freedom"]),
        "indian_governance_application": "Harm principle: when state can restrict freedom (sedition, social media regulation); quality pleasures: education over opium — drug policy",
        "common_mistake": "Conflating Mill with Bentham — Mill adds qualitative dimension (higher pleasures) and individual rights protection",
    },
    {
        "thinker_id": "thinker_rawls",
        "name": "John Rawls",
        "era": "20th century",
        "school_of_thought": "Liberal Egalitarianism / Social Contract",
        "key_works": json.dumps(["A Theory of Justice", "Political Liberalism"]),
        "core_concepts": json.dumps(["Veil of Ignorance", "Original Position", "Difference Principle", "lexical ordering of principles", "justice as fairness"]),
        "upsc_relevance_score": 0.85,
        "most_cited_quote": "Justice is the first virtue of social institutions.",
        "typical_question_angle": "Reservation policy; progressive taxation; welfare state design; impartial policymaking",
        "years_appeared": json.dumps([2016,2017,2018,2019,2020,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_social_justice","gs4_c_impartiality","gs4_c_welfare"]),
        "indian_governance_application": "Veil of Ignorance as impartiality test for civil servants; Difference Principle as justification for reservation; 15th Finance Commission devolution",
        "common_mistake": "Stopping at 'veil of ignorance' — must explain what principles people would choose behind it (liberty + difference principle)",
    },
    {
        "thinker_id": "thinker_plato",
        "name": "Plato",
        "era": "Ancient Greece (428-348 BCE)",
        "school_of_thought": "Idealism / Philosopher-King Theory",
        "key_works": json.dumps(["The Republic", "The Laws", "Apology"]),
        "core_concepts": json.dumps(["Philosopher-King", "cardinal virtues (wisdom/courage/temperance/justice)", "tripartite soul", "Forms (ideal types)", "justice as harmony"]),
        "upsc_relevance_score": 0.75,
        "most_cited_quote": "Until philosophers rule as kings, cities will have no rest from evil.",
        "typical_question_angle": "Ideal civil servant qualities; virtue-based governance; role of wisdom in administration",
        "years_appeared": json.dumps([2014,2015,2016,2017,2019,2021,2023]),
        "concept_links": json.dumps(["gs4_c_integrity","gs4_c_wisdom","gs4_c_justice"]),
        "indian_governance_application": "Four cardinal virtues → IAS officer qualities; philosopher-king → technocrat role in governance; justice as societal harmony",
        "common_mistake": "Philosopher-King as anti-democratic — UPSC wants you to extract virtue framework, not the elitist political theory",
    },
    {
        "thinker_id": "thinker_confucius",
        "name": "Confucius",
        "era": "Ancient China (551-479 BCE)",
        "school_of_thought": "Confucianism / Relational Ethics",
        "key_works": json.dumps(["Analects"]),
        "core_concepts": json.dumps(["Ren (benevolence/humaneness)", "Li (ritual propriety)", "Yi (righteousness)", "filial piety", "rectification of names"]),
        "upsc_relevance_score": 0.72,
        "most_cited_quote": "To know what is right and not do it is the worst cowardice.",
        "typical_question_angle": "Relational ethics in administration; community duty; governance through moral example",
        "years_appeared": json.dumps([2016,2018,2020,2022,2023]),
        "concept_links": json.dumps(["gs4_c_integrity","gs4_c_public_service_values","gs4_c_compassion"]),
        "indian_governance_application": "Ren as empathetic governance; Li as procedural propriety in administration; moral leadership model for officers",
        "common_mistake": "Treating Confucius as purely social thinker — his governance ethics are highly applicable to administrative behaviour",
    },
    {
        "thinker_id": "thinker_aurobindo",
        "name": "Sri Aurobindo",
        "era": "19th-20th century",
        "school_of_thought": "Integral Philosophy / Indian Idealism",
        "key_works": json.dumps(["The Life Divine", "Essays on the Gita", "The Synthesis of Yoga"]),
        "core_concepts": json.dumps(["Integral human development", "inner transformation as governance basis", "divine in humanity", "yogic statecraft"]),
        "upsc_relevance_score": 0.68,
        "most_cited_quote": "All life is yoga.",
        "typical_question_angle": "Inner transformation of civil servant; spiritual dimension of public service; holistic development",
        "years_appeared": json.dumps([2016,2019,2021,2023]),
        "concept_links": json.dumps(["gs4_c_empathy","gs4_c_public_service_values"]),
        "indian_governance_application": "Inner transformation → incorruptible civil servant; integral human development as policy goal beyond GDP",
        "common_mistake": "Appearing too abstract — must ground in concrete governance example to score",
    },
    {
        "thinker_id": "thinker_kohlberg",
        "name": "Lawrence Kohlberg",
        "era": "20th century",
        "school_of_thought": "Moral Development Psychology",
        "key_works": json.dumps(["Essays on Moral Development"]),
        "core_concepts": json.dumps(["6 stages of moral development", "pre-conventional / conventional / post-conventional", "principled moral reasoning", "Heinz dilemma"]),
        "upsc_relevance_score": 0.78,
        "most_cited_quote": "Moral development is not just about knowing what is right, but about being motivated to act on it.",
        "typical_question_angle": "Moral development of civil servant over career; post-conventional reasoning in dilemma resolution",
        "years_appeared": json.dumps([2015,2017,2019,2020,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_emotional_intelligence","gs4_c_integrity","gs4_c_conscience"]),
        "indian_governance_application": "6-stage model: IAS officer expected at Stage 5-6 (social contract / universal principles); training implications; whistleblowing as Stage 6",
        "common_mistake": "Stopping at naming the stages — UPSC wants application of a specific stage to the scenario given",
    },
    {
        "thinker_id": "thinker_kautilya",
        "name": "Kautilya (Chanakya)",
        "era": "Ancient India (350-275 BCE)",
        "school_of_thought": "Realist Political Philosophy / Arthashastra Tradition",
        "key_works": json.dumps(["Arthashastra"]),
        "core_concepts": json.dumps(["Rajadharma (king's duty)", "Matsya Nyaya (big fish eats small)", "Dandaniti (science of punishment)", "spy system", "welfare state (Praja Sukhe Sukham Rajnah)"]),
        "upsc_relevance_score": 0.82,
        "most_cited_quote": "In the happiness of his subjects lies the king's happiness; in their welfare his welfare.",
        "typical_question_angle": "Rajadharma for civil servants; anti-corruption vigilance; accountability mechanisms",
        "years_appeared": json.dumps([2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_accountability","gs4_c_public_interest","gs4_c_integrity"]),
        "indian_governance_application": "Arthashastra surveillance → RTI/Lokpal; Rajadharma → fundamental duties of civil servant; Dandaniti → proportionality in punishment",
        "common_mistake": "Kautilya ≠ Machiavelli — Kautilya's realism is welfare-grounded; Machiavelli is power-only. Conflating both in answers loses marks",
    },
    {
        "thinker_id": "thinker_machiavelli",
        "name": "Niccolò Machiavelli",
        "era": "15th-16th century",
        "school_of_thought": "Political Realism",
        "key_works": json.dumps(["The Prince", "Discourses on Livy"]),
        "core_concepts": json.dumps(["ends justify means (realpolitik)", "Virtu and Fortuna", "practical over idealistic governance", "separation of ethics from politics"]),
        "upsc_relevance_score": 0.70,
        "most_cited_quote": "The end justifies the means.",
        "typical_question_angle": "Contrasting point to Kant/Gandhi (ends vs means debate); limits of consequentialist governance",
        "years_appeared": json.dumps([2015,2017,2019,2021,2022]),
        "concept_links": json.dumps(["gs4_c_utilitarian_ethics","gs4_c_integrity"]),
        "indian_governance_application": "Foil for Gandhi's means-ends inseparability argument; realpolitik in foreign policy IR cases; BUT UPSC expects civil servants to reject Machiavellianism",
        "common_mistake": "Citing Machiavelli approvingly — in UPSC GS4 context, he is typically the position-to-be-rejected, not endorsed",
    },
    {
        "thinker_id": "thinker_nussbaum",
        "name": "Martha Nussbaum",
        "era": "20th-21st century",
        "school_of_thought": "Capabilities Approach / Feminist Ethics",
        "key_works": json.dumps(["Creating Capabilities", "Upheavals of Thought", "Sex and Social Justice"]),
        "core_concepts": json.dumps(["Capabilities Approach (with Sen)", "central human capabilities", "emotions in ethics (moral emotions)", "dignity of marginalised", "narrative imagination"]),
        "upsc_relevance_score": 0.73,
        "most_cited_quote": "Narrative imagination is the ability to think what it might be like to be in the shoes of a person different from oneself.",
        "typical_question_angle": "Empathy in administration; welfare beyond GDP; gender justice; marginalised group dignity",
        "years_appeared": json.dumps([2018,2019,2021,2022,2023,2024]),
        "concept_links": json.dumps(["gs4_c_empathy","gs4_c_social_justice","gs4_c_compassion","gs4_c_human_rights"]),
        "indian_governance_application": "Capabilities list as welfare policy checklist; moral emotions (compassion/anger) as guides in atrocity cases; POCSO/PWDV Act administration",
        "common_mistake": "Conflating with Amartya Sen — both use Capabilities Approach but Nussbaum adds specific capability list and feminist/emotional dimension",
    },
]


# ── GS4 Keywords ─────────────────────────────────────────────────────────────

def _kw(kw_id: str, text: str, canonical: str, synonyms: list, category: str, concept_ids: list) -> dict:
    return {
        "keyword_id": kw_id,
        "keyword_text": text,
        "canonical_form": canonical,
        "synonyms": json.dumps(synonyms),
        "keyword_category": category,
        "concept_ids": json.dumps(concept_ids),
        "created_at": datetime.utcnow().isoformat(),
    }


KEYWORDS = [
    # ── Core Values ──
    _kw("kw_ethics","ethics","Ethics",["moral philosophy","morality"],"core_value",["gs4_c_integrity"]),
    _kw("kw_integrity","integrity","Integrity",["probity","uprightness","rectitude","incorruptibility"],"core_value",["gs4_c_integrity"]),
    _kw("kw_honesty","honesty","Honesty",["truthfulness","sincerity","candour","veracity"],"core_value",["gs4_c_honesty"]),
    _kw("kw_impartiality","impartiality","Impartiality",["objectivity","neutrality","non-partisanship","fairness"],"core_value",["gs4_c_impartiality"]),
    _kw("kw_transparency","transparency","Transparency",["openness","disclosure","right to information"],"core_value",["gs4_c_accountability"]),
    _kw("kw_accountability","accountability","Accountability",["answerability","responsibility","culpability"],"core_value",["gs4_c_accountability"]),
    _kw("kw_dedication","dedication to public service","Dedication to Public Service",["commitment","devotion","selfless service"],"core_value",["gs4_c_public_service_values"]),
    _kw("kw_empathy","empathy","Empathy",["compassion","understanding","fellow-feeling","sensitivity"],"core_value",["gs4_c_empathy"]),
    _kw("kw_tolerance","tolerance","Tolerance",["forbearance","acceptance","pluralism"],"core_value",["gs4_c_public_service_values"]),
    _kw("kw_compassion","compassion","Compassion",["mercy","kindness","benevolence","pity"],"core_value",["gs4_c_compassion"]),

    # ── Ethical Theories ──
    _kw("kw_virtue_ethics","virtue ethics","Virtue Ethics",["aretaic ethics","character ethics","Aristotelian ethics"],"ethical_theory",["gs4_c_virtue_ethics"]),
    _kw("kw_deontology","deontology","Deontology",["duty ethics","Kantian ethics","rule ethics","categorical imperative"],"ethical_theory",["gs4_c_deontology"]),
    _kw("kw_utilitarianism","utilitarianism","Utilitarianism",["consequentialism","greatest happiness","felicific calculus"],"ethical_theory",["gs4_c_utilitarian_ethics"]),
    _kw("kw_social_contract","social contract","Social Contract",["Rawlsian justice","Rousseauian contract","Hobbesian covenant"],"ethical_theory",["gs4_c_social_justice"]),
    _kw("kw_natural_law","natural law","Natural Law",["moral law","divine law","universal law"],"ethical_theory",["gs4_c_deontology"]),
    _kw("kw_ethical_relativism","ethical relativism","Ethical Relativism",["moral relativism","cultural relativism"],"ethical_theory",["gs4_c_integrity"]),
    _kw("kw_moral_absolutism","moral absolutism","Moral Absolutism",["moral objectivism","universal morality"],"ethical_theory",["gs4_c_deontology"]),
    _kw("kw_eudaimonia","eudaimonia","Eudaimonia",["human flourishing","well-being","happiness"],"ethical_theory",["gs4_c_virtue_ethics"]),

    # ── Governance Ethics ──
    _kw("kw_civil_service_values","civil service values","Civil Service Values",["public service ethos","bureaucratic ethics","AIS values"],"governance_ethics",["gs4_c_public_service_values"]),
    _kw("kw_conflict_of_interest","conflict of interest","Conflict of Interest",["pecuniary interest","bias","vested interest","personal interest"],"governance_ethics",["gs4_c_accountability"]),
    _kw("kw_whistleblowing","whistleblowing","Whistleblowing",["public interest disclosure","whistleblower protection","PIDPSA"],"governance_ethics",["gs4_c_conscience"]),
    _kw("kw_administrative_neutrality","administrative neutrality","Administrative Neutrality",["political neutrality","apolitical service","non-partisanship"],"governance_ethics",["gs4_c_impartiality"]),
    _kw("kw_probity","probity","Probity",["integrity","rectitude","uprightness","moral uprightness"],"governance_ethics",["gs4_c_integrity"]),
    _kw("kw_rule_of_law","rule of law","Rule of Law",["legal supremacy","equality before law","due process"],"governance_ethics",["gs4_c_rule_of_law"]),
    _kw("kw_public_trust","public trust","Public Trust",["public confidence","fiduciary duty","trustworthiness"],"governance_ethics",["gs4_c_accountability"]),
    _kw("kw_vigilance","vigilance","Vigilance",["anti-corruption vigilance","CVC","integrity pact"],"governance_ethics",["gs4_c_accountability"]),
    _kw("kw_code_of_conduct","code of conduct","Code of Conduct",["service rules","CCS Rules","All India Services Conduct Rules"],"governance_ethics",["gs4_c_public_service_values"]),
    _kw("kw_ethical_governance","ethical governance","Ethical Governance",["good governance","clean governance","responsive administration"],"governance_ethics",["gs4_c_public_service_values"]),
    _kw("kw_responsiveness","responsiveness","Responsiveness",["citizen-centric service","people-oriented","responsive administration"],"governance_ethics",["gs4_c_public_service_values"]),
    _kw("kw_accountability_mechanisms","accountability mechanisms","Accountability Mechanisms",["RTI","Lokpal","Lokayukta","social audit","CBI","CVC"],"governance_ethics",["gs4_c_accountability"]),
    _kw("kw_political_executive","political executive","Political Executive",["minister-bureaucrat relations","political will","executive discretion"],"governance_ethics",["gs4_c_public_service_values"]),

    # ── Emotional Intelligence ──
    _kw("kw_emotional_intelligence","emotional intelligence","Emotional Intelligence",["EQ","EI","Goleman","social awareness","self-regulation"],"emotional_intelligence",["gs4_c_emotional_intelligence"]),
    _kw("kw_self_awareness","self-awareness","Self-Awareness",["introspection","self-knowledge","metacognition"],"emotional_intelligence",["gs4_c_emotional_intelligence"]),
    _kw("kw_self_regulation","self-regulation","Self-Regulation",["impulse control","emotional control","discipline"],"emotional_intelligence",["gs4_c_emotional_intelligence"]),
    _kw("kw_motivation","motivation","Motivation",["intrinsic motivation","achievement drive","inner drive"],"emotional_intelligence",["gs4_c_emotional_intelligence"]),
    _kw("kw_social_skills","social skills","Social Skills",["interpersonal skills","collaboration","conflict management"],"emotional_intelligence",["gs4_c_emotional_intelligence"]),
    _kw("kw_moral_emotions","moral emotions","Moral Emotions",["shame","guilt","indignation","compassion as emotion"],"emotional_intelligence",["gs4_c_compassion"]),
    _kw("kw_attitude","attitude","Attitude",["values-beliefs-behaviour triangle","positive attitude","work attitude"],"emotional_intelligence",["gs4_c_emotional_intelligence"]),
    _kw("kw_aptitude","aptitude","Aptitude",["ability","talent","skill","IAS aptitude"],"emotional_intelligence",["gs4_c_emotional_intelligence"]),

    # ── Social Justice ──
    _kw("kw_justice","justice","Justice",["fairness","equity","social justice","distributive justice"],"social_justice",["gs4_c_social_justice"]),
    _kw("kw_equality","equality","Equality",["equal rights","non-discrimination","egalitarianism","equal opportunity"],"social_justice",["gs4_c_social_justice"]),
    _kw("kw_equity","equity","Equity",["substantive equality","affirmative action","reservation","targeted assistance"],"social_justice",["gs4_c_social_justice"]),
    _kw("kw_human_rights","human rights","Human Rights",["fundamental rights","civil liberties","human dignity","UDHR"],"social_justice",["gs4_c_human_rights"]),
    _kw("kw_social_justice","social justice","Social Justice",["distributive justice","redistributive policy","welfare state"],"social_justice",["gs4_c_social_justice"]),
    _kw("kw_dignity","dignity","Dignity",["human dignity","self-respect","intrinsic worth","Kantian dignity"],"social_justice",["gs4_c_human_rights"]),
    _kw("kw_gender_justice","gender justice","Gender Justice",["women's rights","gender equality","sexual harassment","POCSO"],"social_justice",["gs4_c_social_justice"]),
    _kw("kw_welfare","welfare","Welfare",["public welfare","social welfare","citizen welfare","common good"],"social_justice",["gs4_c_public_interest"]),

    # ── Case Study Concepts ──
    _kw("kw_dilemma","ethical dilemma","Ethical Dilemma",["moral dilemma","value conflict","ethical conflict","competing values"],"case_study",["gs4_c_integrity"]),
    _kw("kw_stakeholder","stakeholder","Stakeholder",["affected party","beneficiary","interest group","principal"],"case_study",["gs4_c_public_interest"]),
    _kw("kw_public_interest","public interest","Public Interest",["common good","larger interest","societal interest","collective welfare"],"case_study",["gs4_c_public_interest"]),
    _kw("kw_whistleblower","whistleblower","Whistleblower",["informant","informer","public interest disclosure maker"],"case_study",["gs4_c_conscience"]),
    _kw("kw_omission","act vs omission","Act vs Omission",["act-omission distinction","sins of commission","sins of omission"],"case_study",["gs4_c_integrity"]),
    _kw("kw_means_ends","means-ends","Means-Ends Relationship",["ends justify means","Gandhi means","ethical means"],"case_study",["gs4_c_integrity"]),
    _kw("kw_moral_courage","moral courage","Moral Courage",["courage of conviction","standing up for right","ethical courage","civil courage"],"case_study",["gs4_c_conscience"]),
    _kw("kw_political_pressure","political pressure","Political Pressure",["pressure from superior","undue influence","political interference","hierarchical pressure"],"case_study",["gs4_c_impartiality"]),
    _kw("kw_development_vs_env","development vs environment","Development vs Environment",["environmental ethics","sustainability dilemma","green-growth dilemma"],"case_study",["gs4_c_public_interest"]),
    _kw("kw_corruption","corruption","Corruption",["bribery","graft","rent-seeking","malfeasance","abuse of power"],"case_study",["gs4_c_accountability"]),
    _kw("kw_nepotism","nepotism","Nepotism",["favouritism","cronyism","patronage","partiality"],"case_study",["gs4_c_impartiality"]),
    _kw("kw_misuse_of_power","misuse of power","Misuse of Power",["abuse of authority","malfeasance","power abuse","ultra vires"],"case_study",["gs4_c_accountability"]),

    # ── Constitutional/Legal ──
    _kw("kw_constitutional_morality","constitutional morality","Constitutional Morality",["Ambedkar constitutional morality","legal morality","rule-based ethics"],"constitutional",["gs4_c_rule_of_law"]),
    _kw("kw_fundamental_duties","fundamental duties","Fundamental Duties",["Art 51A","citizen duties","constitutional duties"],"constitutional",["gs4_c_public_service_values"]),
    _kw("kw_dpsp","DPSP","Directive Principles of State Policy",["Art 36-51","DPSPs","state obligations"],"constitutional",["gs4_c_public_interest"]),
    _kw("kw_separation_of_powers","separation of powers","Separation of Powers",["checks and balances","executive-judiciary-legislature","trias politica"],"constitutional",["gs4_c_rule_of_law"]),
    _kw("kw_natural_justice","natural justice","Natural Justice",["audi alteram partem","nemo judex","fair hearing","procedural fairness"],"constitutional",["gs4_c_rule_of_law"]),

    # ── Civil Services Specific ──
    _kw("kw_civil_servant","civil servant","Civil Servant",["IAS","IPS","IRS","IFS","civil services","bureaucrat","government servant"],"civil_service",["gs4_c_public_service_values"]),
    _kw("kw_good_governance","good governance","Good Governance",["UNDP governance","efficient governance","responsive government","e-governance"],"civil_service",["gs4_c_public_service_values"]),
    _kw("kw_servant_leadership","servant leadership","Servant Leadership",["Robert Greenleaf","service before self","leader as servant"],"civil_service",["gs4_c_public_service_values"]),
    _kw("kw_administrative_ethics","administrative ethics","Administrative Ethics",["bureaucratic ethics","official ethics","service ethics"],"civil_service",["gs4_c_public_service_values"]),
    _kw("kw_esprit_de_corps","esprit de corps","Esprit de Corps",["team spirit","organisational loyalty","institutional pride"],"civil_service",["gs4_c_public_service_values"]),
    _kw("kw_work_culture","work culture","Work Culture",["organisational culture","office ethics","professional environment"],"civil_service",["gs4_c_public_service_values"]),
    _kw("kw_citizen_charter","citizen charter","Citizen Charter",["service charter","service standards","public service guarantee"],"civil_service",["gs4_c_accountability"]),
    _kw("kw_discretion","discretion","Discretion",["administrative discretion","judgment","prudence","executive discretion"],"civil_service",["gs4_c_impartiality"]),

    # ── Philosophical Concepts ──
    _kw("kw_categorical_imperative","categorical imperative","Categorical Imperative",["Kantian imperative","moral law","universalisability test"],"philosophical",["gs4_c_deontology"]),
    _kw("kw_golden_rule","golden rule","Golden Rule",["do unto others","reciprocity","silver rule"],"philosophical",["gs4_c_compassion"]),
    _kw("kw_conscience","conscience","Conscience",["moral conscience","inner voice","ethical intuition","superego"],"philosophical",["gs4_c_conscience"]),
    _kw("kw_objectivity","objectivity","Objectivity",["impartiality","detachment","rational assessment","value-free"],"philosophical",["gs4_c_impartiality"]),
    _kw("kw_subjectivity","subjectivity","Subjectivity",["personal bias","individual perspective","subjective judgement"],"philosophical",["gs4_c_integrity"]),
    _kw("kw_free_will","free will","Free Will",["moral responsibility","agency","autonomy","determinism debate"],"philosophical",["gs4_c_conscience"]),
    _kw("kw_determinism","determinism","Determinism",["causal determinism","fatalism","predestination"],"philosophical",["gs4_c_conscience"]),
    _kw("kw_altruism","altruism","Altruism",["selflessness","self-sacrifice","beneficence","other-directed"],"philosophical",["gs4_c_compassion"]),
    _kw("kw_hedonism","hedonism","Hedonism",["pleasure-seeking","self-interest","epicureanism"],"philosophical",["gs4_c_utilitarian_ethics"]),
    _kw("kw_stoicism","stoicism","Stoicism",["Stoic ethics","equanimity","Marcus Aurelius","detachment from outcome"],"philosophical",["gs4_c_emotional_intelligence"]),
    _kw("kw_pragmatism","pragmatism","Pragmatism",["practical ethics","what works","William James","John Dewey"],"philosophical",["gs4_c_utilitarian_ethics"]),
    _kw("kw_positivism","positivism","Positivism",["legal positivism","fact-value distinction","Auguste Comte"],"philosophical",["gs4_c_rule_of_law"]),

    # ── Social/Institutional Ethics ──
    _kw("kw_corporate_governance","corporate governance","Corporate Governance",["CSR","ESG","board accountability","fiduciary duty"],"institutional",["gs4_c_accountability"]),
    _kw("kw_family_society","family and society ethics","Family and Society Ethics",["family values","social institutions","societal obligations"],"institutional",["gs4_c_public_service_values"]),
    _kw("kw_media_ethics","media ethics","Media Ethics",["press ethics","journalistic responsibility","paid news","fake news ethics"],"institutional",["gs4_c_accountability"]),
    _kw("kw_academic_ethics","academic ethics","Academic Ethics",["research ethics","plagiarism","academic integrity"],"institutional",["gs4_c_honesty"]),
    _kw("kw_political_ethics","political ethics","Political Ethics",["electoral ethics","political morality","party financing","horse-trading"],"institutional",["gs4_c_public_service_values"]),
    _kw("kw_judicial_ethics","judicial ethics","Judicial Ethics",["judicial accountability","judge conduct","recusal","legal ethics"],"institutional",["gs4_c_impartiality"]),

    # ── Mahatma Gandhi Specific ──
    _kw("kw_satyagraha","satyagraha","Satyagraha",["civil disobedience","non-violent resistance","truth-force","soul-force"],"gandhi",["gs4_c_integrity","gs4_c_conscience"]),
    _kw("kw_ahimsa","ahimsa","Ahimsa",["non-violence","non-harm","pacifism"],"gandhi",["gs4_c_compassion"]),
    _kw("kw_trusteeship","trusteeship","Trusteeship",["Gandhi trusteeship","stewardship of public resources","wealth trusteeship"],"gandhi",["gs4_c_public_service_values","gs4_c_accountability"]),
    _kw("kw_swaraj","swaraj","Swaraj",["self-rule","self-governance","gram swaraj","inner swaraj"],"gandhi",["gs4_c_conscience"]),

    # ── Ambedkar Specific ──
    _kw("kw_annihilation_caste","annihilation of caste","Annihilation of Caste",["caste abolition","Ambedkar social reform","anti-caste"],"ambedkar",["gs4_c_social_justice"]),
    _kw("kw_ambedkar_const_morality","constitutional morality (Ambedkar)","Constitutional Morality (Ambedkar)",["Ambedkar","rule of constitution","legal morality over social morality"],"ambedkar",["gs4_c_rule_of_law"]),

    # ── Applied Ethics Topics ──
    _kw("kw_environment_ethics","environmental ethics","Environmental Ethics",["green ethics","sustainability ethics","intergenerational equity","deep ecology"],"applied_ethics",["gs4_c_public_interest"]),
    _kw("kw_medical_ethics","medical ethics","Medical Ethics",["bioethics","clinical ethics","informed consent","euthanasia ethics"],"applied_ethics",["gs4_c_human_rights"]),
    _kw("kw_war_ethics","war ethics","War Ethics",["just war theory","jus in bello","Geneva Convention","military ethics"],"applied_ethics",["gs4_c_human_rights"]),
    _kw("kw_ai_ethics","AI ethics","AI Ethics",["algorithmic fairness","AI bias","technology ethics","DPDP ethics"],"applied_ethics",["gs4_c_public_interest"]),
    _kw("kw_intl_relations_ethics","ethics in international relations","Ethics in International Relations",["human rights diplomacy","humanitarian intervention","R2P","realism vs idealism"],"applied_ethics",["gs4_c_social_justice"]),
    _kw("kw_business_ethics","business ethics","Business Ethics",["corporate ethics","fiduciary duty","ethical business practices","CSR"],"applied_ethics",["gs4_c_accountability"]),

    # ── Thinker-Concept Bridges ──
    _kw("kw_veil_of_ignorance","veil of ignorance","Veil of Ignorance",["Rawls","original position","thought experiment","impartial design"],"thinker_concept",["gs4_c_social_justice","gs4_c_impartiality"]),
    _kw("kw_difference_principle","difference principle","Difference Principle",["Rawls inequality","benefit poorest","lexical ordering"],"thinker_concept",["gs4_c_social_justice"]),
    _kw("kw_harm_principle","harm principle","Harm Principle",["Mill","liberty","non-interference","state intervention limits"],"thinker_concept",["gs4_c_human_rights"]),
    _kw("kw_phronesis","phronesis","Phronesis",["practical wisdom","Aristotle","prudence","judgment"],"thinker_concept",["gs4_c_virtue_ethics"]),
    _kw("kw_ren","ren","Ren",["Confucian benevolence","humaneness","human-heartedness","仁"],"thinker_concept",["gs4_c_compassion"]),
    _kw("kw_rajadharma","rajadharma","Rajadharma",["Kautilya","king's duty","duty of ruler","governance dharma"],"thinker_concept",["gs4_c_public_service_values"]),
    _kw("kw_capabilities","capabilities approach","Capabilities Approach",["Amartya Sen","Martha Nussbaum","substantive freedoms","human development"],"thinker_concept",["gs4_c_social_justice","gs4_c_human_rights"]),
    _kw("kw_moral_stages","stages of moral development","Stages of Moral Development",["Kohlberg","pre-conventional","conventional","post-conventional","Stage 5","Stage 6"],"thinker_concept",["gs4_c_emotional_intelligence"]),

    # ── Additional UPSC-frequency terms ──
    _kw("kw_leadership","leadership","Leadership",["transformational leadership","ethical leadership","leadership qualities"],"competency",["gs4_c_emotional_intelligence"]),
    _kw("kw_decision_making","decision-making","Decision-Making",["ethical decision-making","framework-based","DECIDE model"],"competency",["gs4_c_emotional_intelligence"]),
    _kw("kw_crisis_management","crisis management","Crisis Management",["disaster response ethics","emergency ethics","triage ethics"],"competency",["gs4_c_public_interest"]),
    _kw("kw_negotiation","negotiation","Negotiation",["conflict resolution","mediation","interest-based negotiation"],"competency",["gs4_c_emotional_intelligence"]),
    _kw("kw_work_life","work-life balance","Work-Life Balance",["burnout","professional wellbeing","sustainable public service"],"competency",["gs4_c_emotional_intelligence"]),
    _kw("kw_persuasion","persuasion and communication","Persuasion and Communication",["ethical persuasion","public communication","spin vs truth"],"competency",["gs4_c_honesty"]),

    # ── Nolan Principles ──
    _kw("kw_nolan_selflessness","selflessness","Selflessness",["Nolan principle 1","altruism in public service","self-sacrifice"],"nolan_principles",["gs4_c_public_service_values"]),
    _kw("kw_nolan_integrity","integrity (Nolan)","Integrity",["Nolan principle 2","no private gain","conflict of interest avoidance"],"nolan_principles",["gs4_c_integrity"]),
    _kw("kw_nolan_objectivity","objectivity (Nolan)","Objectivity",["Nolan principle 3","merit-based decisions","evidence-based"],"nolan_principles",["gs4_c_impartiality"]),
    _kw("kw_nolan_accountability2","accountability (Nolan)","Accountability",["Nolan principle 4","external scrutiny","parliamentary accountability"],"nolan_principles",["gs4_c_accountability"]),
    _kw("kw_nolan_openness","openness","Openness",["Nolan principle 5","information sharing","transparency"],"nolan_principles",["gs4_c_accountability"]),
    _kw("kw_nolan_honesty","honesty (Nolan)","Honesty",["Nolan principle 6","truthfulness in public life"],"nolan_principles",["gs4_c_honesty"]),
    _kw("kw_nolan_leadership","leadership (Nolan)","Leadership",["Nolan principle 7","setting ethical example","tone from top"],"nolan_principles",["gs4_c_emotional_intelligence"]),
]


# ── Seed functions ────────────────────────────────────────────────────────────

def seed_thinkers(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    inserted = 0
    for t in THINKERS:
        cur.execute(
            "INSERT OR IGNORE INTO gs4_thinkers "
            "(thinker_id,name,era,school_of_thought,key_works,core_concepts,"
            "upsc_relevance_score,most_cited_quote,typical_question_angle,"
            "years_appeared,concept_links,indian_governance_application,common_mistake) "
            "VALUES (:thinker_id,:name,:era,:school_of_thought,:key_works,:core_concepts,"
            ":upsc_relevance_score,:most_cited_quote,:typical_question_angle,"
            ":years_appeared,:concept_links,:indian_governance_application,:common_mistake)",
            t,
        )
        inserted += cur.rowcount
    conn.commit()
    return inserted


def seed_keywords(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    inserted = 0
    for kw in KEYWORDS:
        cur.execute(
            "INSERT OR IGNORE INTO gs4_keywords "
            "(keyword_id,keyword_text,canonical_form,synonyms,keyword_category,concept_ids,created_at) "
            "VALUES (:keyword_id,:keyword_text,:canonical_form,:synonyms,:keyword_category,:concept_ids,:created_at)",
            kw,
        )
        inserted += cur.rowcount
    conn.commit()
    return inserted


def seed_synonyms(conn: sqlite3.Connection) -> int:
    """Expand synonym lists from gs4_keywords into gs4_keyword_synonyms."""
    cur = conn.cursor()
    inserted = 0
    cur.execute("SELECT keyword_id, synonyms FROM gs4_keywords")
    rows = cur.fetchall()
    for keyword_id, synonyms_json in rows:
        synonyms = json.loads(synonyms_json or "[]")
        for syn in synonyms:
            syn_id = f"syn_{keyword_id}_{syn[:20].replace(' ','_').lower()}"
            cur.execute(
                "INSERT OR IGNORE INTO gs4_keyword_synonyms (synonym_id, keyword_text, canonical_keyword_id, source) "
                "VALUES (?, ?, ?, 'human')",
                (syn_id, syn, keyword_id),
            )
            inserted += cur.rowcount
    conn.commit()
    return inserted


def main():
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} does not exist. Run migrations first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    t_count = seed_thinkers(conn)
    kw_count = seed_keywords(conn)
    syn_count = seed_synonyms(conn)

    conn.close()

    print(f"GS4 thinkers inserted:        {t_count:>4} / {len(THINKERS)}")
    print(f"GS4 keywords inserted:        {kw_count:>4} / {len(KEYWORDS)}")
    print(f"GS4 keyword synonyms expanded:{syn_count:>4}")


if __name__ == "__main__":
    main()
