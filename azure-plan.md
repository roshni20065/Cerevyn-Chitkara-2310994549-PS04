# Azure deployment plan — PS04

## Architecture
- **Compute:** Azure App Service for Containers hosts the FastAPI REST API.
- **Image registry:** Azure Container Registry (ACR) stores versioned Docker images tagged with the Git commit SHA.
- **Initial persistence:** SQLite at `/home/data/tickets.db` for a low-cost assessment demonstration. Configure App Service persistent storage. SQLite is suitable for this single-instance prototype, not concurrent multi-instance production use.
- **Production evolution:** Azure Database for PostgreSQL for ticket state/audit records; Azure Monitor and Application Insights for request/error telemetry. Azure Blob Storage is unnecessary for this API's current inputs.
- **Human approval:** API approval endpoint records reviewer, note and timestamp. It never sends email or other external messages.

## Identity and secrets
1. Create a dedicated Entra ID app/service principal for GitHub Actions and configure a federated identity credential for the repository and `production` environment.
2. Grant least-privilege permissions scoped to the target resource group and ACR (AcrPush); avoid subscription-wide Owner rights.
3. Store `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID` as GitHub Actions secrets. Store `AZURE_ACR_NAME` as a repository/environment variable.
4. Use `azure/login@v2` with OIDC (`id-token: write`); do not store client secrets or publish credentials in source control.
5. In production, use a managed identity and ACR managed identity pull where supported. The sample workflow uses ACR credentials to keep setup understandable; prefer managed identity for hardened deployment.

## Manual deployment steps
1. Create an Azure resource group, Azure Container Registry, and Linux Web App configured for a custom container. Choose a small supported plan and region near users.
2. Configure the App Service to pull the image from ACR and enable persistent storage for `/home` if SQLite is used.
3. Configure the GitHub OIDC federated credential and required secrets/variable above.
4. From GitHub Actions, run **Deploy to Azure App Service (manual)** via `workflow_dispatch`; enter the existing Web App name and resource group.
5. Verify `https://<app-name>.azurewebsites.net/health`, then use `/docs` to exercise the API.
6. If deployment fails, inspect the workflow log and App Service container logs; confirm ACR permissions, image tag, port 8000, and App Service configuration.

## Monitoring, security and cost controls
- Use `/health` as a smoke check; enable App Service logs and Application Insights for exceptions, latency and failed requests.
- Keep payload sizes limited; do not put real customer information or secrets in sample tickets. Restrict approval endpoint access with authentication before any real deployment.
- Use a low-cost development tier, stop/delete resources after evaluation, and avoid paid AI endpoints. Azure deployment is optional for assessment scoring.
- SQLite is a prototype compromise: ephemeral/container storage is not a reliable multi-instance database. Move to managed PostgreSQL before real usage.

## Workflow design
- `ci.yml` runs on pushes, pull requests and manual invocation: installs pinned Python dependencies, runs pytest and builds the Docker image.
- `deploy-azure.yml` is manual-only, reruns tests, authenticates with GitHub OIDC, builds/pushes a commit-tagged image and updates an existing App Service.
