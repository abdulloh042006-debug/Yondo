# Infrastructure

- Local services and an optional full development stack: root [`compose.yaml`](../compose.yaml)
  (`docker compose --profile app up -d --build`).
- Images: [`apps/api/Dockerfile`](../apps/api/Dockerfile) (API, worker, migrations) and
  [`apps/admin/Dockerfile`](../apps/admin/Dockerfile) (panel served by nginx).
- Production requirements and integration checklist: [`docs/deployment.md`](../docs/deployment.md).

Cloud-specific infrastructure (Terraform, Kubernetes manifests) is not included because the
hosting provider has not been chosen yet.
