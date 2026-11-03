# Competitor price monitoring

An n8n template that finds who else sells your exact products, reads their prices politely, and posts a weekly Slack report of every product where a competitor is cheaper.

- **Discover** searches Google (through DataForSEO) for each model number or barcode in your Shopify store and keeps exact matches only.
- **Recapture** re-reads each competitor page on a schedule, checks robots.txt first, spaces out its visits and reads the price from the page's structured data (JSON-LD). Pages that block a plain request go to Firecrawl.
- **Report** compares the freshest trusted prices with yours every Monday and posts the undercuts, with a health line that counts blocked pages.

There's no AI model in it. Every price is read by plain code.

The full walkthrough is in the guide: [How to Monitor Competitor Prices With n8n](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.45.
- A Shopify app with the `read_products` scope, and its client ID and secret.
- A DataForSEO account (US$50 minimum top-up). A 20-result search costs up to US$0.004.
- Optional: a Firecrawl API key. The free 1,000 credits a month covers the defaults.
- A Slack bot that's a member of your report channel.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for report | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Search Google | Basic Auth | Your DataForSEO API login and password |
| Firecrawl scrape | Header Auth | Name `Authorization`, value `Bearer <your Firecrawl key>` |
| Alert failed searches, Send report | Slack API | Your bot token |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.

## Settings

Each lane starts with a settings node: `Discover settings`, `Recapture settings` and `Report settings`. They hold the same JSON. Set your values in `Discover settings`, then paste the same JSON into the other two.

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `own_domain`, `exclude_domains` | Domains never saved as competitors |
| `currency`, `locale`, `country`, `search_location`, `language_code` | Your market. `search_location` is a DataForSEO location name, such as `United States` or `Australia` |
| `prices_include_tax`, `market_shows_tax`, `tax_rate` | Evens out tax before comparing |
| `tax_exclusive_domains` | Trade or B2B competitors whose JSON-LD prices exclude tax. Their prices get `tax_rate` added before comparing, where your market shows tax-inclusive prices |
| `mpn_source`, `mpn_metafield_namespace`, `mpn_metafield_key` | Where your model numbers live. Set `mpn_source` to `sku` if your SKUs are the manufacturer's part numbers |
| `user_agent`, `robots_agent` | How the workflow names itself to the sites it visits |
| `discovery_batch`, `research_with_listings_days`, `research_without_listings_days`, `search_depth` | How many products are searched a day, how often each is searched again, and how many results each search reads |
| `recapture_every_hours`, `recapture_batch`, `min_delay_seconds` | How often each page is re-read, how many a run, and the minimum gap between visits to one site |
| `max_price_move` | Moves bigger than this (0.6 = 60%) wait for a second reading |
| `use_firecrawl`, `firecrawl_per_run` | Firecrawl for blocked pages, and the cap per run |
| `min_confidence`, `max_price_age_days`, `min_price_ratio`, `undercut_threshold`, `report_limit` | What counts in the report |
| `slack_channel` | Where the report goes, such as `#pricing` |

## Run Setup

Open **Run once to set up** and click **Execute workflow**. Then open the Data tables tab. You should see three empty tables: `competitor_listings`, `competitor_prices` and `competitor_searches`.

## Test on 10 products

1. Set `discovery_batch` to 10 in `Discover settings`, and `recapture_every_hours` to 0 in `Recapture settings` so freshly found listings are due straight away.
2. Run the Discover lane from **Every day at 03:00**. Ten searches cost about US$0.04. Check `competitor_listings`: every row should be your exact product.
3. Run the Recapture lane from **Every 6 hours**. Most rows should end up with `method` set to `http:jsonld`, and Google Shopping links as `robots_disallowed`.
4. Run the Report lane from **Mondays at 08:00** and compare the Slack message with the competitors' pages.
5. Put `discovery_batch` and `recapture_every_hours` back to their defaults (100 and 120).

## Schedule

When the test matches what you see on the competitors' sites, publish the workflow. Discover runs daily at 03:00, Recapture every 6 hours and Report on Mondays at 08:00, in the workflow's time zone (Workflow settings > Timezone). Set an Error Workflow too, so a crashed run reaches you.

## Troubleshooting

### Every search fails with "Payment Required."

Your DataForSEO balance is empty. **Alert failed searches** posts this to Slack the day it happens.

### Get my products returns errors about access

Check the app has `read_products`, is installed on the store, and belongs to the same Shopify organisation as the store. The client credentials grant only works inside one organisation.

### Discover stops after Get my products on the first run

`Get search log` needs **Always Output Data** on. Without it, an empty `competitor_searches` table ends the lane.

### Listings show `moved` or `rate_limited`

`Fetch page` doesn't follow redirects. A permanent redirect saves the new address as `moved`, and the next run checks robots.txt for it before reading it. A 429 marks the listing `rate_limited` until the site's Retry-After time has passed (an hour if it doesn't say).

### Most pages come back `blocked`

The report leads with a warning when that happens. Turn on `use_firecrawl`, or raise `firecrawl_per_run` if you have the credits.

### The report has preview cards under every link

Turn off **Unfurl Links** and **Unfurl Media** in the options of **Send report**.

### No listings for a product you know others sell

Products without a model number or barcode are skipped. Check the metafield namespace and key in the settings, and that the product is active.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres.
