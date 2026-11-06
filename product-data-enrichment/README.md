# Product data enrichment

An n8n template that scrapes each queued product's manufacturer spec page, has an AI model return every attribute with a confidence, a source label and an exact quote, checks each quote in code, and asks you in Slack about anything it isn't sure of. Approved values go to your `custom.*` product metafields and, where Shopify's Standard Product Taxonomy has the attribute, to Shopify's matching standard product attribute as well.

- **Setup** creates the `attribute_schema`, `extract_runs`, `attribute_values` and `taxonomy_values` data tables, saves the attribute schema from **Setup settings**, creates a pinned metafield definition per attribute (usable in smart collection rules and as an admin filter) and turns on the `shopify--<attribute>` metaobject definitions the schema's `standard` fields name.
- **Extract** takes products tagged `enrich` (or the IDs in `product_ids`), scrapes the spec page with one HTTP request and falls back to Firecrawl when a site blocks it, adds an optional product database and optional text read from the product images, and labels the sources S1, S2 and so on, with the supplier description last as SUP. The model returns each value with a confidence, a source and a quote; code checks the quote is in that source and carries the value, then approves values from the spec page or a database at 0.85 or above and holds the rest for review. It records the run and removes the tag.
- **Review** posts a bulk card per category and attribute once `bulk_min_products` products are waiting on the same value, and a card per product with every other pending value editable inline. It checks Slack's signature on every click, ignores clicks on old cards, and sends approvals straight to Push.
- **Push** writes approved values with `metafieldsSet` (25 per call), creates the standard attribute value (a metaobject) on the first use of a value with `metaobjectUpsert`, proves every write in Shopify's reply and retries a failed batch one metafield at a time. `dry_run` is on until you turn it off.

The full walkthrough is in the guide: [Product Data Enrichment With AI](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.45.
- A Shopify app with the `read_products`, `write_products`, `read_metaobjects`, `write_metaobjects`, `read_metaobject_definitions` and `write_metaobject_definitions` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- An AI model. The template uses Ollama Cloud with `gemma4:31b` for both extraction and the optional image step; any chat model sub-node works. In our tests `gpt-oss:120b` did as well but took twice as long; a small local `qwen3.5:9b` broke the JSON on a quarter of products.
- Optional: a Firecrawl API key, for spec pages that refuse a plain request.
- Products with a category from Shopify's Standard Product Taxonomy. Setup creates the `custom.spec_url` and `custom.mpn` fields; you fill in each product's spec page URL and model number (by hand, in the bulk editor, or by CSV import with columns headed `Spec page URL (product.metafields.custom.spec_url)` and `Model number (MPN) (product.metafields.custom.mpn)`).

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token for Setup, Get Shopify token, Get Shopify token for Push | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Update the card | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Ollama Chat Model, Vision Chat Model | Ollama | Base URL `https://ollama.com` and your API key |
| Firecrawl scrape (optional) | Header Auth | Name `Authorization`, Value `Bearer fc-...` |

**Product database (optional)** ships switched off. To use it, turn it on, point it at your industry's database (the URL shows Open Icecat) and give it that database's credential.

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Setup settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `namespace` | The metafield namespace for your attributes (`custom`) |
| `spec_url_metafield`, `mpn_metafield` | The fields Setup creates for the spec page URL and the model number, as `namespace.key`. Keep them the same as in **Extract settings** |
| `schema` | One list of attributes per category name, exactly as Shopify names the category (`Surveillance Cameras`, `Tumblers`). Each attribute has a `key`, a `label`, a `type` (`enum`, `list`, `number`, `boolean` or `text`), an optional `unit`, an `allowed` list for `enum` and `list`, an optional `standard` (the Shopify taxonomy attribute it twins, such as `Power source`) and an optional `standard_map` from your value to the taxonomy's name for it. Look up your categories, their attributes and accepted values in [Shopify's taxonomy explorer](https://shopify.github.io/product-taxonomy/releases/latest/). A standard attribute only works on the categories it's mapped to, so leave `standard` out where your category doesn't have it |

**Extract settings**:

| Setting | What it does |
|---|---|
| `store_domain` | As above |
| `queue_tag` | The tag that queues a product (`enrich`) |
| `product_ids` | Product IDs to enrich instead of the tagged ones, for a test batch. Leave it `[]` to use the tag |
| `batch_size` | The most products per run (5 every 15 minutes is 480 a day) |
| `text_model`, `vision_model` | The model names on the two Ollama sub-nodes |
| `spec_url_metafield`, `mpn_metafield` | The metafields that hold the spec page URL and the model number, as `namespace.key` |
| `use_firecrawl` | true to retry blocked or empty pages through Firecrawl |
| `use_images` | true to read printed specs and visible features from up to `max_images` product photos |
| `auto_approve_confidence` | The lowest confidence that skips review (0.85) |
| `max_list_values` | The most values a list attribute can have and still skip review |
| `max_chars_spec`, `max_chars_other` | How much of the spec page and the other sources go into the prompt |
| `user_agent` | The User-Agent the spec page request sends. Name your store and give a URL |

**Review settings**: `slack_channel`, `store_handle` (the part of your admin URL after `admin.shopify.com/store/`), `max_products` (product cards per run) and `bulk_min_products` (products that must share an attribute before it gets a bulk card).

**Push settings**: `store_domain`, `namespace`, `dry_run` (true until you've checked the payloads) and `max_products` (products per run).

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get four data tables, one row per category and attribute in `attribute_schema`, a pinned definition per attribute plus **Spec page URL** and **Model number (MPN)** under **Settings > Custom data > Products**, and the standard attribute types turned on. Running it again is safe: a definition that already exists answers `TAKEN`, and enabling a type twice returns the same definition.

## Test on 10 products

1. Fill in `custom.spec_url` on ten products in one or two categories that are in your `schema`, put their IDs in `product_ids`, and point `slack_channel` at a test channel.
2. Open **Run now** and click **Execute workflow**. Check `extract_runs`: `spec_status` should say `ok` or `firecrawl` for products with a spec page. If it says `blocked (403)` or `blocked (429)`, turn on `use_firecrawl`.
3. Open **Post cards now** and click **Execute workflow** to post the cards.
4. Publish the workflow so **Slack button click** answers, then approve, edit and reject a few cards. With `dry_run` on, Push stops at **Build the metafields**: open it and read the payloads.
5. Set `dry_run` to false and approve one more card, or run **Every 15 minutes (Push)**. The values appear on the product in Shopify, custom metafields under **Product metafields** and the standard attribute twins under the admin's **Category metafields** section.
6. Do this on a development store first: Setup, Extract (the tag removal) and Push write to Shopify.

## Schedule

Publish the workflow. Extract and Push run every 15 minutes and Review every 10, in the workflow's time zone (Workflow settings > Timezone), and the Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: the Push call after each approval runs as a sub-workflow, which doesn't count towards n8n Cloud's quota. Expect about 10,000 schedule runs a month plus one webhook run per Slack click; on n8n Cloud, slow the schedules down (every hour is plenty once the backlog is done).

## Troubleshooting

### Extract finds no products

Shopify's search index takes a minute or so to see a tag you just added. Wait and run again, or put the IDs in `product_ids`.

### Every value is held for review

Check `spec_status` in `extract_runs`. `no spec URL` means the metafield in `spec_url_metafield` is empty, so only the description (SUP) was read, and SUP never skips review. `blocked (...)` means the site refused the request: turn on `use_firecrawl`.

### A product has no values at all

Its category isn't in `schema`, or its name doesn't match Shopify's category name exactly. `extract_runs.error` says `no fields set up for category ...`.

### Nothing happens when I click a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### A value is stuck on `failed`

Read `push_error` in `attribute_values`. `Value must be a decimal.` means someone typed text into a number field in Slack; fix the value in Shopify or tag the product again. Push retries a rejected batch one metafield at a time, so one bad value never holds up the rest.

### The standard attribute isn't set

Read `taxonomy_values` and `push_error`. `Standard attribute skipped: no metaobject for every value yet` means a value couldn't be resolved; check the app has the metaobject scopes and that Setup's **Enable standard attribute types** returned no errors. `category_mismatch` means the product's category doesn't have that taxonomy attribute; the custom metafield is still written.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres (next section).

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py product-data-enrichment --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`attribute_schema`, `extract_runs`, `attribute_values`, `taxonomy_values`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. `attribute_values` has a unique key on `product_id`, `key` and `value`, so re-extracting a product never duplicates a value you already decided. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Product data enrichment" n8n template in ./product-data-enrichment.

1. Read product-data-enrichment/README.md, SETUP.md and product-data-enrichment/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py product-data-enrichment
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Help me write the schema in Setup settings: ask which Shopify categories I sell, suggest 4 to 8 attributes per category that shoppers filter by, with allowed values, and look each category up in Shopify's taxonomy explorer (https://shopify.github.io/product-taxonomy/releases/latest/) to set `standard` and `standard_map` only where that category has the attribute. Wait for my answer on each category.
5. Walk me through every other settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
6. Run the Setup lane and check its output with me.
7. Test on about 5 products with nothing written to my store yet (dry_run on, and no Slack card approved), show me what it extracted and check it with me before anything writes to my store.
8. Stop and ask me whenever something doesn't match the README.
```
