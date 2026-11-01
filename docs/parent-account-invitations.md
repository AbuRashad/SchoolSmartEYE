# Parent account invitations

The Principal+ invitation flow creates a short-lived activation token for one student in the principal's authenticated school. Staff must verify the adult against official school records before issuing it.

- Tokens are generated with a cryptographically secure random source and only SHA-256 digests are stored.
- Tokens expire after 48 hours, can be revoked, and are accepted once.
- The invited adult chooses a password during activation; the server stores only the existing password hash format.
- The account is created with the exact `parent` role and linked only to the invitation's student and school.
- The raw token is returned only in the create response. Deliver it through a school-approved private channel; this implementation does not send email or SMS.
- The API does not expose or accept an arbitrary role, school ID, verifier ID, or student mapping from the accepting client.

Routes (under `/api/v1`):
- `POST /parent/invitations` — Principal+ creates an invitation.
- `GET /parent/invitations` — Principal+ lists the latest 100 invitations for the active school.
- `DELETE /parent/invitations/{id}` — Principal+ revokes a pending invitation.
- `POST /parent/invitations/accept` — public one-time activation with token and chosen password.

Operational note: because delivery is manual, never send tokens in public channels, tickets, logs, or screenshots. Configure transport-level rate limiting and an approved email/SMS delivery provider before production rollout.
