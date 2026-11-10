# Manufacturer reviews

An n8n template that finds each product's page on the manufacturer's own online store, reads every review of that exact product, checks the set is complete and really is the same product, and asks you in Slack before anything is exported. Approved pages become a Judge.me import CSV with the source on every review ("First published on Tapo Australia" and a link to the page). Every star rating is kept and the review text is never changed. No AI model.

- **Setup** creates the `review_sites`, `review_sources`, `reviews` and `review_batches` data tables and the **Model number (MPN)** (`custom.mpn`) and **Manufacturer review page** (`custom.review_source_url`) product fields, then saves the manufacturer sites from its settings.
- **Find** takes up to `batch_size` products tagged `find-reviews` an hour (or the IDs in `product_ids`). A URL you pasted into **Manufacturer review page** wins. Otherwise it searches each of the brand's sites with the store's own product search (`/search/suggest.json`, which Shopify stores answer for free) and keeps the first result that:
  - names the exact model number as a whole word (C410 matches "Tapo C410" but never "C4100"), or, for a product with no model number, has the same name once the brand is taken out;
  - isn't a kit, bundle or multipack your product isn't (`pack_words`).

  The product loses its tag either way. Tag it again to search again.
- **Collect** reads each new page, and every approved page again once a week. It reads every review from the page's Judge.me widget, page by page through Judge.me's public widget endpoint (older widgets send HTML, newer ones JSON), or from a page whose structured data lists every review. It holds the page back unless:
  - the page title names the model and isn't a kit or pack;
  - it read as many reviews as the page says it has, with no duplicates;
  - the average of what it read matches the page's average.

  Then it keeps the reviews that belong on your product page: reviews filed under other products the manufacturer pools together (another size, another model) are left out, and so are reviews the manufacturer imported from somewhere else (`skip_imported`). Each new page becomes a Slack card with the counts, the stars and the lowest and highest rated review in full.
- **Review** answers Slack at once, then checks the signature, age and approver list. Approve releases the page's reviews to Export; Reject retires the page. **Mark imported** on an export card closes that batch.
- **Export** runs every morning. It takes new reviews from approved pages, whole products only, up to `max_rows`, builds the Judge.me CSV and posts it in the thread of a Slack card. You import it in Judge.me and click **Mark imported**.

The full walkthrough is in the guide: [How to Scrape Manufacturer Reviews and Import Them to Shopify With n8n](https://www.reganmcgregor.com.au/manufacturer-reviews-shopify/).

## Before you start: is it allowed?

Reposting genuine reviews of the exact same product is allowed in the US and Australia when you show where they came from, keep them word for word, keep every rating and don't present them as your own customers' reviews. Google doesn't want them in your star markup or a Merchant Center reviews feed. Copyright and the manufacturer's site terms are a separate question: read the terms and ask the manufacturer or your distributor first. The guide covers each rule with its source. This is not legal advice.

## What you need

- n8n with Data Tables (self-hosted or Cloud) on a public HTTPS URL, because Slack has to reach the webhook. Tested on n8n 2.46.
- A Shopify app with the `read_products` and `write_products` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write` and `files:write`; invite the bot to your review channel), Interactivity turned on, and its signing secret.
- A review app that imports CSV files. The CSV is in Judge.me's format (Judge.me Free imports it, with the custom columns).
- Manufacturers that sell online themselves, with reviews on their product pages. The search works on Shopify stores; any other site works when you paste the page URL into the product, as long as its reviews are in a Judge.me widget or listed in full in the page's structured data.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token for Setup, Get Shopify token | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Show approved, Show rejected, Show imported, Post the export card, Upload the CSV | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Setup settings**: `store_domain`, the namespaces and keys of the two product fields, and `manufacturer_sites`, one entry per site:

- `brand`: exactly as your products' Vendor field (case doesn't matter).
- `domain`: the manufacturer's own store, such as `au.store.tapo.com`.
- `source_name`: what shoppers see next to each review, such as `Tapo Australia`.

A brand can have several sites (a local store and an overseas one). Find tries them in order.

**Find settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `find_tag` | The tag that queues a product (`find-reviews`) |
| `product_ids` | Product IDs (numbers or `gid://` IDs) to search instead of the tagged ones, for a test batch. Leave it `[]` to use the tag |
| `batch_size` | Products per run |
| `model_namespace`, `model_key`, `page_namespace`, `page_key` | The two product fields, as in Setup settings |
| `pack_words` | Words that make a page a different product from yours when your title lacks them (kit, bundle, pack, twin...). `2pack` style words count too |
| `user_agent` | Sent to manufacturer sites. Name your store and give a URL |

**Collect settings**:

| Setting | What it does |
|---|---|
| `batch_size` | Pages per run |
| `recheck_days` | How often an approved page is read again for new reviews |
| `retry_hours`, `max_attempts` | When a failed page is tried again, and how often |
| `max_pages` | The most widget pages to read (30 reviews a page) |
| `same_product` | `page`: only reviews filed under that product page. `title`: also its other colours, when the manufacturer pools them under the same name before " \| " |
| `skip_imported` | true leaves out reviews the manufacturer imported from another site (Judge.me's "collected from another provider" badge) |
| `max_photos` | Photos per review in the CSV (Judge.me takes five) |
| `pack_words`, `user_agent` | As in Find settings |
| `slack_channel` | Where the cards go |

**Review settings**: `slack_app_id` (blank accepts any) and `approver_ids` (Slack user IDs; empty means anyone in the channel).

**Export settings**: `max_rows` (the CSV never splits a product), `slack_channel` and `review_app` (the name in the card's instructions).

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get four data tables, the two pinned product fields under **Settings > Custom data > Products**, and one `review_sites` row per site. Running Setup again is safe. A product field that already exists answers `TAKEN`.

## Test on a few products

1. Fill in the model number on three products (or paste their manufacturer page into **Manufacturer review page**), put their IDs in `product_ids`, and point `slack_channel` at a test channel.
2. Run **Find now**. Each product gets a row in `review_sources`: `new` with a URL, or `not_found` with a note saying what it skipped.
3. Run **Collect now**. Read each row's `status`, `review_count`, `stars`, `left_out` and `error`, and the Slack cards.
4. Publish the workflow so **Slack button click** answers, approve one card and reject another.
5. Run **Export now**. Download the CSV from the card's thread and open it before you import anything.
6. In Judge.me, go to **Reviews > Import > From review apps > Judge.me format** and attach the file once. Check the import log, then click **Mark imported** on the card.

Do this on a development store first: imported reviews show on your product pages straight away.

## Schedule

Publish the workflow. Find runs every hour, Collect every hour at half past, and Export at 8am, in the workflow's time zone (Workflow settings > Timezone). The Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

## Show the source on the product page

Judge.me shows the CSV's custom columns under each review as answers, labelled **First published on** and **Source page**. Add a line above the reviews so shoppers know what they're reading: in the theme editor, open the product template and add a **Text** block above the Judge.me reviews block, such as "Some reviews were first published on the manufacturer's website and are marked with their source." Leave imported reviews out of any star markup you add yourself, because Google's review snippet guidelines say ratings must come directly from your own users.

## Troubleshooting

### A product gets `not_found`

Read its `error`. "No manufacturer site for X" means the product's Vendor doesn't match a `brand` in `review_sites`. "No matching product" means the search found nothing that names the model: check the model number, or paste the page into **Manufacturer review page** and tag the product again. "Skipped ... (kit)" lists pages it turned down.

### A page is `unsupported`

Its reviews aren't in a Judge.me widget or listed in full in the page's structured data (many manufacturers use Yotpo, Okendo, Bazaarvoice or no reviews at all). The guide's "Make it your own" section shows how to add a reader.

### A page is `incomplete` or `failed`

`incomplete` means it read fewer reviews than the page says it has; raise `max_pages` if the page has more than 1,200. `Average ... doesn't match` means the page's own numbers disagree with what it read, so nothing is kept. Failed pages are tried again `max_attempts` times.

### A page is `mismatch`

The page title doesn't name the model, or it's a kit or pack your product isn't. Reject it by leaving it, or paste the right page and tag the product again.

### Nothing happens when I click a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### The CSV never arrives

Export only posts when an approved page has new reviews. If **Upload the CSV** fails with `missing_scope`, add `files:write` to the bot and reinstall the app.

### Judge.me rejects a row

Use the import log's error file to find the review, but fix it in the original CSV, not the error file (which can lose accented characters). Judge.me doesn't skip duplicates, so re-import only the failed rows.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py manufacturer-reviews --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the four tables if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. `reviews` has a unique key on `key` (page and review ID), so a review is never saved twice.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Manufacturer reviews" n8n template in ./manufacturer-reviews.

1. Read manufacturer-reviews/README.md, SETUP.md and manufacturer-reviews/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py manufacturer-reviews
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Help me fill in manufacturer_sites in Setup settings: ask which brands I sell, find each manufacturer's own online store, check its product pages show reviews, and confirm each site and its source_name with me.
5. Walk me through every other settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
6. Run the Setup lane and check its output with me.
7. Test on about 3 products: run Find and Collect, show me the review_sources rows and the Slack cards, and check them with me. Don't import anything into my review app until I've opened the CSV myself.
8. Stop and ask me whenever something doesn't match the README.
```
