# Infrastructure

Reserved for deployment and infrastructure configuration. Local development dependencies are
currently defined in the root [`compose.yaml`](../compose.yaml).

- [`deploy/`](deploy/README.md): public **demo** image (API + web in one container) for free hosting; not production.
- [`jobs/`](jobs/README.md): scheduling for `python -m yondo_api.jobs` (booking expiry + account erasure).
