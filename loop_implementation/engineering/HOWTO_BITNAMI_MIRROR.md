# How to rotate Bitnami chart mirrors

This runbook describes how Loop mirrors pinned Bitnami charts and their default runtime images into GHCR.

## Why this exists

Bitnami chart and image access policy can change independently from our release cadence.
Mirroring protects installs from upstream pull disruptions and keeps chart dependencies reproducible.

## Mirror destinations

- Helm chart OCI artifacts: ghcr.io/loop-ai/mirrored/bitnami/charts/<chart>:<version>
- Runtime images: ghcr.io/loop-ai/mirrored/bitnami/<chart>:<image-tag>

## Automated mirror job

Workflow: .github/workflows/mirror-bitnami-subcharts.yml

It mirrors these pinned charts:

- postgresql:15.5.38
- redis:20.3.0
- minio:14.10.5
- clickhouse:6.2.18

The job uploads a mirror manifest artifact showing source and destination references.

## Rotation procedure

1. Update pinned versions in infra/helm/loop/Chart.yaml.
2. Run the mirror workflow with workflow_dispatch.
3. Confirm the artifact contains all charts and mirrored images.
4. Validate chart resolution locally:
   - helm dependency build infra/helm/loop
   - helm lint infra/helm/loop
5. Open a PR that includes:
   - Chart.yaml version updates
   - Mirror workflow run URL
   - Any release-note caveats for image tag changes

## Rollback

If a mirrored chart or image is bad:

1. Revert Chart.yaml to last known-good versions.
2. Re-run helm dependency build and helm lint.
3. Re-run the mirror workflow for the last known-good versions.
4. Post incident note in engineering/RUNBOOKS.md under RB-018 if customer traffic was impacted.
