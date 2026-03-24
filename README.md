# 🛡️ SecureShield — Agentic AI Insurance Eligibility Engine

> GenAI-powered health insurance claim eligibility checker for Indian patients.  
> Uses a **neuro-symbolic architecture** with **12 custom tools**, **3 ReAct agents**, and a **deterministic decision engine** for zero-hallucination verdicts.

## Architecture

```
Patient Case → Case Agent (4 tools) → Decision Engine (deterministic) → Explanation Agent (3 tools) → Verdict
                    ↑                                                           ↑
              Knowledge Bases                                            Savings Calculator
         (IRDAI, ICD-10, City Tiers)                                    (What-If Analyzer)
```

### Agent Pipeline
| Agent | Tools | Role |
|-------|-------|------|
| **Policy Agent** | `pdf_text_extractor`, `pdf_table_extractor`, `irdai_regulation_lookup`, `rule_validator` | Extract rules from insurance PDFs |
| **Case Agent** | `medical_term_normalizer`, `icd_procedure_lookup`, `city_tier_classifier`, `hospital_cost_estimator` | Analyze patient cases |
| **Decision Engine** | Deterministic (no LLM) | Apply rules → verdict |
| **Explanation Agent** | `clause_explainer`, `savings_calculator`, `what_if_analyzer` | Generate patient-friendly explanations |
| **Audit Logger** | `audit_trail_logger` | Compliance traceability |

## Tech Stack

- **Backend**: Python, FastAPI, LangGraph, OpenRouter (Gemini/Llama)
- **Frontend**: Next.js 16, React, Vanilla CSS
- **Knowledge Bases**: IRDAI regulations, ICD-10 procedures, Indian city tiers
- **Testing**: 76 tests (pytest)

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
# Set your OpenRouter API key in .env:
# OPENROUTER_API_KEY=sk-or-v1-your-key-here
uvicorn main:app --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### Usage
1. Go to **Settings** → paste the API key shown in the backend console
2. **Upload Policy** → drag a health insurance PDF
3. **Check Eligibility** → fill patient case → get instant verdict

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check (no auth) |
| POST | `/api/upload-policy` | Upload policy PDF |
| GET | `/api/policies` | List all policies |
| POST | `/api/check-eligibility` | Run eligibility check |
| GET | `/api/history` | Past eligibility checks |
| GET | `/api/audit-trail` | Agent audit trail |

All endpoints except `/api/health` require `X-API-Key` header.

## Project Structure
```
SecureShield/
├── backend/
│   ├── agents/          # ReAct agents (policy, case, explanation, orchestrator)
│   ├── engine/          # Deterministic decision engine
│   ├── knowledge/       # Domain KBs (IRDAI, ICD-10, city tiers)
│   ├── tools/           # 12 custom tools (4 modules)
│   ├── models/          # Pydantic schemas
│   ├── db/              # Async SQLite
│   ├── tests/           # 76 tests
│   ├── security.py      # Auth, rate limiting, input sanitization
│   ├── config.py        # Central configuration
│   └── main.py          # FastAPI application
├── frontend/
│   └── src/
│       ├── app/         # Next.js pages (dashboard, upload, check, history, audit, settings)
│       ├── components/  # Sidebar, CoverageRing
│       └── lib/         # API client
└── README.md
```

## License

MIT
