# Authentication System — Technical Reference

## Key Architecture

Three independent secrets. Each rotates independently. Compromising one does not expose the others.

| Variable | Algorithm | Purpose | Rotation impact |
|---|---|---|---|
| `JWT_SECRET_KEY` | HS256 (HMAC-SHA256) | Sign and verify all JWTs | Invalidates all active tokens — all users must re-login |
| `ENCRYPTION_KEY` | Fernet (AES-128-CBC) | Encrypt PII at rest: `full_name`, `phone_number` | Re-encryption of all user rows required before old key is removed |
| `PHONE_LOOKUP_KEY` | HMAC-SHA256 | Hash phone numbers for O(1) DB lookups | Rehash all `phone_hash` values before old key is removed |

Generate:
```bash
openssl rand -hex 32      # JWT_SECRET_KEY and PHONE_LOOKUP_KEY
openssl rand -base64 32   # ENCRYPTION_KEY
```

---

## Token Types

All tokens are JWTs signed with `JWT_SECRET_KEY` (HS256), except password reset tokens which are opaque random strings stored as SHA-256 hashes.

| Type | `"type"` claim | Lifetime | Single-use | Stateful (DB) | Accepted by |
|---|---|---|---|---|---|
| **access** | `"access"` | 30 min | No | No | All authenticated endpoints |
| **refresh** | `"refresh"` | 7 days | Yes | Yes (`refresh_tokens` table) | `POST /auth/refresh` only |
| **onboarding** | `"onboarding"` | 30 min | No | No | `PUT /auth/complete-profile` only |
| **password_reset** | — (opaque) | 1 hour | Yes | Yes (`password_reset_tokens` table) | `POST /auth/password-reset/confirm` only |
| **webauthn_registration** | `"webauthn_registration"` | 5 min | Implicit (challenge consumed) | No | `POST /auth/webauthn/register/complete` only |
| **webauthn_authentication** | `"webauthn_authentication"` | 5 min | Implicit (challenge consumed) | No | `POST /auth/webauthn/authenticate/complete` only |

### Access Token Payload

```json
{
  "sub":  "user-uuid",
  "role": "client | detailer | admin",
  "type": "access",
  "v":    1,
  "iat":  1234567890,
  "exp":  1234569600
}
```

The `"v"` claim is the user's `token_version`. It enables instant session revocation — see [Session Revocation](#session-revocation) below.

### Onboarding Token Payload

```json
{
  "sub":  "user-uuid",
  "type": "onboarding",
  "iat":  1234567890,
  "exp":  1234569600
}
```

No `role` claim (user has not selected a role yet). No `"v"` claim.

---

## Authentication Flows

### Registration → Onboarding → Full Access

```
POST /auth/register { email, password }
  → User created (onboarding_completed=False, no role)
  → Returns: { onboarding_token }

PUT /auth/complete-profile { full_name, phone_number?, service_type? }
  Bearer: onboarding_token
  → Backend assigns role based on service_type (frontend never controls role):
      service_type=null/omitted  → role="client"  → next_step="app"
      service_type="detailer"    → role="detailer" → next_step="detailer_onboarding"
  → Invalid service_type → 422 Unprocessable Entity
  → Profile created (ClientProfile or ProviderProfile), onboarding_completed=True
  → Returns: { access_token, refresh_token, next_step, assigned_role }

GET /auth/me
  Bearer: access_token
  → Full access to all endpoints
```

**Provider registration flow (UI):**

```
RegisterScreen → [Join as Provider] → ProviderTypeScreen
  → user selects service type (currently: "detailer")
  → navigate to CompleteProfile with service_type param
  → PUT /auth/complete-profile { service_type: "detailer" }
  → DetailerOnboarding
```

**Security invariant:** The `service_type` field is validated against an allowlist
(`VALID_SERVICE_TYPES` in `schemas.py`). Sending `service_type: "admin"` or any unlisted
value returns 422. The legacy `role` field is not present in the DTO — extra fields are
silently ignored by Pydantic.

### Login (Existing User)

```
POST /auth/login { email, password }
  → If onboarding_completed=True:  returns { access_token, refresh_token }
  → If onboarding_completed=False: returns { onboarding_token }
```

### Social Login (Google / Apple)

```
POST /auth/google { code, code_verifier, redirect_uri }
POST /auth/apple  { identity_token, full_name? }
  → New user or user with no role: returns { onboarding_token }
  → Existing user with role:       returns { access_token, refresh_token }
```

### Token Rotation

```
POST /auth/refresh { refresh_token }
  → Mark refresh_token as used (used_at = NOW)
  → Issue new access_token + refresh_token (same family_id)
  → Return: { access_token, refresh_token }

If the same refresh_token is used a second time:
  → Entire token family is revoked (theft detection)
  → Return: 401 Unauthorized
```

### Password Reset Flow

```
POST /auth/password-reset { email }
  → Lookup user by email (always returns 200 — user enumeration protection)
  → Invalidate any existing unused reset tokens for this user
  → Create PasswordResetToken: store SHA-256(raw_token) in DB, send raw_token by email
  → Return: { message: "If that email is registered, a reset link has been sent." }

POST /auth/password-reset/confirm { token, new_password }
  → Hash the token, look up in password_reset_tokens
  → Reject if:  token not found → 400
                token.used_at is not NULL → 400  (already used)
                token.expires_at < NOW → 400     (expired)
  → Mark token as used (used_at = NOW)
  → Update user.password_hash
  → Increment user.token_version  (invalidates all active JWTs)
  → Return: { message: "Password reset successfully." }
```

Key properties:
- **Single-use**: `used_at` column prevents replay attacks from intercepted emails.
- **One active reset per user**: requesting a second reset invalidates the first token.
- **Session invalidation**: `token_version` increment means all existing access tokens are stale on the next request (future validation step).
- **Raw token never stored**: only `SHA-256(raw_token)` in the DB.

---

## Token Type Validation

`get_current_user()` in `app/services/auth.py` rejects tokens by type:

```python
# Normal endpoints — reject onboarding tokens
user = Depends(get_current_user)

# Onboarding endpoints — accept onboarding tokens
user = Depends(get_current_user_for_onboarding)
```

Type confusion prevention: every token type has a dedicated `"type"` claim. `decode_token(expected_type)` raises `JWTError` if the type doesn't match. An onboarding token cannot be used as an access token because the `"type"` field is checked before the user is loaded.

---

## Session Revocation

### Revoke a Specific Device
`DELETE /auth/sessions/{family_id}` — revokes one refresh token family (one device session).

### Revoke All Devices  
`DELETE /auth/sessions` — revokes all refresh token families for the authenticated user.

### Instant Revocation via `token_version`

`user.token_version` is stored in the DB and embedded as `"v"` in every access token. To instantly invalidate all sessions:

```sql
UPDATE users SET token_version = token_version + 1 WHERE id = <user_id>;
```

On the next request, the `"v"` claim in the JWT will not match the DB value, and the request will be rejected. This happens automatically on:
- Successful password reset (`confirm_password_reset`)
- (Future) role removal by admin

> **Note**: `token_version` validation in `get_current_user()` is pending implementation (Phase 2). The `"v"` claim is currently present in all tokens but not yet checked on every request.

---

## WebAuthn (Passkeys)

Challenges are stateless: a short-lived JWT (`webauthn_registration` or `webauthn_authentication` type, 5-minute expiry) carries the challenge bytes. The client echoes the challenge JWT in the `/complete` request; the server decodes it to recover the challenge without a DB lookup.

```
Register:
  POST /auth/webauthn/register/begin  (authenticated)
    → Returns: challenge_token + PublicKeyCredentialCreationOptions

  POST /auth/webauthn/register/complete (authenticated)
    { challenge_token, credential_response }
    → Verifies attestation, stores credential_id + public_key + sign_count

Authenticate:
  POST /auth/webauthn/authenticate/begin  { email }
    → Returns: challenge_token + PublicKeyCredentialRequestOptions

  POST /auth/webauthn/authenticate/complete
    { challenge_token, credential_response }
    → Verifies assertion, updates sign_count (replay detection)
    → Returns: { access_token, refresh_token }
```

---

## Security Properties

| Property | Mechanism |
|---|---|
| **User enumeration prevention** | Password check always runs `bcrypt.dummy_verify()` on missing users; password reset always returns 200 |
| **Token type confusion prevention** | Dedicated `"type"` claim checked before user load |
| **Refresh token theft detection** | Single-use tokens; reuse triggers family revocation → all devices logged out |
| **PII at rest** | `full_name` and `phone_number` encrypted with Fernet (`ENCRYPTION_KEY`) |
| **Password reset replay prevention** | `used_at` column; token consumed on first use |
| **Session revocation on password change** | `token_version` incremented; `"v"` claim will mismatch on next request |
| **Credential cloning detection** | WebAuthn `sign_count` must increase; py_webauthn raises on regression |
| **Rate limiting** | slowapi: 10 auth attempts/minute per IP on `/auth/*` endpoints |
| **Audit trail** | `AuditLog` table: INSERT-only, no UPDATE/DELETE at DB privilege level |
