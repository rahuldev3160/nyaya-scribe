#!/bin/bash
# RBI DEPR 2026 — Full audio pipeline (fully automated)
# Creates 1 notebook, adds 2 sources, generates 6 × 20-min audios, uploads to YouTube.
# Usage: bash scripts/generate_rbi_audios.sh [--skip-upload]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
PROMPTS_DIR="$SCRIPT_DIR/notebooklm_prompts"
AUDIO_OUT="$ROOT/data/audio/rbi"
NLM="notebooklm"
SKIP_UPLOAD="${1:-}"

mkdir -p "$AUDIO_OUT"

# ── Step 1: Create notebook ──────────────────────────────────────────────────
echo ""
echo "======================================"
echo "STEP 1: Creating RBI DEPR notebook"
echo "======================================"
CREATE_OUT=$($NLM create "RBI DEPR 2026 — MCQ Audio Series")
echo "$CREATE_OUT"
RBI_NB=$(echo "$CREATE_OUT" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
if [[ -z "$RBI_NB" ]]; then
    echo "ERROR: Could not parse notebook ID from create output."
    exit 1
fi
echo "Notebook ID: $RBI_NB"

# ── Step 2: Add sources (--type text avoids .md format rejection) ────────────
echo ""
echo "======================================"
echo "STEP 2: Adding source documents"
echo "======================================"
SRC1=$($NLM source add -n "$RBI_NB" --type text \
    "$(cat "$ROOT/data/notebooklm/rbi_theory_mcq_source.md")" \
    --title "RBI Theory & MCQ Source" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
echo "Added theory source: $SRC1"

SRC2=$($NLM source add -n "$RBI_NB" --type text \
    "$(cat "$ROOT/data/notebooklm/rbi_current_data_formatted.md")" \
    --title "RBI Current Data & Fiscal" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
echo "Added data source: $SRC2"

echo "Waiting for sources to process..."
$NLM source wait -n "$RBI_NB" "$SRC1" --timeout 300
$NLM source wait -n "$RBI_NB" "$SRC2" --timeout 300
echo "Sources ready."

# ── Step 3: Generate 6 audios ────────────────────────────────────────────────
generate_audio() {
    local prompt_file="$1"
    local audio_title="$2"

    echo ""
    echo "--------------------------------------"
    echo "Generating: $audio_title"
    echo "--------------------------------------"

    $NLM generate audio \
        -n "$RBI_NB" \
        --prompt-file "$prompt_file" \
        --format deep-dive \
        --length default \
        --wait \
        --timeout 900

    echo "Downloading..."
    $NLM download audio \
        -n "$RBI_NB" \
        --latest \
        "$AUDIO_OUT/${audio_title}.mp4"

    echo "Saved: $AUDIO_OUT/${audio_title}.mp4"
    echo "Waiting 30s before next episode..."
    sleep 30
}

echo ""
echo "======================================"
echo "STEP 3: Generating 6 audio episodes"
echo "======================================"

generate_audio "$PROMPTS_DIR/RBI_A1_macro_monetary_mcq.txt" \
    "RBI_A1_macro_monetary_mcq"

generate_audio "$PROMPTS_DIR/RBI_A2_growth_development_quant.txt" \
    "RBI_A2_growth_development_quant"

generate_audio "$PROMPTS_DIR/RBI_A3_micro_international_pf.txt" \
    "RBI_A3_micro_international_pf"

generate_audio "$PROMPTS_DIR/RBI_A4_rbi_instruments_monetary.txt" \
    "RBI_A4_rbi_instruments_monetary"

generate_audio "$PROMPTS_DIR/RBI_A5_banking_regulation_payments.txt" \
    "RBI_A5_banking_regulation_payments"

generate_audio "$PROMPTS_DIR/RBI_A6_indian_economy_current.txt" \
    "RBI_A6_indian_economy_current"

# ── Step 4: Convert mp4 → mp3 ────────────────────────────────────────────────
echo ""
echo "======================================"
echo "STEP 4: Converting mp4 → mp3"
echo "======================================"

# zsh-compatible (no associative arrays)
convert_ep() {
    local mp4="$AUDIO_OUT/$1.mp4" mp3="$AUDIO_OUT/$2.mp3"
    [[ -f "$mp4" ]] && ffmpeg -y -i "$mp4" -vn -acodec libmp3lame -q:a 2 "$mp3" && echo "Converted: $2.mp3" || echo "WARNING: $mp4 not found"
}
convert_ep "RBI_A1_macro_monetary_mcq"          "RBI - A1 - Macro & Monetary MCQ"
convert_ep "RBI_A2_growth_development_quant"     "RBI - A2 - Growth Development & Quant"
convert_ep "RBI_A3_micro_international_pf"       "RBI - A3 - Micro International & Public Finance"
convert_ep "RBI_A4_rbi_instruments_monetary"     "RBI - A4 - RBI Instruments & Monetary Transmission"
convert_ep "RBI_A5_banking_regulation_payments"  "RBI - A5 - Banking Regulation & Payment Systems"
convert_ep "RBI_A6_indian_economy_current"       "RBI - A6 - Indian Economy Current Data"

# ── Step 5: Thumbnails + upload ───────────────────────────────────────────────
if [[ "$SKIP_UPLOAD" != "--skip-upload" ]]; then
    echo ""
    echo "======================================"
    echo "STEP 5: Generating thumbnails"
    echo "======================================"
    python3.11 "$SCRIPT_DIR/create_thumbnails.py" --paper rbi

    echo ""
    echo "======================================"
    echo "STEP 6: Uploading to YouTube"
    echo "======================================"
    python3.11 "$SCRIPT_DIR/upload_to_youtube.py" --paper rbi
fi

echo ""
echo "======================================"
echo "DONE — RBI DEPR 2026 audio series"
echo "6 episodes generated and uploaded."
echo "Notebook ID: $RBI_NB"
echo "(Save this ID if you need to regenerate)"
echo "======================================"
