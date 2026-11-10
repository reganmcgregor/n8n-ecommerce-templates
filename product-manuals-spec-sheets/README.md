# Product manuals and spec sheets

An n8n template that finds each Shopify product's user manuals, setup guides, datasheets and compliance documents on the manufacturer's own website, checks the model number and the document type in code, asks you in Slack only when it isn't sure, uploads PDFs to Shopify Files and fills a **Documents** table on the product page.

- **Setup** creates the `documents` and `document_searches` data tables, a **Product document** metaobject (Title, Document type, File, Link, Source, Model, with Storefronts access on) and three pinned product fields: **Documents** (a list of Product documents), **Model number (MPN)** and **Manufacturer page**.
- **Find** takes products tagged `documents` (or the IDs in `product_ids`). It reads the manufacturer page you saved on the product, follows up to two of its support or download pages for the same model, and keeps every link to a document on the manufacturer's own domains. With `use_search` on, it also runs one Google search per product through DataForSEO, cached for 30 days. Each candidate gets a HEAD request (file type, size and ETag, no download; HTML guides are read as text), a label from its title and address, and a whole-token check for the exact model number. It saves each one as `ready`, `review` or `rejected` with the reason, and removes the tag.
- **Review** posts one Slack card per product for the documents Find wasn't sure about (a model number only in the page text, a variant such as `C540-W`, a family guide that doesn't name the model). Each document has Approve, Reject and Change type. Clicks are checked against your signing secret and against the table, so a second click or an old card does nothing. Approve sends the product to Publish.
- **Publish** keeps one copy of each file (the same ETag at five regional addresses is one file) and, by default, one document of each type. It uploads PDFs to Shopify Files with a readable name (`tapo-c211-user-manual.pdf`), waits until Shopify says READY, writes one Product document per file with a stable handle (`doc-<row id>`), and writes the product's whole Documents list in one call. HTML guides are linked at their official address. `dry_run` is on until you turn it off.

The full walkthrough is in the guide: [Add Product Manuals and Spec Sheets to Shopify Automatically](https://www.reganmcgregor.com.au/shopify-product-manuals/).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.
- A Shopify app with the `read_products`, `write_products`, `read_files`, `write_files`, `read_metaobjects`, `write_metaobjects`, `read_metaobject_definitions` and `write_metaobject_definitions` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret. Only needed for the Review lane; set `review_mode` to `none` to skip it.
- Optional: a DataForSEO account for `use_search` (about US$0.0035 a search at 20 results; see Troubleshooting for why there's no `site:` in the query).
- Products with a vendor and a model number. Setup creates **Model number (MPN)** (`custom.mpn`) and **Manufacturer page** (`custom.manufacturer_url`); the variant SKU is used when the MPN is empty (`use_sku_if_no_mpn`). Fill them by hand, in the bulk editor, or by CSV import with columns headed `Model number (MPN) (product.metafields.custom.mpn)` and `Manufacturer page (product.metafields.custom.manufacturer_url)`. If you ran the AI product descriptions or product data enrichment templates, the same fields are reused.

No AI model: matching and labelling are rules in code.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token for Setup, Get Shopify token, Get Shopify token for Publish | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Update the card, Post the summary | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Search the manufacturer's site (optional) | Basic Auth | Your DataForSEO API login and password |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Setup settings**: `store_domain` (your permanent `*.myshopify.com` domain), `namespace` (`custom`), `documents_key`, `mpn_key`, `manufacturer_url_key` and `metaobject_type` (`product_document`). Keep the keys the same in the other settings nodes.

**Find settings**:

| Setting | What it does |
|---|---|
| `queue_tag` | The tag that queues a product (`documents`) |
| `product_ids` | Product IDs to check instead of the tagged ones, for a test batch. Leave it `[]` to use the tag |
| `batch_size` | The most products per run (5 an hour is 120 a day) |
| `use_sku_if_no_mpn` | Use the first variant's SKU when **Model number (MPN)** is empty |
| `manufacturer_domains` | Each vendor, exactly as Shopify spells it, and the domains its documents live on: `{"TP-LINK": ["tp-link.com", "vigi.com", "tapo.com"], "Ubiquiti": ["ui.com"]}`. Subdomains count (`dl.ui.com`, `static.tp-link.com`). Products whose vendor isn't listed are saved as `skipped` |
| `family_prefixes` | Words some brands put in front of the model number (`Tapo`, `VIGI`, `UVC`). A match without the prefix is sent to review, not published |
| `exclude_patterns` | Regular expressions for links you never want, matched against the address and title (`"\\buacc[-_]"` for a brand's accessory codes) |
| `follow_support_pages`, `max_pages` | Follow the manufacturer page's own support or download pages for the same model, up to `max_pages` pages in total |
| `max_candidates` | The most document links checked per product |
| `use_search` | true to run one DataForSEO search per product as well |
| `search_words`, `search_location`, `language_code`, `search_depth`, `cache_days` | The words added after the vendor and model (`user guide datasheet`), the DataForSEO location name (`Australia`, `United States`), language, results per search and how long a search is reused |
| `include_compliance` | Keep declarations of conformity and certificates, labelled Compliance document |
| `review_mode` | `uncertain` (default) sends only doubtful matches to Slack; `all` sends everything; `none` publishes doubtful matches without asking |
| `user_agent` | The User-Agent sent to manufacturer sites. Name your store and give a URL |

**Review settings**: `slack_channel`, `store_handle` (the part of your admin URL after `admin.shopify.com/store/`) and `max_products` (cards per run).

**Publish settings**:

| Setting | What it does |
|---|---|
| `host_files` | true uploads PDFs to Shopify Files; false links the manufacturer's file instead |
| `dry_run` | true until you've checked the plan in **Plan the documents** |
| `max_products` | Products per run |
| `max_documents`, `max_per_type` | The most documents on one product, and per type (1: one user manual, one setup guide, one datasheet, one compliance document) |
| `max_file_mb` | Bigger files are linked rather than uploaded. Check Shopify's current file size limit for your plan |
| `preferred_locales` | Address fragments to prefer when the same file sits on several regional sites (`/au/`, `/en-au/`) |
| `slack_channel` | Where the run summary goes |

## Add the Documents table to your theme

Horizon has no block that lists metaobjects, so the table is a Custom Liquid block.

1. **Online Store > Themes > ... > Duplicate**, then **Customize** the copy.
2. Open a product page, select the **Product information** section, **Add block > Custom Liquid**, and drag it under the description.
3. Paste [`liquid/documents-table.liquid`](liquid/documents-table.liquid). It prints nothing on products with no documents.
4. Preview a product with documents, click each link, then publish the theme when you're happy.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. **Report setup** lists what it created. Running it again is safe: it answers "already there".

## Test it

1. Fill **Model number (MPN)** and **Manufacturer page** on five products from one or two brands, add those brands to `manufacturer_domains`, and put the product IDs in `product_ids`. Point `slack_channel` at a test channel.
2. Run **Run Find now** and open the `documents` table. Each row has its `status`, `reason` and `evidence` (where the model number was found).
3. Publish the workflow so **Slack button click** answers, run **Post cards now**, and approve, reject or retype a few documents.
4. Run **Run Publish now** with `dry_run` on and read **Plan the documents**: `upload`, `link`, `check` or `keep` for each document, and the duplicates it dropped.
5. Set `dry_run` to false and run it twice, a minute apart: the first run uploads, the second links the files Shopify has finished processing.
6. Do this on a development store first: Setup, Find (the tag removal) and Publish write to Shopify.

## Schedule

Publish the workflow. Find runs hourly, Review and Publish every 10 minutes, in the workflow's time zone (Workflow settings > Timezone). Set an Error Workflow too. Once the backlog is done, Find only has new tagged products to look at; on n8n Cloud, slow the Review and Publish schedules to hourly.

## Troubleshooting

### A product is `skipped` with "no manufacturer domains listed"

Its vendor isn't in `manufacturer_domains`, or it's spelled differently. The lookup ignores case but not spacing or punctuation.

### "no new document links found"

The manufacturer page has no document links on your domains, or every link it has is already in the table. Check `manufacturer_url` points at the product's own page (not a range page), turn on `use_search`, or add the brand's download host to its domains.

### Lots of family guides in review

Brands list general guides (an app guide, a guide for a whole camera range) on every model's support page. Find sends them to review only when nothing names the exact model for that type, and rejects them when something does. Reject the ones you don't want; the decision sticks.

### The search fails with 40101 "Internal SE Server Error"

DataForSEO answers this now and then. The failed search isn't cached and the product keeps its tag, so the next hourly run tries again.

### Why there's no `site:` in the search

DataForSEO charged about five times as much for a `site:` search (US$0.0175 against US$0.0035 at 20 results in our tests), and wrapping it in brackets made Google ignore it. A plain search plus the domain check in code finds the same official documents for less.

### Shopify says "Provided filename extension must match original source"

The file's address has a different extension from the name. Publish follows redirects to the real file address and only sets a name when it ends in `.pdf`, `.doc`, `.docx` or `.zip`; anything else keeps Shopify's own name.

### A document is stuck on `uploading`

Shopify is still processing it. After 24 hours it's marked `failed` with Shopify's reason. Files over `max_file_mb` are linked instead of uploaded.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres (next section).

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py product-manuals-spec-sheets --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`documents`, `document_searches`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. `documents` has a unique key on `product_id` and `url`, so a link is checked once per product. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Product manuals and spec sheets" n8n template in ./product-manuals-spec-sheets.

1. Read product-manuals-spec-sheets/README.md, SETUP.md and product-manuals-spec-sheets/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py product-manuals-spec-sheets
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Ask which brands I sell, and for each one help me find the domains its manuals and datasheets live on (open a product's support page together). Fill manufacturer_domains and family_prefixes with my answers.
5. Walk me through every other settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
6. Run the Setup lane and check its output with me.
7. Walk me through adding liquid/documents-table.liquid as a Custom Liquid block on a copy of my theme, in preview only.
8. Test on about 5 products with dry_run on: run Find, show me the documents table, and check it with me before anything writes to my store.
9. Stop and ask me whenever something doesn't match the README.
```
