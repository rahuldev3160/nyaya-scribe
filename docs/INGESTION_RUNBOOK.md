# New Exam Paper Runbook

When a new exam paper is available (e.g., IES 2027):

1. `python3 scripts/ingest_pyq.py --exam ies_2026 --pdf <path>`
2. `python3 scripts/generate_rubrics.py --exam ies_2026`
3. `python3 scripts/generate_answers.py --exam ies_2026`
4. `python3 scripts/compute_base_scores.py --exam ies_2026`
5. `git add migrations/ && git commit && git push` → Railway auto-deploys

For UPSC: replace `ies_2026` with `upsc_eco_opt`, uses `data/upsc_eco_opt.db`
For RBI: replace `ies_2026` with `rbi_depr`, uses `data/rbi.db`

## Batch ID files

Each exam gets its own batch tracking files so concurrent runs don't collide:

| Exam          | Rubrics batch file                    | Answers batch file                   |
|---------------|---------------------------------------|--------------------------------------|
| ies_2026      | data/ies_2026_rubrics_batch.txt       | data/ies_2026_answers_batch.txt      |
| upsc_eco_opt  | data/upsc_eco_opt_rubrics_batch.txt   | data/upsc_eco_opt_answers_batch.txt  |
| rbi_depr      | data/rbi_depr_rubrics_batch.txt       | data/rbi_depr_answers_batch.txt      |

If a script was interrupted, re-run the same command — it will resume the existing batch automatically.
Delete the batch file only if you want to start a fresh batch.

## DB map

| exam_id       | DB file       |
|---------------|---------------|
| ies_2026      | data/ies.db   |
| upsc_eco_opt  | data/upsc_eco_opt.db  |
| rbi_depr      | data/rbi.db   |
