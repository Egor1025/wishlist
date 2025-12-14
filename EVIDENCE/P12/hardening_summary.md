# P12 hardening summary

## Dockerfile
- Base image pinned (no :latest)
- Non-root user
- Reduced privileges (no-new-privileges in compose), dropped caps, read-only rootfs with tmpfs

## Notes
- Reports are attached as artifacts and stored in EVIDENCE/P12/
