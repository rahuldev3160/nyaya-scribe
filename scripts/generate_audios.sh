#!/bin/bash
# NotebookLM Audio Generation Script — IES 2026 General Economics
# Usage: ./generate_audios.sh [ge01|ge02|ge03|ge04|all]
# Generates --length long --format deep-dive audios sequentially.
# Each audio waits for completion before the next starts.
# Downloads audio after each generation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR/notebooklm_prompts"
AUDIO_OUT="$SCRIPT_DIR/../data/audio"
NLM="notebooklm"

GE01="a6f5f267-0f0c-46f3-9d05-967d40142f33"
GE02="68f995e3-0f94-4ee4-86f1-e7cffd753893"
GE03="83490f1c-2225-4288-ad0f-58979a44a060"
GE04="3fbeeffd-2975-49b4-a948-d56d92a185ca"

mkdir -p "$AUDIO_OUT/ge01" "$AUDIO_OUT/ge02" "$AUDIO_OUT/ge03" "$AUDIO_OUT/ge04"

TARGET="${1:-all}"

generate_audio() {
    local notebook_id="$1"
    local prompt_file="$2"
    local audio_title="$3"
    local out_dir="$4"

    echo ""
    echo "======================================"
    echo "Generating: $audio_title"
    echo "Notebook:   $notebook_id"
    echo "======================================"

    $NLM generate audio \
        -n "$notebook_id" \
        --prompt-file "$prompt_file" \
        --format deep-dive \
        --length long \
        --wait \
        --timeout 1200

    echo "Generation complete. Downloading..."
    $NLM download audio \
        -n "$notebook_id" \
        --latest \
        "$out_dir/${audio_title}.mp4"

    echo "Saved: $out_dir/${audio_title}.mp4"
    echo "Waiting 30 seconds before next audio..."
    sleep 30
}

generate_ge01() {
    echo "=== GE-01: Micro and Macro Economics (5 audios) ==="
    generate_audio "$GE01" "$PROMPTS_DIR/GE01_A1_consumers_demand_utility_indifference.txt" \
        "GE01_A1_consumers_demand_utility_indifference" "$AUDIO_OUT/ge01"
    generate_audio "$GE01" "$PROMPTS_DIR/GE01_A2_consumers_demand_risk_asymmetric_information.txt" \
        "GE01_A2_consumers_demand_risk_asymmetric_information" "$AUDIO_OUT/ge01"
    generate_audio "$GE01" "$PROMPTS_DIR/GE01_A3_theory_of_value_market_structures_game_theory.txt" \
        "GE01_A3_theory_of_value_market_structures_game_theory" "$AUDIO_OUT/ge01"
    generate_audio "$GE01" "$PROMPTS_DIR/GE01_A4_theory_production_distribution_mathematical_methods.txt" \
        "GE01_A4_theory_production_distribution_mathematical_methods" "$AUDIO_OUT/ge01"
    generate_audio "$GE01" "$PROMPTS_DIR/GE01_A5_statistical_econometric_welfare.txt" \
        "GE01_A5_statistical_econometric_welfare" "$AUDIO_OUT/ge01"
    echo "GE-01 complete: 5 audios in $AUDIO_OUT/ge01/"
}

generate_ge02() {
    echo "=== GE-02: Growth, Trade and Money (5 audios) ==="
    generate_audio "$GE02" "$PROMPTS_DIR/GE02_A1_growth_classical_neoclassical_endogenous.txt" \
        "GE02_A1_growth_classical_neoclassical_endogenous" "$AUDIO_OUT/ge02"
    generate_audio "$GE02" "$PROMPTS_DIR/GE02_A2_development_theories_measurement_capability.txt" \
        "GE02_A2_development_theories_measurement_capability" "$AUDIO_OUT/ge02"
    generate_audio "$GE02" "$PROMPTS_DIR/GE02_A3_employment_output_inflation_money_NIA.txt" \
        "GE02_A3_employment_output_inflation_money_NIA" "$AUDIO_OUT/ge02"
    generate_audio "$GE02" "$PROMPTS_DIR/GE02_A4_international_economics_trade_thought_finance.txt" \
        "GE02_A4_international_economics_trade_thought_finance" "$AUDIO_OUT/ge02"
    generate_audio "$GE02" "$PROMPTS_DIR/GE02_A5_balance_of_payments_open_economy_global_institutions.txt" \
        "GE02_A5_balance_of_payments_open_economy_global_institutions" "$AUDIO_OUT/ge02"
    echo "GE-02 complete: 5 audios in $AUDIO_OUT/ge02/"
}

generate_ge03() {
    echo "=== GE-03: Indian Economy Applied (7 audios, ~15 min each) ==="
    generate_audio "$GE03" "$PROMPTS_DIR/GE03_A1a_environmental_externalities_instruments.txt" \
        "GE03_A1a_environmental_externalities_instruments" "$AUDIO_OUT/ge03"
    generate_audio "$GE03" "$PROMPTS_DIR/GE03_A1b_environmental_valuation_resources_climate.txt" \
        "GE03_A1b_environmental_valuation_resources_climate" "$AUDIO_OUT/ge03"
    generate_audio "$GE03" "$PROMPTS_DIR/GE03_A2a_industrial_economics_SCP_barriers_conduct.txt" \
        "GE03_A2a_industrial_economics_SCP_barriers_conduct" "$AUDIO_OUT/ge03"
    generate_audio "$GE03" "$PROMPTS_DIR/GE03_A2b_industrial_economics_regulation_innovation_policy.txt" \
        "GE03_A2b_industrial_economics_regulation_innovation_policy" "$AUDIO_OUT/ge03"
    generate_audio "$GE03" "$PROMPTS_DIR/GE03_A3a_public_finance_public_goods_taxation_theory.txt" \
        "GE03_A3a_public_finance_public_goods_taxation_theory" "$AUDIO_OUT/ge03"
    generate_audio "$GE03" "$PROMPTS_DIR/GE03_A3b_public_finance_debt_federalism_expenditure.txt" \
        "GE03_A3b_public_finance_debt_federalism_expenditure" "$AUDIO_OUT/ge03"
    generate_audio "$GE03" "$PROMPTS_DIR/GE03_A4_state_market_planning_reform.txt" \
        "GE03_A4_state_market_planning_reform" "$AUDIO_OUT/ge03"
    echo "GE-03 complete: 7 audios in $AUDIO_OUT/ge03/"
}

generate_ge04() {
    echo "=== GE-04: Economic Policy Indian Context (7+1 audios, ~15 min each) ==="
    generate_audio "$GE04" "$PROMPTS_DIR/GE04_A1a_agriculture_rural_development.txt" \
        "GE04_A1a_agriculture_rural_development" "$AUDIO_OUT/ge04"
    generate_audio "$GE04" "$PROMPTS_DIR/GE04_A1b_poverty_unemployment_human_development.txt" \
        "GE04_A1b_poverty_unemployment_human_development" "$AUDIO_OUT/ge04"
    generate_audio "$GE04" "$PROMPTS_DIR/GE04_A1c_labour_india_urbanisation_migration.txt" \
        "GE04_A1c_labour_india_urbanisation_migration" "$AUDIO_OUT/ge04"
    generate_audio "$GE04" "$PROMPTS_DIR/GE04_A2_money_banking_inflation_india.txt" \
        "GE04_A2_money_banking_inflation_india" "$AUDIO_OUT/ge04"
    generate_audio "$GE04" "$PROMPTS_DIR/GE04_A3_fiscal_federal_finance_india.txt" \
        "GE04_A3_fiscal_federal_finance_india" "$AUDIO_OUT/ge04"
    generate_audio "$GE04" "$PROMPTS_DIR/GE04_A4_foreign_trade_development_planning_industry_india.txt" \
        "GE04_A4_foreign_trade_development_planning_industry_india" "$AUDIO_OUT/ge04"
    generate_audio "$GE04" "$PROMPTS_DIR/GE04_A5_synthesis_exam_strategy.txt" \
        "GE04_A5_synthesis_exam_strategy" "$AUDIO_OUT/ge04"
    echo "GE-04 complete: 7 audios in $AUDIO_OUT/ge04/"
}

case "$TARGET" in
    ge01) generate_ge01 ;;
    ge02) generate_ge02 ;;
    ge03) generate_ge03 ;;
    ge04) generate_ge04 ;;
    all)
        generate_ge01
        generate_ge02
        generate_ge03
        generate_ge04
        ;;
    *)
        echo "Usage: $0 [ge01|ge02|ge03|ge04|all]"
        exit 1
        ;;
esac

echo ""
echo "Done. Audio files are in: $AUDIO_OUT/"
echo "Transfer to phone or podcast player to listen."
