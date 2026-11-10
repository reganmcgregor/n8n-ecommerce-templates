# Shopify repricing engine

An n8n template that sets every Shopify price from three rules you can read: 1 cent under the cheapest trusted competitor, your RRP (the compare-at price), or cost plus a multiplier for the product type. It never prices under break-even or over RRP, every price carries a one-line reason, and it stops itself when too many prices move a lot at once.

- **Setup** creates the `pricing_rules`, `price_decisions`, `price_changes` and `pricing_runs` data tables and adds a `default` pricing rule.
- **Decide** (hourly at :30) reads every variant's price, compare-at price and Cost per item, the rule for its product type, and the competitor prices from the [competitor price monitoring template](../competitor-price-monitoring/). It works out one decision per variant: the rule, the break-even floor, the proposed price, any flags and the reason. Only decisions that changed are saved.
- **Push** sends the changes to Shopify with `productVariantsBulkUpdate`, price only. Live prices under break-even (floor fixes) go first and always go out. Then live changes, biggest move first, up to `per_run_cap`, and drafts in a lane of their own. When too many live prices move 50% or more, or the share of variants with no cost jumps, live changes stop and Slack hears why. Every change is logged with its old price.
- **Review** (hourly at :40) posts a Slack card for each held price (a flag listed in `hold_on_flags`) with Apply, Hold and Lock.
- **Click** checks Slack's signature on every click. **Apply** reprices that variant there and then, with the hold lifted. **Hold** keeps today's price until the proposal changes. **Lock** takes the variant out of automation. **Revert** puts the old price back and locks the variant.
- **Report** (daily at 08:00) posts the last 24 hours: changes, floor fixes, anything waiting on you, and the biggest moves with Revert. A quiet day posts a one-line all-clear.

There's no AI model in it. Every price comes from plain code you can read in **Decide prices**.

The full walkthrough is in the guide: [How to Build a Shopify Repricing Engine With n8n](https://www.reganmcgregor.com.au/shopify-repricing/).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.
- A Shopify app with the `read_products`, `write_products` and `read_inventory` scopes (Cost per item lives on the inventory item), and its client ID and secret.
- Cost per item filled in on your variants. The [automated inventory management template](../automated-inventory-management/) keeps it in step with a supplier feed.
- Optional: the [competitor price monitoring template](../competitor-price-monitoring/) on the same n8n instance. Without it, every product prices on RRP or cost plus.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- No AI model and no paid APIs.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Click | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the alert, Post the card, Close the old card, Update the message, Reply in thread, Post the digest | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

Every lane starts with a settings node holding the same JSON (**Pricing settings**, **Review settings**, **Click settings**, **Report settings**). Fill in one and paste it into the others.

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `currency`, `locale` | How prices are written in reasons, cards and the digest, such as `AUD` and `en-AU` |
| `product_query` | Which variants are priced, in Shopify's search syntax. Narrow it to test, such as `tag:reprice-test` |
| `prices_include_tax`, `tax_rate` | Whether your shelf prices include tax (`tax_rate` 0.1 for 10%). Cost per item is always ex tax |
| `market_shows_tax`, `tax_exclusive_domains` | Whether competitor prices include tax, and trade sites whose prices don't, as in the competitor template |
| `free_shipping_over`, `shipping_you_absorb` | Your free-shipping threshold (`null` for none) and what an order costs you to ship. The floor counts the shipping only when the price clears the threshold |
| `price_ending` | Cost-plus prices round up to this ending, such as `0.95`. `null` rounds to the cent |
| `use_competitor_prices` | Read the competitor template's `competitor_listings` table |
| `min_confidence`, `max_price_age_days` | A competitor price counts only when its match is this sure and it was checked this recently |
| `outlier_below_median` | With three or more trusted prices, ignore any under this share of the median (0.6 = 60%) |
| `exclude_competitors` | Domains or seller names that are never counted, such as your own |
| `large_move_pct` | A change this big (in %) is flagged `large_move` |
| `hold_on_flags` | Flags that hold a price for a Slack card instead of applying it. `[]` applies everything |
| `per_run_cap`, `draft_lane_cap` | The most live and draft changes one run sends; the rest wait for the next run |
| `stop_min_changes`, `stop_min_large_moves`, `stop_large_move_share_pct` | Stop live changes when at least this many are due, at least this many move `large_move_pct` or more, and they're more than this share of the run |
| `stop_missing_cost_jump_pct` | Stop live changes when the share of variants with no cost rises by more than this since the last full run |
| `cards_per_run` | The most Slack cards one Review run posts |
| `digest_moves` | How many of the biggest moves the digest lists with Revert |
| `slack_review_channel`, `slack_alert_channel`, `slack_digest_channel` | Where cards, run alerts and the digest go (a name such as `#pricing` or a channel ID) |
| `dry_run` | While true, nothing is sent to Shopify: decisions stay `pending`, and Apply and Revert reply in the thread instead |

## Pricing rules

`pricing_rules` has one row per product type (Shopify's **Product type** field, matched without case), plus `default` for everything else.

| Column | What it does |
|---|---|
| `margin_floor_pct` | The margin the floor protects, in %. 0 = break-even |
| `cost_plus_multiplier` | Cost x this (plus tax where prices include it) when there's no RRP |
| `fee_pct`, `fee_fixed` | Your payment provider's card fee, such as 2 and 0.30 |
| `undercut_amount` | How far under the cheapest trusted competitor, such as 0.01 |
| `cost_change_pct` | Flag `cost_change` when cost has moved this much (in %) since the price was last set |
| `notes` | Yours |

## How a price is chosen

1. **Target.** The cheapest trusted competitor minus `undercut_amount`, when that's under RRP. Otherwise RRP (the compare-at price). Without a compare-at price, cost x `cost_plus_multiplier`, rounded up to `price_ending`. No cost means no price: the variant is skipped.
2. **Floor.** The lowest price that covers cost, the margin floor, card fees and any shipping you absorb, after tax. A target under the floor becomes the floor (rule `at_floor`).
3. **Flags.** `floor_breach` (a competitor is under your floor), `above_ceiling` (break-even is above RRP), `cost_change` and `large_move`.
4. **Status.** `unchanged`, `pending` (goes out this run), `held` (waiting for a card), `kept` (Hold), `locked`, `skipped`, then `applied` or `failed`. A held price stays held until someone decides or the proposal changes.
5. **Floor fix.** A live price already under break-even goes up this run, whatever its status: to the proposal, or to the floor when the proposal is held or the variant is locked.

The template only ever writes the price. Your compare-at price stays as you set it, and Shopify shows it as a was-price only while it's above the price.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get four data tables, with one `default` row in `pricing_rules`. Add a row for each product type that needs its own margin or multiplier.

## Test on a few products

1. Tag a few products `reprice-test` and set `product_query` to `tag:reprice-test`. Point the three Slack channels at a test channel. Keep `dry_run` on.
2. Run **Run Decide now**. Open `price_decisions`: each row has its rule, floor, proposed price and the reason in `explanation`.
3. Turn `dry_run` off and run Decide again. Check the prices in Shopify admin and the rows in `price_changes`.
4. Publish the workflow, run **Run Review now** and try Apply, Hold and Lock on a card. Run **Run Report now** and try Revert.
5. Put `product_query` back and publish. The first full run saves a decision for every variant, so it takes longer than the hourly runs after it.

## Schedule

Publish the workflow. Decide runs hourly at :30, Review at :40 and Report daily at 08:00, in the workflow's time zone (Workflow settings > Timezone). Run Decide after the competitor scan and any cost sync: move its schedule if those run at :30. Set an Error Workflow too, so a crashed run reaches you.

Executions: about 49 schedule runs a day (1,470 a month), plus one webhook run per Slack click. On n8n Cloud, daily repricing (change **Every hour at :30** and **Every hour at :40** to once a day) is 60 a month.

## Troubleshooting

### Decide fails with "pricing_rules has no default row"

Run the Setup lane, or add a row with `product_type` `default` yourself.

### A product isn't repriced

Look at its row in `price_decisions`. `skipped` means no Cost per item; `locked` means someone locked it (set `locked` to false to unlock); `held` and `kept` wait for a person. A variant `product_query` doesn't match has no row.

### Competitor prices are ignored

A price counts only with `status` `ok` or `robots_disallowed`, not out of stock, `confidence` of at least `min_confidence`, checked within `max_price_age_days`, not in `exclude_competitors` and not an outlier. The digest counts variants whose competitor prices are all too old.

### The run stopped

The alert gives the reason. Check your Cost per item values and the competitor scan, then run Decide again. Floor fixes and drafts still go out while live changes are stopped.

### A change failed

Shopify answers HTTP 200 even when it refuses a change, so **Read results** reads the body and records the error in `price_decisions.error`. The change is tried again next run.

### Nothing happens when I click a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret. A click on a card a newer proposal replaced stops at **Still the same proposal?**.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise use the Supabase version.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py shopify-repricing-engine --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`pricing_rules`, `price_decisions`, `price_changes`, `pricing_runs`) if they don't exist and adds the `default` rule. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first. **Get competitor listings** reads the competitor template's `competitor_listings` table in the same database.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the columns the workflow upserts on. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Shopify repricing engine" n8n template in ./shopify-repricing-engine.

1. Read shopify-repricing-engine/README.md, SETUP.md and shopify-repricing-engine/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py shopify-repricing-engine
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Check with me that my variants have Cost per item filled in, whether my compare-at prices are real RRPs, and whether I run the competitor price monitoring template.
5. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. Then help me add a pricing_rules row for each product type that needs its own margin.
6. Run the Setup lane. With dry_run on and product_query limited to 5 tagged products, run Decide and check every explanation in price_decisions with me before anything writes to my store.
7. Stop and ask me whenever something doesn't match the README.
```
