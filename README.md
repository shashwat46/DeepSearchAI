# People DeepSearch AI – MVP

DeepSearch AI is an MVP backend for background check and identity discovery. Given minimal inputs (name, email, phone, username, optional free-text context), it gathers public evidence, synthesizes a draft profile using LLMs, and performs a judge pass to validate and score the final profile.

## What it does

- Accepts person identifiers and optional free-text context
- Plans (optional) a search strategy via LLM
- Runs parallel tools (APIs + scrapers) to collect evidence
- Synthesizes a coherent profile via LLM
- Performs a judge pass via LLM to validate, score confidence, and add provenance
- Returns candidates (shallow) and a judged FinalProfile (deep)

## High-level architecture

![High-level architecture](SystemDesign.png)



## Key components

- Orchestrator (`services/orchestrator.py`)
  - Merges inputs, infers region, geocodes, runs tools in parallel via `ToolRegistry`, caches/uses best links, aggregates evidence, calls LLM agent and judge.
- Tool Registry (`tools/registry.py`)
  - Selects applicable tools per stage (shallow/deep). Executes async in parallel.
- Tools (in `tools/`)
  - Web scrapers (GitHub, LinkedIn, X, Hyperbrowser), OSINT (GHunt, Holehe, Ignorant), Data APIs (Numverify, ESPY).
- LLM Agent (`services/ai_agent.py`)
  - Parses free-text to structure, synthesizes profile.
- Judge (`services/judge.py`)
  - Validates profile using raw evidence, outputs confidence and provenance.
- Planner (`services/planner.py`)
  - Optional plan generation based on tool manifest and inputs.
- Geocoding/Region (`services/geocoding.py`, `services/region.py`)
  - Normalizes location context.

## API Endpoints

- POST `/search` → shallow results: candidates + raw evidence
- POST `/profile/enrich` → deep results: judged `FinalProfile` + raw evidence
- POST `/plan/search` → optional LLM-generated plan for shallow
- POST `/plan/enrich` → optional LLM-generated plan for deep
- GET `/` → serves minimal demo UI in `static/index.html`

Request payloads follow `schemas.py` (`SearchQuery`, `Candidate`). Responses use `ShallowResponse`, `DeepResponse`, `PlanResponse`.

## Running locally

1. Python 3.12+ recommended. Create and activate venv.
2. Install deps:
   - `pip install -r requirements.txt`
3. Environment:
   - `GEMINI_API_KEY` (required for LLM features)
   - Optional: `ESPY_ENABLE=true` and ESPY creds if you have them
   - Optional LLM model envs:
     - `GEMINI_PLANNER_MODEL` (default: `gemini-2.5-flash`)
     - `GEMINI_SYNTHESIS_MODEL` (default: `gemini-2.5-pro`)
     - `GEMINI_JUDGE_MODEL` (default: `gemini-2.5-pro`)
4. Start API:
   - `uvicorn main:app --reload`
5. Visit:
   - `http://localhost:8000` for demo front-end
   - Use `test_api.py` for a simple API walk-through

## Data flow summary

- Shallow: Inputs → normalize/geo/region → select+run tools → candidates + raw
- Deep: Candidate → run tools (+ targeted verifies) → synthesize (LLM) → judge (LLM) → final profile

## Notes

- ESPY tools are optional; gated by `ESPY_ENABLE`.
- Hyperbrowser scrape/extract/crawl are used when URLs are available or inferred.
- Judge pass enforces evidence-first policy, resolves conflicts, assigns confidences, and records provenance.

## Tools used

- Holehe CLI: Email enumeration across services; fast signal for account presence.
- GHunt: Google ecosystem OSINT (accounts, artifacts) from public signals.
- Ignorant CLI: Phone/email checks for service usage signals.
- Hyperbrowser (Scrape/Extract/Crawl): Headless browser automation with extraction, crawling, and markdown scraping; supports proxy/stealth.
- GitHub + GitHub Extras: User/org discovery, repo heuristics, and profile enrichment.
- LinkedIn Finder + Verify: SERP-based discovery and verification via scraping adapter.
- X (Twitter) Finder + Verify: SERP-based discovery and verification for X profiles.
- Numverify: Phone validation and metadata enrichment.
- ESPY Suite (optional): Email/phone/name deep enrichment, court records, deep web.

Environment hints: `GEMINI_API_KEY`, `NUMVERIFY_API_KEY`, `HYPERBROWSER_API_KEY`, `ESPY_API_KEY`, `SCRAPINGDOG_API_KEY`, `SERPAPI_API_KEY`, plus feature toggles like `LINKEDIN_*`, `X_*`, `ESPY_ENABLE`.

## Extensions / Enterprise software sources

| Vendor | Enterprise price | Included usage (enterprise) | Notes |
|---|---:|---|---|
| People Data Labs | Custom, ~$2,500+/month commonly cited | Custom credit volumes for person/company/IP; premium fields; dedicated support; custom integrations | Official page shows plans but not pricing; multiple sources place enterprise starting “around $2,500/month” with effective person-credit costs trending toward ~$0.20 at high volume. Annual enterprise often spans ~$30k–$100k+. |
| Intelligence X | €20,000+/year (Enterprise) | 5,000+ selector searches/day; 2,500+ phonebook lookups/day; unlimited alerts; multi-user | Other tiers: API at €7,000/year with 500 selectors/day; Identity Portal at €10,000/year; enterprise raises daily caps and access scope. |
| Pipl | Custom (contact sales) | API person/identity search with enterprise SLAs; quotas undisclosed publicly | Public enterprise pricing not listed; third-party overviews suggest four-figure monthly minimums with per-search or volume-based pricing, but figures vary and are negotiated. Treat as “custom, likely 4–5 figures monthly” depending on scale. |
| CrustData | Custom (contact sales) | Real-time API and/or flat-file datasets; refresh cadence and user seats negotiated | Trackers indicate no free plan; some products mention entry paid tiers for limited searches, but enterprise is quote-based, often combining bulk datasets plus API for deltas. |