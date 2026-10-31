# SchoolSmartEYE — Engineering & Security Audit

**Audit date:** 2026-10-31  
**Repository:** `AbuRashad/SchoolSmartEYE`  
**Branch reviewed:** `feat/native-school-intelligence-engine`  
**Scope:** source review of the FastAPI backend, React/Vite frontend, Docker configuration, GitHub Actions, tenant authorization, camera ingestion, analytics provenance, seed data, and Lovable UI-transfer boundary.

## Executive summary

The repository has a substantial test suite and an established school-tenant authorization layer. The latest pre-audit frontend build and Python test workflows were green. The review nevertheless found two high-impact issues in the camera privacy and production bootstrap paths. Both were corrected on this branch and regression tests were added.

This is not a production-readiness certification. Real camera/edge-agent operation, deployment configuration, external penetration testing, and live hardware validation have not been performed.

## Changes implemented in this audit

### 1. Camera anonymization now fails closed

**Finding:** if face anonymization raised an exception, the camera worker logged the error and continued with the original frame. This could expose an un-anonymized image.

**Correction:** frames that fail anonymization are dropped; the raw frame is never encoded or streamed. A regression test verifies the failure path.

**Additional guard:** production mode forces anonymization even if a camera source requests `anonymize_faces=false`. Development/test mode can still opt out for synthetic test footage.

### 2. Production startup no longer inserts demo records

**Finding:** application startup called the demo seeding routine in all environments. On an empty production database, this could insert fictional students, attendance, zones, cameras, incidents, and other sample records even though demo-user creation had a separate password safeguard.

**Correction:** `seed_data.populate()` now skips all demo seeding when `APP_ENV=production`. A regression test verifies that students, users, zones, and cameras remain absent after production-mode population.

**Operational implication:** production environments must provision their real school records and initial administrator accounts through a controlled process before onboarding. This repository does not yet provide a dedicated first-admin bootstrap workflow.

## Confirmed findings requiring follow-up

| Priority | Area | Finding | Recommended action |
|---|---|---|---|
| High | SSI API | `/ssi/live` uses fixed simulated sensor inputs and `/ssi/history` reads shared seeded history. These routes do not currently expose an explicit demo/unavailable provenance marker and are not protected by an authentication dependency. | Require authenticated access, label the response `data_status=demo` until verified tenant data exists, then implement school-scoped history and Ministry-only aggregate access. |
| High | Camera source registration | A principal can submit arbitrary RTSP/HTTP URLs or local paths. This is a potential SSRF/internal-network and local-resource access boundary if an account is compromised. | Add strict scheme validation, host/IP policy, DNS-rebinding-resistant resolution checks, filesystem allowlisting, connection timeouts, and network egress restrictions. Validate against actual supported camera networks before enforcing. |
| High | Stream authentication | Browser camera streams support JWTs in query strings because image elements cannot set Authorization headers. Query tokens can leak through browser history, reverse-proxy logs, telemetry, and copied URLs. | Replace query JWTs with short-lived, camera-scoped stream tickets or a secure same-site cookie flow; redact query strings from logs until then. |
| Medium | Demo endpoints | `/portal/student`, report lists/statistics, and several dashboard/SSI/unit signals are illustrative or seeded. Some are explicitly marked demo; others return realistic-looking sample records. | Standardize `data_status`, `data_notice`, `source`, and `observed_at` on every user-facing dataset. Ensure demo fixtures cannot be mistaken for actual students or live alerts. |
| Medium | Unit status | `/units` reports every unit as `active` from static metadata; this is not a health check of the underlying workers or sensors. | Return separate `configured`, `operational`, and `data_status` fields based on actual health probes. |
| Medium | WebSocket tenancy | Dashboard WebSocket snapshots are global in-memory demo snapshots. They are not suitable for real multi-school data without per-connection tenant filtering and per-tenant broadcast channels. | Before connecting live school data, make snapshots tenant-aware and prevent cross-tenant broadcasts. |
| Medium | Frontend session storage | JWTs are stored in browser localStorage. This is vulnerable to token theft if an XSS defect is introduced. | Adopt a secure HttpOnly, Secure, SameSite cookie/session design where deployment architecture permits; add CSP and security headers. |
| Medium | Deployment hardening | Nginx currently has no explicit browser security headers; backend container runs as root; Python dependency ranges are not fully locked. | Add tested security headers/CSP, non-root container execution, dependency lock/audit, image scanning, and an automated static security workflow. |
| Medium | Authentication abuse | Login endpoint has no application-level throttling or lockout policy. | Add rate limiting at the reverse proxy/API layer and monitoring for repeated failed logins. |
| Low | Frontend navigation | The new institutional sidebar preserves the existing page state and role-based visibility; the UI still uses the existing Vite/React architecture. Lovable's TanStack route tree should not be copied wholesale. | Continue translating visual components only; keep existing API, authentication, and tenant boundaries. |

## Architecture and data-governance notes

- FastAPI remains the authoritative backend; the frontend must not replace backend authorization with client-side visibility rules.
- Teacher and principal school access is intended to remain tenant-scoped. Ministry access is read-only for school records and should expose aggregates where appropriate.
- The verified analytics engine accepts only fresh authenticated edge-agent camera telemetry for live camera metrics. Principal-entered health snapshots remain excluded from those metrics.
- Wearable observations are marked `live_unverified` / `pending_hardware_verification`; they must not be represented as validated health signals. Ministry-facing identifiable physiological data must remain excluded.
- Camera hardware and RTSP feeds were not available for this review. No claim is made that live camera ingestion or edge-agent telemetry has passed a field test.
- Lovable contains a project-level `.env` file. It was deliberately not read, copied, or migrated. No Lovable secrets, Supabase auth/database/functions, or environment files are part of the UI-only transfer.

## Verification status

- Earlier branch baseline: frontend production build passed; Python suite passed.
- Camera anonymization regression: Python workflow passed on commit `8803e6a67aeb37cdafd50b2fc216b8eba9da4150`.
- Production seed guard regression: Python workflow passed on commit `d4b2f78a83abb2663e7500799cfb582b8bd08909`.
- Production-forced anonymization and its regression test passed the Python test workflow on commit `7b8e28047fde7e3700aaab7476041b5ccb5faecc` (run `41163971503`).
- Frontend was not changed by the backend privacy fixes; the most recent frontend build for the existing UI batch passed.
- No live RTSP/ONVIF camera, edge-agent device, wearable hardware, external penetration test, or production deployment was available for validation.

## Release gate

Do not deploy this branch as a live school system until the high-priority follow-ups are resolved or explicitly accepted by the deployment owner, production provisioning is documented and exercised, and camera privacy/tenant-isolation behavior is validated with representative hardware and two separate school tenants.
