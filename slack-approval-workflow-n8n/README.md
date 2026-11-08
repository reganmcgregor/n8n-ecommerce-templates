# Slack approvals with Block Kit

An n8n template that asks a person in Slack before any workflow changes something. Each request becomes a Block Kit card with Before and After. The reviewer can Approve, Edit the value in a modal, Reject with a reason, or open a page that lists everything waiting. Alerts get buttons that do the next step (Match price, Snooze, Ignore), and routing cards send work to the right team. The card only changes once the change has landed, and it closes itself when the item changes somewhere else first.

- **Setup** creates the `approvals` data table. For the Shopify demo it also subscribes the Sync webhook to product updates.
- **Ask**: any workflow calls this one with Execute Workflow. It skips an item that already has an open card, saves a row, posts the card and returns at once, so nothing sits waiting.
- **Click** is your Slack app's Request URL. It checks Slack's signature and the request's age, your app, workspace and approver list, and that the row is still pending, before it does anything. Edit and Reject open a modal; the other buttons go to Apply.
- **Apply** runs your apply workflow, or the demo Shopify branch (product title or variant price) after checking the live value hasn't changed. Only then does it update the card. A failure keeps the buttons and replies in the thread.
- **Page**: Open in page sends whoever clicked a private link, signed for 8 hours, to a page of everything pending.
- **Remind** runs daily: one thread nudge, expiry after a week, snoozed alerts back with their buttons.
- **Sync** closes open cards whose item changed somewhere else: from any workflow, or from Shopify's product update webhook.

The full walkthrough is in the guide: [Build Human-in-the-Loop Slack Approvals With n8n and Block Kit](https://www.reganmcgregor.com.au/slack-approval-workflow-n8n/).

## What you need

- n8n with Data Tables (self-hosted or Cloud) on a public HTTPS URL, because Slack has to reach the webhook. Tested on n8n 2.46.
- A Slack app with Interactivity turned on, the bot scopes `chat:write` and `chat:write.public`, its bot token and its signing secret. Slack's free plan works; it keeps 90 days of history, so the data table is your record of who decided what.
- For the demo Shopify branch only: a Shopify app with `read_products` and `write_products`, and its client ID and secret.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Create the Slack app

A Slack app has one Interactivity Request URL, so give this template its own app (or route its `approval_` buttons from the workflow that owns your existing URL). At [api.slack.com/apps](https://api.slack.com/apps), click **Create New App**, choose **From a manifest**, pick your workspace and paste this, with your n8n URL in `request_url`:

```yaml
display_information:
  name: Approvals
features:
  bot_user:
    display_name: Approvals
    always_online: false
oauth_config:
  scopes:
    bot:
      - chat:write
      - chat:write.public
settings:
  interactivity:
    is_enabled: true
    request_url: https://your-n8n.example.com/webhook/slack-approvals
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```

Then **Install to Workspace**, copy the **Bot User OAuth Token** (OAuth & Permissions) and the **Signing Secret** (Basic Information), and note the **App ID** (Basic Information) and your workspace ID (it starts with `T`) for **Click settings**.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Post the card, Open the edit modal, Open the reject modal, Close the card, Reply with the error, Nudge in the thread, Show expired on the card, Put the buttons back, Say it is back, Show it changed | Slack API | Your bot token |
| Sign the request, Sign a page link, Check the link, Check the page signature | Crypto | Hmac Secret = your Slack app's Signing Secret (it signs the page links too) |
| Get Shopify token for Setup, Get Shopify token | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` (demo only) |
| Check Shopify's signature | Crypto | Hmac Secret = your Shopify app's client secret, which Shopify signs webhooks with (demo only) |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. Fill in the settings below, run Setup, then publish the workflow.
4. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**). Slack only checks the URL saves; it sends nothing until the first click.

## Settings

**Setup settings**: `store_domain` (your permanent `*.myshopify.com` domain; leave `your-store.myshopify.com` to skip the Shopify demo) and `sync_webhook_url` (the production URL of **Shopify product updated**).

**Ask settings**: `slack_channel` (a channel name such as `#approvals`, or its ID) and `page_button` (adds Open in page to every card).

**Kinds**: one entry per kind of card. `type` is `approval` (Approve, Edit, Reject), `alert` (one `action` button with an optional confirm dialog, a Snooze menu of `snooze_hours`, Ignore) or `route` (one button per entry in `routes`, plus Ignore). `value_prefix` goes in front of values on alert cards, such as a currency symbol. `hint` is a grey line above the buttons that says what each one does. `large_image: true` shows the caller's image full width (a pin, a chart) instead of as a thumbnail. The template ships with `product_title`, `price_alert` and `content_decay`.

**Click settings**:

| Setting | What it does |
|---|---|
| `slack_app_id`, `slack_team_id` | Your app's ID and your workspace ID. Clicks from any other app or workspace stop here. Blank accepts any |
| `approver_ids` | Slack user IDs that may decide. Empty means anyone in the channel; anyone else gets a private "Only approvers can decide these cards" |
| `reject_reasons` | The choices in the Reject modal (a reason is optional) |
| `page_url` | The production URL of **Review page** |
| `link_hours` | How long a page link works |

**Apply settings**: `store_domain` (the demo Shopify branch) and `timezone` (for the time on decided cards).

**Page settings**: `decide_url` (the production URL of **Page decision**) and `timezone`.

**Remind settings**: `remind_after_hours` (one thread nudge, 24 by default) and `expire_after_days` (7 by default).

**Sync settings**: `statuses_to_close` (pending, processing and snoozed rows close when the source changes).

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get the `approvals` data table; running it again keeps your rows. With the Shopify demo on, it also subscribes **Shopify product updated** to `products/update` (Shopify refuses a second identical subscription with "Address for this topic has already been taken", which is fine).

## Ask for approval from your workflow

Add an **Execute Workflow** node to the workflow that proposes the change, pick this workflow, and send one item per approval with these fields:

| Field | What it is |
|---|---|
| `lane` | `ask` (the default, so you can leave it out) |
| `kind` | A key in **Kinds**, such as `product_title` |
| `item_id` | The thing being changed, such as a Shopify product GID |
| `item_label` | What the card calls it |
| `current_value`, `proposed_value` | Before and After. On alerts, the value now and the value the action sets |
| `context` | One line under the card (who asked), or the alert's fact |
| `image_url`, `link` | Optional image (a thumbnail, or full width for kinds with `large_image`), and a link on the item's name |
| `image_title` | Optional caption over a full-width image, such as `Impressions, last 12 weeks` |
| `details` | Optional `{ label: value }` pairs. Short values sit side by side, long ones get their own line. Emoji and arrows make a change easy to see: `'1,900   :large_green_circle: ▲ 169%'` |
| `max_length`, `must_include` | Optional checks on an edit, such as `70` and `RLC-820A` (comma-separated) |
| `apply_workflow_id` | Optional: the workflow that applies the decision (below) |

It returns straight away with `asked` (row ids, channel and ts), `skipped` (items that already had an open card) and `failed`.

**Send a test card** posts one title approval and one price alert for a Reolink RLC-820A. Change the product and variant IDs in **Test cards** to ones on your store.

## Apply the decision in your own workflow

Give a request an `apply_workflow_id` and Apply calls that workflow for every decision on it, with `row_id`, `kind`, `item_id`, `item_label`, `decision` (`approve`, `edit`, `reject`, `action`, `ignore`, `snooze` or `route_<id>`), `final_value`, `reason`, `decided_by` (a Slack user ID) and `context`. Use an Execute Workflow Trigger set to accept all data, and publish that workflow: a published workflow can't call an unpublished one. Return `{ "ok": false, "error": "..." }`, or let it fail, to keep the card open and post the error in its thread. A reject reason or a routing choice arrives the same way, so the caller can write a new draft from the feedback or create the card on the other team's board.

Without an `apply_workflow_id`, the demo kinds write to Shopify: `product_title` sets the product title and `price_alert` sets the variant price, each after reading the live value first.

## Close a card from another system

When a workflow sees an item change somewhere else, call this workflow with `lane: close`, `item_id`, `new_value`, `source` (shown on the card, such as `Shopify`) and optionally `kind`. Open cards for that item whose value no longer matches close as "Already changed in ...". The demo **Shopify product updated** webhook does this for product titles and variant prices, after checking Shopify's HMAC.

## Test it

1. Point `slack_channel` at a test channel and `store_domain` at a development store, run Setup, then **Send a test card**.
2. Publish the workflow and set the Request URL. Press **Edit** on the title card, change the title and save: the title changes in Shopify and the card says "Edited and approved by @you". Try an edit without the model number to see the error under the field.
3. Snooze the price alert, then press **Match price** after it comes back, or **Ignore** it.
4. Change a title in Shopify admin while a card is open: the card closes as "Already changed in Shopify".
5. Press **Open in page** to get your private link.

## Schedule

Publish the workflow. Remind runs daily at 09:00 in the workflow's time zone (Workflow settings > Timezone), and the three webhooks only answer while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: each card is one execution to ask, plus one or two per decision (the click, a modal, and Apply as a sub-workflow, which doesn't count towards n8n Cloud's quota). Remind is 30 runs a month; Sync is one run per product update in Shopify.

## Troubleshooting

### Every click stops at Signature valid?

The Crypto credential on **Sign the request** doesn't hold this app's signing secret, or something sits between **Slack button click** and **Read the click**. The raw body has to be read first: a Set node in between drops it.

### Slack shows "This app responded with status code 404"

The workflow isn't published, or the Request URL is the test URL rather than the production one.

### Edit or Reject doesn't open the modal

Slack's `trigger_id` lasts 3 seconds and works once. Keep the two **Open the ... modal** nodes straight after **Route the click**, with nothing slow before them.

### A second click does nothing

That's on purpose. **Get pending row** only finds pending rows, so a second click, a Slack retry, or a click on a card someone decided on the page stops there.

### The card says "That didn't apply"

Apply couldn't make the change (the thread reply has the reason), so the row went back to pending and the buttons still work. If the reason is "Workflow is not active", publish your apply workflow.

### A card closed as "Already changed in Shopify"

The live value no longer matched the card's Before, so nothing was overwritten. Ask again if you still want the change.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the table to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the queue in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py slack-approval-workflow-n8n --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the `approvals` table and two indexes if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

The table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Slack approvals" n8n template in ./slack-approval-workflow-n8n.

1. Read slack-approval-workflow-n8n/README.md, SETUP.md and slack-approval-workflow-n8n/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json), and whether I want the Shopify demo.
2. Walk me through creating the Slack app from the manifest in the README, with my n8n URL in request_url. Tell me exactly where to click.
3. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
4. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py slack-approval-workflow-n8n
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
5. Walk me through every settings node and the Kinds node one value at a time: say what the value does, suggest one for my setup, and wait for my answer.
6. Run the Setup lane and check its output with me.
7. Send one test card to a test channel, publish the workflow, and have me press each button once. Nothing should write to my store until I approve a card, and only on a development store first.
8. Show me how to call it from one of my own workflows with Execute Workflow.
9. Stop and ask me whenever something doesn't match the README.
```
