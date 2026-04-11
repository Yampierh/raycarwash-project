# app/routers/wellknown_router.py
#
# Serves /.well-known/ files required for WebAuthn/passkey domain verification:
#
#   iOS  — apple-app-site-association (Associated Domains)
#           Tells iOS that `webcredentials:WEBAUTHN_RP_ID` belongs to this app,
#           enabling Passkeys and AutoFill in the app.
#
#   Android — assetlinks.json (Digital Asset Links)
#              Tells Android that the WEBAUTHN_RP_ID domain is associated with
#              the app identified by its SHA-256 signing cert fingerprint.
#
# These files must be reachable at:
#   GET https://<WEBAUTHN_RP_ID>/.well-known/apple-app-site-association
#   GET https://<WEBAUTHN_RP_ID>/.well-known/assetlinks.json
#
# No auth required — Apple and Google's servers fetch these on first passkey use.

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings

router = APIRouter(tags=["Domain Verification"])


@router.get(
    "/.well-known/apple-app-site-association",
    include_in_schema=False,
)
async def apple_app_site_association() -> JSONResponse:
    """
    Apple Associated Domains file.

    Required for:
      - `webcredentials` → enables Passkeys / AutoFill credential provider
      - `applinks`       → deep links (useful for password-reset links too)

    The `apps` field must be empty (Apple spec requirement).
    The bundle ID must match APPLE_BUNDLE_ID in .env.
    """
    settings = get_settings()
    bundle_id = settings.APPLE_BUNDLE_ID  # e.g. "com.raycarwash.app"

    # Apple requires the format: "<TeamID>.<BundleID>" in the credentials list.
    # If APPLE_TEAM_ID is not configured yet, fall back to bundle ID only — update
    # this once the Apple Developer Team ID is known.
    team_bundle = bundle_id  # Replace with f"{TEAM_ID}.{bundle_id}" when known

    content = {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appID": team_bundle,
                    "paths": ["/auth/*"],
                }
            ],
        },
        "webcredentials": {
            "apps": [team_bundle],
        },
    }
    return JSONResponse(
        content=content,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/.well-known/assetlinks.json",
    include_in_schema=False,
)
async def asset_links() -> JSONResponse:
    """
    Android Digital Asset Links file.

    Required for Android Credential Manager passkeys.
    ANDROID_SHA256_CERT must be set in .env to the SHA-256 fingerprint of
    your Android signing certificate (colon-separated uppercase hex).

    Obtain with:
        keytool -list -v -keystore release.keystore -alias <alias>
    or from Google Play → Setup → App signing (if using Play App Signing).
    """
    settings = get_settings()
    bundle_id  = settings.APPLE_BUNDLE_ID  # reuse as Android package name or set separate env
    sha256_cert = settings.ANDROID_SHA256_CERT  # e.g. "AB:CD:12:..."

    content = [
        {
            "relation": ["delegate_permission/common.handle_all_urls", "delegate_permission/common.get_login_creds"],
            "target": {
                "namespace": "android_app",
                "package_name": bundle_id,
                "sha256_cert_fingerprints": [sha256_cert] if sha256_cert else [],
            },
        }
    ]
    return JSONResponse(
        content=content,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
