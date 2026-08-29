"""Single source of truth for exam countdown dates shown across dashboards.

Previously duplicated as two independent literals in rbi_prep_bp.py and
rbi_dashboard_bp.py, which had already drifted stale (2026-06-14, in the past).
"""

# RBI Grade B 2027 cycle: no official notification yet as of 2026-08-30.
# Provisional estimate based on the 2026 cycle's Phase 1 date (2026-06-14) --
# update once RBI's real notification lands.
RBI_DATE = "2027-06-15"
