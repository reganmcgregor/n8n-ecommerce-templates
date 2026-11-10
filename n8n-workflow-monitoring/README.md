# n8n workflow monitoring

An n8n template that catches the four ways an automation goes quiet: it **errors**, it **never starts**, it **runs but does nothing**, or the monitor itself stops. You get one Slack alert per outage instead of one per failure, a line when it's fixed, and an all-clear every morning, so silence looks wrong.

- **Setup** creates three data tables: `monitor_failures`, `monitor_runs` and `monitor_watch`.
- **Catch** is the error workflow. Every workflow that names this one under *Settings > Error workflow* reports its failures here. Each failure is saved, then alerted once per workflow per cooldown, with the node, the error and a link to the execution. Turn on the email fallback and an alert still arrives when Slack is the thing that's down.
- **Log a run** (optional): call it at the end of a workflow with the number of items it handled, so a run that succeeds with nothing in it can alert.
- **Watch** runs every 15 minutes. It reads every published workflow with a Schedule Trigger through the n8n API, works out how often each should run, and flags **stalled** (no run within the expected gap), **failing** (a burst of errors) and **empty** (logged runs with too few items) workflows, then says when each one **recovers**.
- **Digest** runs every morning at 08:00. It posts the all-clear, or what's wrong and the day's failures, plus the published workflows with no error workflow set. It can ping an outside heartbeat check, and it deletes old rows.
- **Demo** fails on purpose, so you can see an alert without breaking a real workflow.

The full walkthrough is in the guide: [n8n Error Handling: Catch Failed, Stalled and Empty Workflows Before Anyone Else Does](https://www.reganmcgregor.com.au/n8n-error-handling/).


## What you need

- n8n with Data Tables, self-hosted or a paid n8n Cloud plan (the API isn't available on the Cloud free trial). Tested on n8n 2.46.6.
- An n8n API key for the Watch and Digest lanes, which read your workflows and executions through the API. In **Settings > n8n API > Create an API key**, choose the **Read only** scopes if the dialog offers them (without scopes the key has full access, which works too, because this template only reads): they include `workflow:list`, `workflow:read`, `execution:list` and `execution:read`, which is all this template uses. Keys expire after 30 days unless you pick another expiry; when the key expires, Watch and Digest fail, and Catch tells you so.
- A Slack app with the bot scope `chat:write` (add `chat:write.public` to post in channels the bot hasn't joined), and its bot token. Or swap the Slack nodes for email, Telegram or Microsoft Teams.
- Optional: an SMTP account for the email fallback (off by default), and a free heartbeat check such as [Healthchecks.io](https://healthchecks.io/) for when n8n itself is down.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get published workflows, Get recent executions, Get workflows for the digest | n8n API | An API key for the instance you're watching, and its API URL (`https://your-n8n.example.com/api/v1`) |
| Post the alert, Post the health alert, Post the digest | Slack API | Your bot token |
| Email the alert, Email the health alert, Email the digest | SMTP | Optional, and the three nodes ship disabled. Enable them (select, then **D**) and add your SMTP host, user and password |

## Import

1. In n8n, create a workflow, open the `...` menu, choose **Import from File** and pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential. n8n won't publish a workflow with an enabled node that has no credential, which is why the Email nodes ship disabled.
3. Fill in the settings below, then open **Run once to set up** and click **Execute workflow**.
4. Publish the workflow. It has to be published before any workflow can call **Log a run**, and for Watch and Digest to run on schedule.
5. In every workflow you want watched: **Settings > Error workflow >** this workflow, then save.

## Settings

**Catch settings**

| Setting | What it does |
|---|---|
| `slack_channel` | A channel name such as `#n8n-alerts`, or its ID |
| `alert_email`, `from_email` | Where the alert goes if the Slack post fails (only with the Email nodes enabled), and who it's from |
| `cooldown_minutes` | One alert per workflow in this window (120). Later failures are saved, and Watch reports a burst |
| `timezone` | For the time on each message |

**Watch settings**

| Setting | What it does |
|---|---|
| `slack_channel`, `alert_email`, `from_email`, `timezone` | As above |
| `n8n_url` | Your n8n address, for the Executions link on each line |
| `only_tag` | Watch only workflows with this tag. Blank watches every published workflow |
| `ignore_tag` | Never watch workflows with this tag (`no-monitor`) |
| `grace_ratio`, `grace_min_minutes` | A workflow is stalled after its expected gap plus the larger of `grace_min_minutes` (30) or the gap × `grace_ratio` (0.5). An hourly workflow is stalled after 90 minutes, a daily one after 36 hours |
| `failing_threshold` | Failed runs in the last hour that count as a burst (5) |
| `cooldown_minutes` | How long before the same issue alerts again (120) |

**Digest settings**: `slack_channel`, `alert_email`, `from_email`, `only_tag`, `ignore_tag` and `timezone` as above; `heartbeat_url` (pinged after every digest, blank = off); `keep_days` (rows older than this are deleted, 30).

The schedules live on the triggers: **Every 15 minutes** and **Every morning** (08:00 in the workflow's time zone, Workflow settings > Timezone).

## Tune a workflow

Watch adds a row to `monitor_watch` for every workflow it finds, with its schedule and the gap it worked out. Edit these columns on a row; Watch never overwrites them:

| Column | What it does |
|---|---|
| `override_gap_minutes` | Use this gap instead of the one worked out from the schedule. Also the way to watch a webhook workflow you expect to run, say, once a day: add a row with its `workflow_id` and a gap |
| `min_items`, `empty_runs_before_alert` | For workflows that call Log a run: alert when the last `empty_runs_before_alert` runs (3) all had fewer than `min_items` |
| `enabled` | `false` stops watching it |

## Log runs that finish with nothing in them

n8n marks a run that fetched zero rows as a success. To catch that, add an **Execute Workflow** node at the end of the workflow:

| Setting | Value |
|---|---|
| Source | Database |
| Workflow | This monitoring workflow (By ID) |
| Mode | Run once with all items |
| Wait for sub-workflow completion | Off |
| `workflow_id` | `{{ $workflow.id }}` |
| `workflow_name` | `{{ $workflow.name }}` |
| `items` | The count from the node that matters, such as `{{ $('Get the feed').all().length }}` |
| `note` | Optional |

Then set `min_items` on that workflow's row in `monitor_watch`.

## Test it

1. Point `slack_channel` at a test channel and run Setup.
2. Run **Try it by hand**. The demo fails, but no alert arrives: the Error Trigger only fires for automatic runs.
3. Enable **Every 5 minutes (demo)** and publish. Within 5 minutes you get "n8n workflow monitoring (template) failed". After the next run you get nothing (the cooldown), but `monitor_failures` has two rows. Disable the demo trigger again and publish.
4. Set `override_gap_minutes` to `1` on any watched workflow's row and run **Every 15 minutes** by hand: it's stalled. Clear the value and run it again: it's recovered.
5. Run **Every morning** by hand to see the digest.

## Executions

Watch is one execution per run however many workflows it checks: 2,880 a month every 15 minutes, 720 hourly. On n8n Cloud, set **Every 15 minutes** to hourly. Catch adds one per failure, Log a run one per logged run, Digest 30 a month.

## Troubleshooting

### A workflow fails but no alert arrives

Check, in order: its Settings > Error workflow names this workflow; the run was automatic (manual runs never reach the Error Trigger); this workflow is saved; and the workflow didn't alert in the last `cooldown_minutes` (look in `monitor_failures`).

### A workflow shows as stalled but it runs

Watch counts executions n8n has saved. If the workflow doesn't save successful production executions (Workflow settings > Save successful production executions), or your instance prunes executions sooner than the workflow runs, Watch can't see the runs. The digest lists workflows that don't save successful runs.

### "Schedule not understood" in the digest

The cron expression uses something Watch doesn't read (such as `L`, `W` or `#`), or runs less than once in two months. Set `override_gap_minutes` on its row.

### Calling Log a run fails with "references workflow ... which is not published"

Publish this workflow first. A published workflow can't call an unpublished one.

### A Slack post failed and no alert arrived

With the email fallback off, a failed Slack post (a revoked token, a renamed channel, a Slack outage) leaves the failure in `monitor_failures` with `alerted = false`, and nothing else. Enable the three Email nodes so the alert has a second way out. If Catch itself fails, n8n doesn't run it again (tested on 2.46.6): the failure row is already saved and the execution shows red.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. The Digest deletes rows older than `keep_days`; self-hosters can also raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`, or use the Supabase version.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the credentials: run `python3 scripts/create-credentials.py n8n-workflow-monitoring --supabase` from the repo root, or create them by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the three tables and their indexes if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

The tables have the same columns as the data tables, plus `id`, `createdAt` and `updatedAt`. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "n8n workflow monitoring" template in ./n8n-workflow-monitoring.

1. Read n8n-workflow-monitoring/README.md, SETUP.md and n8n-workflow-monitoring/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json), and whether I want the email fallback.
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py n8n-workflow-monitoring
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through each settings node one value at a time: say what it does, suggest a value for my setup, and wait for my answer. Ask whether I want to watch every published workflow or only ones with a tag.
5. Run the Setup lane and check its output with me, then have me publish the workflow.
6. List my published workflows and help me set this workflow as the Error workflow on each one I want watched (Settings > Error workflow). Don't change any other setting on them.
7. Test it with the Demo lane as the README describes, then make sure the demo trigger is disabled again.
8. Run Watch and Digest once by hand and read the results with me.
9. Stop and ask me whenever something doesn't match the README.
```
