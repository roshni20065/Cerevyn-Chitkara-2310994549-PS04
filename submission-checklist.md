# PS04 submission checklist

The source package includes the implementation, 30 fictional labelled tickets (20 baseline/train and 10 holdout/test), automated tests, Docker packaging, a CI workflow, a manually triggered Azure OIDC deployment workflow, an Azure plan, and a credential-free `.env.example`.

## Complete these account-specific steps before submitting

- [ ] Create a GitHub repository named `Cerevyn-Chitkara-2310994549-PS04` (or the exact naming format requested by the placement team).
- [ ] Push the contents of this project to the repository.
- [ ] Confirm the GitHub Actions CI workflow runs successfully; do not claim a hosted CI pass until the run is green.
- [ ] Run locally: `pytest -q`. Expected result: all tests pass.
- [ ] Run `docker build -t cerevyn-ps04 .` and `docker run --rm -p 8000:8000 -v cerevyn-data:/data cerevyn-ps04`, then check `/health` and `/docs`.
- [ ] Record a 3–5 minute demonstration or add a demo link. Show a normal ticket, ambiguous ticket routed for review, duplicate ID (409), invalid input (422), human approval/audit trail, `/evaluation`, and local Docker run.
- [ ] Add screenshots to `docs/screenshots/` if requested/available and link them from the README. Do not use fabricated screenshots or claim a live Azure deployment unless you performed one.
- [ ] Check the public repository or reviewer access, then submit the GitHub URL and final commit hash/release tag.
- [ ] Disclose AI assistance and any reused code as required by the assessment.

## Honest scope statement

The category classifier is an explainable keyword-scoring baseline, not a trained ML model or an external LLM. The 100% result is on a tiny synthetic 10-ticket holdout and must not be interpreted as production performance. Live Azure deployment and real message sending are not implemented as completed actions.
