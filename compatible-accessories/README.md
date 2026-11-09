# Compatible accessories

An n8n template that matches each accessory you sell to the products it fits, using only what the accessory's manufacturer says on its own page. Code finds the products you sell that the page names (any brand), an AI model proposes matches with a verbatim quote for each, code checks every quote, a second AI pass audits what's left, and you approve each accessory in Slack. Approved accessories go to the product's **Complementary products** (the Search & Discovery field a stock theme such as Horizon shows), and each accessory gets a **Compatible with** list of plain links.

- **Setup** creates the `accessory_sources`, `accessory_reviews` and `accessory_matches` data tables, turns on Shopify's standard **Complementary products** field, and creates the **Model number (MPN)** (`custom.mpn`), **Manufacturer page** (`custom.manufacturer_url`) and **Compatible with** (`custom.compatible_with`, a list of products) fields.
- **Find** (called by Match) reads each accessory's manufacturer page, plus any extra URL fields you list (a datasheet field, say). With `use_search` on, it fills a missing manufacturer page from a Google search through DataForSEO, keeping the first result on one of the brand's own domains that names the model (not its shop, forum or support site). It fetches each page (PDFs too, with an optional Firecrawl fallback for sites that refuse a plain request) and keeps the text only if it names the accessory's own model.
- **Match** takes up to `batch_size` accessories tagged `accessories` an hour (or the IDs in `product_ids`) and reads your whole catalogue. For each accessory it:
  - finds the products you sell whose model number appears on its pages, as a whole token (`UVC-G5-PTZ` never matches `UVC-G5-PTZ-W`), any brand. No candidates means no model call;
  - asks the model which of them the page says the accessory fits, each with a quote;
  - checks in code that every quote is on the page and names that product's exact model;
  - has a second model audit each match (on by default);
  - posts one Slack card per accessory and removes the tag. A failed model call keeps the tag for the next run.
- **Review** answers Slack at once, then checks the signature and age. **Exclude** strikes one match off the card; **Approve remaining** approves the rest and starts Publish; **Reject all** keeps Shopify as it is. A click on an old card changes nothing, and nothing you excluded or rejected is proposed again.
- **Publish** re-reads each manufacturer page to check the quote is still there, then adds each approved accessory to its product's Complementary products. It keeps what's already in the list, stops at `max_complementary` (Shopify's limit is 10) and never removes anything, and writes with Shopify's `compareDigest`, so an edit made in the meantime isn't overwritten. It fills the accessory's Compatible with list and replies in the card's thread. `dry_run` is on until you turn it off.

The full walkthrough is in the guide: [How to Add Compatible Accessories to Shopify Complementary Products Automatically](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud) on a public HTTPS URL, because Slack has to reach the webhook. Tested on n8n 2.46.
- A Shopify app with the `read_products` and `write_products` scopes, and its client ID and secret.
- The free Search & Discovery app if you want to see and edit complementary products in its Recommendations page (the template writes the same field directly).
- A Slack app with a bot token (`chat:write`; invite the bot to your review channel, or add `chat:write.public`), Interactivity turned on, and its signing secret.
- An AI model. The template uses Ollama Cloud with `gemma4:31b` for both the draft and the audit; any chat model sub-node works.
- Optional: DataForSEO, to find missing manufacturer pages (about US$0.0035 a search at depth 20); Firecrawl, for sites that refuse a plain request.
- Model numbers. Setup creates `custom.mpn`; fill it in by hand, in the bulk editor, or by CSV import with a column headed `Model number (MPN) (product.metafields.custom.mpn)`. When it's empty the template uses the first variant's SKU. A model number needs letters and digits and at least four characters to be matched.
- Each accessory's manufacturer page in `custom.manufacturer_url` (`Manufacturer page (product.metafields.custom.manufacturer_url)` in a CSV), unless you turn on `use_search`.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token for Setup, Get Shopify token for Find, Get Shopify token for Match, Get Shopify token for Publish | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Update the card, Update the decided card, Reply in the thread | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Draft model, Audit model | Ollama | Base URL `https://ollama.com` and your API key |
| Search Google (optional) | Basic Auth | Your DataForSEO API login and password |
| Firecrawl scrape (optional) | Header Auth | Name `Authorization`, Value `Bearer fc-...` |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Show complementary products on your product page

On Horizon: **Online Store > Themes > Customize > Products > Default product > Add section > Product recommendations**, set **Type** to **Complementary**, and change its heading to something like "Compatible accessories". Keep the existing Related one for "You may also like". An empty complementary row hides itself.

For the accessory's **Compatible with** list, add a **Custom Liquid** block to the product information section and paste:

```liquid
{%- assign fits = product.metafields.custom.compatible_with.value -%}
{%- if fits != blank -%}
  <div class="compatible-with">
    <h2 class="h5">Compatible with</h2>
    <ul>
      {%- for item in fits -%}
        <li><a href="{{ item.url }}">{{ item.title }}</a></li>
      {%- endfor -%}
    </ul>
  </div>
{%- endif -%}
```

## Settings

**Setup settings**: `store_domain`.

**Find settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `queue_tag` | The tag that queues an accessory (`accessories`) |
| `product_ids` | Product IDs to read instead of the tagged ones, for a test batch. Leave it `[]` (Match passes its own batch) |
| `batch_size` | The most accessories per run |
| `model_number_from` | `metafield` (`custom.mpn`, then the SKU) or `sku` |
| `colour_suffixes` | Model endings that mean the same product in another colour (`-B`, `-W`). Leave out endings that mean a different model |
| `extra_url_fields` | More URL fields to read, as `namespace.key` (`["custom.spec_url"]`). A `list.url` field works too |
| `manufacturer_domains` | Each brand's own domains, by Vendor, for the search: `{"Ubiquiti": ["ui.com"]}` |
| `use_search` | true to find missing manufacturer pages with DataForSEO |
| `search_location`, `search_language`, `search_depth` | DataForSEO's settings |
| `max_source_chars` | How much of each page is kept |
| `use_firecrawl` | true to retry blocked or empty pages through Firecrawl |
| `user_agent` | Sent to manufacturer sites. Name your store and give a URL |

**Match settings**:

| Setting | What it does |
|---|---|
| `store_domain`, `queue_tag`, `product_ids`, `model_number_from`, `colour_suffixes` | As above |
| `batch_size` | Accessories per run (5 an hour is 120 a day) |
| `model`, `audit_model` | The model names on the two Ollama sub-nodes |
| `use_audit` | false skips the second model (cheaper, less strict) |
| `max_matches` | The most matches on one card (12) |
| `max_candidates` | The most products from one page sent to the model |
| `max_prompt_chars` | How much page text goes into the prompt. Long pages are cut to the passages around each model number and fit word |
| `review_channel` | The Slack channel ID for the cards |

**Publish settings**: `store_domain`, `dry_run` (true until you've checked a run), `max_complementary` (10), `write_compatible_with`, `recheck_quotes`, `batch_size` and `user_agent`.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get three data tables and the fields under **Settings > Custom data > Products**. **Setup summary** shows each field as `created`, `already there` or the error to fix; `complementary: on` means Shopify's Complementary products field is turned on. Running Setup again is safe.

## Test on a few accessories

1. Fill in the model number and manufacturer page on three to five accessories whose pages list compatible models, make sure the products they fit have model numbers too, put the accessories' IDs in both `product_ids`, and point `review_channel` at a test channel.
2. Open **Run Match now** and click **Execute workflow**. Open **Find the candidates**: each accessory shows `drafting`, `no_page`, `no_candidates` or `unchanged`, with the products its pages name. **Check the verdicts** shows what was kept and why the rest was dropped.
3. Publish the workflow so **Slack button click** answers. Exclude a match on one card, approve the rest, and reject another card.
4. With `dry_run` on, Publish saves each match as `dry_run` and replies "Dry run, would add to ...". Read **Plan the writes**.
5. Set `dry_run` to false, set those rows' `status` back to `approved` in `accessory_matches`, and run **Run Publish now**. The accessory appears in the product's Complementary products, and the card's thread says where.
6. Do this on a development store first: Setup, Find, Match (the tag removal) and Publish write to Shopify.

## Schedule

Publish the workflow. Match runs every hour and the Publish backstop every hour at half past, in the workflow's time zone (Workflow settings > Timezone). An approval in Slack starts Publish straight away; the backstop only catches anything left approved. That's about 1,440 schedule runs a month plus one webhook run per Slack click; the Find and Publish lanes run as sub-workflows when another lane calls them, which don't count towards n8n Cloud's quota. The Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you. Once the backlog is done, run Match daily, or tag new accessories as they arrive.

## Troubleshooting

### Nothing happens when I click a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### An accessory gets no card

Read its row in `accessory_reviews`:
- `no_page`: no saved page names its model. Fill in the Manufacturer page field, or check the model number matches the way the page writes it.
- `no_candidates`: the page names no other product you sell. Check those products have model numbers. Accessories that fit by a standard (memory cards, drives, cables) rarely list models.
- `no_matches`: the model or the audit found no compatibility statement. `rejected` lists why each claim was dropped.
- `unchanged`: nothing changed since the last card, or every product the page names is already decided.

Rows in `accessory_sources` with `wrong_model` or `empty` say why a page wasn't used.

### The search finds the wrong page, or none

The search is a plain one (`site:` costs more and Google often ignores it), so most results are resellers, which the template skips; Google returns links through `google.com/goto`, which Find resolves to the real address. Check `manufacturer_domains` holds the brand's own domain, or fill in the manufacturer page by hand.

### A match wasn't added

Read the thread reply, or `error` in `accessory_matches`. `list_full` means the product already has `max_complementary` complementary products: remove one, set the row back to `approved` and run Publish. `source_changed` means the quote is gone from the manufacturer page. `unavailable` means the product or accessory isn't active and published. An accessory with no stock doesn't show in the row even when it's in the list.

### I want a decided match proposed again

Delete its row in `accessory_matches` and tag the accessory again.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py compatible-accessories --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`accessory_sources`, `accessory_reviews`, `accessory_matches`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key: `accessory_sources` on `accessory_id` and `url`, `accessory_reviews` on `accessory_id`, `accessory_matches` on `accessory_id` and `target_id`. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Compatible accessories" n8n template in ./compatible-accessories.

1. Read compatible-accessories/README.md, SETUP.md and compatible-accessories/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py compatible-accessories
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Help me check my catalogue is ready: which accessories I sell, whether they and the products they fit have model numbers, and where each accessory's manufacturer page is. Fill in manufacturer_domains with me if I want the search.
5. Walk me through every other settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
6. Run the Setup lane and check its output with me, then help me add the Complementary products section and the Compatible with block to my theme (in a copy of the theme first).
7. Test on about 3 accessories with nothing written to my store yet (dry_run on in Publish settings): show me the cards and the dry-run output, and check them with me before anything writes to my store.
8. Stop and ask me whenever something doesn't match the README.
```
