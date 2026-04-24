"""
Test script para verificar los fixes de auth (rondas 1-3).
Corre el servidor en un thread y testea los flujos criticos.
"""
import os
import sys
import threading
import time
import warnings
import logging

os.environ["PYTHONUNBUFFERED"] = "1"
warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

import uvicorn
from main import app

BASE = "http://127.0.0.1:8002"

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="critical")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(6)

import requests

PASS = "\033[92m  PASS\033[0m"
FAIL = "\033[91m  FAIL\033[0m"

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    suffix = f" â€” {detail}" if detail else ""
    print(f"{status}  {label}{suffix}")
    return condition

import time as _time
ts = int(_time.time())
email = f"fix_test_{ts}@raytest.com"

print("\n" + "="*60)
print("BLOQUE 1 â€” Health check")
print("="*60)
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    check("Server up + DB reachable", r.status_code == 200 and r.json().get("db_reachable"))
except Exception as e:
    print(f"  FAIL  Server not responding: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("BLOQUE 2 â€” Registro nuevo usuario via /auth/verify (C2 + C3)")
print("="*60)

r = requests.post(f"{BASE}/auth/verify", json={
    "identifier": email,
    "identifier_type": "email",
    "password": "Test1234!"
}, timeout=10)

check("Responde 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 200:
    data = r.json()
    check("is_new_user = True", data.get("is_new_user") is True)
    check("needs_profile_completion = True", data.get("needs_profile_completion") is True)
    check("next_step = complete_profile", data.get("next_step") == "complete_profile")
    check("assigned_role devuelto", data.get("assigned_role") is not None, data.get("assigned_role"))
    check("access_token presente", bool(data.get("access_token")))
    check("refresh_token presente", bool(data.get("refresh_token")))
    check("temp_token presente (para onboarding)", bool(data.get("temp_token")))
    temp_token = data.get("temp_token")
    access_token_new = data.get("access_token")
else:
    temp_token = None
    access_token_new = None

print("\n" + "="*60)
print("BLOQUE 3 â€” complete-profile asigna rol y crea perfil (C2 + I1)")
print("="*60)

if temp_token:
    r = requests.put(f"{BASE}/auth/complete-profile", json={
        "full_name": "Test User Fix",
        "phone_number": None,
        "role": "client"
    }, headers={"Authorization": f"Bearer {temp_token}"}, timeout=10)

    check("Responde 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        data = r.json()
        check("needs_profile_completion = False", data.get("needs_profile_completion") is False)
        check("next_step = app", data.get("next_step") == "app")
        check("assigned_role = client", data.get("assigned_role") == "client")
        check("access_token presente", bool(data.get("access_token")))
        check("refresh_token presente", bool(data.get("refresh_token")))
        final_access_token = data.get("access_token")
    else:
        final_access_token = None
else:
    print("  SKIP â€” sin temp_token del bloque anterior")
    final_access_token = access_token_new

print("\n" + "="*60)
print("BLOQUE 4 â€” /auth/me con token final (I3: usuario con rol puede acceder)")
print("="*60)

if final_access_token:
    r = requests.get(f"{BASE}/auth/me",
        headers={"Authorization": f"Bearer {final_access_token}"}, timeout=10)
    check("Responde 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        data = r.json()
        check("email correcto", data.get("email") == email)
        check("roles contiene 'client'", "client" in data.get("roles", []), str(data.get("roles")))
else:
    print("  SKIP â€” sin access_token")

print("\n" + "="*60)
print("BLOQUE 5 â€” Login normal via /auth/token")
print("="*60)

r = requests.post(f"{BASE}/auth/token",
    data={"username": email, "password": "Test1234!"},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=10)

check("Responde 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 200:
    data = r.json()
    check("access_token presente", bool(data.get("access_token")))
    check("refresh_token presente", bool(data.get("refresh_token")))
    login_access = data.get("access_token")
else:
    login_access = None

print("\n" + "="*60)
print("BLOQUE 6 â€” Refresh token rotation")
print("="*60)

# Get a fresh refresh token from login
r = requests.post(f"{BASE}/auth/token",
    data={"username": email, "password": "Test1234!"},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=10)
if r.status_code == 200:
    refresh_tok = r.json().get("refresh_token")
    r2 = requests.post(f"{BASE}/auth/refresh",
        params={"refresh_token": refresh_tok}, timeout=10)
    check("Refresh responde 200", r2.status_code == 200, f"got {r2.status_code}: {r2.text[:200]}")
    if r2.status_code == 200:
        data = r2.json()
        check("Nuevo access_token presente", bool(data.get("access_token")))
        check("Nuevo refresh_token presente", bool(data.get("refresh_token")))

    # Test theft detection: reuse the same refresh token
    r3 = requests.post(f"{BASE}/auth/refresh",
        params={"refresh_token": refresh_tok}, timeout=10)
    check("Reuso detectado â†’ 401", r3.status_code == 401, f"got {r3.status_code}")

print("\n" + "="*60)
print("BLOQUE 7 â€” /auth/identify con phone â†’ 422 (C4)")
print("="*60)

r = requests.post(f"{BASE}/auth/identify", json={
    "identifier": "+12605551234",
    "identifier_type": "phone"
}, timeout=10)
check("Phone identify â†’ 422", r.status_code == 422, f"got {r.status_code}: {r.text[:150]}")

print("\n" + "="*60)
print("BLOQUE 8 â€” complete-profile con rol detailer crea DetailerProfile (I1)")
print("="*60)

detailer_email = f"detailer_test_{ts}@raytest.com"
r = requests.post(f"{BASE}/auth/verify", json={
    "identifier": detailer_email,
    "identifier_type": "email",
    "password": "Test1234!"
}, timeout=10)

if r.status_code == 200:
    det_temp = r.json().get("temp_token")
    if det_temp:
        r2 = requests.put(f"{BASE}/auth/complete-profile", json={
            "full_name": "Det Tester",
            "phone_number": None,
            "role": "detailer"
        }, headers={"Authorization": f"Bearer {det_temp}"}, timeout=10)
        check("Detailer complete-profile â†’ 200", r2.status_code == 200,
              f"got {r2.status_code}: {r2.text[:200]}")
        if r2.status_code == 200:
            data = r2.json()
            check("next_step = detailer_onboarding", data.get("next_step") == "detailer_onboarding")
            check("assigned_role = detailer", data.get("assigned_role") == "detailer")
    else:
        print("  SKIP â€” no temp_token del registro")
else:
    print(f"  SKIP â€” registro fallÃ³: {r.status_code}")

print("\n" + "="*60)
print("BLOQUE 9 â€” Token sin rol â†’ 403 en /auth/me (I3 guard)")
print("="*60)
# We simulate by using an onboarding token (user without role) on a non-onboarding endpoint
if access_token_new:
    # access_token_new was issued before complete-profile, user had a role by then
    # so let's use the temp_token (onboarding scope) on /auth/me â€” should 403
    if temp_token:
        r = requests.get(f"{BASE}/auth/me",
            headers={"Authorization": f"Bearer {temp_token}"}, timeout=10)
        check("Onboarding token en /auth/me â†’ 403", r.status_code == 403,
              f"got {r.status_code}: {r.text[:150]}")

print("\n" + "="*60)
print("BLOQUE 10 â€” check-email endpoint")
print("="*60)

r = requests.post(f"{BASE}/auth/check-email", json={"email": email}, timeout=10)
check("check-email usuario existente â†’ 200", r.status_code == 200)
if r.status_code == 200:
    data = r.json()
    check("exists = True", data.get("exists") is True)
    check("auth_method = password", data.get("auth_method") == "password")

r = requests.post(f"{BASE}/auth/check-email",
    json={"email": f"noexiste_{ts}@raytest.com"}, timeout=10)
check("check-email usuario nuevo â†’ exists=False", r.status_code == 200 and not r.json().get("exists"))

print("\n" + "="*60)
print("FIN DE TESTS")
print("="*60 + "\n")

