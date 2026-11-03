# Category page SEO

An n8n template that writes the intro and meta tags for each Shopify collection from its live products, links it to its parent, children and siblings in code, and asks you in Slack before anything changes. It sorts every collection daily so buyable products come first, and audits internal links weekly.

- **Setup** creates the `collection_copy` and `link_audit` data tables. You import your keyword rows into `collection_copy`.
- **Write** (every 4 hours) picks collections with no description, or queued for a refresh, highest search volume first. It reads each one's live products and its place in your menu (and, for collections not in the menu, its smart collection rules), writes the copy with AI for head terms or a short template for the long tail, checks it in code, adds the links and posts a card.
- **Review** checks Slack's signature on every tap and ignores old cards. Approve re-reads the live description, so a hand edit is never overwritten, then writes the description and SEO title and description with `collectionUpdate`. Redraft queues it again; Skip leaves it.
- **Sort** (daily) puts relevant, buyable products first and sold-out, draft, image-less and unpriced ones last. It starts as a dry run that only reports.
- **Audit** (weekly) finds collections nothing links to, menu links to empty collections and children their parent doesn't link to, saves the findings and queues those parents for a redraft.

The full walkthrough is in the guide: [How to Automate Ecommerce Category Page SEO](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.45.7.
- A Shopify app with the `read_products`, `write_products` and `read_online_store_navigation` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- An AI model. The template uses Ollama Cloud with `gemma4:31b`; any chat model sub-node works.
- Optional: search volumes for your collections, from any keyword tool. Collections made by the shopify-collections-seo template already carry theirs.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Review, Get Shopify token for Sort, Get Shopify token for Audit | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Update the card, Post sort report, Post audit report | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Ollama Chat Model | Ollama | Base URL `https://ollama.com` and your API key |

When you import, n8n may fill these slots with existing credentials of the same type. Check each one.

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Write settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `store_name` | Added to meta titles when it fits in 60 characters |
| `tree_menu` | The menu whose nesting gives parent, children and siblings (`main-menu`) |
| `max_per_run` | The most collections drafted per run (5) |
| `ai_min_volume` | Collections with at least this many searches get AI copy; the rest get the short template (100) |
| `rewrite_existing` | False drafts only collections with an empty description |
| `skip_handles` | Collections never drafted (`frontpage`, the Home page collection every store has) |
| `intro_words` | The intro's word range (55 to 75) |
| `max_links` | The most links in the intro |
| `model` | The model name on the Ollama Chat Model sub-node |
| `slack_channel` | Where the cards go |
| `keyword_namespace` | Where the shopify-collections-seo template saved each collection's keyword and volume (`seo`) |
| `spec_keys`, `spec_labels` | Product metafields (`namespace.key`) to read as specs, and their names in the prompt |
| `voice`, `store_facts`, `examples` | Your voice, the only shipping and returns claims allowed, and example intros until you've approved your own |

**Review settings**: `store_domain`.

**Sort settings**: `store_domain`, `keyword_namespace`, `skip_handles`, `min_secondary`, `stopwords`, `synonyms`, `dry_run` (true until you've read a report) and `slack_channel`.

**Audit settings**: `store_domain`, `keyword_namespace`, `tree_menu`, `ignore`, `theme_linked` (handles your theme links in code, such as a brands page) and `slack_channel`.

## Run Setup and import keywords

Open **Run once to set up** and click **Execute workflow**. Then, in the `collection_copy` table, add a row per collection you have keyword data for: `handle`, `keyword`, `other_searches` (comma-separated) and `volume`. Collections without a row are drafted with their title as the keyword and get the template copy.

## Test

1. Set `max_per_run` to 2 and point every `slack_channel` at a test channel.
2. Open **Run Write now** and click **Execute workflow**. Each collection gets a card with the meta title, meta description, intro, links and any warnings.
3. Publish the workflow so **Slack button click** answers, then tap **Approve**, **Redraft** and **Skip**. Approved copy appears in Shopify and becomes an example for the next drafts.
4. Open **Run Sort now** with `dry_run` true and read the report before you set it to false.
5. Do this on a development store first: Review and Sort write to Shopify.

## Schedule

Publish the workflow. Write runs every 4 hours, Sort daily and Audit on Mondays, in the workflow's time zone (Workflow settings > Timezone). The Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

## Troubleshooting

### A card says "no draft"

The model call failed or its reply had no JSON object in it. The row is marked `failed` and tried again on the next run. **Check and link** already strips code fences and trailing commas; if a model keeps failing, try another model in **Write settings**.

### The card says someone edited the page

The description changed in Shopify after the draft was written, so Approve left it alone and queued a fresh draft.

### A collection says "switches to Manual, products move on the next run"

Shopify re-sorts a collection after it switches to Manual, so the first live run only switches it and the moves happen on the next run.

### Sort only orders the first 250 products

Each collection's first 250 products are read and moved. Bigger collections keep the rest in their current order.

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py category-page-seo --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`collection_copy`, `link_audit`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the columns the workflow upserts on. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Category page SEO" n8n template in ./category-page-seo.

1. Read category-page-seo/README.md, SETUP.md and category-page-seo/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py category-page-seo
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
5. Run the Setup lane and check its output with me.
6. Test on about 5 products with nothing written to my store yet (dry_run on where the template has it, and no Slack card approved), show me what it produced and check it with me before anything writes to my store.
7. Stop and ask me whenever something doesn't match the README.
```
