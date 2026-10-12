# Cerevyn PS04 — Azure Support Ticket Automation

**Problem ID:** PS04 — Azure Support Ticket Automation  
**Candidate:** Roshni Singh  
**Roll number:** 2310994549  
**Branch:** Electronics and Communication Engineering (ECE)

## 1. Problem and approach
This project provides a REST API that accepts fictional support tickets and returns a category, priority, assigned team, short summary and proposed response. It stores tickets in SQLite, rejects duplicate IDs, routes uncertain classifications for human review, and records approvals in an audit log. Approval marks a draft as `draft_ready`; the API does **not** send email or contact customers.

The initial classifier is a transparent keyword-scoring baseline. It is deterministic and requires no API key, network call or paid model. It is an AI-assisted workflow prototype rather than a trained machine-learning model. A zero-match or tied/uncertain message is flagged for review. Confidence is a heuristic score, not a calibrated probability.

## 2. Category, priority and routing policy
- **Billing → Finance Support:** invoices, charges, refunds, receipts, subscriptions and payments.
- **Technical → Technical Support:** bugs, crashes, APIs, timeouts, uploads, downloads and server failures.
- **Access → Identity & Access Support:** login, password, account lockout, permissions and authentication.
- **General → Customer Support:** questions, documentation, hours and general feedback.
- **Urgent:** explicit urgent/critical/production-down/security/data-leak terms.
- **High:** blocked work, multi-user impact, failed payment, duplicate charge or data-loss terms.
- **Low:** minor requests, suggestions and non-urgent questions; otherwise **Medium**.
- If no category keyword matches or category scores tie, `needs_review=true`. All draft responses require human approval before they become `draft_ready`.

This policy is a small explainable baseline. Real deployment should replace it with a reviewed model/ruleset and role-based authentication.

## 3. Repository layout
```text
app/main.py                      FastAPI routes, rules, SQLite persistence
sample_data/tickets.json         30 fictional labelled tickets: 20 train / 10 test
tests/test_api.py                API, validation, duplicate, review and evaluation tests
Dockerfile                       Reproducible container
requirements.txt                 Pinned direct dependencies
.env.example                     Credential-free local configuration example
docs/azure-plan.md               Azure architecture, identity, deployment and cost plan
.github/workflows/ci.yml         CI tests and Docker build
.github/workflows/deploy-azure.yml Manual OIDC Azure deployment
```

## 4. Run locally (Python beginner path)
Python 3.12 is recommended.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Start the API from the project root
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation. Health check: `http://127.0.0.1:8000/health`. SQLite file `tickets.db` is created locally on first request.

## 5. Example request
In `/docs`, choose `POST /tickets` and use:
```json
{
  "ticket_id": "T-2001",
  "message": "I was charged twice for my monthly invoice and need help."
}
```
Expected key outputs include `category: "Billing"`, `priority: "High"`, `assigned_team: "Finance Support"`, a draft response, `message_sent: false`, and a status that requires approval or review. The exact confidence value is a heuristic.

Other endpoints:
- `GET /health` — service status.
- `POST /tickets` — classify and create a ticket; duplicate IDs return HTTP 409.
- `GET /tickets` and `GET /tickets/{ticket_id}` — list/retrieve tickets.
- `POST /tickets/{ticket_id}/approve` — record human approval.
- `GET /tickets/{ticket_id}/audit` — view creation and approval events.
- `GET /evaluation` — report accuracy against the frozen 10-item synthetic test split.

Approval example:
```json
{
  "reviewer": "support-supervisor",
  "note": "Reviewed the proposed response"
}
```

## 6. Tests and evaluation
```bash
pytest -q
```
The tests cover health, category and priority assignment, draft generation, duplicate ticket rejection, invalid input, ambiguous-ticket review, approval/audit, unknown ticket, repeat approval and the ten-case holdout endpoint. The `sample_data/tickets.json` test split is kept separate from the 20 baseline examples. The current deterministic evaluation returns 10/10 correct (100%) on the synthetic holdout; a regression test checks that result. This is a small, synthetic baseline and must not be presented as production accuracy. Run `GET /evaluation` to reproduce the measurement.

## 7. Docker
```bash
docker build -t cerevyn-ps04 .
docker run --rm -p 8000:8000 -v cerevyn-data:/data cerevyn-ps04
```
Then visit `http://127.0.0.1:8000/docs`. The named volume preserves the SQLite database between container runs.

## 8. GitHub and Azure
- `.github/workflows/ci.yml` installs dependencies, runs tests and builds the Docker image on pushes and pull requests.
- `.github/workflows/deploy-azure.yml` is a **manual** deployment workflow. Configure GitHub OIDC, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` secrets and `AZURE_ACR_NAME` variable, then provide an existing App Service name/resource group.
- See [`docs/azure-plan.md`](docs/azure-plan.md) for architecture, permissions, deployment, monitoring and cost controls. Live deployment is optional.

## 9. Demo plan (3–5 minutes)
1. **0:00–0:30:** Explain PS04 and the rule-based baseline; show the project tree.
2. **0:30–1:15:** Open `/docs`, submit a Billing ticket, and point out category, priority, team, summary and draft.
3. **1:15–2:00:** Submit an unclear message and show `needs_review`; replay an existing ID and show HTTP 409; submit invalid input and show validation error.
4. **2:00–2:45:** Approve a ticket and show `draft_ready` plus its audit log. Emphasize no email is sent.
5. **2:45–3:30:** Run `pytest -q` and open `/evaluation` to show held-out accuracy.
6. **3:30–4:30:** Build/run Docker and show CI workflow plus Azure plan.

**Optional evidence to add if your evaluator requests it:** save screenshots in `docs/screenshots/` and add a demo video link here. Do not claim a cloud deployment or CI run unless you actually complete it. The source archive can be reviewed and run locally without cloud deployment.

See [`docs/submission-checklist.md`](docs/submission-checklist.md) for the final GitHub, CI, Docker, demo and handover steps. The demo script above is a plan, not a recording; add your own recording/link and real screenshots before submission if required.

## 10. Limitations and contribution
- Keyword rules can miss synonyms and may misclassify messages with multiple topics.
- Confidence is a heuristic; no model training or external LLM is used.
- SQLite is intended for a single-instance demo; production should use managed database storage and authentication/authorization.
- Sample records are fictional. No real email/WhatsApp action occurs.
- Implementation and documentation were prepared with AI assistance; review, run, understand and disclose any changes or reused code according to the assessment instructions.

**Final submission checklist:** automated tests are included; run `pytest -q` locally and confirm the result before submitting. Before submitting, run `pytest -q` on your own machine, ensure the source files are included, and follow any evaluator-specific requirement for a GitHub repository URL, screenshots, demo video, or deployment. This archive does not claim a live Azure deployment or a GitHub Actions run.
