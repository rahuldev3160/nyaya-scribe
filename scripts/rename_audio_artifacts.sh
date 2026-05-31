#!/bin/bash
# Rename NotebookLM audio artifacts to structured IES 2026 titles.
# Usage: ./rename_audio_artifacts.sh [ge01|ge02|ge03|ge04|all]
# Artifacts are renamed in creation-time order to match submission order.

set -euo pipefail

NLM="notebooklm"

GE01="a6f5f267-0f0c-46f3-9d05-967d40142f33"
GE02="68f995e3-0f94-4ee4-86f1-e7cffd753893"
GE03="83490f1c-2225-4288-ad0f-58979a44a060"
GE04="3fbeeffd-2975-49b4-a948-d56d92a185ca"

rename_in_order() {
    local notebook_id="$1"
    shift
    local titles=("$@")

    echo "Fetching artifact list for notebook $notebook_id..."
    local artifact_json
    artifact_json=$($NLM artifact list -n "$notebook_id" --json 2>/dev/null)

    # Extract completed audio artifacts sorted by created_at (ascending)
    local ids
    ids=$(echo "$artifact_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
audios = [a for a in data['artifacts'] if a['type_id'] == 'audio' and a['status_id'] == 3]
audios.sort(key=lambda x: x['created_at'])
for a in audios:
    print(a['id'])
")

    local count
    count=$(echo "$ids" | grep -c . || true)
    local expected=${#titles[@]}

    echo "Found $count completed audio artifacts, expecting $expected titles."

    if [ "$count" -lt "$expected" ]; then
        echo "WARNING: Only $count audios completed, expected $expected."
        echo "Run again after all audios finish generating."
    fi

    local i=0
    while IFS= read -r artifact_id && [ $i -lt $expected ]; do
        local new_title="${titles[$i]}"
        echo "Renaming $artifact_id → $new_title"
        $NLM artifact rename -n "$notebook_id" "$artifact_id" "$new_title" 2>&1 || true
        i=$((i + 1))
    done <<< "$ids"
}

rename_ge01() {
    echo "=== Renaming GE-01 artifacts ==="
    local titles=(
        "GE-01 | A1 | Consumer Demand — Utility & Indifference"
        "GE-01 | A2 | Consumer Demand — Risk & Asymmetric Info"
        "GE-01 | A3 | Theory of Value — Market Structures & Game Theory"
        "GE-01 | A4 | Theory of Production, Distribution & Math Methods"
        "GE-01 | A5 | Statistical & Econometric Methods + Welfare Economics"
    )
    rename_in_order "$GE01" "${titles[@]}"
}

rename_ge02() {
    echo "=== Renaming GE-02 artifacts ==="
    local titles=(
        "GE-02 | A1 | Growth Theory — Classical, Solow & Endogenous"
        "GE-02 | A2 | Development Theories — Big Push to Sen's Capability"
        "GE-02 | A3 | Employment, IS-LM, Inflation & National Accounts"
        "GE-02 | A4 | International Trade, Economic Thought & Capital Markets"
        "GE-02 | A5 | Balance of Payments, Mundell-Fleming & Global Institutions"
    )
    rename_in_order "$GE02" "${titles[@]}"
}

rename_ge03() {
    echo "=== Renaming GE-03 artifacts ==="
    local titles=(
        "GE-03 | A1a | Environmental Externalities & Policy Instruments"
        "GE-03 | A1b | Environmental Valuation, Resources & Climate"
        "GE-03 | A2a | Industrial Economics — SCP, Barriers & Firm Conduct"
        "GE-03 | A2b | Industrial Economics — Regulation, Innovation & Policy"
        "GE-03 | A3a | Public Finance — Public Goods & Optimal Taxation"
        "GE-03 | A3b | Public Finance — Debt, Ricardian Equivalence & Federalism"
        "GE-03 | A4 | State, Market & Planning — Washington Consensus to Dev State"
    )
    rename_in_order "$GE03" "${titles[@]}"
}

rename_ge04() {
    echo "=== Renaming GE-04 artifacts ==="
    local titles=(
        "GE-04 | A1a | Agriculture & Rural Development"
        "GE-04 | A1b | Poverty, Unemployment & Human Development"
        "GE-04 | A1c | Labour Markets & Urbanisation in India"
        "GE-04 | A2 | Money, Banking & Inflation in India"
        "GE-04 | A3 | Fiscal Policy, GST & Federal Finance"
        "GE-04 | A4 | Foreign Trade, Planning History & Industrial Policy"
        "GE-04 | A5 | GE-04 Synthesis — Exam Traps & 2026 Predictions"
    )
    rename_in_order "$GE04" "${titles[@]}"
}

TARGET="${1:-all}"
case "$TARGET" in
    ge01) rename_ge01 ;;
    ge02) rename_ge02 ;;
    ge03) rename_ge03 ;;
    ge04) rename_ge04 ;;
    all)
        rename_ge01
        rename_ge02
        rename_ge03
        rename_ge04
        ;;
    *)
        echo "Usage: $0 [ge01|ge02|ge03|ge04|all]"
        exit 1
        ;;
esac

echo ""
echo "Rename complete. Verify in NotebookLM or with: notebooklm artifact list -n <id>"
