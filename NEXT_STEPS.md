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

### 4. Ofsted Full Inspection Data - DONE
- **Client:** `clients/ofsted.py`
- **Provides:** Report URL generation, rating formatting, and full inspection data (overall effectiveness, quality of education, behaviour & attitudes, personal development, leadership & management, early years, sixth form grades, plus previous inspection grades, dates, and types)
- **Source:** Ofsted Management Information Excel files downloaded from GOV.UK via Content API
- **Tool:** `get_ofsted_ratings` - Look up inspection grades by URN
- **Notes:** Data cached monthly as parquet. Uses GOV.UK Content API to find download URL, with HTML fallback.

### 5. EES Dataset Querying - DONE
- **Tools:** `get_dataset_metadata` + `query_dataset`
- **Provides:** Full access to query any DfE Explore Education Statistics dataset with filters, indicators, time periods, geographic levels, and locations
- **Enables:** School-level data on absence, exclusions, performance, applications & offers, workforce, and more
- **Notes:** Works with the existing EES client. The workflow is: search_education_statistics → get_publication_datasets → get_dataset_metadata → query_dataset

### 6. EES Topic Discovery - DONE
- **Tools:** `list_ees_topics` + `discover_dataset`
- **Provides:** Registry of 23 education data topics with one-step dataset discovery
- **Topics:** absence, exclusions, KS2/KS4/KS5 performance, SEND, school characteristics, FSM, school capacity, admission appeals, destinations, children looked after/in need, MAT performance, school funding, LA expenditure, FE/skills, early years, NEET, elective home education
- **Notes:** Replaces the manual 4-step workflow with a single `discover_dataset` call that auto-finds the right publication and lists available datasets with IDs

---

## Now Accessible via `discover_dataset` + `query_dataset`

All 23 topics below are discoverable via `list_ees_topics` and `discover_dataset`, then queryable via `get_dataset_metadata` + `query_dataset`.

### School Performance
- **`ks2_performance`** - KS2 SATs: reading, writing, maths scores, expected/higher standard %
- **`gcse_performance`** - GCSEs: Attainment 8, Progress 8, EBacc, Grade 5+ English & maths
- **`a_level_performance`** - A-levels: average point score, A*-B %, value added
- **`mat_performance`** - Multi-academy trust KS2/KS4/KS5 performance measures

### Pupil Welfare
- **`absence`** - Overall/persistent absence rates, authorised vs unauthorised, by reason
- **`exclusions`** - Permanent exclusion and suspension rates, by reason/ethnicity/SEN/FSM
- **`children_looked_after`** - Children in care numbers, placements, outcomes
- **`children_in_need`** - Educational outcomes for CIN/CLA (KS2, KS4, absence, exclusions)

### Pupil Demographics
- **`school_pupils_characteristics`** - Per-school pupil headcount by demographics, class sizes
- **`sen`** - SEND: EHC plans, SEN support, type of need, demographics
- **`free_school_meals`** - FSM eligibility rates at school/LA/national level

### Admissions & Capacity
- **`applications_offers`** - Preference applications, offers by rank, historical data
- **`admission_appeals`** - Appeals lodged, heard, upheld by LA and phase
- **`school_capacity`** - School capacity, pupil forecasts, planned place changes

### Workforce & Finance
- **`workforce`** - Teacher numbers, pupil-teacher ratios, turnover, vacancies, pay
- **`school_funding`** - Per-pupil funding: DSG, pupil premium, UIFSM
- **`la_school_expenditure`** - LA-maintained school income/expenditure (CFR)

### Post-16 & Destinations
- **`destinations`** - 16-18 progression to HE, apprenticeships, employment
- **`neet`** - Young people not in education, employment or training
- **`further_education`** - FE learner numbers, apprenticeships, adult skills

### Early Years
- **`early_years`** - Childcare provider numbers, types, costs, workforce
- **`early_years_foundation`** - Reception year assessment outcomes (EYFSP)

### Other
- **`elective_home_education`** - Children registered for EHE by LA

---

## Not Yet Implemented

### 11. School Financial Benchmarking
**Feasibility: LOW** - No public API

The [Schools Financial Benchmarking](https://schools-financial-benchmarking.service.gov.uk/) service shows per-pupil spending, income/expenditure breakdowns, and comparisons between similar schools. However:
- There is **no public API**
- Data is only available through the web interface

**Workaround:** Some financial data is available through Explore Education Statistics (search for "school funding" or "school finance") and can be queried via `query_dataset`.

### 12. Published Admission Numbers (PAN)
**Feasibility: LOW** - No centralised data source

PAN data is **not included in GIAS** and is fragmented across 150+ local authority websites. Each LA publishes their own admission arrangements.

**Workaround:** GIAS includes `SchoolCapacity` (total capacity) which can serve as a proxy.

---

## Implementation Status

| Source | Status | Tool(s) |
|--------|--------|---------|
| GIAS (school data) | Done | `search_schools`, `get_school_details`, `find_schools_near_postcode`, `compare_schools` |
| Postcodes.io | Done | Used by `find_schools_near_postcode` |
| EES (publication browse) | Done | `search_education_statistics`, `get_publication_datasets` |
| EES (dataset querying) | Done | `get_dataset_metadata`, `query_dataset` |
| EES (topic discovery) | Done | `list_ees_topics`, `discover_dataset` (23 topics) |
| Ofsted inspection grades | Done | `get_ofsted_ratings` |
| 23 EES datasets | Accessible | Via `discover_dataset` + `query_dataset` |
| Financial benchmarking | Not feasible | No public API |
| PAN data | Not feasible | Fragmented across 150+ LA websites |
