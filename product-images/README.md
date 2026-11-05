# Shopify product images

An n8n template that finds each tagged product's page on the manufacturer's own website, scrapes its gallery, ranks the photos by their real pixel size, checks each one with a vision model (which writes its alt text in the same call) and asks you in Slack which ones to add. Approved photos are padded onto white 2048 x 2048 squares, named after the product and added to Shopify. A weekly lane rewrites weak alt text on the images you already have.

- **Setup** creates the `image_queue`, `image_log`, `brand_domains` and `alt_queue` data tables and adds your brand websites to `brand_domains`.
- **Find** picks up to 10 products tagged `needs-images` an hour. It finds the manufacturer page (the `manufacturer_url` metafield, a brand URL pattern, or an optional DataForSEO search), checks robots.txt, reads `og:image`, JSON-LD and `<img>` tags on the brand's own domains, drops icons and banners, collapses sizes of the same shot, reads each file's real size from its header, and asks the vision model about every ranked photo. It posts one Slack card per product with a numbered contact sheet, tick boxes and a main-image choice, and removes the tag.
- **Review** checks Slack's signature on every tap and ignores taps on cards that are already decided. Approve saves your ticks and starts Publish straight away.
- **Publish** skips photos already on the product, pads each one to a white square (wsrv.nl, or in n8n when a brand's server blocks wsrv.nl), adds them with `productUpdate`, waits until Shopify says `READY`, moves the main image first, detaches the old main image if you unticked it (or deletes it if Shopify could never load it), and replies in the card's thread. It also builds the contact sheets for Find.
- **Alt text** runs weekly over the products in `product_query`, finds empty, title-copy, file-name and repeated alt text, writes a new one with the vision model and posts a digest. Approve all applies it with `fileUpdate`.

The full walkthrough is in the guide: [Shopify Product Images: Find, Scrape and Optimise Manufacturer Images With AI](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.
- A Shopify app with the `read_products`, `write_products`, `read_files` and `write_files` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write` and `files:write`), Interactivity turned on, and its signing secret.
- A vision-capable AI model. The template uses Ollama Cloud with `gemma4:31b`; any chat model sub-node that takes images works.
- Optional: DataForSEO, if you want the workflow to search Google for manufacturer pages it has no URL for.
- [wsrv.nl](https://wsrv.nl/docs/) for resizing and padding. It's free and needs no account.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Review, Get Shopify token for Publish, Get Shopify token for Alt text | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Update the card, Update the digest, Reply in the thread, Get upload URL, Complete upload, Post the digest | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Ollama Chat Model, Ollama Chat Model for alt text | Ollama | Base URL `https://ollama.com` and your API key |
| Search Google (optional) | Basic Auth | Your DataForSEO API login and API password |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential. Leave **Search Google** without one if you won't use DataForSEO.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Setup settings**: `brand_domains`, one row per brand website. `brand` is the vendor exactly as Shopify has it (the match ignores case). A brand can have several domains (TP-Link has `tp-link.com` and `vigi.com`). `url_pattern` is optional: a product page URL with `{model}` where the model slug goes, used when a product has no `manufacturer_url`.

**Find settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `admin_store_handle` | The part after `admin.shopify.com/store/`, for the card's Shopify button |
| `pick_tag` | The tag that queues a product (`needs-images`) |
| `batch_size` | The most products per run |
| `min_short_side` | The smallest short side kept, in pixels (500, Google Merchant Center's minimum) |
| `fallback_min_side` | The smallest short side kept when the product has no working image at all (250) |
| `max_candidates` | The most photos per card (Slack shows up to nine) |
| `vision_top_n` | How many of the ranked photos the model checks |
| `vision_model` | The model on the Ollama Chat Model sub-node |
| `max_alt_length` | The longest alt text allowed |
| `mpn_namespace`, `mpn_key` | The metafield that holds the model number, on the product or its first variant |
| `page_namespace`, `page_key` | The metafield that holds the manufacturer's product page URL |
| `use_dataforseo` | true to search Google for a product with no URL and no URL pattern |
| `search_location`, `language_code` | The DataForSEO search location and language |
| `user_agent` | Sent with every page and image request. Name your store and give a contact URL |
| `strip_query_params` | URL parameters to remove before anything is stored or shown, such as `content_token` |
| `slack_channel` | Where the cards go, such as `#review-images` |

**Publish settings**: `store_domain`, `admin_store_handle`, `image_size` (2048), `pad_colour` (white), `max_wait_seconds` (how long to wait for Shopify to process the images), `dry_run` (true until the first report looks right).

**Review settings**: `store_domain`, for the alt text digest buttons.

**Alt text settings**: `store_domain`, `product_query` (the Shopify product search the lane scans, `status:active` by default), `batch_size` (40 keeps the digest under Slack's 50 blocks), `max_pages`, `auto_apply` (false sends a digest first), `vision_model`, `slack_channel`.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get four data tables and your brand rows in `brand_domains`. Running Setup again keeps your tables and doesn't duplicate the brands.

## Test on a few products

1. Put the model number in each product's `mpn` metafield and, if you have it, the manufacturer page in `manufacturer_url`. Tag three products `needs-images` and point `slack_channel` at a test channel.
2. Open **Run Find now** and click **Execute workflow**. Each product gets a card with a numbered contact sheet. A product with no usable photo gets no card; its `error` in `image_queue` says why.
3. Publish the workflow so **Slack button click** answers, then tap **Approve** on a card with `dry_run` on. The `report` column in `image_queue` lists the padded URLs and alt text that would be added.
4. Set `dry_run` to false, set that row's `status` back to `approved` and run **Every hour (backstop)**, or approve a new card. Do this on a development store first: Publish, the tag removal and the alt text lane write to Shopify.

## Schedule

Publish the workflow. Find and the Publish backstop run every hour and Alt text runs on Mondays at 9am, in the workflow's time zone (Workflow settings > Timezone). The Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: Publish and the contact sheet helper run as sub-workflows, which don't count towards n8n Cloud's quota. Expect about 1,440 schedule runs a month plus one webhook run per Slack tap.

## Troubleshooting

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **From Slack?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### A product gets no card

Look at its `error` in `image_queue`. `no manufacturer page` means there's no `manufacturer_url`, no `url_pattern` for its brand, and the search (if on) found nothing on the brand's domains. `page returned 403` means the brand's site refuses your `user_agent`; some sites only answer a plain one such as `curl/8.7.1`. `robots.txt disallows` means the site asks bots to stay away from that page. `no usable image` means every photo was too small, a banner, or failed the vision checks.

### The search rarely finds a page

Google now hides many result URLs behind encrypted redirect links, which can't be matched to a brand domain. Fill in `manufacturer_url` or a brand `url_pattern` instead; they're free and always right.

### Approved images don't appear

Read the reply in the card's thread. `Shopify could not fetch` means Shopify (or wsrv.nl) was refused by the image host; Publish tries a staged upload from n8n for sources wsrv.nl can't read, but some hosts refuse every server. `Still processing` means Shopify hadn't finished within `max_wait_seconds`; the hourly backstop checks again.

### The alt text digest has no buttons

Every proposed alt text failed its checks (empty, too long, or the model didn't recognise the product). Those rows are saved as `failed` and listed at the bottom of the digest.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default, and `candidates` holds JSON for every product. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py product-images --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`image_queue`, `image_log`, `brand_domains`, `alt_queue`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the columns the workflow upserts on (`image_queue.product_id`, `brand_domains.brand` + `domain`). The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Shopify product images" n8n template in ./product-images.

1. Read product-images/README.md, SETUP.md and product-images/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py product-images
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. Help me list my brands and their websites in Setup settings.
5. Run the Setup lane and check its output with me.
6. Test on about 3 products with nothing written to my store yet (dry_run on in Publish settings), show me the cards and the dry-run report, and check them with me before anything writes to my store.
7. Stop and ask me whenever something doesn't match the README.
```
