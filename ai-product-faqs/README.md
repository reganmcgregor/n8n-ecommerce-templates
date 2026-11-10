# AI product FAQs

An n8n template that writes FAQs for your Shopify products from each product's manufacturer page and documents. Every answer has to quote its source: code checks each quote and every number, a second AI pass audits what's left, and you approve each product's set in Slack before it goes live. Approved answers are saved as Product FAQ metaobjects and shown on the product page with FAQPage schema. Shoppers can ask new questions from the product page, and your team can add them from Slack.

- **Setup** creates the `faq_drafts`, `faq_sources` and `faq_questions` data tables, the `product_faq` metaobject type, the product fields **FAQs** (`custom.faqs`), **Manufacturer page** (`custom.manufacturer_url`) and **Model number (MPN)** (`custom.mpn`), seeds a few questions and posts an **Add a question** button in Slack.
- **Find** (run by Draft, or on its own) collects each product's sources: the page in the Manufacturer page field, document links on that page (manuals, quick start guides, datasheets), and, if you turn it on, a Google search through DataForSEO that keeps only results on the manufacturer's own domain. It fetches each one (PDFs too, and through Firecrawl if a site blocks the plain request), keeps only text that names the exact model number, trims it and saves it.
- **Draft** (hourly) takes products tagged `faq`, writes up to `max_faqs` answers that each quote their source, checks every quote and number in code, has a second model audit each answer, and posts one Slack card per product with every answer, its quotes and what was dropped. Products whose sources haven't changed since their last set get no new card.
- **Review** (Slack buttons) checks Slack's signature. Approve starts Publish; Reject leaves Shopify as it is. It also handles the question cards and the Add a question form.
- **Publish** writes the answers as metaobjects, links the set to the product in one call, then deletes the previous set. `dry_run` is on until you turn it off.
- **Ask** takes questions from the product page form and the Slack form, and posts a card: **Answer it**, **Add to question bank** or **Ignore**.
- **Refresh** (weekly, off until you turn it on) re-tags products whose live FAQs are older than `refresh_after_days`, so Draft checks their sources again.

The full walkthrough is in the guide: [AI FAQ Generator for Product Pages That Get Cited in AI Search](https://www.reganmcgregor.com.au/ai-faq-generator/).

## What you need

- n8n with Data Tables (self-hosted or Cloud), on a public HTTPS URL so Slack and your store can reach the webhooks. Tested on n8n 2.46.
- A Shopify app with the `read_products`, `write_products`, `read_metaobjects`, `write_metaobjects`, `read_metaobject_definitions` and `write_metaobject_definitions` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- An AI model. The template uses Ollama Cloud with `gemma4:31b` for both the writer and the auditor; any chat model sub-node works.
- Each product's model number, in the Model number (MPN) field (or set `model_number_from` to `sku`).
- Optional: DataForSEO for the search and People Also Ask; Firecrawl for sites that refuse a plain request.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Every **Get Shopify token** node | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Update the card, Post the question card, Update the question card, Open the form, Reply: live, Reply: failed, Post the Add a question button | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Writer model, Auditor model | Ollama | Base URL `https://ollama.com` and your API key |
| Search Google (optional) | Basic Auth | Your DataForSEO API login and password |
| Firecrawl scrape (optional) | Header Auth | Name `Authorization`, Value `Bearer fc-...` |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential. Leave the two optional ones empty if you don't use them.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click**.

## Settings

Each lane has a settings node at its head. The ones you'll change:

| Setting | Lane | What it does |
|---|---|---|
| `store_domain` | all | Your `*.myshopify.com` domain |
| `review_channel` | Setup, Draft, Ask | The Slack channel ID for cards (right-click the channel > Copy link; the ID is the last part) |
| `queue_tag` | Find, Draft, Refresh | The tag that queues a product (`faq`) |
| `product_ids` | Find, Draft | Numeric product IDs to test with, instead of the tag |
| `manufacturer_domains` | Find | Each brand you sell and its own domains, as written in the product's Vendor: `{"Ubiquiti": ["ui.com"]}` |
| `use_search`, `use_people_also_ask` | Find | Search Google through DataForSEO for the manufacturer's page and documents, and for People Also Ask questions |
| `use_firecrawl` | Find | Fetch a blocked page through Firecrawl |
| `max_documents`, `max_source_chars` | Find | How many documents per product, and how much of each one is kept |
| `model`, `audit_model` | Draft | The writer and the auditor (they can differ) |
| `max_faqs`, `max_prompt_chars` | Draft | Answers per product, and how much source text goes into the prompt |
| `intents`, `banned_words` | Draft | Topics to cover when customers haven't asked, and words an answer must not use |
| `dry_run` | Publish | `true` builds everything but writes nothing to Shopify |
| `max_per_hour`, `salt` | Ask | Questions one visitor can send in an hour, and any random text for hashing their IP address |
| `enabled`, `refresh_after_days` | Refresh | Turn the weekly check on, and how old a live set must be |

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get three data tables, the Product FAQ metaobject type (Content > Metaobjects in Shopify), the three product fields and a few seed questions in `faq_questions`. Replace the seeds with the questions your customers actually ask, by product type (`default` applies to every product). Pin the **Add a question** message in your Slack channel. Running Setup again keeps your tables; Shopify answers `TAKEN` for anything that already exists.

## Add the blocks to your theme

In the theme editor, open a product page, then **Product information > Add block > Custom Liquid**, below the description:

1. Paste [`theme/faqs.liquid`](theme/faqs.liquid). It shows the answers as collapsible rows with a link to each source, and adds FAQPage JSON-LD from the same fields. It prints nothing for a product without FAQs.
2. Add a second Custom Liquid block and paste [`theme/ask.liquid`](theme/ask.liquid). Replace `https://your-n8n.example.com/webhook/faq-ask` with the production URL of **Question from the store**, and set that node's **Allowed Origins (CORS)** to your store's address.

Check with your browser's View source (the questions are in the HTML) and [validator.schema.org](https://validator.schema.org). Google's Rich Results Test no longer checks FAQ markup.

## Test on a few products

1. Fill in each product's Model number (MPN) and, if you know it, its Manufacturer page.
2. Put two or three product IDs in `product_ids` in **Find settings** and **Draft settings**. Keep `dry_run` on.
3. Run **Run Draft now**. Read each card: the quotes under each answer are what the answer rests on.
4. Approve one. With `dry_run` on, its row becomes `dry_run`. Set `dry_run` to false, set the row back to `approved`, and run **Every 15 minutes** (or approve the next one) to publish.
5. Check the product page, then empty `product_ids` and tag products `faq`.

## Schedule

Publish the workflow. **Every hour** drafts tagged products, **Every 15 minutes** publishes anything still approved, and **Every Monday** runs Refresh once you set `enabled` to true.

## Troubleshooting

### A product gets no card

Its row in `faq_drafts` says why: `no_sources` (nothing found names the model: fill in the Manufacturer page, or check the model number), `no_answers` (every answer was dropped: the reasons are in `rejected`), `failed` (no model number, or the model call failed: the tag stays on and the next run tries again). A product whose sources haven't changed since its last set gets no new card.

### A source is missing

Look in `faq_sources`. `wrong_model` means the text never names the exact model number (a page for the whole product family, or a guide built by scripts). `empty` means nothing could be read: a blocked site (turn on Firecrawl), a scanned PDF, or a page built by JavaScript.

### Nothing happens when I tap a button

Check the Request URL in your Slack app and that the workflow is published. A tap on an old card, or a second tap, does nothing on purpose.

### The Ask form says to try again

The question must be 10 to 300 characters, and one visitor can send `max_per_hour` an hour. If nothing arrives at all, check the URL in the block and the webhook's Allowed Origins.

### Shopify refused it

The reply under the card has Shopify's reason, and the row is `failed`. Fix the cause and set the row back to `approved`.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py ai-product-faqs --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`faq_drafts`, `faq_sources`, `faq_questions`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the columns the workflow upserts on. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "AI product FAQs" n8n template in ./ai-product-faqs.

1. Read ai-product-faqs/README.md, SETUP.md and ai-product-faqs/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json), and whether I'll use DataForSEO and Firecrawl.
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py ai-product-faqs --only httpCustomAuth,ollamaApi,slackApi,crypto
   (add httpBasicAuth for DataForSEO and httpHeaderAuth for Firecrawl if I use them, and --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. Help me fill manufacturer_domains from my store's vendors, and replace the seed questions with questions my customers ask.
5. Run the Setup lane and check its output with me. Help me add the two Custom Liquid blocks in theme/ to a copy of my theme first.
6. Test on 2 or 3 products with dry_run on and product_ids set, show me the Slack cards and check the quotes with me before anything writes to my store.
7. Stop and ask me whenever something doesn't match the README.
```
