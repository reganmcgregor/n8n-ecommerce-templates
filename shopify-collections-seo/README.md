# Shopify collections SEO

An n8n template that finds the collections your catalogue can support and shoppers search for, asks you in Slack, then creates them as smart collections. It gives every brand its own page and proposes unpublishing collections that run out of stock.

- **Setup** creates the `collection_proposals` data table.
- **Propose** (weekly) groups your live products by product type and metafield value (`PoE Switches` + `poe_ports = 8`), and by brand and type (`TP-LINK PoE Switches`). It names each group with AI, checks the name in code (any number or model code must come from the value or the category), looks up Google search volume, keyword difficulty and whether you already rank with DataForSEO, scores it out of 100 and posts the best to Slack. Every candidate is kept in the table, including the ones with no demand or that the model said only work as a filter, so you can see why they were left out.
- **Review** checks Slack's signature on every tap and ignores taps on old cards. Approve sends the proposal to Apply; Skip records it.
- **Apply** checks the handle is free, creates the smart collection with `collectionCreate`, publishes it to your Online Store and replies on the card. It also unpublishes and republishes collections for Retire.
- **Brands** (daily) creates a `VENDOR is <brand>` collection for every vendor that has none, using the vendor exactly as written, and posts one summary.
- **Retire** (weekly) counts live products in every collection this template created (brand pages are left alone). Below `retire_below` it posts an Unpublish card; when a retired collection is back to `restore_at` it posts a Republish card.

The full walkthrough is in the guide: [How to Automate Shopify Collections for SEO](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.45.7.
- A Shopify app with the `read_products`, `write_products`, `read_publications` and `write_publications` scopes, and its client ID and secret.
- Product specs in product metafields, with **Use as a condition in collections** turned on for each definition (Settings > Metafields and metaobjects > Products).
- A DataForSEO account (pay as you go).
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- An AI model. The template uses Ollama Cloud with `gpt-oss:120b`; any chat model sub-node works.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Apply, Get Shopify token for Brands, Get Shopify token for Retire | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Search volume, Keyword difficulty, Rank check | Basic Auth | Your DataForSEO API login and API password |
| Post the card, Update the card, Post brand card, Post retire card, Reply in Slack, Post brand summary | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Ollama Chat Model | Ollama | Base URL `https://ollama.com` and your API key |

When you import, n8n may fill these slots with existing credentials of the same type. Check each one.

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Propose settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `namespace` | The metafield namespace your specs live in (`custom`) |
| `min_products` | The fewest live products a new collection needs (5) |
| `max_candidates` | The most groups named and looked up per run (30) |
| `max_cards` | The most cards posted per run (10) |
| `min_volume` | Monthly searches below this mark a proposal `no_demand` (30) |
| `create_score` | The lowest score that gets a card (65) |
| `location_code`, `language_code` | DataForSEO's market: 2840 is the United States, 2826 the UK, 2036 Australia |
| `own_domain` | Your storefront domain, to spot whether you already rank |
| `slack_channel` | Where the cards go, such as `#review-collections` |

**Apply settings**: `store_domain`, `seo_title_suffix` (added to each new collection's SEO title), `sort_order` (`BEST_SELLING`), `publication_name` (`Online Store`), `keyword_namespace` (where the main keyword and its volume are saved on the collection, for the category page template) and `slack_channel` (for replies on brand pages that had no card).

**Brands settings**: `store_domain`, `exclude_vendors`, `review_brands` (false creates brand pages straight away; true posts a card first) and `slack_channel`.

**Retire settings**: `store_domain`, `retire_below` (3), `restore_at` (5), `keep_days` (how long a Keep tap holds before the collection can be proposed again) and `slack_channel`.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. Running it again keeps your table.

## Test

1. Point every `slack_channel` at a test channel and lower `min_products` and `create_score` if your test store is small.
2. Open **Run Propose now** and click **Execute workflow**. Read the `collection_proposals` table: every candidate is there with its keyword, volume, score and status. One run costs about US$0.11 in DataForSEO calls (one volume task, one difficulty task and a results page per candidate with demand).
3. Publish the workflow so **Slack button click** answers, then tap **Approve & Create** and **Skip** on a few cards. Approved collections appear in Shopify, published, with a reply on the card.
4. Do this on a development store first: Apply creates, publishes and unpublishes collections.

## Schedule

Publish the workflow. Propose runs on Mondays, Retire on Sundays and Brands every day, in the workflow's time zone (Workflow settings > Timezone). The Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

## Troubleshooting

### No candidates

Check `namespace`, and that each metafield definition has **Use as a condition in collections** turned on: definitions without it, and types other than single line text, integer, decimal and true or false, are skipped. Groups smaller than `min_products`, groups that hold the whole category, and rules a collection already uses are skipped too.

### A card uses the raw value as its title

The model's title failed the check, usually because it added a number or model code that isn't in the value or the category (a brand page titled `Reolink 4K Security Cameras` when some of its cameras are 12MP). The reason is in `name_problems` on the run's **Check names** output.

### Not done: handle taken

A collection already uses that handle. Shopify refuses a taken handle in `collectionCreate`, so the row is marked `failed` and nothing changes. Rename or delete the old collection, then delete the row from `collection_proposals`, and the next Propose or Brands run proposes it again.

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the table to Postgres.
