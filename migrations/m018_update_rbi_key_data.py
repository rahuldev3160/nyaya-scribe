"""INSERT OR REPLACE rbi_key_data so content changes in the Python seed propagate to existing DBs."""
DB = "rbi"

_SEED_DATA = [
    # LAF Corridor
    ("laf_01","LAF Corridor & Policy Rates","#8AB4F8",1,"Repo Rate","5.25%","MPC Feb 2026 kept unchanged. Cumulative 125 bps cuts since Feb 2025 (from 6.50%). MPC stance: Neutral.",0,1,1),
    ("laf_02","LAF Corridor & Policy Rates","#8AB4F8",1,"SDF Rate","5.00% (Repo − 25 bps)","Standing Deposit Facility (Apr 2022). LAF floor. Banks park surplus with RBI collateral-free.",0,0,2),
    ("laf_03","LAF Corridor & Policy Rates","#8AB4F8",1,"MSF Rate","5.50% (Repo + 25 bps)","Marginal Standing Facility. LAF ceiling. Banks borrow up to 3% of NDTL of SLR portfolio.",0,0,3),
    ("laf_04","LAF Corridor & Policy Rates","#8AB4F8",1,"Bank Rate","= MSF Rate","Rate for long-term advances outside LAF. Benchmark for penal rates.",0,0,4),
    ("laf_05","LAF Corridor & Policy Rates","#8AB4F8",1,"LAF Corridor width","±25 bps = 50 bps total","Symmetric: SDF (floor) ↔ Repo (signal) ↔ MSF (ceiling). Post-Apr 2022 structure.",0,0,5),
    ("laf_06","LAF Corridor & Policy Rates","#8AB4F8",1,"Reverse Repo","3.35% (superseded by SDF)","Exists in statute but SDF is the operative floor since Apr 2022. Exam trap: SDF ≠ reverse repo.",0,0,6),
    # Reserve Ratios & PSL
    ("rr_01","Reserve Ratios & PSL","#C084FC",2,"CRR","4% of NDTL","% of NDTL held as cash with RBI. No interest paid. RBI cut CRR injecting ₹2.5 lakh crore in FY26.",1,1,1),
    ("rr_02","Reserve Ratios & PSL","#C084FC",2,"SLR","18% of NDTL","% of NDTL held in approved G-secs/gold/cash. Banks borrow under MSF against SLR.",1,1,2),
    ("rr_03","Reserve Ratios & PSL","#C084FC",2,"Base for CRR & SLR","NDTL (Net Demand and Time Liabilities)","NDTL = Demand liabilities + Time liabilities − Inter-bank liabilities.",0,0,3),
    ("rr_04","Reserve Ratios & PSL","#C084FC",2,"PSL — domestic SCBs","40% of ANBC","Priority Sector Lending total. Sub-targets: Agriculture 18%, Micro enterprises 7.5%, Weaker sections 12%.",0,0,4),
    ("rr_05","Reserve Ratios & PSL","#C084FC",2,"Agriculture PSL sub-target","18% of ANBC","Of which ≥10% must go to Small & Marginal Farmers specifically.",0,0,5),
    # Banking Regulation
    ("brk_01","Banking Regulation & Asset Quality","#F28B82",3,"NPA trigger","90 days overdue","Interest/installment unpaid for 90 days → Sub-Standard NPA.",0,1,1),
    ("brk_02","Banking Regulation & Asset Quality","#F28B82",3,"NPA categories","Sub-standard → Doubtful → Loss","Sub-standard (<12 months) → Doubtful (12–36 months) → Loss (>3 yrs).",0,0,2),
    ("brk_03","Banking Regulation & Asset Quality","#F28B82",3,"CRAR minimum (India)","9% (Basel III global: 8%)","RBI mandates 9%. With CCB (2.5%) → effective minimum = 11.5%.",0,0,3),
    ("brk_04","Banking Regulation & Asset Quality","#F28B82",3,"Stressed assets","Gross NPA + Restructured Standard Assets","Broader than GNPA. Captures restructured loans that avoided NPA classification.",0,0,4),
    ("brk_05","Banking Regulation & Asset Quality","#F28B82",3,"PCA triggers","Net NPA > 6%; CRAR below threshold; ROA < 0 for 2 yrs","Prompt Corrective Action. Any one trigger → restrictions on dividends, lending, branches.",0,0,5),
    ("brk_06","Banking Regulation & Asset Quality","#F28B82",3,"IBC CIRP timeline","180 + 90 = 270 days max","Insolvency & Bankruptcy Code 2016. Time-bound NCLT process to maximise creditor recovery.",0,0,6),
    # Payment Infrastructure
    ("pay_01","Payment Infrastructure","#81C995",4,"RTGS","Min ₹2 lakh · Real-time · 24×7 · RBI","Real Time Gross Settlement. Instant gross settlement. No upper limit.",0,0,1),
    ("pay_02","Payment Infrastructure","#81C995",4,"NEFT","No minimum · 48 half-hourly batches · 24×7 · RBI","Deferred Net Settlement. Available 24×7 since Dec 2019.",0,0,2),
    ("pay_03","Payment Infrastructure","#81C995",4,"NPCI operates","UPI, IMPS, RuPay, NACH, FASTag, AePS, BBPS","Exam trap: RTGS and NEFT are RBI; UPI/IMPS etc. are NPCI.",0,0,3),
    ("pay_04","Payment Infrastructure","#81C995",4,"e-RUPI","Digital voucher — NOT CBDC","Person/purpose-specific prepaid e-voucher for targeted DBT. NPCI. Aug 2021.",0,0,4),
    ("pay_05","Payment Infrastructure","#81C995",4,"Digital Rupee (e₹)","CBDC — Central Bank Digital Currency","Legal tender issued by RBI. Retail pilot Nov 2022, Wholesale Dec 2022.",0,0,5),
    ("pay_06","Payment Infrastructure","#81C995",4,"NACH","Bulk recurring: salary/pension/EMI/utilities","National Automated Clearing House (NPCI). Replaced ECS.",0,0,6),
    # Fiscal Framework
    ("fis_01","Fiscal Framework","#FDD663",5,"GFD formula","Total Expenditure − Revenue Receipts − Non-debt Capital Receipts","Gross Fiscal Deficit = total borrowing requirement.",0,0,1),
    ("fis_02","Fiscal Framework","#FDD663",5,"GFD — FY26-27 BE","4.3% of GDP · ₹16,95,768 cr","Down from 4.4% (FY25-26 RE) and 4.8% (FY24-25 actual).",0,1,2),
    ("fis_03","Fiscal Framework","#FDD663",5,"Revenue Deficit — FY26-27 BE","1.5% of GDP","Revenue Expenditure − Revenue Receipts.",0,0,3),
    ("fis_04","Fiscal Framework","#FDD663",5,"Primary Deficit — FY26-27 BE","0.7% of GDP","GFD − Interest Payments. Declining (was 2.5% in FY22).",0,0,4),
    ("fis_05","Fiscal Framework","#FDD663",5,"Capital Expenditure — FY26-27 BE","₹12.21 lakh crore (+11.5%)","Highest ever. Effective capex = ₹17.1 lakh crore.",0,0,5),
    ("fis_06","Fiscal Framework","#FDD663",5,"States' share (16th FC)","41% (unchanged from 15th FC)","16th FC Chair: Dr Arvind Panagariya. Report tabled Feb 1, 2026.",0,0,6),
    ("fis_07","Fiscal Framework","#FDD663",5,"FRBM / debt anchor","GFD ≤ 3% · Debt: 50% ± 1% by 2031","Centre at 4.3%. 16th FC recommends 3.5% by 2030-31.",0,0,7),
    ("fis_08","Fiscal Framework","#FDD663",5,"Interest payments burden","26% of expenditure · 40% of revenue","₹14.04 lakh crore in FY26-27 BE.",0,0,8),
    # Indian Economy
    ("ine_01","Indian Economy — Quick Facts","#9AA0A6",6,"GDP rank by nominal size","6th globally (IMF 2025)","Ahead: USA, China, Germany, Japan, UK. Aspiration: 3rd by early 2030s.",0,0,1),
    ("ine_01b","Indian Economy — Quick Facts","#9AA0A6",6,"GDP rank by PPP","3rd globally (IMF 2025)","Ahead: USA & China.",0,0,2),
    ("ine_02","Indian Economy — Quick Facts","#9AA0A6",6,"Real GDP growth FY26","7.6% (2nd Advance Estimate)","FY25: 7.1%. FY27 projection: 6.8–7.2% (Economic Survey). Base: 2022-23.",0,1,3),
    ("ine_03","Indian Economy — Quick Facts","#9AA0A6",6,"GDP base year","2022-23 (revised from 2011-12)","MoSPI revised base year in FY26.",0,0,4),
    ("ine_04","Indian Economy — Quick Facts","#9AA0A6",6,"Headline CPI — FY26","1.7% · Core CPI: 4.3%","Sharp disinflation from food prices.",0,0,5),
    ("ine_05","Indian Economy — Quick Facts","#9AA0A6",6,"CPI base year","2024 (revised from 2012)","RBI targets CPI Combined at 4% ± 2% under FITF.",0,0,6),
    ("ine_06","Indian Economy — Quick Facts","#9AA0A6",6,"MPC inflation target","4% ± 2% (2%–6%) · FITF","FITF was effective until March 31, 2026. Verify if renewed.",1,0,7),
    ("ine_07","Indian Economy — Quick Facts","#9AA0A6",6,"Gross NPA ratio","2.2% (Sep 2025) — multi-decade low","Peak was 11.2% (March 2018). Bank credit growth: ~11.4% YoY.",0,0,8),
    ("ine_08","Indian Economy — Quick Facts","#9AA0A6",6,"RBI surplus transfer","₹2.68 lakh crore (FY25 — record)","27% higher than FY24 transfer. Under revised ECF (2025 review).",0,0,9),
    ("ine_09","Indian Economy — Quick Facts","#9AA0A6",6,"FI-Index (RBI)","67 in 2025 (↑24.3% since 2021)","Scale 0-100. Access (35%), Usage (45%), Quality (20%). Published annually in July.",0,0,10),
]


def run(conn):
    # INSERT OR REPLACE so content changes in the Python seed propagate to existing DBs
    conn.executemany(
        "INSERT OR REPLACE INTO rbi_key_data "
        "(data_id,section,section_color,section_sort,item_name,item_value,item_note,needs_verify,is_must_know,sort_order) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        _SEED_DATA,
    )
    conn.commit()
