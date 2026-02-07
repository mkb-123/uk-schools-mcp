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

---

## Now Accessible via `query_dataset`

The following data sources are now queryable via the `get_dataset_metadata` and `query_dataset` tools. Use the workflow: `search_education_statistics` → `get_publication_datasets` → `get_dataset_metadata` → `query_dataset`.

### 6. School Performance Data (KS2/KS4/KS5)
Available through EES API. Search for publications on "KS2 results", "GCSE results", or "A-level results".

**Data available:**
- KS2: Reading, writing, maths scores; expected standard %; higher standard %
- KS4 (GCSE): Attainment 8, Progress 8, EBacc entry/achievement, Grade 5+ in English & maths
- KS5 (A-level): Average point score, A*-B %, value added

### 7. School Applications & Offers (Admissions)
Available through EES API. Search for "applications and offers".

**Data available:**
- Number of first, second, third preferences by school
- Number of offers made by preference rank
- Historical data back to 2014

### 8. Pupil Absence Data
Available through EES API. Search for "pupil absence".

**Data available:**
- Overall absence rate, persistent absence rate
- Authorised vs unauthorised absence
- Breakdown by reason

### 9. Exclusions Data
Available through EES API. Search for "exclusions and suspensions".

**Data available:**
- Permanent exclusion rate, suspension rate
- Breakdown by reason, ethnicity, SEN status, FSM eligibility

### 10. School Workforce Data
Available through EES API. Search for "school workforce".

**Data available:**
- Teacher numbers, pupil-teacher ratios
- Teacher qualifications, turnover, vacancy rates

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
| Ofsted inspection grades | Done | `get_ofsted_ratings` |
| Performance (KS2/KS4/KS5) | Accessible | Via `query_dataset` with EES |
| Applications & offers | Accessible | Via `query_dataset` with EES |
| Absence data | Accessible | Via `query_dataset` with EES |
| Exclusions data | Accessible | Via `query_dataset` with EES |
| Workforce data | Accessible | Via `query_dataset` with EES |
| Financial benchmarking | Not feasible | No public API |
| PAN data | Not feasible | Fragmented across 150+ LA websites |
