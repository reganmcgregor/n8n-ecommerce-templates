#!/usr/bin/env python3
"""Build the Slack-run store: every template in this repo, wired into one system.

Usage:
    python3 slack-run-store/build.py [--plan starter|full] [--import] [--update] [--config file] [--out folder]

It reads config.json (your store, n8n URL and Slack channel names) and system.json (which template does what
in which phase), then writes:

    workflows/<phase>/*.json   one workflow per template, plus the glue workflows
    supabase/schema.sql        every table the system uses, and the store_queues view
    credentials.json           the credentials, read by scripts/create-credentials.py
    slack-app-manifest.yml     one Slack app for every card, button and /store

The phase workflows are copies of each template's workflow-supabase.json with your settings filled in, the
webhook paths prefixed, and one extra entry point so /store run can start any lane. Nothing else changes, so a
fix to a template reaches the store the next time you build.

--import creates (or, with --update, replaces) the workflows on your n8n through its public API, with each
credential selected by name. It asks for your n8n URL and API key (or reads N8N_URL and N8N_API_KEY) and never
prints them. It doesn't publish anything: run Setup and publish each workflow yourself, phase by phase.

Python 3.8+ standard library only.
"""
import copy
import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
NS = uuid.UUID("6f1e1c52-5d0b-4c39-9a51-3f2e7f0c2a11")  # stable ids for the nodes this script adds
PLACEHOLDER_N8N = "https://your-n8n.example.com"
PLACEHOLDER_STORE = "your-store.myshopify.com"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def sid(*parts):
    return str(uuid.uuid5(NS, "|".join(parts)))


# ---------------------------------------------------------------- settings nodes

def settings_nodes(wf):
    """Set nodes whose name ends in 'settings': the only place a template keeps its settings."""
    return [n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.set" and n["name"].lower().endswith("settings")]


VALUE = r'("(?:[^"\\]|\\.)*"|\[[^\]]*\]|true|false|null|-?\d+(?:\.\d+)?)'


def _raw(node):
    text = node["parameters"].get("jsonOutput", "{}")
    return text, text.startswith("=")


def read_settings(node):
    p = node["parameters"]
    if p.get("mode") == "raw":
        text, expr = _raw(node)
        try:
            return json.loads(text[1:] if expr else text)
        except ValueError:
            # Settings with {{ expressions }} in them aren't JSON until n8n fills them in: read the plain values only.
            out = {}
            for k, v in re.findall(r'"(\w+)"\s*:\s*' + VALUE, text):
                try:
                    out.setdefault(k, json.loads(v))
                except ValueError:
                    pass
            return out
    return {a["name"]: a.get("value") for a in p.get("assignments", {}).get("assignments", [])}


def write_settings(node, values):
    """Change only the keys given, keeping the node's own layout (raw JSON or one field per setting)."""
    p = node["parameters"]
    if p.get("mode") == "raw":
        text, expr = _raw(node)
        try:
            data = json.loads(text[1:] if expr else text)
        except ValueError:
            for k, v in values.items():
                text = re.sub(r'("' + re.escape(k) + r'"\s*:\s*)' + VALUE, lambda m: m.group(1) + json.dumps(v, ensure_ascii=False), text, count=1)
            p["jsonOutput"] = text
            return
        for k, v in values.items():
            if k in data:
                data[k] = v
        p["jsonOutput"] = ("=" if expr else "") + json.dumps(data, indent=2, ensure_ascii=False)
    else:
        for a in p.get("assignments", {}).get("assignments", []):
            if a["name"] in values:
                a["value"] = values[a["name"]]


def channel(cfg, key):
    """A channel key from system.json (review-pricing) to the name or ID in config.json."""
    value = cfg["channels"].get(key)
    if value is None:
        raise SystemExit(f"config.json has no channel for '{key}'. Add it under channels.")
    return value


def settings_values(cfg, spec, node_name, current):
    """The values to write into one settings node: store-wide ones it has, plus its channels."""
    out = {}
    store = cfg["store"]
    common = {
        "store_domain": store["store_domain"],
        "store_url": store.get("store_url"),
        "currency": store.get("currency"),
        "timezone": store.get("timezone"),
        "slack_app_id": cfg["slack"].get("app_id"),
        "slack_team_id": cfg["slack"].get("team_id"),
        "approver_ids": cfg["slack"].get("approver_ids"),
        "store_name": store.get("store_name"),
        "internal_url": cfg["n8n"].get("internal_url"),
    }
    for k, v in common.items():
        if k in current and v not in (None, ""):
            out[k] = v
    chans = dict(spec.get("channels", {}).get("*", {}))
    chans.update(spec.get("channels", {}).get(node_name, {}))
    for k, ch in chans.items():
        if k in current:
            out[k] = channel(cfg, ch)
    out.update({k: v for k, v in spec.get("settings", {}).get(node_name, {}).items() if k in current})
    mine = cfg.get("overrides", {}).get(spec["slug"], {})
    out.update({k: v for k, v in mine.get("*", {}).items() if k in current})
    for k, v in mine.get(node_name, {}).items():
        if k not in current:
            print(f"Note: overrides.{spec['slug']}.{node_name} has '{k}', which that settings node doesn't have. Ignored.")
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------- one template into the system

def lanes(wf, spec=None):
    """Schedule triggers, plus manual triggers that start something no schedule does: lane name -> first nodes."""
    out = []
    conns = wf["connections"]
    skip = set((spec or {}).get("skip_lanes", []))
    for n in wf["nodes"]:
        if n["type"] in ("n8n-nodes-base.scheduleTrigger", "n8n-nodes-base.manualTrigger") and not n.get("disabled"):
            targets = [c["node"] for outs in conns.get(n["name"], {}).get("main", []) for c in outs]
            if targets and slug(n["name"]) not in skip:
                out.append({"trigger": n["name"], "lane": slug(n["name"]), "targets": targets,
                            "schedule": n["type"].endswith("scheduleTrigger")})
    # A manual trigger that only repeats a schedule ("Run now") is dropped; the rest ("Run once to set up") stay.
    scheduled = [sorted(l["targets"]) for l in out if l["schedule"]]
    return [l for l in out if l["schedule"] or sorted(l["targets"]) not in scheduled]


def add_run_entry(wf, spec, cfg):
    """One webhook that starts any lane, so /store run (and the conductor) can run a job now."""
    found = lanes(wf, spec)
    if not found:
        return []
    prefix = cfg["n8n"]["webhook_prefix"]
    xs = [n["position"][0] for n in wf["nodes"]]
    ys = [n["position"][1] for n in wf["nodes"]]
    x0, y0 = min(xs) - 900, min(ys) - 700
    hook = {
        "id": sid(spec["slug"], "run-hook"), "name": "Run from /store", "type": "n8n-nodes-base.webhook",
        "typeVersion": 2, "position": [x0, y0], "webhookId": sid(spec["slug"], "run-hook-id"),
        "parameters": {"httpMethod": "POST", "path": f"{prefix}run-{spec['slug']}", "authentication": "headerAuth",
                       "responseMode": "onReceived", "options": {}},
        "credentials": {"httpHeaderAuth": {"name": "Store run key"}},
        "notes": "Store Command (/store run) and the conductor call this with { lane }. Header auth: Store run key.",
    }
    rules = []
    for l in found:
        rules.append({"outputKey": l["lane"], "renameOutput": True, "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
            "conditions": [{"id": sid(spec["slug"], "rule", l["lane"]), "leftValue": "={{ $json.body.lane }}",
                            "rightValue": l["lane"], "operator": {"type": "string", "operation": "equals"}}],
            "combinator": "and"}})
    switch = {
        "id": sid(spec["slug"], "run-switch"), "name": "Which lane to run?", "type": "n8n-nodes-base.switch",
        "typeVersion": 3.2, "position": [x0 + 260, y0], "parameters": {"rules": {"values": rules}, "options": {}},
        "notes": "One output per lane, wired to the same first node as its schedule or manual trigger.",
    }
    note = {
        "id": sid(spec["slug"], "run-note"), "name": "Part of the Slack-run store", "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1, "position": [x0 - 40, y0 - 360],
        "parameters": {"width": 560, "height": 300, "color": 6, "content": (
            f"## {spec['title']}, phase {spec['phase']}\n\nPart of the Slack-run store. Slack sends every button tap to "
            "**Store · Slack router**, which passes this workflow's taps to its own webhook unchanged.\n\n"
            "**Run from /store** starts any lane now: `/store run " + spec["jobs_prefix"] + "`. The settings nodes were filled "
            "in from config.json by build.py; change them there and build again.")},
    }
    wf["nodes"] += [note, hook, switch]
    wf["connections"]["Run from /store"] = {"main": [[{"node": "Which lane to run?", "type": "main", "index": 0}]]}
    wf["connections"]["Which lane to run?"] = {"main": [[{"node": t, "type": "main", "index": 0} for t in l["targets"]] for l in found]}
    return found


def build_template(spec, cfg):
    src = os.path.join(REPO, spec["slug"], "workflow-supabase.json")
    wf = load(src)
    prefix = cfg["n8n"]["webhook_prefix"]
    paths = {}
    for n in wf["nodes"]:
        if n["type"] == "n8n-nodes-base.webhook":
            old = n["parameters"]["path"]
            paths[old] = prefix + old
            n["parameters"]["path"] = prefix + old
            n["webhookId"] = sid(spec["slug"], "webhook", old)
        elif "webhookId" in n:
            n["webhookId"] = sid(spec["slug"], "node", n["name"])
    for n in settings_nodes(wf):
        current = read_settings(n)
        write_settings(n, settings_values(cfg, spec, n["name"], current))
    if cfg.get("plan", "full") == "full":
        for n in wf["nodes"]:
            if n["name"] in spec.get("full_plan_disable", []):
                n["disabled"] = True
                n["notes"] = (n.get("notes", "") + " Off in the full plan: Store 4 · Collection sorting owns the order.").strip()
    found = add_run_entry(wf, spec, cfg)
    names = [n["name"] for n in wf["nodes"]]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise SystemExit(f"{spec['slug']}: two nodes share a name after adding the run entry: {', '.join(sorted(dupes))}")
    text = json.dumps(wf, ensure_ascii=False)
    public = cfg["n8n"]["public_url"].rstrip("/")
    for old, new in sorted(paths.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(f"{PLACEHOLDER_N8N}/webhook/{old}", f"{public}/webhook/{new}")
    text = text.replace(PLACEHOLDER_N8N, public)
    wf = json.loads(text)
    out = {"name": f"Store {spec['phase']} · {spec['title']}", "nodes": wf["nodes"], "connections": wf["connections"],
           "settings": {"executionOrder": "v1", "timezone": cfg["store"].get("timezone", "UTC")}}
    return out, paths, found


# ---------------------------------------------------------------- glue workflows

def build_glue(gname, cfg, system, generated):
    name = system["glue"][gname]["source"]
    wf = load(os.path.join(HERE, "src", name))
    public = cfg["n8n"]["public_url"].rstrip("/")
    prefix = cfg["n8n"]["webhook_prefix"]
    for n in wf["nodes"]:
        if n["type"] == "n8n-nodes-base.webhook":
            n["parameters"]["path"] = prefix + n["parameters"]["path"].replace("{prefix}", "")
            n["webhookId"] = sid("glue", name, n["parameters"]["path"])
    spec = {"slug": gname, "channels": system["glue"][gname].get("channels", {}), "settings": {}}
    for n in settings_nodes(wf):
        current = read_settings(n)
        values = settings_values(cfg, spec, n["name"], current)
        for k, v in generated.items():
            if k in current:
                values[k] = v
        write_settings(n, values)
    text = json.dumps(wf, ensure_ascii=False).replace(PLACEHOLDER_N8N + "/webhook/", f"{public}/webhook/{prefix}")
    wf = json.loads(text.replace(PLACEHOLDER_N8N, public))
    wf["settings"] = {"executionOrder": "v1", "timezone": cfg["store"].get("timezone", "UTC")}
    return wf


# ---------------------------------------------------------------- the maps the glue reads

def routes(system, built, cfg, glue_in):
    """Where the Slack router sends each tap: by action_id prefix, modal callback_id, then channel."""
    by_prefix, by_callback, by_channel, ignore = [], [], [], list(system.get("router_ignore", []))
    for spec in system["templates"]:
        if spec["slug"] not in built:
            continue
        r = spec.get("slack")
        if not r:
            continue
        path = built[spec["slug"]]["paths"][r["webhook"]]
        for p in r.get("action_prefixes", []):
            by_prefix.append({"prefix": p, "path": path, "workflow": spec["slug"]})
        for c in r.get("callback_ids", []):
            by_callback.append({"prefix": c, "path": path, "workflow": spec["slug"]})
        for ch in r.get("channels", []):
            by_channel.append({"channel": channel(cfg, ch), "path": path, "workflow": spec["slug"]})
    for g in [system["glue"][k] for k in glue_in]:
        r = g.get("slack")
        if r:
            path = cfg["n8n"]["webhook_prefix"] + r["webhook"]
            by_prefix += [{"prefix": p, "path": path, "workflow": g["name"]} for p in r.get("action_prefixes", [])]
            by_channel += [{"channel": channel(cfg, ch), "path": path, "workflow": g["name"]} for ch in r.get("channels", [])]
    by_prefix.sort(key=lambda r: -len(r["prefix"]))
    by_callback.sort(key=lambda r: -len(r["prefix"]))
    return {"action_prefixes": by_prefix, "callback_ids": by_callback, "channels": by_channel, "ignore_actions": ignore}


def jobs(system, built, cfg, glue_in):
    out = []
    for spec in system["templates"]:
        b = built.get(spec["slug"])
        if not b:
            continue
        for l in b["lanes"]:
            name = spec["jobs_prefix"] if l["lane"] == spec.get("main_lane") else f"{spec['jobs_prefix']} {spec.get('lane_names', {}).get(l['lane'], l['lane'])}"
            out.append({"job": name, "phase": spec["phase"], "title": spec["title"], "lane": l["lane"],
                        "path": f"{cfg['n8n']['webhook_prefix']}run-{spec['slug']}", "setup": not l["schedule"] and bool(re.search(r"set-?up", l["lane"]))})
    for gname in glue_in:
        for j in system["glue"][gname].get("jobs", []):
            out.append({**j, "path": cfg["n8n"]["webhook_prefix"] + j["path"]})
    return sorted(out, key=lambda j: (j["phase"], j["job"]))


def stages(system, built):
    """The conductor's stages, with each tag read from its template's own settings as built."""
    out = []
    for st in system["conductor_stages"]:
        steps = []
        for spec in system["templates"]:
            c = spec.get("conductor")
            if not c or c["stage"] != st["stage"] or spec["slug"] not in built:
                continue
            node_name, key = c["tag_from"]
            node = next(n for n in built[spec["slug"]]["workflow"]["nodes"] if n["name"] == node_name)
            steps.append({"workflow": spec["title"], "tag": read_settings(node)[key], "pending": c["pending"]})
        if steps:
            out.append({"stage": st["stage"], "label": st["label"], "steps": steps})
    return out


def queues(system, built, cfg, glue_in):
    out = []
    for spec in system["templates"]:
        b = built.get(spec["slug"])
        for q in spec.get("queues", []):
            if not b:
                continue
            q = dict(q)
            q["workflow"] = spec["title"]
            q["phase"] = spec["phase"]
            q["channel"] = channel(cfg, q["channel"])
            if q.get("replay"):
                q["replay"] = {**q["replay"], "path": b["paths"][spec["slack"]["webhook"]]}
            out.append(q)
    for g in [system["glue"][k] for k in glue_in]:
        for q in g.get("queues", []):
            q = dict(q)
            q["channel"] = channel(cfg, q["channel"])
            if q.get("replay"):
                q["replay"] = {**q["replay"], "path": cfg["n8n"]["webhook_prefix"] + g["slack"]["webhook"]}
            out.append(q)
    return out


def queue_view(qs):
    esc = lambda t: str(t).replace("'", "''")
    parts = [f"  select '{q['key']}'::text as queue, '{esc(q['label'])}'::text as label, {q['phase']}::int as phase, "
             f"'{esc(q['channel'])}'::text as channel, count(*)::int as waiting, min(x.since)::timestamptz as oldest\n"
             f"  from ({q['rows']}) x" for q in qs]
    body = "\n  union all\n".join(parts) if parts else "  select null::text, null::text, null::int, null::text, 0, null::timestamptz where false"
    return ("-- What /store status counts: one row per review queue. Generated by build.py from system.json.\n"
            "create or replace view store_queues as\n" + body + ";\n")


# ---------------------------------------------------------------- schema, credentials, manifest

def schema(system, built, qs):
    seen_tables = set()
    out = ["-- The Slack-run store: every table its workflows use, in one Supabase (Postgres) database.",
           "-- Generated by build.py. Run it once in Supabase's SQL editor; it's safe to run again.", ""]
    for spec in system["templates"]:
        if spec["slug"] not in built:
            continue
        sql = open(os.path.join(REPO, spec["slug"], "supabase", "schema.sql"), encoding="utf-8").read()
        # Templates that share a table (offers) define it the same way; keep the first definition only.
        blocks = re.split(r"(?=^create table if not exists )", sql, flags=re.M)
        keep = []
        for b in blocks:
            m = re.match(r"create table if not exists (\w+)", b)
            if m and m.group(1) in seen_tables:
                b = re.sub(r"^create table if not exists \w+ \(.*?\n\);\n?", "", b, count=1, flags=re.S)
            if m:
                seen_tables.add(m.group(1))
            keep.append(b)
        out += [f"-- ===== Phase {spec['phase']} · {spec['title']} ({spec['slug']}/supabase/schema.sql)", "".join(keep).strip(), ""]
    out += ["-- ===== The glue: conductor, review page links, buyer guides", open(os.path.join(HERE, "src", "glue.sql"), encoding="utf-8").read().strip(), ""]
    out.append(queue_view(qs))
    return "\n".join(out)


def credentials(system, workflows):
    merged = {}
    order = []
    sources = [os.path.join(REPO, t["slug"], "credentials.json") for t in system["templates"]]
    sources += [os.path.join(HERE, "src", g["credentials_from"]) for g in system["glue"].values() if g.get("credentials_from")]
    for path in sources:
        if not os.path.exists(path):
            continue
        for c in load(path)["credentials"]:
            key = (c["name"], c["type"])
            if key not in merged:
                merged[key] = {k: v for k, v in c.items() if k != "nodes"}
                merged[key]["nodes"] = []
                order.append(key)
            elif not c.get("optional"):
                merged[key].pop("optional", None)
    # Every node that uses each credential, by workflow, read from the built workflows themselves.
    for wf in workflows:
        for n in wf["nodes"]:
            for t, ref in (n.get("credentials") or {}).items():
                key = (ref.get("name"), t)
                if key in merged:
                    merged[key]["nodes"].append(f"{wf['name']}: {n['name']}")
    for key in merged:
        merged[key].pop("supabase_only", None)
        if key == ("Shopify client credentials", "httpCustomAuth"):
            merged[key]["help"] = "Your Shopify app's client ID and secret (Dev Dashboard > your app > Settings), with every scope in the README"
        if key == ("DataForSEO", "httpBasicAuth"):
            merged[key].update({"user_label": "API login", "password_label": "API password",
                                "help": "Your DataForSEO API login and API password (dataforseo.com > API Access)"})
            merged[key].pop("optional", None)
    return {"template": "Slack-run store", "credentials": [merged[k] for k in order if merged[k]["nodes"]]}


def manifest(cfg, prefix):
    url = cfg["n8n"]["public_url"].rstrip("/")
    name = cfg["slack"].get("app_name", "Store")
    return f"""# Paste this at api.slack.com/apps > Create New App > From a manifest. Generated by build.py.
display_information:
  name: {name}
  description: Cards, buttons and /store for the Slack-run store
features:
  bot_user:
    display_name: {name}
    always_online: false
  slash_commands:
    - command: /store
      url: {url}/webhook/{prefix}command
      description: What's waiting, run any job, open the review page
      usage_hint: help | status | run <job> | page <queue>
      should_escape: false
oauth_config:
  scopes:
    bot:
      - chat:write
      - chat:write.public
      - files:write
      - commands
      - channels:history
      - groups:history
settings:
  interactivity:
    is_enabled: true
    request_url: {url}/webhook/{prefix}slack
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
"""


# ---------------------------------------------------------------- import through the n8n public API

def api(base, key, method, path, body=None):
    req = urllib.request.Request(base + "/api/v1" + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"X-N8N-API-KEY": key, "Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": "n8n-ecommerce-templates/slack-run-store"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"n8n answered {e.code} on {method} {path}: {e.read().decode(errors='replace')[:300]}")


def import_all(workflows, update, error_workflow=None):
    base = (os.environ.get("N8N_URL") or input("n8n URL, e.g. https://n8n.example.com: ")).strip().rstrip("/")
    key = os.environ.get("N8N_API_KEY") or getpass.getpass("n8n API key (Settings > n8n API): ").strip()
    creds = {}
    cursor = None
    while True:
        page = api(base, key, "GET", "/credentials?limit=250" + (f"&cursor={cursor}" if cursor else ""))
        for c in page.get("data", []):
            creds.setdefault((c["name"], c["type"]), c["id"])
        cursor = page.get("nextCursor")
        if not cursor:
            break
    existing = {}
    cursor = None
    while True:
        page = api(base, key, "GET", "/workflows?limit=250" + (f"&cursor={cursor}" if cursor else ""))
        for w in page.get("data", []):
            if not w.get("isArchived"):
                existing.setdefault(w["name"], w["id"])
        cursor = page.get("nextCursor")
        if not cursor:
            break
    missing = set()
    # The monitoring workflow goes first, so every other workflow can name it as its Error Workflow.
    workflows = sorted(workflows, key=lambda w: w["name"] != error_workflow)
    error_id = None
    for wf in workflows:
        body = copy.deepcopy(wf)
        if error_id:
            body["settings"]["errorWorkflow"] = error_id
        for n in body["nodes"]:
            for t, ref in (n.get("credentials") or {}).items():
                cid = creds.get((ref.get("name"), t))
                if cid:
                    ref["id"] = cid
                else:
                    missing.add(f"{ref.get('name')} ({t})")
        if wf["name"] in existing and update:
            api(base, key, "PUT", f"/workflows/{existing[wf['name']]}", body)
            wid = existing[wf["name"]]
            print(f"  updated: {wf['name']} (id {wid})")
        elif wf["name"] in existing:
            wid = existing[wf["name"]]
            print(f"  skipped: {wf['name']} already exists (id {wid}); pass --update to replace it")
        else:
            wid = api(base, key, "POST", "/workflows", body).get("id")
            print(f"  created: {wf['name']} (id {wid})")
        if wf["name"] == error_workflow:
            error_id = wid
    if missing:
        print("\nNo credential with these names yet, so those nodes need one selected (or run scripts/create-credentials.py first):")
        for m in sorted(missing):
            print(f"- {m}")


# ---------------------------------------------------------------- main

def main():
    argv = sys.argv[1:]
    opt = lambda name, default: argv[argv.index(name) + 1] if name in argv else default
    cfg = load(opt("--config", os.path.join(HERE, "config.json")))
    out_root = opt("--out", HERE)
    system = load(os.path.join(HERE, "system.json"))
    plan = cfg.get("plan", "full")
    if "--plan" in argv:
        plan = argv[argv.index("--plan") + 1]
    if plan not in ("starter", "full"):
        raise SystemExit("--plan is starter or full")
    prefix = cfg["n8n"]["webhook_prefix"]

    built = {}
    workflows = []
    for spec in system["templates"]:
        if plan == "starter" and not spec.get("starter"):
            continue
        wf, paths, found = build_template(spec, {**cfg, "plan": plan})
        built[spec["slug"]] = {"paths": paths, "lanes": found, "workflow": wf}
        workflows.append((spec["phase_folder"], slug(spec["title"]), wf))

    glue_in = [k for k, g in system["glue"].items() if plan == "full" or g.get("starter")]
    generated = {
        "routes": routes(system, built, cfg, glue_in),
        "jobs": jobs(system, built, cfg, glue_in),
        "queues": queues(system, built, cfg, glue_in),
        "phases": [{"phase": p["phase"], "name": p["name"]} for p in system["phases"]],
        "stages": stages(system, built),
    }
    if any(not re.match(r"^[CG][A-Z0-9]{8,}$", str(c)) for c in cfg["channels"].values()):
        print("Note: some channels in config.json are names (#...), not IDs. Use channel IDs before you go live, so cards update in place.")
    for gname in glue_in:
        g = system["glue"][gname]
        wf = build_glue(gname, cfg, system, generated)
        workflows.append((g["phase_folder"], gname, wf))

    out_dir = os.path.join(out_root, "workflows")
    if os.path.isdir(out_dir):
        for root, _, files in os.walk(out_dir):
            for f in files:
                if f.endswith(".json"):
                    os.remove(os.path.join(root, f))
    for folder, name, wf in workflows:
        save(os.path.join(out_dir, folder, name + ".json"), wf)
    save(os.path.join(out_root, "supabase", "schema.sql"), schema(system, built, generated["queues"]))
    save(os.path.join(out_root, "credentials.json"), credentials(system, [w for _, _, w in workflows]))
    save(os.path.join(out_root, "slack-app-manifest.yml"), manifest(cfg, prefix))
    print(f"Built the {plan} plan: {len(workflows)} workflows in workflows/, supabase/schema.sql, credentials.json and slack-app-manifest.yml.")

    if "--import" in argv:
        monitor = next((f"Store {t['phase']} · {t['title']}" for t in system["templates"] if t.get("error_workflow") and t["slug"] in built), None)
        import_all([w for _, _, w in workflows], "--update" in argv, monitor)


if __name__ == "__main__":
    main()
