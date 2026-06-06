"""Replace all 5 essay prompts with genuinely open-ended UPSC-style topics.

UPSC essay paper style: a broad theme or phrase — no built-in proposition to
agree/disagree with, no binary framing. The writer sets the angle, thesis, and
structure entirely.
"""

DB = "ies"

_ESSAYS = [
    {
        "question_id": "eng_essay_001",
        "source_exam": "upsc_style",
        "difficulty": "medium",
        "prompt_text": (
            "The cost of inequality is borne by the whole society, not just the poor.\n\n"
            "Write an essay of approximately 500 words. A clear title is required.\n"
            "(UPSC / IES General English — Essay)"
        ),
        "intro_text": (
            "Inequality's Hidden Tax: Why Everyone Pays\n\n"
            "Inequality is typically discussed as a problem for those at the bottom — the poor, "
            "the marginalised, the excluded. This framing is incomplete. Societies with high "
            "inequality systematically underperform in health, education, crime, and institutional "
            "trust — outcomes that burden every citizen, regardless of income. The cost of "
            "inequality is not merely a redistributive question but a question of what kind of "
            "society everyone inhabits."
        ),
        "body_text": (
            "The mechanisms through which inequality harms those who are not poor are well "
            "documented. In high-inequality societies, crime rates are elevated — a direct "
            "consequence of the frustration, relative deprivation, and institutional erosion "
            "that concentrated poverty produces. The affluent pay for this in private security, "
            "gated communities, and the erosion of shared public spaces. They pay too in "
            "healthcare: countries and cities with greater inequality have worse average health "
            "outcomes even among their middle and upper classes, because public health systems "
            "atrophy when the wealthy exit them.\n\n"
            "In India, the consequences of inequality reach into economic performance. The "
            "consumption-driven growth model requires a broad middle class with purchasing power. "
            "When income concentrates at the top, domestic demand narrows, economic dynamism "
            "depends on the spending decisions of a small elite, and the vast productive "
            "potential of hundreds of millions of workers is left partially mobilised. CMIE data "
            "shows that the top 10% of Indian households account for over 50% of consumption — "
            "a structure that leaves growth permanently vulnerable to the preferences of the few.\n\n"
            "Inequality also corrodes institutions. When the gap between the powerful and the "
            "powerless becomes large enough, public institutions — the judiciary, the civil "
            "service, the legislature — bend toward the interests of those with resources to "
            "influence them. This is not merely a problem for those who cannot afford legal "
            "representation; it is a problem for the legitimacy of the entire system. Once "
            "citizens lose confidence that institutions treat them equally, compliance erodes, "
            "social contracts fray, and governance becomes harder for everyone.\n\n"
            "The evidence from India's own history reinforces this. Regions with greater land "
            "inequality — inherited from colonial revenue systems — have consistently shown "
            "lower literacy, weaker public services, and higher social conflict than those "
            "where land was distributed more broadly. The inequalities of the colonial era "
            "imposed costs on development trajectories that persist eight decades after "
            "independence."
        ),
        "conclusion_text": (
            "Inequality is not a problem the rich can afford to ignore because it only "
            "hurts the poor. It is a structural condition that degrades the quality of "
            "life, institutions, and economic performance available to everyone. The "
            "argument for addressing it is not merely moral — though it is that — but "
            "practical: a more equal society is a more productive, safer, healthier, "
            "and more governable one. The cost of inequality is a tax paid by the whole "
            "society; only the rate differs."
        ),
    },
    {
        "question_id": "eng_essay_002",
        "source_exam": "upsc_style",
        "difficulty": "medium",
        "prompt_text": (
            "Agriculture is India's past — but it need not remain India's problem.\n\n"
            "Write an essay of approximately 500 words. A clear title is required.\n"
            "(UPSC / IES General English — Essay)"
        ),
        "intro_text": (
            "From Burden to Asset: Reimagining Indian Agriculture\n\n"
            "Indian agriculture supports the livelihoods of over 700 million people yet "
            "contributes less than 18% of GDP. It is simultaneously the foundation of "
            "India's food security and the source of its deepest developmental contradictions: "
            "persistent farmer distress, erratic monsoon dependence, stagnant productivity, "
            "and the political economy of subsidies that crowd out investment. To say that "
            "agriculture is India's past is accurate; to accept that it must remain India's "
            "defining problem is a choice, not a destiny."
        ),
        "body_text": (
            "The structural roots of agrarian distress are well-known. Farm sizes have "
            "fragmented with each generation of inheritance — the average holding is now "
            "under 1.1 hectares — making mechanisation unviable and market access difficult. "
            "Irrigation covers barely 53% of net sown area, leaving nearly half of India's "
            "farmland hostage to rainfall variability. Post-harvest losses of 15–20% mean "
            "that crops grown are never fully monetised. And the terms of trade have "
            "historically favoured urban industry over rural agriculture — the implicit "
            "taxation of the sector that industrialisation strategies in both colonial and "
            "post-Independence India imposed.\n\n"
            "Yet the pathways to transformation exist and are not hypothetical. Contract "
            "farming and Farmer Producer Organisations (FPOs) offer mechanisms to aggregate "
            "fragmented holdings into economically viable units without requiring "
            "consolidation of ownership — preserving the social function of land while "
            "enabling the economic efficiencies of scale. India now has over 6,000 FPOs; "
            "the challenge is deepening their reach and financial capacity. Cold-chain "
            "infrastructure investment can directly address post-harvest loss, which is "
            "economically equivalent to adding farmland without clearing a single tree.\n\n"
            "Technological leverage offers the most scalable transformation. Precision "
            "agriculture using satellite imagery, soil sensors, and AI-driven crop advisory "
            "has demonstrated yield improvements of 20–30% in pilot programmes in Punjab "
            "and Andhra Pradesh. Digital crop insurance linked to satellite-verified "
            "weather data can replace the slow, fraud-prone manual assessment system that "
            "has made crop insurance distrusted by farmers. The PM-KISAN registry and "
            "e-NAM platform provide the digital infrastructure on which these capabilities "
            "can be built.\n\n"
            "Transformation also requires an honest reckoning with the subsidy regime. "
            "Power and fertiliser subsidies worth over ₹3 lakh crore annually are "
            "disproportionately captured by larger, wealthier farmers and have encouraged "
            "water-intensive crops in water-scarce regions. Redirecting even a fraction "
            "toward public goods — rural roads, irrigation, agricultural research, and "
            "extension services — would yield higher long-run returns for the majority "
            "of cultivators."
        ),
        "conclusion_text": (
            "Indian agriculture's problems are real but they are not immutable. They are "
            "the products of historical choices — about land, water, technology, and policy "
            "— that can be unmade and remade. The 700 million people whose lives are bound "
            "to the soil are not a burden to be managed; they are a productive force to be "
            "unleashed. Whether agriculture remains India's problem or becomes its next "
            "great driver of inclusive growth depends not on geography or demography but "
            "on the quality of political will and institutional design brought to bear on "
            "its transformation."
        ),
    },
    {
        "question_id": "eng_essay_003",
        "source_exam": "upsc_style",
        "difficulty": "hard",
        "prompt_text": (
            "A democracy that fails its poor has failed its purpose.\n\n"
            "Write an essay of approximately 500 words. A clear title is required.\n"
            "(UPSC / IES General English — Essay)"
        ),
        "intro_text": (
            "The Unfinished Promise: Democracy and the Poor\n\n"
            "Democracy's foundational promise is political equality: each citizen, regardless "
            "of wealth, caste, or education, commands one vote and one voice. Yet between "
            "this formal equality and the lived reality of the poorest citizens lies a gulf "
            "that reveals democracy's most enduring contradiction. If the purpose of "
            "democratic governance is to serve the interests of all its citizens — and "
            "especially its most vulnerable — then the record of Indian democracy, like "
            "that of most democracies, is one of partial and uneven fulfilment."
        ),
        "body_text": (
            "The mechanisms of democratic failure for the poor are structural. Money and "
            "organisation have always translated into political influence in excess of what "
            "the one-person-one-vote principle implies. Campaign financing, media access, "
            "and the ability to sustain sustained lobbying are unevenly distributed. "
            "Regulatory agencies and courts — nominally independent — operate in practical "
            "proximity to those with resources to engage them. The result is a gap between "
            "the formal arithmetic of democracy and the effective distribution of political "
            "power.\n\n"
            "India illustrates this acutely. Universal adult franchise arrived in 1950 — "
            "before literacy, before land reform, before any of the social conditions that "
            "historically accompanied democratisation in the West. Indian democracy was thus "
            "required to perform the redistribution of power that other societies achieved "
            "through social revolutions before their democracies were constituted. The "
            "results have been mixed. Dalit and OBC political mobilisation has achieved "
            "genuine representation gains. MGNREGS and PDS have delivered measurable "
            "welfare. The Right to Information Act gave citizens a democratic instrument "
            "of accountability. Yet hunger, malnutrition, and educational deprivation "
            "persist at levels inconsistent with a functional democracy.\n\n"
            "The failure is not only of distribution but of voice. Democratic responsiveness "
            "depends on articulation: citizens must be able to name what they need and hold "
            "governments accountable for delivering it. Where education is poor, information "
            "is captured, and civil society is weak, this articulation fails. Voters may "
            "choose governments on the basis of identity, patronage, or charisma rather "
            "than policy performance — not irrationally, but because the mechanisms for "
            "tracking policy performance are inaccessible. The poor then receive what "
            "governments choose to give, not what they have the power to demand.\n\n"
            "There is also the temporal problem. Democratic cycles are short; poverty's "
            "structural causes — malnutrition in early childhood, learning deficits in "
            "school, the intergenerational transmission of occupational disadvantage — "
            "operate on timescales of decades. Governments have weak incentives to invest "
            "in interventions whose results materialise after the next election."
        ),
        "conclusion_text": (
            "Democracy has given India's poor something of great value: the periodic ability "
            "to remove governments that fail them and the constitutional guarantee that their "
            "dignity is not contingent on birth or wealth. But formal equality has not yet "
            "become substantive equality. A democracy that delivers elections without "
            "delivering education, healthcare, and economic security to its most vulnerable "
            "citizens has fulfilled its procedural promise while betraying its substantive "
            "one. The measure of democratic success is not the number of elections held "
            "but the quality of life available to those at the bottom."
        ),
    },
    {
        "question_id": "eng_essay_004",
        "source_exam": "upsc_style",
        "difficulty": "medium",
        "prompt_text": (
            "India's cities are broken by design — but they can be repaired by will.\n\n"
            "Write an essay of approximately 500 words. A clear title is required.\n"
            "(UPSC / IES General English — Essay)"
        ),
        "intro_text": (
            "The Urban Question: Building Cities That Work for Everyone\n\n"
            "India's cities are home to 500 million people and generate over 60% of GDP. "
            "They are also chronically overwhelmed: traffic that paralyses, water that fails "
            "to reach the tap, air that shortens lives, and informal settlements housing "
            "millions with no legal security of tenure. These failures are often described "
            "as the inevitable consequences of rapid, unplanned urbanisation. They are more "
            "accurately the consequences of a set of deliberate — if historically contingent "
            "— choices about land, governance, and investment that produced cities not "
            "designed to serve those who live in them."
        ),
        "body_text": (
            "The design failures begin with land. India's urban land markets are among the "
            "most distorted in the world — a legacy of the Urban Land Ceiling Act (repealed "
            "but leaving an inheritance of fragmented title and speculative holding), "
            "Floor Space Index restrictions that keep building densities artificially low "
            "in central areas, and a stamp duty regime that inhibits formal transactions. "
            "The result is a city that sprawls horizontally rather than growing vertically "
            "— forcing workers to commute across vast distances, pricing the poor out of "
            "central locations, and making public transport economically unviable because "
            "densities are too low.\n\n"
            "Governance is the second structural failure. Indian city governments are among "
            "the weakest in the democratic world: chronically underfunded, with limited "
            "revenue autonomy, politically subordinate to state governments, and lacking "
            "the technical capacity to plan and execute complex urban infrastructure. The "
            "74th Constitutional Amendment promised empowered urban local bodies; three "
            "decades on, most cities remain dependent on state transfers for the most "
            "basic functions. When no one is clearly accountable for a city's failures, "
            "they compound.\n\n"
            "The consequences fall hardest on the urban poor. Over 65 million people live "
            "in informal settlements where tenure insecurity, waterlogging, and the absence "
            "of sanitation are daily realities. These are not passive victims of urbanisation "
            "— they built the city with their labour — but the city's design excludes them "
            "from its formal economy of secure housing and legal address.\n\n"
            "The will to repair exists in pockets. Ahmedabad's Bus Rapid Transit, Indore's "
            "solid waste management transformation, and Surat's flood resilience investments "
            "show that Indian city governments, when given resources and political support, "
            "can deliver. The Smart Cities Mission and AMRUT have channelled investment into "
            "urban infrastructure — imperfectly, with variable outcomes, but demonstrating "
            "state capacity that can be built upon."
        ),
        "conclusion_text": (
            "India's cities were not broken by accident. They were built by a combination "
            "of colonial neglect, post-independence industrial bias, and state-level "
            "political incentives that systematically under-invested in urban governance "
            "and land markets. Repairing them requires acknowledging that the choices that "
            "created these conditions can be unmade: FSI restrictions can be relaxed, "
            "municipal finances can be reformed, tenure security can be extended. The "
            "500 million people in India's cities — and the 250 million more who will join "
            "them in the next two decades — deserve cities built for them, not despite them."
        ),
    },
    {
        "question_id": "eng_essay_005",
        "source_exam": "upsc_style",
        "difficulty": "hard",
        "prompt_text": (
            "The climate crisis and the development crisis are one and the same crisis.\n\n"
            "Write an essay of approximately 500 words. A clear title is required.\n"
            "(UPSC / IES General English — Essay)"
        ),
        "intro_text": (
            "Two Crises, One Root: Climate, Development, and the Way Forward\n\n"
            "The conventional framing presents climate change and poverty as two separate "
            "challenges that occasionally intersect and sometimes trade off against each "
            "other. This framing has done enormous damage to both the climate debate and "
            "the development debate — allowing each to proceed on the assumption that the "
            "other is a different department's problem. The deeper reality is that the "
            "climate crisis and the development crisis share common roots in the same "
            "model of resource extraction, exclusion, and short-termism. Understanding "
            "them as one crisis is the precondition for addressing either."
        ),
        "body_text": (
            "The development crisis is most visible in its human face: 700 million people "
            "globally in extreme poverty, 200 million chronically hungry, billions without "
            "reliable energy, clean water, or adequate healthcare. What is less often "
            "acknowledged is the structural cause: a model of growth that externalises "
            "its environmental costs and concentrates its gains. The same industrial "
            "processes that have generated unprecedented wealth over the past two centuries "
            "have depleted aquifers, degraded soils, released heat-trapping gases, and "
            "disrupted the ecological systems on which agriculture — and therefore food "
            "security — depends. Development that degrades its natural foundation eventually "
            "undermines itself.\n\n"
            "For India, the connection is not theoretical. The Himalayan glaciers that feed "
            "the Ganga, Yamuna, and Brahmaputra — the water systems that sustain half a "
            "billion people and the irrigated agriculture they depend on — are retreating at "
            "measurable and accelerating rates. Extreme heat events are already reducing "
            "agricultural output and outdoor labour productivity in some of India's poorest "
            "states. Coastal flooding threatens 40 million people and some of the country's "
            "most productive delta agriculture. These are not future risks; they are present "
            "costs that compound existing deprivation.\n\n"
            "The political economy of the two crises is also shared. In both, the costs are "
            "disproportionately borne by those with the least power to influence the "
            "decisions that generate them. The smallholder farmer in Vidarbha did not "
            "choose the industrial energy model that changed the monsoon; the fisherfolk "
            "of the Sundarbans did not vote for the development path that is inundating "
            "their islands. The carbon emitted by rich nations and by India's own urban "
            "industrial economy falls as rain — or fails to fall — on those whose "
            "livelihoods depend on the predictability of seasons.\n\n"
            "The resolution too must be shared. Climate-resilient development — in "
            "agriculture, in energy, in urban planning — is not a different project from "
            "inclusive development. Investments in renewable energy reach the rural poor "
            "faster than grid extension from distant coal plants. Climate-smart agriculture "
            "reduces input costs for smallholders while building soil carbon. Urban flood "
            "management protects informal settlements first."
        ),
        "conclusion_text": (
            "Separating the climate crisis from the development crisis has served no one "
            "except those who benefit from addressing neither. India's developmental "
            "ambitions and its climate obligations are not in opposition — they are "
            "convergent, because both require building an economy that is productive, "
            "equitable, and capable of sustaining itself across generations. The first "
            "step is to stop treating them as separate problems and to ask, instead, "
            "what a development model would look like that solved both at once. The "
            "answer, in outline, already exists. What is required is the political "
            "imagination to pursue it."
        ),
    },
]


def run(conn):
    for q in _ESSAYS:
        conn.execute(
            "UPDATE english_questions "
            "SET prompt_text=?, intro_text=?, body_text=?, conclusion_text=?, source_exam=?, difficulty=? "
            "WHERE question_id=? AND exam_id='english_practice'",
            (
                q["prompt_text"], q["intro_text"], q["body_text"],
                q["conclusion_text"], q["source_exam"], q["difficulty"],
                q["question_id"],
            ),
        )
    conn.commit()
