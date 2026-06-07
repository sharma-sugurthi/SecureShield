<div align="center">

# 🛡️ SecureShield

### Agentic AI — Health Insurance Eligibility & Grievance Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000.svg)](https://nextjs.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL+pgvector-3ECF8E.svg)](https://supabase.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)
[![Cerebras](https://img.shields.io/badge/Cerebras-1M_Tokens/Day-FFCC00.svg)](https://cloud.cerebras.ai)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-AI_Gateway-F38020.svg)](https://developers.cloudflare.com/ai-gateway)

**GenAI-powered health insurance claim eligibility checker & dispute resolution engine for Indian patients.**

> **Claim Guardian Architecture:** 5 Specialized Agents · 18 Custom Tools · Deterministic Decision Engine · Zero-Hallucination Verdicts · **IRDAI 2024 (June) Compliant**

</div>

---

## ✨ Features

| Feature | Description |
|:--------|:------------|
| 📄 **Policy Ingestion** | Upload any insurance PDF → Agent extracts & freezes rules in seconds |
| 🔍 **AI Eligibility Check** | Multi-agent pipeline analyzes patient case against frozen policy rules |
| ⚙️ **Deterministic Verdict** | 6-phase rule engine with zero LLM involvement in financial math |
| 🧠 **Medical Coding** | Automatic ICD-10-PCS code lookup for 500+ procedures |
| 🏙️ **City-Tier Classification** | Auto-applies IRDAI Tier 1/2/3 room rent limits based on location |
| 💰 **Agentic Savings** | `what_if_analyzer` finds cheaper alternatives (e.g., room downgrade tips) |
| ⚖️ **Grievance Agent** | Denied claim? Agent generates PDF report, formal letter & sends grievance email |
| 📚 **IRDAI Precedents** | Searches real Ombudsman/NCDRC rulings to strengthen your dispute |
| 🔐 **User Authentication** | Supabase JWT-based signup/login with protected routes |
| 📧 **Transactional Emails** | Zero-cost Gmail SMTP — Welcome emails & Grievance PDF delivery |
| 🔄 **Multi-Model Failover** | Auto-switches across 10+ models (Cerebras, Groq, Gemini) — never goes down |
| 🎨 **Premium UI/UX** | Dribbble-inspired Deep Indigo dashboard with micro-animations |

---

## 🏗️ Architecture

### Full System Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        📄 INPUT LAYER                                   │
│                                                                         │
│  Insurance Policy PDF  ──►  Patient Case Facts                          │
└─────────┬───────────────────────────┬───────────────────────────────────┘
          │                           │
          ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐
│ 🤖 AGENT 1              │ │ 🤖 AGENT 2              │
│ Policy Agent (ReAct)    │ │ Case Agent (ReAct)      │
│                         │ │                         │
│ ├─ pdf_text_extractor   │ │ ├─ medical_normalizer   │
│ ├─ pdf_table_extractor  │ │ ├─ icd_procedure_lookup │
│ ├─ irdai_regulation_lkp │ │ ├─ city_tier_classifier │
│ └─ rule_validator       │ │ └─ hospital_cost_est    │
│                         │ │                         │
│  LLM: Gemini Flash      │ │  LLM: Cerebras/Groq     │
└──────────┬──────────────┘ └──────────┬──────────────┘
           │  Frozen Rules (JSON)       │  Structured Facts
           │                            │
           ▼                            ▼
┌─────────────────────────────────────────────────────┐
│           ⚙️  DETERMINISTIC DECISION ENGINE          │
│                                                     │
│  ① Exclusions → ② Room Rent → ③ Sub-limits         │
│  ④ Waiting Periods → ⑤ Deductibles → ⑥ Co-pays    │
│                                                     │
│          ⚠️  ZERO LLM — ZERO HALLUCINATION           │
└──────────┬──────────────────────────┬───────────────┘
           │                          │
           ▼                          ▼ (if Denied/Partial)
┌─────────────────────────┐ ┌─────────────────────────┐
│ 🤖 AGENT 3              │ │ 🤖 AGENT 4              │
│ Explanation Agent       │ │ Grievance Agent         │
│                         │ │                         │
│ ├─ clause_explainer     │ │ ├─ search_irdai_prcdnts │
│ ├─ savings_calculator   │ │ ├─ draft_grv_letter     │
│ └─ what_if_analyzer     │ │ ├─ generate_pdf_report  │
│                         │ │ └─ send_grievance_email  │
│  LLM: Cerebras/Groq     │ │                         │
└──────────┬──────────────┘ │  LLM: Cerebras/Groq     │
           │                └──────────┬──────────────┘
           ▼                           ▼
┌─────────────────────────────────────────────────────┐
│                     📋 OUTPUT LAYER                  │
│                                                     │
│  ✅ Verdict    📝 Explanation    💰 Savings Tips     │
│  📄 PDF Report   ✉️ Grievance Letter   📧 Email     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              ⚡ OPTIMIZATION LAYERS                  │
│                                                     │
│  🗄️ Supabase PostgreSQL + pgvector (Semantic Search)│
│  ☁️ Cloudflare AI Gateway (Semantic Caching)        │
│  🔄 6-Provider LLM Failover Chain                   │
│  📧 Gmail SMTP (Zero-Cost Transactional Emails)     │
└─────────────────────────────────────────────────────┘
```

### LangGraph State Machine

```
  ┌─────────┐
  │  START  │
  └────┬────┘
       ▼
┌──────────────┐
│ Load Policy  │  Agent 1: Extract & freeze rules from PDF
└──────┬───────┘
       ▼
┌──────────────┐
│ Analyze Case │  Agent 2: Normalize medical terms, ICD codes, costs
└──────┬───────┘
       ▼
┌──────────────────────────────────────────────┐
│         DECISION ENGINE (Deterministic)       │
│                                              │
│  ┌─────────────┐  ┌─────────────┐            │
│  │ Exclusions  │─►│ Room Rent   │            │
│  └─────────────┘  └──────┬──────┘            │
│                          ▼                   │
│  ┌─────────────┐  ┌─────────────┐            │
│  │ Sub-limits  │─►│ Waiting Per │            │
│  └─────────────┘  └──────┬──────┘            │
│                          ▼                   │
│  ┌─────────────┐  ┌─────────────┐            │
│  │ Deductibles │─►│  Co-pays    │            │
│  └─────────────┘  └─────────────┘            │
└──────────────────────┬───────────────────────┘
                       ▼
                ┌──────────────┐
                │   Verdict    │
                └──────┬───────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     ✅ Approved   ⚠️ Partial   ❌ Denied
          │            │            │
          ▼            └─────┬──────┘
       [DONE]                ▼
                  ┌──────────────────┐
                  │ Grievance Agent  │
                  │ PDF + Letter +   │
                  │ Email Dispatch   │
                  └────────┬─────────┘
                           ▼
                        [DONE]
```

---

## 🤖 Agents & Tools

SecureShield has **5 specialized agents** with **18 custom domain tools**.

### Agent 1 — Policy Agent
> Reads insurance PDF → extracts & validates structured rules

| # | Tool | Purpose |
|:--|:-----|:--------|
| 1 | `pdf_text_extractor` | Extract raw text from insurance PDF (PyMuPDF) |
| 2 | `pdf_table_extractor` | Extract tables from PDF (premium plans, limits) |
| 3 | `irdai_regulation_lookup` | Cross-reference clauses with IRDAI regulations KB |
| 4 | `rule_validator` | Validate and freeze extracted rules into Supabase |

### Agent 2 — Case Agent
> Enriches raw patient case with medical coding and location intelligence

| # | Tool | Purpose |
|:--|:-----|:--------|
| 5 | `medical_term_normalizer` | Expand abbreviations (CABG → Coronary Artery Bypass) |
| 6 | `icd_procedure_lookup` | Map procedure → ICD-10-PCS code (500+ procedures) |
| 7 | `city_tier_classifier` | Auto-classify city → IRDAI Tier 1/2/3 for room rent |
| 8 | `hospital_cost_estimator` | Benchmark procedure cost vs regional market rates |

### Agent 3 — Explanation Agent
> Translates verdict into plain language + finds savings

| # | Tool | Purpose |
|:--|:-----|:--------|
| 9 | `clause_explainer` | Explain each triggered rule in simple language |
| 10 | `savings_calculator` | Find max savings via room downgrade or alternatives |
| 11 | `what_if_analyzer` | Re-run engine with modified params to show options |
| 12 | `audit_trail_logger` | Log every agent step for compliance traceability |

### Agent 4 — Grievance Agent
> Turns a "No" into a formal dispute with legal backing

| # | Tool | Purpose |
|:--|:-----|:--------|
| 13 | `search_irdai_precedents` | Semantic search across 49 IRDAI/NCDRC/SC rulings (pgvector) |
| 14 | `draft_grievance_letter` | LLM drafts formal letter citing IRDAI regulations |
| 15 | `generate_claim_report_pdf` | Professional PDF report with rule-by-rule breakdown |
| 16 | `send_grievance_email` | Emails the grievance PDF directly to the user's inbox |

### Agent 5 — Medical Chat Assistant
> Instant answers to policy & medical queries via 3-tier hierarchy

| # | Tool | Purpose |
|:--|:-----|:--------|
| 17 | `faq_lookup` | Instant keyword search in local `faq.json` (FREE) |
| 18 | `google_vision_ocr` | OCR for medical documents/photos (1000 free req/mo) |

---

## ⚖️ Compliance Guardrails

SecureShield enforces **IRDAI 2024 Master Circular** rules deterministically — no LLM guesswork.

### The "Symbolic Shield" (Why We Don't Hallucinate)

```
LLM Agent             →   Extracts parameters from unstructured PDF
Deterministic Engine  →   Applies EXACT financial math (no LLM)
Guardrail             →   LLM never performs final math or verdict
```

### Key Regulatory Rules Implemented

| Rule | Implementation |
|:-----|:--------------|
| **5-Year Moratorium** | Claims after 60 continuous months cannot be denied for PED/non-disclosure |
| **Waiting Periods** | Procedure-specific validation (e.g., Joint Replacement: 4yr, Cataract: 2yr) |
| **Room Rent Deduction** | Correctly applied per IRDAI PPHI Regulations 2017 (Section 7) |
| **Age-Based Co-pay** | 20% co-payment auto-triggered for patients aged 60+ |
| **City-Tier Limits** | Tier 1/2/3 room rent caps automatically applied based on hospital location |

---

## 🛠️ Tech Stack

| Layer | Technology |
|:------|:-----------|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, LangGraph 0.2 |
| **Frontend** | Next.js 16, React 19, Vanilla CSS (Deep Indigo Design System) |
| **Database** | Supabase PostgreSQL + pgvector (semantic search over 49 IRDAI regulation chunks) |
| **Auth** | Supabase Auth (JWT), protected routes, session management |
| **Email** | Gmail SMTP via `fastapi-mail` (zero-cost transactional emails) |
| **LLM Providers** | Cerebras, Groq, Google Gemini, xAI Grok, OpenRouter (10+ models) |
| **Edge Cache** | Cloudflare AI Gateway (Semantic Caching & Analytics) |
| **PDF Parsing** | PyMuPDF (text + table extraction) |
| **PDF Generation** | ReportLab (professional claim reports) |
| **DevOps** | Docker, GitHub Actions CI/CD (lint + test + build) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- API Keys: [Cerebras](https://cloud.cerebras.ai) (free), [Groq](https://console.groq.com) (free), [Google AI Studio](https://aistudio.google.com/apikey) (free)
- [Supabase](https://supabase.com) project (free tier)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys, Supabase credentials, and Gmail App Password

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install

# Configure Supabase Auth
cat > .env.local << EOF
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
EOF

npm run dev
# Open http://localhost:3000
```

### 3. Docker Deployment

```bash
docker compose up --build
# Backend: http://localhost:8000 | Frontend: http://localhost:3000
```

### 4. Usage

1. Open **http://localhost:3000** → Create an account (check your email for the welcome message!)
2. **Upload Policy** → Drag any health insurance PDF
3. **Check Eligibility** → Submit patient details and watch the 5-agent pipeline
4. **Dispute Claim** → Generate a formal grievance PDF (auto-emailed to you)
5. **Chat Assistant** → Ask any policy or medical question

---

## 📡 API Reference

| Method | Endpoint | Description | Auth |
|:-------|:---------|:------------|:----:|
| `GET` | `/api/health` | Health check | ❌ |
| `POST` | `/api/upload-policy` | Upload & ingest policy PDF | 🔐 |
| `GET` | `/api/policies` | List ingested policies | 🔐 |
| `GET` | `/api/policies/{id}` | Policy details + extracted rules | 🔐 |
| `POST` | `/api/check-eligibility` | Run full agentic eligibility pipeline | 🔐 |
| `GET` | `/api/history` | Recent eligibility check history | 🔐 |
| `GET` | `/api/audit-trail` | Agent audit trail | 🔐 |
| `POST` | `/api/chat` | Medical Chat Assistant (3-tier) | 🔐 |
| `POST` | `/api/dispute-claim` | Run Grievance Agent pipeline | 🔐 |
| `GET` | `/api/download-report/{file}` | Download generated PDF report | 🔐 |
| `POST` | `/api/users/welcome` | Trigger welcome email | 🔐 |

> 🔐 = Requires `Authorization: Bearer <JWT>` or `X-API-Key` header.

---

## 🔐 Security

| Layer | Implementation |
|:------|:--------------|
| **Authentication** | Supabase JWT (RS256/HS256) with cryptographic verification |
| **API Key Fallback** | HMAC-SHA256 generated keys for CLI/MCP tool access |
| **Rate Limiting** | Per-IP sliding window: 30 req/min, 200 req/hr |
| **PDF Validation** | Size check (20MB), magic bytes, MIME type enforcement |
| **Input Sanitization** | Prompt injection detection with compiled regex patterns |
| **Path Traversal** | `os.path.basename()` enforced on all file downloads |

---

## 🏅 Key Design Decisions

| Decision | Why |
|:---------|:----|
| **Deterministic Decision Engine** | Financial verdicts must be reproducible & auditable — LLMs hallucinate numbers |
| **LLM only for NLP tasks** | AI does what it excels at (extraction/explanation); math stays in code |
| **Frozen rules in Supabase** | Once extracted, rules are immutable — same case always → same verdict |
| **18 domain-specific tools** | Purpose-built tools (IRDAI lookup, ICD-10 resolver) beat generic search |
| **Grievance Agent** | Transforms "Denied" into a legally-backed action — unique differentiator |
| **Multi-model failover** | 10+ models across 6 providers — free-tier rate limits are never a showstopper |
| **Zero-cost emails** | Gmail SMTP delivers real emails without any paid service |

---

## 📜 License

Licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">

*5 Agents · 18 Tools · Zero Hallucination · Full IRDAI Compliance*

**Built with ❤️ for Indian patients who deserve transparency in health insurance.**

</div>
