# Automated inventory management

An n8n template that keeps Shopify stock in step with a supplier's CSV price list. Each supplier's stock goes into a Shopify location of its own, so the stock you hold yourself is never overwritten. A broken feed is held, a late one is skipped, and a product every supplier has dropped is put to you in Slack before anything is archived.

- **Setup** creates the `offers`, `stock_locations`, `feed_runs` and `retire_queue` data tables.
- **Locations** (daily at 01:05) copies your Shopify locations into `stock_locations`. A location Shopify no longer returns is marked inactive, never deleted, and the `source` column you type in is never overwritten.
- **Ingest** (every 3 hours, on the hour) downloads the price list and compares it with the last good run. A feed that's empty, or shrank by more than `max_feed_shrink` in rows or in rows in stock, is held and Slack is told. A good feed writes only what changed into `offers`: new rows, changed rows, rows that went missing (`missing_since`) and rows that came back.
- **Sync** (every 3 hours, at half past) skips any source with no good feed run for `freshness_hours`, finds each supplier SKU and MPN in Shopify, keeps exact matches only, and sets stock at that source's location with `inventorySetQuantities` (or `inventoryActivate` the first time). Unit cost follows supplier cost plus shipping when `sync_cost` is on. It posts one summary line to Slack, including any variant still set to sell when out of stock.
- **Sweep** (daily at 09:00) finds active products whose every offer is marked discontinued, or has been missing from the feed for `gone_days`, and posts up to `cards_per_run` Slack cards.
- **Review** checks Slack's signature on every tap and ignores taps on decided cards. **Archive and redirect** archives the product, tags it and creates a 301 from its URL to its closest collection; **Keep the page** tags it so it stays live as sold out and isn't proposed again; **Snooze** brings it back after `snooze_days`. Nothing is ever deleted.

The full walkthrough is in the guide: [Automated Inventory Management for Shopify](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.
- A Shopify app with the `read_products`, `write_products`, `read_inventory`, `write_inventory`, `read_locations` and `write_online_store_navigation` scopes, and its client ID and secret.
- One Shopify location per supplier (Settings > Locations > Add location), with **Use inventory at this location to fulfill online orders** on, separate from the location that holds your own stock.
- A supplier price list you can download as CSV from a URL.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- No AI model and no paid APIs.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Sync, Get Shopify token for Sweep, Get Shopify token for Review | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Feed held, Feed warning, Post summary, Post the card, Update the card, Reply in thread | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

Every lane starts with a settings node holding the same JSON (**Locations settings**, **Ingest settings**, **Sync settings**, **Sweep settings**, **Review settings**). Fill in one and paste it into the others.

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `currency` | Shown next to the last cost on Slack cards |
| `source_name` | The name of this feed, such as `wholesaler`. Type the same name into `stock_locations` |
| `price_list_url` | The CSV to download |
| `columns` | Which CSV column holds each field. `discontinued` is the column that marks a discontinued line; leave it `""` if your supplier has none |
| `discontinued_values` | Values in that column that mean discontinued, lower case |
| `cost_includes_tax`, `tax_rate` | Strip tax from the cost when the price list includes it (`tax_rate` 0.1 for 10%) |
| `shipping_per_unit` | Added to the supplier cost for the unit cost |
| `max_feed_shrink` | Hold a feed whose rows, or rows in stock, fell by more than this share of the last good run (0.2 = 20%) |
| `freshness_hours` | Skip a source with no good feed run for this long |
| `safety_stock` | List this many fewer than the supplier has (0 lists the supplier's number) |
| `sync_cost` | Keep each variant's cost per item equal to supplier cost plus shipping |
| `max_changes` | The most stock changes one run writes; the rest wait for the next run |
| `batch_size` | Stock or cost changes per GraphQL request |
| `gone_days` | How long every offer must be missing from the feed before a product is proposed |
| `cards_per_run` | The most Slack cards one Sweep posts |
| `snooze_days` | How long Snooze hides a card |
| `retire_tag` | The tag Archive and Keep add |
| `keep_template_suffix` | A product template to switch to on Keep, such as `discontinued` for `product.discontinued.json`. Leave it `""` to keep the current one |
| `fallback_redirect` | Where a retired product's URL goes when it's in no collection |
| `slack_review_channel` | Where the cards go (a channel ID such as `C0123456789`) |
| `slack_log_channel` | Where sync summaries and feed alerts go |
| `dry_run` | While true, Sync stops after **Plan changes** and Review records nothing and changes nothing in Shopify |

## Run Setup and Locations

1. Open **Run once to set up** and click **Execute workflow**. You get four data tables. If you already use the add-products template, its `offers` table is reused: add a `missing_since` (Date) and a `discontinued` (Boolean) column to it.
2. Open **Run Locations now** and click **Execute workflow**. Open the `stock_locations` data table and type your `source_name` into the `source` column of the supplier's location. Leave your own locations empty.

## Test

1. Point `price_list_url` at a copy of your supplier's CSV and `slack_log_channel` and `slack_review_channel` at a test channel. Keep `dry_run` on.
2. Run **Run Ingest now**. The first run writes every row into `offers`; later runs write only rows that changed.
3. Run **Run Sync now** and open **Plan changes**: each item lists the variant, its current level at the supplier's location, the target and the reason (`supplier stock`, `discontinued` or `dropped from feed`), plus the exact mutation.
4. Turn `dry_run` off and run Sync again. Check a product in Shopify admin: the supplier's location has the feed's number and your own location hasn't changed.
5. To test Review, publish the workflow, run **Run Sweep now** with `gone_days` set low enough to propose a test product, and tap the buttons on a development store first: Archive and redirect writes to Shopify.

## Schedule

Publish the workflow. Ingest runs every 3 hours on the hour and Sync at half past, in the workflow's time zone (Workflow settings > Timezone); Locations runs daily at 01:05 and Sweep at 09:00. Set an Error Workflow too, so a crashed run reaches you.

Executions: about 18 schedule runs a day (540 a month) plus one webhook run per Slack tap.

## Troubleshooting

### Sync says a feed has gone quiet

No good Ingest run for `freshness_hours`. Look at `feed_runs`: a run of `held` rows means the feed is still broken; no rows means Ingest isn't running or the download fails.

### Sync says there's no Shopify location for a source

Type the feed's `source_name` into the `source` column of its row in `stock_locations`.

### A product doesn't update

The variant's SKU must equal the feed's MPN or supplier SKU exactly (case doesn't matter). Archived products and variants that don't track inventory are skipped, and the summary counts them.

### The summary says "Still selling at zero stock"

Those variants have **Sell when out of stock** on (the help centre calls it Continue selling when out of stock), so zero stock doesn't stop orders. Turn it off in Shopify admin.

### Archive and redirect says the URL already had a redirect

Shopify refuses a second redirect for the same path. The product is archived and the existing redirect stays; change it under Content > Menus > URL redirects if it points somewhere else.

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise use the Supabase version.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py automated-inventory-management --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`offers`, `stock_locations`, `feed_runs`, `retire_queue`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first. Type your `source_name` into `stock_locations.source` with the Table Editor.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the columns the workflow upserts on. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Automated inventory management" n8n template in ./automated-inventory-management.

1. Read automated-inventory-management/README.md, SETUP.md and automated-inventory-management/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py automated-inventory-management
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Check with me that each supplier has its own Shopify location that fulfils online orders, separate from the location that holds my own stock.
5. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. Map the columns from a real copy of my supplier's CSV.
6. Run the Setup and Locations lanes, and help me type the source name into stock_locations.
7. With dry_run on, run Ingest and Sync, show me the Plan changes output for 5 products and check it with me before anything writes to my store.
8. Stop and ask me whenever something doesn't match the README.
```
