#!/usr/bin/env python3
"""Create the n8n credentials a template needs, without secrets ever being printed or pasted into a chat.

Usage:
    python3 scripts/create-credentials.py <template-folder> [--supabase] [--only TYPE[,TYPE]]

Run it in your own terminal. It asks for your n8n URL and an n8n API key, then for each credential the
template lists in <template-folder>/credentials.json. Secrets are read with getpass (nothing is shown as you
type) and sent straight to your n8n instance's public API. Only credential names and IDs are printed.

--supabase also creates the Postgres credential for the template's workflow-supabase.json.
--only creates just the listed credential types, e.g. --only postgres to add Supabase later.
Set N8N_URL and N8N_API_KEY in the environment to skip those two questions.

Python 3.8+ standard library only.
"""
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def ask(label, secret=False, default=None):
    prompt = f"{label}{f' [{default}]' if default else ''}: "
    value = getpass.getpass(prompt) if secret else input(prompt)
    value = value.strip()
    if not value and default is not None:
        return default
    while not value:
        value = (getpass.getpass(prompt) if secret else input(prompt)).strip()
    return value


def api(base, key, method, path, body=None):
    req = urllib.request.Request(
        base + "/api/v1" + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"X-N8N-API-KEY": key, "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        # n8n's error messages name fields, never echo values, but keep it short anyway.
        msg = e.read().decode(errors="replace")[:300]
        raise SystemExit(f"n8n answered {e.code} on {method} {path}: {msg}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Couldn't reach {base}: {e.reason}")


def postgres_from_url(url):
    """postgresql://user:password@host:port/database -> n8n Postgres credential fields."""
    if "YOUR-PASSWORD" in url.upper() or "YOUR_PASSWORD" in url.upper():
        raise SystemExit("The connection string still has the [YOUR-PASSWORD] placeholder. Put your database password in its place.")
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("postgres", "postgresql") or not u.hostname:
        raise SystemExit("That doesn't look like a Postgres connection string (postgresql://user:password@host:port/database).")
    if u.hostname.startswith("db.") and u.hostname.endswith(".supabase.co"):
        raise SystemExit("That's Supabase's direct connection, which only works over IPv6 and most n8n servers can't reach it. "
                         "In Supabase, click Connect and copy the Session pooler string instead (host ...pooler.supabase.com).")
    return {
        "host": u.hostname,
        "port": u.port or 5432,
        "database": (u.path or "/postgres").lstrip("/") or "postgres",
        "user": urllib.parse.unquote(u.username or ""),
        "password": urllib.parse.unquote(u.password or ""),
        "ssl": "require",
        # Supabase signs its database certificates with its own CA, which n8n rejects unless told to accept it.
        "allowUnauthorizedCerts": True,
        "maxConnections": 10,
        "sshTunnel": False,
    }


def build(cred):
    """Ask for one credential's values and return n8n's data object for its type."""
    t = cred["type"]
    print(f"\n{cred['name']} ({t}){': ' + cred['help'] if cred.get('help') else ''}")
    if t == "httpCustomAuth":  # Shopify client credentials grant
        client_id = ask("  Client ID")
        client_secret = ask("  Client secret", secret=True)
        return {"json": json.dumps({"body": {"client_id": client_id, "client_secret": client_secret}})}
    if t == "slackApi":
        return {"accessToken": ask("  Bot User OAuth Token (xoxb-...)", secret=True)}
    if t == "crypto":
        return {"hmacSecret": ask(f"  {cred.get('secret_label', 'Hmac secret')}", secret=True)}
    if t == "ollamaApi":
        return {"baseUrl": ask("  Base URL", default="https://ollama.com"), "apiKey": ask("  API key", secret=True)}
    if t == "httpBasicAuth":
        return {"user": ask(f"  {cred.get('user_label', 'User')}"), "password": ask(f"  {cred.get('password_label', 'Password')}", secret=True)}
    if t == "httpHeaderAuth":
        key = ask(f"  {cred.get('secret_label', 'API key')}", secret=True)
        return {"name": cred.get("header", "Authorization"), "value": cred.get("prefix", "Bearer ") + key}
    if t == "postgres":
        return postgres_from_url(ask("  Connection string (Supabase: Connect > Session pooler)", secret=True))
    raise SystemExit(f"credentials.json lists a type this script doesn't know: {t}")


def main():
    argv = sys.argv[1:]
    only = None
    if "--only" in argv:
        i = argv.index("--only")
        if i + 1 >= len(argv):
            raise SystemExit("--only needs a credential type, e.g. --only postgres")
        only = set(argv[i + 1].split(","))
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        raise SystemExit(__doc__)
    folder = args[0].rstrip("/")
    spec_path = os.path.join(folder, "credentials.json")
    if not os.path.exists(spec_path):
        raise SystemExit(f"No {spec_path}. Pass a template folder, e.g. shopify-collections-seo")
    spec = json.load(open(spec_path))
    creds = [c for c in spec["credentials"] if "--supabase" in argv or not c.get("supabase_only")]
    if only:
        creds = [c for c in creds if c["type"] in only]
    if not creds:
        raise SystemExit("Nothing to create: check --only and --supabase against credentials.json.")

    print(f"Credentials for {spec['template']}: " + ", ".join(c["name"] for c in creds))
    base = (os.environ.get("N8N_URL") or ask("n8n URL, e.g. https://n8n.example.com")).rstrip("/")
    key = os.environ.get("N8N_API_KEY") or ask("n8n API key (Settings > n8n API)", secret=True)

    existing = {}
    try:
        for c in api(base, key, "GET", "/credentials?limit=250").get("data", []):
            existing[(c["name"], c["type"])] = c["id"]
    except SystemExit:
        pass  # older n8n versions can't list credentials; carry on

    made = []
    for cred in creds:
        if (cred["name"], cred["type"]) in existing:
            again = input(f"\n{cred['name']} already exists (id {existing[(cred['name'], cred['type'])]}). Create another? [y/N]: ")
            if again.strip().lower() != "y":
                made.append((cred, existing[(cred["name"], cred["type"])], "kept"))
                continue
        data = build(cred)
        res = api(base, key, "POST", "/credentials", {"name": cred["name"], "type": cred["type"], "data": data})
        data.clear()
        made.append((cred, res.get("id"), "created"))
        print(f"  created: {cred['name']} (id {res.get('id')})")

    print("\nDone. Select each credential on these nodes (or ask your agent to):")
    for cred, cid, how in made:
        print(f"- {cred['name']} [{how}, id {cid}]: {', '.join(cred['nodes'])}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nStopped. Nothing else was created.")
