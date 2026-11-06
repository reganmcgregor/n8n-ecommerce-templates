# AI product descriptions

An n8n template that writes a short intro for each Shopify product you tag `describe`, from the product's own specs and its maker's page, checks every number in code, and asks you in Slack before anything changes. It replaces only the intro: the lists, tables and headings below it stay exactly as they are. Intros you approve become examples for the next batch.

- **Setup** creates the `description_drafts`, `description_examples` and `source_pages` data tables, adds a **Manufacturer page** product field (`custom.manufacturer_url`, a URL) and seeds three example descriptions.
- **Write** reads the tagged products (or the IDs in `product_ids`), collects their facts from metafields and from the lists and tables already in the description, trims the manufacturer's page to its spec paragraphs (cached, so a redraft never fetches it twice), and asks the model for two or three paragraphs in your `brand_voice`, with up to three approved examples from the same product type. It then checks every number and model code against the sources and posts a card with the draft in an edit box. Products with fewer than `min_facts` facts are saved as `needs_specs` with no card.
- **Review** checks Slack's signature on every tap and ignores taps on old cards. Approve saves whatever is in the edit box and starts Push; Reject marks the draft.
- **Push** reads the live description, swaps only the intro and writes it with `productUpdate`, then saves the text as an example and replies under the card. An hourly run pushes anything left approved.

The full walkthrough is in the guide: [Build an AI Product Description Generator That Checks Its Facts](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.
- A Shopify app with the `read_products` and `write_products` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- An AI model. The template uses Ollama Cloud with `gemma4:31b`; any chat model sub-node works.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token for Setup, Get Shopify token, Get Shopify token for Push | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Show the decision, Reply: live, Reply: failed | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Ollama Chat Model | Ollama | Base URL `https://ollama.com` and your API key |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Setup settings**: `store_domain`, plus `manufacturer_url_namespace` and `manufacturer_url_key` for the product field that holds the maker's page (`custom` and `manufacturer_url`). If you already keep that URL in another URL metafield, point both settings nodes at it instead.

**Write settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `queue_tag` | The tag that queues a product for a description (`describe`) |
| `product_ids` | Product IDs to describe instead of the tagged ones, for a test batch. Leave it `[]` to use the tag |
| `batch_size` | The most products per run |
| `model` | The model name on the Ollama Chat Model sub-node |
| `brand_voice` | Two or three sentences on how your store sounds. It fills the Voice line of the system message |
| `min_facts` | Products with fewer facts than this are saved as `needs_specs` and skipped |
| `min_words` | Shorter replies are saved as `failed` |
| `max_chars_manufacturer`, `max_chars_supplier` | How much of the maker's page and of the current description goes into the prompt |
| `manufacturer_url_namespace`, `manufacturer_url_key` | The product field that holds the maker's page |
| `intro_ends_at` | The HTML tags where the intro ends (headings, lists, tables, `div` blocks and so on). Everything from the first one down is kept |
| `user_agent` | The User-Agent sent to manufacturer sites |
| `slack_channel` | Where the cards go, such as `#review-descriptions` |
| `spec_words` | Words that mark a spec paragraph on a manufacturer page |
| `always_ok` | Standards a draft may mention even when the sources don't, such as `19-inch` or `H.265` |
| `banned_phrases` | Phrases that add a warning to the card |
| `strip_patterns` | Sentences in the current description that contain these never reach the model |

**Push settings**: `store_domain`, `intro_ends_at` (keep it the same as in Write settings) and `dry_run`. With `dry_run` true, Push saves the merged HTML in `description_drafts` (status `dry_run`) without touching Shopify; set a row back to `approved` to push it.

## How the intro is found

The intro is everything above the first tag in `intro_ends_at`. A wrapper `div` around the whole description is looked inside, and a short label paragraph just above a list or table ("Specifications:" or a bold line) stays with the block it introduces. So:

- a description that opens with paragraphs and then has headings, lists or tables gets those paragraphs replaced;
- a description that opens with a list or table keeps all of it, and the new intro goes on top;
- a description that is only paragraphs is replaced whole. The card says which of the three will happen before you approve.

If your intros themselves contain a list, take `ul` and `ol` out of `intro_ends_at`.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get three data tables, the Manufacturer page field on products (pinned, so it shows on every product page in admin) and three seed rows in `description_examples`. Replace the seed rows with two or three descriptions you already like from your own catalogue, one per product type; the model copies their tone and length. Running Setup again keeps your tables and doesn't duplicate the seeds.

## Test on 5 products

1. Put five product IDs (the number at the end of the product's admin URL) in `product_ids`, point `slack_channel` at a test channel, and set `dry_run` to true in **Push settings**.
2. Open **Run now** and click **Execute workflow**. Each product gets a card with the current intro, the draft in an edit box, the word count and any flagged numbers.
3. Publish the workflow so **Slack button click** answers, then edit a draft in its box and tap **Approve**, and tap **Reject** on another. Check the merged HTML in `description_drafts`.
4. Set `dry_run` back to false and approve one more to see it in Shopify. Do this on a development store first: Push and the tag removal write to Shopify.

## Schedule

Publish the workflow. Write runs every 3 hours and Push every hour, in the workflow's time zone (Workflow settings > Timezone), and the Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: Push started from Slack runs as a sub-workflow, which doesn't count towards n8n Cloud's quota. Expect 240 Write runs and 720 hourly Push runs a month plus one webhook run per Slack tap; if that's too many for your plan, change **Every hour** to every 6 hours, since Slack starts Push straight away anyway.

## Troubleshooting

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions show up and stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### A tap does nothing the second time

That's on purpose. **Get pending draft** only finds drafts that are still pending, so a second tap, or a tap on an old card, stops there.

### A product never gets a card

Look it up in `description_drafts`. `needs_specs` means it had fewer than `min_facts` facts: fill in its metafields or add a spec list to its description, then tag it again. `failed` with "model call failed" keeps the tag, so the next run tries again; other failures remove it.

### The draft ignores the maker's page

Check `source_pages`. Status `empty` means the page blocked the request or held nothing that looked like specs (some sites answer a plain request with 403). The draft is still written from the specs. A scraping API such as Firecrawl can fetch pages that block plain requests.

### Shopify refused it

The reply under the card has Shopify's reason, and the row is `failed`. Fix the cause and set the row back to `approved`; the hourly Push picks it up.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py ai-product-descriptions --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`description_drafts`, `description_examples`, `source_pages`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the column the workflow upserts on (`description_examples` is unique on a hash of the text, because a long description is too big for a plain unique index). The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "AI product descriptions" n8n template in ./ai-product-descriptions.

1. Read ai-product-descriptions/README.md, SETUP.md and ai-product-descriptions/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py ai-product-descriptions
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. Help me write brand_voice and pick two or three of my own best descriptions to replace the seed examples.
5. Run the Setup lane and check its output with me.
6. Test on about 5 products with nothing written to my store yet (dry_run on, and no Slack card approved), show me what it produced and check it with me before anything writes to my store.
7. Stop and ask me whenever something doesn't match the README.
```
