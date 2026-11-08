# Add products to Shopify

An n8n template that brings a wholesaler's CSV price list and hand-picked AliExpress listings into one table, finds what you don't sell yet, asks you in Slack, writes the title and description with AI, creates a Shopify draft and puts it live on a second tap.

- **Ingest** maps the price list into an `offers` data table every morning (or when you upload a CSV in its form), and refreshes each AliExpress variant's cost, stock and cheapest tracked freight.
- **Detect** applies your category rules, skips what's already on your store (barcode, then SKU and MPN), prices from landed cost and posts a Slack card for each new product. Hand-picked AliExpress rows skip the card.
- **Review** checks Slack's signature on every button tap, ignores old or repeated taps, and sends approved rows on.
- **Draft** writes the copy, checks every model number against the supplier data, creates a `DRAFT` product and posts a second card.
- **Go live** reads the draft back, checks it has an image, a type, a category and a price above cost, then publishes it to your Online Store.
- **Token** keeps the AliExpress access token fresh.

Nothing is created in Shopify until you set `dry_run` to false.

The full walkthrough is in the guide: [How to Add Products to Shopify Automatically](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.45.
- A Shopify app with the `read_products`, `write_products`, `read_inventory`, `write_inventory`, `read_publications`, `write_publications` and `read_locations` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret. The [Slack approvals guide](https://www.reganmcgregor.com.au/slack-approval-workflow-n8n/) explains how the cards, taps and modals work.
- An AI model. The template uses Ollama Cloud; any chat model sub-node works.
- For AliExpress: a free AliExpress Open Platform app with Dropshipping API access, its App Key and App Secret. Skip it if you only use a price list.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Detect, Get Shopify token for Draft, Get Shopify token for Go live | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post offer card, Show approval on card, Show decision on card, Post draft card, Reply in thread | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Sign product request, Sign freight request, Sign refresh request | Crypto | Hmac Secret = your AliExpress App Secret |
| Ollama Chat Model | Ollama | Base URL `https://ollama.com` and your API key |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

Each lane starts with a settings node: `Setup settings`, `Ingest settings`, `AliExpress settings`, `Token settings`, `Detect settings`, `Review settings`, `Draft settings` and `Go live settings`. They hold the same JSON. Set your values in `Ingest settings`, then paste the same JSON into the others.

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `currency`, `prices_include_tax`, `tax_rate` | Your store's currency, and whether its prices include tax (and at what rate) |
| `markup`, `min_margin`, `round_to` | Price = landed cost x `markup` (plus tax), never above the brand's RRP when the RRP still clears `min_margin`, rounded up to end in `round_to` |
| `ship_to_country`, `ships_from_allowed`, `max_delivery_days` | AliExpress: where you ship, which warehouses you accept (lower case, as AliExpress names them), and the slowest tracked method you'll take |
| `batch_limit` | The most new products handled per Detect run |
| `aliexpress_pre_approved` | AliExpress rows go straight to a draft, without the first card |
| `slack_channel` | Where the cards go: a channel ID such as `C0123456789`, or `#new-products` |
| `location_id`, `online_store_publication_id` | From the Setup lane |
| `default_vendor` | Vendor for products with no brand |
| `dry_run` | While true, Draft posts its card but creates nothing, and Go live only reports what it would do |
| `source_name`, `price_list_url`, `columns` | Your wholesaler's name, its price list URL, and which CSV column holds each field |
| `cost_includes_tax`, `shipping_per_unit`, `ships_from` | How the wholesaler quotes cost, a flat shipping cost per unit, and where it ships from |

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You should get four empty data tables (`offers`, `category_map`, `aliexpress_items`, `aliexpress_auth`), and **Get publication and location IDs** lists your sales channels and locations. Copy the Online Store publication ID and your main location ID into the settings.

Then add your rules to `category_map`, one row each:

| source | match_field | pattern | product_type | shopify_category_id | action | reason |
|---|---|---|---|---|---|---|
| wholesaler | category | IP Cameras | Security Cameras | co-2-5 | include | |
| wholesaler | title | `\bjammer\b` | | | block | not legal to sell |
| aliexpress | category | 100006507 | Dash Cams | co-2-7-6 | include | |

Category rules match the supplier's category exactly. Title rules are regular expressions and win over category rules. Rows with no rule are kept as `unmapped`, never dropped.

## AliExpress: first authorisation

The Token lane only refreshes a token, so you get the first one by hand:

1. In the AliExpress Open Platform console, give your app a callback URL (any HTTPS page you control) and note the App Key and App Secret.
2. Open `https://api-sg.aliexpress.com/oauth/authorize?response_type=code&force_auth=true&client_id=YOUR_APP_KEY&redirect_uri=YOUR_CALLBACK_URL`, sign in with the AliExpress account you'll buy from, and copy the `code` from the address you land on. It expires in about 30 minutes.
3. Exchange it with `/auth/token/create`. It's signed like the refresh call: in **Build refresh request**, temporarily swap `refresh_token: a.refresh_token` for `code: 'YOUR_CODE'` and both `/auth/token/refresh` paths for `/auth/token/create` (in the string to sign and in the **Refresh token** URL). Add a row to `aliexpress_auth` with your `app_key` and an `access_expires_at` in the past, run the Token lane once, then undo the two changes.

While your app is in test status, refresh tokens last 48 hours and refreshing doesn't extend them, so repeat this every two days until AliExpress approves the app.

Then paste the listings you want into `aliexpress_items`: an `item_id` per row, plus a `sku_id` if you want just one variant.

## Test on 10 products

1. Keep `dry_run` true and set `batch_limit` to 10.
2. Point `price_list_url` at a short CSV (ten rows is plenty), and put two or three listings in `aliexpress_items`.
3. Run the Ingest lane from **Every day at 05:00**. Check `offers`: one row per CSV line and per AliExpress variant, with `cost`, `stock` and, for AliExpress, `shipping_cost` and `freight_method`.
4. Run the Detect lane from **Every day at 06:00**. Rows already on your store get `on_store`, rows without a rule `unmapped`, and new ones post a card. Hand-picked AliExpress rows post a dry-run draft card.
5. Tap **Approve** on a card. The draft card that follows shows the AI copy next to the supplier's title.
6. When the copy looks right, set `dry_run` to false in `Draft settings` and `Go live settings`, approve one product, and check the draft in Shopify before you tap **Approve and go live**. Do this on a development store first.

## Schedule

Publish the workflow. Ingest runs daily at 05:00, Detect at 06:00 and Token every 6 hours, in the workflow's time zone (Workflow settings > Timezone). The Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: sub-workflow runs (Draft and Go live) don't count towards n8n Cloud's quota. Expect about 180 schedule runs a month plus one webhook run per Slack tap.

## Troubleshooting

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions show up and stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### A tap does nothing the second time

That's on purpose. Each card carries a one-time `card_nonce`; **Still pending?** drops taps on old or already-decided cards.

### AliExpress rows are missing

Listings that can't ship to `ship_to_country` come back as `SHIP_TO_COUNTRY_PROHIBITED` and are skipped. Variants out of stock or shipping from a warehouse not in `ships_from_allowed` are skipped too.

### An AliExpress row is blocked with "no freight quote: DELIVERY_RATE_LIMIT_FOR_SINGLE_PRODUCT"

AliExpress limits freight quotes per product. The lane waits 60 seconds and tries once more; if that fails too the row is blocked until the next run. Pin one `sku_id` per listing to make fewer calls.

### Every AliExpress call fails with an error_response

The token has expired (run the first authorisation again), or the App Secret on the three Sign nodes is wrong.

### Go live says the draft still needs something

It reads the product back from Shopify, so fix it there (add an image, a type, a category or a higher price) and tap **Approve and go live** again.

### publishablePublish fails

The app is missing `write_publications`, or `online_store_publication_id` isn't your Online Store's publication.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move `offers` to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py add-products-to-shopify --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`offers`, `category_map`, `aliexpress_items`, `aliexpress_auth`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the columns the workflow upserts on. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Add products to Shopify" n8n template in ./add-products-to-shopify.

1. Read add-products-to-shopify/README.md, SETUP.md and add-products-to-shopify/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py add-products-to-shopify
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
5. Run the Setup lane and check its output with me.
6. Test on about 5 products with nothing written to my store yet (dry_run on where the template has it, and no Slack card approved), show me what it produced and check it with me before anything writes to my store.
7. Stop and ask me whenever something doesn't match the README.
```
