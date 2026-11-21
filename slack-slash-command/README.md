# Slack slash command

An n8n template that gives your workflows one Slack slash command, `/store`. Anyone in your workspace can see what's waiting for a decision, and the people you choose can run any workflow on your list now instead of waiting for its schedule. The command answers inside Slack's three seconds, then posts in the channel when the job finishes or fails.

- **Receive and check**: Slack posts the command to a webhook. The workflow reads the raw body, checks Slack's signature and the request's age, and that it came from your app and workspace. Anything else gets a 401.
- **Help**: `/store` or `/store help` lists the commands and every job you've set up.
- **Status**: `/store status` counts the cards waiting in each queue of the [Slack approvals](../slack-approval-workflow-n8n/) template, with how old the oldest is and a private button to its review page.
- **Run**: `/store run <job> [args]` checks the person and the job against your lists, says it's starting, runs the job's workflow and waits, then posts "finished in 4 min" or the error in the channel and logs the run.

The full walkthrough is in the guide: [How to Run Any n8n Workflow From a Slack Slash Command](https://www.reganmcgregor.com.au/slack-slash-command-n8n/).

## What you need

- n8n with Data Tables (self-hosted or Cloud) on a public HTTPS URL, because Slack has to reach the webhook. Tested on n8n 2.46.
- A Slack app you can add a slash command to. Slack's free plan works. If you use the Slack approvals template, add the command to that app, so one signing secret signs everything and the review page accepts the status links.
- For `/store status`: the Slack approvals template's `approvals` table. Without it, help and run still work and status says nothing is waiting.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Create the slash command

In your Slack app at [api.slack.com/apps](https://api.slack.com/apps), open **Slash Commands** > **Create New Command**:

| Field | Value |
|---|---|
| Command | `/store` |
| Request URL | The production URL of **Slack sends /store** (open the node, then **Production URL**) |
| Short Description | See what's waiting and run n8n jobs now |
| Usage Hint | `[help \| status \| run <job>]` |

Save, then **reinstall your app** when Slack asks: the command adds the `commands` scope. Copy the **Signing Secret** and **App ID** (Basic Information) and your workspace ID (it starts with `T`).

Starting a new app instead? Create it **From a manifest** with this, using your n8n URL:

```yaml
display_information:
  name: Store
features:
  bot_user:
    display_name: Store
    always_online: false
  slash_commands:
    - command: /store
      url: https://your-n8n.example.com/webhook/slack-command
      description: See what's waiting and run n8n jobs now
      usage_hint: "[help | status | run <job>]"
      should_escape: false
oauth_config:
  scopes:
    bot:
      - commands
settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```

The command needs no bot token: replies go back through the webhook response and Slack's `response_url`.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Sign the request, Sign a page link | Crypto | Hmac Secret = your Slack app's Signing Secret |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Select the Crypto credential on both nodes in the table above.
3. Run **Run once to set up**. It creates the `command_runs` data table.
4. Fill in **Command settings** (below), publish the workflow, and paste the production URL of **Slack sends /store** into the command's Request URL.

## Settings

**Command settings**:

| Setting | What it does |
|---|---|
| `slack_app_id`, `slack_team_id` | Your app's ID and your workspace ID. Commands from any other app or workspace get a 401. Blank accepts any |
| `approver_ids` | Slack user IDs that may run jobs and get the review page button. Empty means anyone in the workspace |
| `page_url` | The production URL of the Slack approvals template's **Review page** webhook |
| `link_hours` | How long a review page link works (8) |
| `jobs` | The only workflows `/store run` can start: `key` (what people type), `label` (what Slack shows) and `workflow_id` (from the workflow's URL) |

```json
"jobs": [
  { "key": "prices", "label": "Check competitor prices", "workflow_id": "aBcD1234eFgH5678" },
  { "key": "feed", "label": "Rebuild the Google Shopping feed", "workflow_id": "iJkL9012mNoP3456" }
]
```

## Let a workflow run from Slack

Each job's workflow needs a **When Executed by Another Workflow** trigger with **Input data mode** set to **Accept all data**, wired into the same first node as its Schedule Trigger. It receives one item:

```json
{ "run_source": "slack", "requested_by": "regan", "args": "15482774847741" }
```

`args` is everything typed after the job's key, so `/store run prices 15482774847741` can check one product instead of all of them. Publish the job's workflow too: an unpublished workflow can't be run this way.

The command waits for the job so it can say how it went. Slack's `response_url` works for 30 minutes, so a longer job still runs to the end, but its "finished" line won't post; let the job post its own summary.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with Postgres nodes on your Supabase database: **Count what's waiting** reads the approvals template's Supabase `approvals` table, and **Log the run** writes to `command_runs`.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py slack-slash-command --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on **Create command_runs**, **Count what's waiting** and **Log the run**.
4. Run **Run once to set up**, or run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Slack slash command" n8n template in ./slack-slash-command.

1. Read slack-slash-command/README.md, SETUP.md and slack-slash-command/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json), and whether I already use the Slack approvals template.
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Walk me through adding /store to my Slack app (or creating one from the manifest in the README) with the production URL of "Slack sends /store". Tell me exactly where to click.
4. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py slack-slash-command
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
5. Ask me which of my workflows I want to run from Slack. For each one, add a When Executed by Another Workflow trigger (Accept all data) next to its schedule, and add it to jobs in Command settings with a short key and label.
6. Walk me through the rest of Command settings one value at a time, then run the Setup lane and publish.
7. Have me type /store help, /store status and /store run <job> in Slack and check each reply with me.
8. Stop and ask me whenever something doesn't match the README.
```
