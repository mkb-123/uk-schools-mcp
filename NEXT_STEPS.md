# Next Steps - Additional Data Sources

This document outlines data sources that could enhance the UK Schools MCP server, their feasibility, and suggested implementation approaches.

## Implemented

### 1. GIAS (Get Information About Schools) - DONE
- **Client:** `clients/gias.py`
- **Source:** Daily bulk CSV from `ea-edubase-api-prod.azurewebsites.net`
- **Provides:** All ~65k establishments with 120+ fields (name, URN, type, phase, address, capacity, pupils, head teacher, SEN provision, religious character, admissions policy, lat/lng coordinates, etc.)
- **Notes:** CSV is ~30MB, cached locally, refreshed daily. No authentication required.

### 2. Postcodes.io - DONE
- **Client:** `clients/postcodes.py`
- **Source:** REST API at `api.postcodes.io`
- **Provides:** UK postcode geocoding (lat/lng), reverse geocoding, validation
- **Notes:** Free, no auth, open source. Used for `find_schools_near_postcode` tool.

### 3. Explore Education Statistics API - DONE
- **Client:** `clients/ees.py`
- **Source:** REST API at `api.education.gov.uk/statistics/v1`
- **Provides:** Publication search and dataset listing for DfE statistics (performance, absence, exclusions, applications & offers, workforce, etc.)
- **Notes:** Free, no auth. Currently supports browsing publications and listing datasets. Could be extended to query specific datasets with filters.

### 4. Ofsted - PARTIAL
- **Client:** `clients/ofsted.py`
- **Provides:** Report URL generation from URN, rating code formatting
- **Limitation:** Full inspection data (ratings, grades, dates) requires downloading Ofsted Management Information files (Excel/ODS from GOV.UK), which are published monthly and change URL with each release.

---

## Not Yet Implemented - Recommended Next Steps

### 5. Ofsted Full Inspection Data
**Feasibility: MEDIUM** - Requires scraping GOV.UK page for download link

The Ofsted management information dataset contains detailed inspection outcomes for all state-funded schools, including:
- Overall effectiveness grade (1-4)
- Grades for each inspection judgement area
- Inspection date and type
- Previous inspection results (trajectory)

**How to implement:**
1. Scrape the [Ofsted MI page](https://www.gov.uk/government/statistical-data-sets/monthly-management-information-ofsteds-school-inspections-outcomes) to find the latest download link
2. Download the Excel/ODS file (changes URL monthly)
3. Parse with polars and cache locally alongside GIAS data
4. Join with GIAS data on URN for enriched school details
5. Add a `get_ofsted_rating` tool

**Key fields available:**
- URN, school name, LA
- Overall effectiveness (current and previous)
- Quality of education, behaviour & attitudes, personal development, leadership & management
- Early years / sixth form provision grades
- Date of inspection, inspection type
- Whether the school has been placed in special measures or given a serious weakness notice

### 6. School Performance Data (Find & Compare)
**Feasibility: MEDIUM** - Available through EES API

Key Stage 2 (SATs), GCSE, and A-level results are published via the Explore Education Statistics API. The current `search_education_statistics` tool can find these publications. Next step is to:

1. Identify the specific publication/dataset IDs for KS2, KS4 (GCSE), and KS5 (A-level) results
2. Build pre-configured queries that fetch school-level performance data by URN
3. Add a `get_school_performance` tool

**Data available:**
- KS2: Reading, writing, maths scores; expected standard %; higher standard %
- KS4 (GCSE): Attainment 8, Progress 8, EBacc entry/achievement, Grade 5+ in English & maths
- KS5 (A-level): Average point score, A*-B %, value added

**Source:** `https://www.find-school-performance-data.service.gov.uk/`

### 7. School Applications & Offers (Admissions)
**Feasibility: HIGH** - Structured CSV via EES API

School-level data on applications and offers is published annually:
- Number of first, second, third preferences by school
- Number of offers made by preference rank
- Historical data back to 2014
- National Offer Day statistics

**How to implement:**
1. The dataset ID is available through the EES API (search "applications and offers")
2. Download the 61MB CSV directly: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/65b074b6-b6df-419b-af04-dd0f19865b59/csv`
3. Parse and cache similarly to GIAS data
4. Add a `get_school_admissions` tool that shows preference/offer data for a given URN

### 8. School Financial Benchmarking
**Feasibility: LOW** - No public API

The [Schools Financial Benchmarking](https://schools-financial-benchmarking.service.gov.uk/) service shows per-pupil spending, income/expenditure breakdowns, and comparisons between similar schools. However:
- There is **no public API**
- Data is only available through the web interface
- Some underlying data may be available via FOI requests or data.gov.uk

**Alternative:** The DfE publishes some financial data through Explore Education Statistics (search for "school funding" or "school finance"). This could be integrated via the existing EES client.

### 9. Pupil Absence Data
**Feasibility: HIGH** - Available through EES API

Absence data includes:
- Overall absence rate
- Persistent absence rate (10%+ sessions missed)
- Authorised vs unauthorised absence
- Breakdown by reason

**How to implement:** Use the EES client to query the "Pupil absence in schools in England" publication. Add a `get_school_absence` tool.

### 10. Exclusions Data
**Feasibility: HIGH** - Available through EES API

Exclusion data includes:
- Permanent exclusion rate
- Fixed-period (suspension) rate
- Breakdown by reason, ethnicity, SEN status, FSM eligibility

**How to implement:** Use the EES client to query the "Permanent exclusions and suspensions in England" publication. Add a `get_school_exclusions` tool.

### 11. School Workforce Data
**Feasibility: HIGH** - Available through EES API

Workforce data includes:
- Teacher numbers and pupil-teacher ratios
- Teacher qualifications
- Staff turnover and vacancy rates
- Support staff numbers

**How to implement:** Use the EES client to query the "School workforce in England" publication. Add a `get_school_workforce` tool.

### 12. Published Admission Numbers (PAN)
**Feasibility: LOW** - No centralised data source

PAN data is **not included in GIAS** and is fragmented across 150+ local authority websites. Each LA publishes their own admission arrangements.

**Workaround:** GIAS does include `SchoolCapacity` (total capacity) which can serve as a proxy. Some LAs publish PAN data as open data (e.g., York), but there is no national dataset.

---

## Implementation Priority

| Priority | Source | Effort | Impact |
|----------|--------|--------|--------|
| 1 | Ofsted full inspection data | Medium | High - inspection grades are the most-asked-about data |
| 2 | School performance (KS2/KS4/KS5) | Medium | High - exam results are critical for school comparison |
| 3 | Applications & offers | Low | Medium - useful for understanding school popularity |
| 4 | Absence data | Low | Medium - key indicator of school culture |
| 5 | Exclusions data | Low | Medium - important for understanding behaviour policies |
| 6 | Workforce data | Low | Low-Medium - less commonly requested |
| 7 | Financial benchmarking | High | Low - no public API available |
| 8 | PAN data | Very High | Low - fragmented across 150+ LA websites |
