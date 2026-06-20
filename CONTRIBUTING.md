# Contributing to PolicyEye

Thank you for your interest in PolicyEye! We are building an agentic AI engine to make health insurance claim eligibility transparent, deterministic, and fair for Indian patients.

Because PolicyEye straddles the line between deep tech (Agentic LLMs) and heavy domain expertise (IRDAI regulations, medical coding), we rely heavily on feedback from both the developer community and domain experts.

---

## 🩺 For Domain Experts (Insurance, Underwriting, Medical)

We built the tech, but we need your expertise to ensure the deterministic engine perfectly aligns with reality. If you are an underwriter, claims adjudicator, doctor, or insurance lawyer, your feedback is the most valuable thing you can contribute.

### How to Help
1. **Test the Live Application**: Run real or hypothetical patient claims through the live PolicyEye application at [https://policyeye.vercel.app](https://policyeye.vercel.app).
2. **Break the Engine**: Try to find edge cases where our deterministic engine or LLM extraction fails (e.g., incorrect room rent calculation, missing a sub-limit).
3. **Submit Feedback**: If you have the direct Google Forms link provided by the author, please submit your detailed feedback there.
4. **Open a GitHub Issue**: If you are comfortable with GitHub, please open an issue using the `[Domain Expert Feedback]` tag in the title. Describe:
   - What the engine got wrong.
   - What the correct regulatory/adjudication outcome should have been.
   - Reference the specific IRDAI master circular or policy clause if possible.

---

## 💻 For Developers

We welcome pull requests for bug fixes, new features, and infrastructure improvements.

### Development Workflow

1. **Fork & Clone**: Fork the repository and clone it locally.
2. **Setup Backend**:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env # Add your API keys here
   uvicorn main:app --reload
   ```
3. **Setup Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. **Branching**: Create a feature branch (`git checkout -b feature/amazing-feature`).
5. **Commit & Push**: Commit your changes and push to your fork.
6. **Pull Request**: Open a Pull Request against the `main` branch.

### Architectural Rules to Maintain
- **Zero Hallucination Guarantee**: Ensure that any new financial or eligibility math is placed strictly in the Python *deterministic engine* (`engine/`), NEVER inside an LLM prompt.
- **Agent Modularity**: If adding a new tool, ensure it follows the strict input/output Pydantic schemas expected by LangGraph.
- **Security**: Do not hardcode API keys. All keys must be routed through `core/config.py`.

Thank you for helping us make healthcare fairer!
