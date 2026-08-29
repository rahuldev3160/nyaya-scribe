#!/bin/bash
# Generate, convert, rename, and upload the 9 remaining GE-03/GE-04 episodes.
# Run in background: bash scripts/generate_remaining.sh >> logs/generate_remaining.log 2>&1
#
# Skips already-downloaded episodes (A1a, A1b for GE-03; A1a, A1b for GE-04).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AUDIO_OUT="$PROJECT_ROOT/data/audio"
THUMB_DIR="$PROJECT_ROOT/data/thumbnails"
PROMPTS_DIR="$SCRIPT_DIR/notebooklm_prompts"
NLM="notebooklm"

GE03="83490f1c-2225-4288-ad0f-58979a44a060"
GE04="3fbeeffd-2975-49b4-a948-d56d92a185ca"

IES_PLAYLIST="PLG8cSH86vt8YyNB-tJPdFkp59B33ZFoRj"
YOUTUBE_MANAGE="/Users/rahulsingh/Desktop/Claude Projects/youtube/manage.py"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

generate_convert_upload() {
    local notebook_id="$1"
    local prompt_file="$2"
    local raw_stem="$3"     # e.g. GE03_A2b_industrial_economics_regulation_innovation_policy
    local pretty_stem="$4"  # e.g. GE-03 _ A2b _ Industrial Economics Regulation & Innovation
    local paper="$5"        # e.g. ge03
    local out_dir="$AUDIO_OUT/$paper"

    local mp4_path="$out_dir/${raw_stem}.mp4"
    local mp3_raw="$out_dir/${raw_stem}.mp3"
    local mp3_final="$out_dir/${pretty_stem}.mp3"

    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "EPISODE: $pretty_stem"

    # Generate
    log "Generating audio via NotebookLM..."
    $NLM generate audio \
        -n "$notebook_id" \
        --prompt-file "$prompt_file" \
        --format deep-dive \
        --length long \
        --wait \
        --timeout 1200

    # Download
    log "Downloading..."
    $NLM download audio -n "$notebook_id" --latest "$mp4_path"
    log "Saved: $(basename "$mp4_path")"

    # Convert to MP3
    log "Converting to MP3..."
    ffmpeg -i "$mp4_path" -vn -acodec libmp3lame -q:a 2 -ar 44100 -ac 2 "$mp3_raw" -y -loglevel error
    cp "$mp3_raw" "$mp3_final"
    rm "$mp3_raw"
    log "MP3 ready: $(basename "$mp3_final")"

    # Upload to YouTube
    log "Uploading to YouTube..."
    local video_id
    video_id=$(python3.11 "$PROJECT_ROOT/scripts/upload_to_youtube.py" --file "$mp3_final" 2>&1 | grep "Uploaded:" | grep -oE '[A-Za-z0-9_-]{11}$' || true)

    if [ -n "$video_id" ]; then
        log "Uploaded: https://youtu.be/$video_id"
        # Add to playlist
        python3.11 "$YOUTUBE_MANAGE" playlist add "$IES_PLAYLIST" "$video_id" 2>&1 || true
        log "Added to IES playlist."
    else
        log "⚠ Could not parse video ID from upload output. Check manually."
    fi

    log "Sleeping 60s before next episode..."
    sleep 60
}

mkdir -p logs

log "Starting remaining 9-episode pipeline"
log "GE-03: A2b, A3a, A3b, A4"
log "GE-04: A1c, A2, A3, A4, A5"

# ── GE-03 remaining ──────────────────────────────────────────────────────────
generate_convert_upload "$GE03" \
    "$PROMPTS_DIR/GE03_A2b_industrial_economics_regulation_innovation_policy.txt" \
    "GE03_A2b_industrial_economics_regulation_innovation_policy" \
    "GE-03 _ A2b _ Industrial Economics Regulation & Innovation" \
    "ge03"

generate_convert_upload "$GE03" \
    "$PROMPTS_DIR/GE03_A3a_public_finance_public_goods_taxation_theory.txt" \
    "GE03_A3a_public_finance_public_goods_taxation_theory" \
    "GE-03 _ A3a _ Public Finance Public Goods & Optimal Taxation" \
    "ge03"

generate_convert_upload "$GE03" \
    "$PROMPTS_DIR/GE03_A3b_public_finance_debt_federalism_expenditure.txt" \
    "GE03_A3b_public_finance_debt_federalism_expenditure" \
    "GE-03 _ A3b _ Government Debt Fiscal Federalism & Expenditure" \
    "ge03"

generate_convert_upload "$GE03" \
    "$PROMPTS_DIR/GE03_A4_state_market_planning_reform.txt" \
    "GE03_A4_state_market_planning_reform" \
    "GE-03 _ A4 _ State vs Market Planning & Development Strategy" \
    "ge03"

# ── GE-04 remaining ──────────────────────────────────────────────────────────
generate_convert_upload "$GE04" \
    "$PROMPTS_DIR/GE04_A1c_labour_india_urbanisation_migration.txt" \
    "GE04_A1c_labour_india_urbanisation_migration" \
    "GE-04 _ A1c _ Labour Markets Employment & Urbanisation in India" \
    "ge04"

generate_convert_upload "$GE04" \
    "$PROMPTS_DIR/GE04_A2_money_banking_inflation_india.txt" \
    "GE04_A2_money_banking_inflation_india" \
    "GE-04 _ A2 _ Money Banking Inflation & Monetary Policy in India" \
    "ge04"

generate_convert_upload "$GE04" \
    "$PROMPTS_DIR/GE04_A3_fiscal_federal_finance_india.txt" \
    "GE04_A3_fiscal_federal_finance_india" \
    "GE-04 _ A3 _ Fiscal Policy GST & Fiscal Federalism in India" \
    "ge04"

generate_convert_upload "$GE04" \
    "$PROMPTS_DIR/GE04_A4_foreign_trade_development_planning_industry_india.txt" \
    "GE04_A4_foreign_trade_development_planning_industry_india" \
    "GE-04 _ A4 _ Trade Policy 1991 Reforms & Industrial Policy in India" \
    "ge04"

generate_convert_upload "$GE04" \
    "$PROMPTS_DIR/GE04_A5_synthesis_exam_strategy.txt" \
    "GE04_A5_synthesis_exam_strategy" \
    "GE-04 _ A5 _ Synthesis Connections Exam Traps & 2026 Predictions" \
    "ge04"

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "ALL 9 EPISODES DONE. IES series complete."
