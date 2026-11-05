# Shopify collection sorting

An n8n template that writes each Shopify collection's Manual order so the products that best match the collection's keyword come first, and sold-out, draft, image-less and unpriced products go last. It runs every 2 hours, so a sell-out or a restock moves within 2 hours, and it never hides, unpublishes or deletes anything.

- **Setup** creates the `collection_sort` and `title_vectors` data tables and adds a row per published collection: a keyword (from the `seo.target_keyword` metafield, or the collection title) and a mode from the collection's current sort. Best selling and Newest collections become `skip`, Manual collections become `tier` (your order kept, sold-out and unbuyable products moved down), and the rest `keyword`. Running it again only adds new collections, so your edits stay.
- **Sort** (every 2 hours) reads each collection's first 250 products in their current order and scores every title against the keyword, by shared words (`words`) or by words blended with meaning from an embeddings model (`blend`). Each search in `other_searches` places its one best product near the top. Buyable products go first by score, then sold-out products, then drafts and products with no image or no price. A collection that isn't on Manual sort is switched on one run and its products move on the next, because Shopify re-sorts a collection after the switch. It reports to Slack when something changed, and starts as a dry run that only reports.

The full walkthrough is in the guide: [How to Sort Shopify Collections by Relevance With Keyword Scoring and Embeddings](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.6.
- A Shopify app with the `read_products` and `write_products` scopes, and its client ID and secret.
- Optional: a Slack app with a bot token (`chat:write`) for the report.
- Optional, for `blend` mode: an embeddings endpoint. The template defaults to Ollama's `/api/embed` with `nomic-embed-text` (free on your own machine: `ollama pull nomic-embed-text`). Any OpenAI-style `/v1/embeddings` API works too.

No chat model. [SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Sort | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post sort report | Slack API | Your bot token |

When you import, n8n may fill these slots with existing credentials of the same type. Check each one.

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.

## Settings

**Setup settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `keyword_namespace`, `keyword_key` | The collection metafield Setup reads the keyword from (`seo.target_keyword`); the title is used when it's empty |
| `leave_alone` | Sorts that Setup marks `skip` (`BEST_SELLING`, `CREATED_DESC`), because switching them to Manual would freeze them |

**Sort settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `min_secondary` | The lowest score a product needs to be placed by one of the `other_searches` (0.5) |
| `stopwords` | Words ignored when matching (`for`, `with`, `and`, `the`, `a`) |
| `synonyms` | Words counted as another word (`lte` counts as `4g`, `wireless` as `wifi`) |
| `match_mode` | `words` (shared words only, no model) or `blend` (meaning from embeddings blended with the word score) |
| `meaning_weight` | The share of meaning in `blend` (0.6, so words keep 0.4) |
| `embed_url`, `embed_model` | The embeddings endpoint and model (`http://localhost:11434/api/embed`, `nomic-embed-text`). If n8n runs in Docker and Ollama on the host, use `http://host.docker.internal:11434/api/embed` |
| `embed_api_key` | Only for a hosted embeddings API. It sits in the workflow in plain text, so leave it empty unless you need it and don't share the workflow with it filled in |
| `query_prefix`, `doc_prefix` | The prefixes `nomic-embed-text` expects (`search_query: `, `search_document: `). Clear both for other models |
| `max_moves` | The most moves per collection per run (250, Shopify's limit per call). The rest wait for the next run |
| `dry_run` | True until you've read a report. Nothing is written while it's true |
| `slack_channel` | Where the report goes |

## Run Setup and set keywords

Open **Run Setup** and click **Execute workflow**. Then open the `collection_sort` table and, for each collection you want sorted by relevance, set `keyword` to the search the page should rank for and `other_searches` to a comma-separated list of related searches, in your order. Change `mode` to `keyword`, `tier` or `skip` as you like. Collections you never edit are sorted by their title.

## Test

1. Point `slack_channel` at a test channel and keep `dry_run` true.
2. Open **Run Sort now** and click **Execute workflow**. The report lists each collection that would change, its first three products and how many sold-out and unbuyable products sit last.
3. Set `dry_run` to false and run it again. Collections that weren't on Manual are switched; run it once more and their products move. A third run should change nothing.
4. Do this on a development store first: Sort writes to Shopify.

## Schedule

Publish the workflow. Sort runs every 2 hours, in the workflow's time zone (Workflow settings > Timezone). That's about 360 executions a month. Set an Error Workflow too, so a crashed run reaches you.

In testing, a dry run over 18 collections took about 10 seconds; a `blend` run embedded 12 texts in under 5 seconds on a local Ollama, and the next run embedded none.

## Troubleshooting

### A collection says "switches to Manual, products move on the next run"

Shopify re-sorts a collection after it switches to Manual, so the first live run only switches it and the moves happen on the next run.

### A collection says "(the rest on the next run)"

It needed more moves than `max_moves`. The next run reads the new order and carries on.

### Products I edited by hand moved again

Collections in `keyword` mode are rewritten every run. Set the collection's `mode` to `tier` to keep your order (only sold-out and unbuyable products move down), or `skip` to leave it alone.

### Sort only orders the first 250 products

Each collection's first 250 products are read and moved. Bigger collections keep the rest in their current order.

### Blend mode fails at Add meaning scores

n8n can't reach `embed_url`, or the model isn't pulled. From the n8n machine, `curl <embed_url> -d '{"model":"nomic-embed-text","input":["test"]}'` should return an `embeddings` array.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Each saved title vector takes about 5 KB, so a 10,000-product catalogue needs about 50 MB in `title_vectors`. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py shopify-collection-sorting --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run Setup**. It creates the tables (`collection_sort`, `title_vectors`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first. Edit the keywords in Supabase's table editor.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the columns the workflow inserts on (`handle`, `text`). The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Shopify collection sorting" n8n template in ./shopify-collection-sorting.

1. Read shopify-collection-sorting/README.md, SETUP.md and shopify-collection-sorting/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json), and whether I want word matching only or embeddings too (match_mode).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py shopify-collection-sorting
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
5. Run the Setup lane and check the collection_sort table with me: the keyword, other searches and mode for my main collections.
6. Run Sort with dry_run true, show me the report and check it with me before anything writes to my store.
7. Stop and ask me whenever something doesn't match the README.
```
