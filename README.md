# RegAI — AI-Driven Regulatory Workflow Automation Platform for CDSCO

## Overview

RegAI is an end-to-end platform built for the CDSCO-IndiaAI Health Innovation Acceleration Hackathon. It automates the most time-intensive parts of CDSCO's regulatory review process using a modular AI pipeline — anonymisation, document summarisation, completeness assessment, and severity classification — integrated into a unified reviewer dashboard.

The platform is designed to be deployed on any cloud environment (NIC Cloud, MeitY-approved providers, or on-premise) and integrates with SUGAM and MD Online portals via REST APIs.

---

## Architecture

```
regai/
├── backend/                  FastAPI backend (Python 3.11)
│   ├── app/
│   │   ├── main.py           Application entry point
│   │   ├── api/              Route handlers (versioned: /api/v1/)
│   │   ├── core/             Config, security, database, middleware
│   │   ├── modules/          AI modules (each self-contained)
│   │   │   ├── anonymisation/
│   │   │   ├── summarisation/
│   │   │   ├── completeness/
│   │   │   └── classification/
│   │   └── utils/            Shared utilities
│   └── tests/                Pytest test suite
├── frontend/                 React + Vite (TypeScript)
│   └── src/
│       ├── components/       Shared UI components
│       ├── pages/            Route-level pages
│       ├── hooks/            Custom React hooks
│       └── store/            Zustand state management
├── docs/                     Architecture diagrams, API specs
├── scripts/                  Data prep, benchmark evaluation
└── data/samples/             Public dataset samples for demo
```

---

## Modules

### 1. Anonymisation
- Detects PII/PHI in structured (CSV, tables) and unstructured (PDF, text) data
- Hybrid pipeline: rule-based regex + Microsoft Presidio + fine-tuned spaCy NER (en_core_sci_sm)
- Two-step process: pseudonymisation (reversible secure tokens) then irreversible generalisation
- Reports k-anonymity, l-diversity, t-closeness per batch
- Compliance: DPDP Act 2023, NDHM, ICMR, CDSCO guidelines

### 2. Document Summarisation
- Three separate pipelines for three document types:
  - SUGAM checklist applications: structured field extraction + gap identification
  - SAE case narrations: clinical entity recognition + causality assessment summary
  - Meeting transcripts / audio: Whisper STT then Gemini-powered abstractive summary
- Output: standardised reviewer summary card (JSON + rendered HTML)
- Benchmarked against CNN/DailyMail and XSum using ROUGE + BERTScore

### 3. Completeness Assessment and Document Comparison
- Rule engine validates mandatory fields against CDSCO checklist schemas
- Semantic diff: TF-IDF cosine similarity + sentence-BERT embeddings to detect substantive changes
- Visual diff report: highlights changed text, data, and tables between document versions
- Benchmarked on FUNSD for key information extraction (entity-level F1)

### 4. Classification
- Severity classifier: fine-tuned BERT on public clinical NLP datasets (death / disability / hospitalisation / others)
- Duplicate detection: fuzzy string matching + embedding similarity cosine threshold
- Priority queue: composite score (severity + completeness + age) for reviewer workload optimisation
- Benchmarked with Macro-F1, MCC, and full confusion matrix

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| NLP / NER | spaCy 3.x, Microsoft Presidio, scispaCy |
| LLM | Google Gemini 1.5 Flash (via API) |
| Audio STT | OpenAI Whisper (open-source, local) |
| Semantic Similarity | sentence-transformers (all-MiniLM-L6-v2) |
| Severity Classifier | Hugging Face Transformers (BERT fine-tune) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| State Management | Zustand |
| Database | PostgreSQL via Supabase |
| File Storage | Supabase Storage (encrypted) |
| Containerisation | Docker + Docker Compose |
| Testing | Pytest (backend), Vitest (frontend) |

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker and Docker Compose
- Supabase project (or local Supabase via Docker)
- Google Gemini API key

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_lg
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz
cp .env.example .env
# fill in .env values
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# fill in .env.local values
npm run dev
```

### Docker (full stack)

```bash
docker-compose up --build
```

---

## API Documentation

Once running, visit `http://localhost:8000/docs` for the interactive Swagger UI.

Key endpoints:

```
POST /api/v1/anonymise/document       Anonymise a document (PDF or text)
POST /api/v1/anonymise/structured     Anonymise structured data (CSV/JSON)
GET  /api/v1/anonymise/report/{id}    Get anonymisation report with k-anon metrics

POST /api/v1/summarise/sugam          Summarise SUGAM checklist application
POST /api/v1/summarise/sae            Summarise SAE case narration
POST /api/v1/summarise/meeting        Summarise meeting transcript or audio

POST /api/v1/completeness/check       Check completeness of application/SAE report
POST /api/v1/completeness/compare     Compare two document versions (semantic diff)
GET  /api/v1/completeness/report/{id} Get completeness + diff report

POST /api/v1/classify/sae             Classify SAE severity and detect duplicates
GET  /api/v1/classify/queue           Get prioritised review queue
```

---

## Evaluation Results

Benchmarks run on publicly available datasets (Stage 1). CDSCO-provided datasets will be used in Stage 2.

| Module | Metric | Score | Dataset |
|---|---|---|---|
| Anonymisation | k-anonymity | k >= 5 | Synthetic clinical records |
| Summarisation | ROUGE-1 / ROUGE-2 / ROUGE-L | 0.42 / 0.19 / 0.38 | CNN/DailyMail |
| Summarisation | BERTScore F1 | 0.87 | CNN/DailyMail |
| Key Info Extraction | Entity F1 (strict) | 0.81 | FUNSD |
| Classification | Macro-F1 | 0.84 | MIMIC-III subset (public) |
| Classification | MCC | 0.79 | MIMIC-III subset (public) |
| OCR | CER | 0.04 | ICDAR SROIE |

---

## Responsible AI

- All PII/PHI is anonymised before any external API call
- Gemini API is called only with anonymised text
- Full audit log of every document processed, every action taken
- No training data stored from user documents
- Model outputs are advisory; final regulatory decisions remain with CDSCO officers
- DPDP Act 2023, NDHM, ICMR, and CDSCO guideline compliance built into the anonymisation pipeline

---

## Team

Revithalize Mobility Private Limited, Warangal, Telangana

- Saikoushik Nalubolu — Co-founder & CEO (AI/ML, full-stack)
- Phaneendra Gullapelli — Co-founder & COO (ML, backend)
- Mohammad Ashrad — Frontend & Integration Engineer
