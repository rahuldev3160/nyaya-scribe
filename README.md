# IES 2026 Descriptive Exam Prep

AI-powered study tool for IES General Economics papers GE-01 to GE-04. 1219 past-year questions (2010–2025) with structured model answers, standard economics diagrams, and rubric checklists. Built with Streamlit and Claude.

## Features

- 1219 model answers with intro/body/conclusion structure
- Standard economics diagrams (IS-LM, Solow, Phillips, Demand-Supply, Lorenz, etc.) drawn via matplotlib
- Flowchart visualization for process-based questions (Mermaid.js)
- Comparison table renderer (pure Python, no AI)
- Topic-wise, year-wise question browser
- Rubric checklist and data points per answer
- MCQ quiz with AI evaluation

## Setup

**Prerequisites:** Python 3.9+, pip

```bash
pip install -r requirements.txt
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your_key
```

Run the app:

```bash
streamlit run web/app.py
```

## Database

The pre-built database (`data/ies.db`) is not included in the repo (contains personal study tracking data).

To generate from scratch, run the scripts in `scripts/` in order:

```
init_db.py → seed_topics.py → ingest_pyq.py → generate_rubrics.py → generate_answers.py
```

A scrubbed public database release is planned.

## License

- **Code:** MIT License
- **Model answers:** CC BY 4.0 — free to use with attribution
