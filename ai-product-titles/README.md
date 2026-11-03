# AI product titles

An n8n template that rewrites the Shopify product titles you tag `retitle` to a formula per product type, checks every title in code, and asks you in Slack before anything changes. Titles you approve become examples for the next batch.

- **Setup** creates the `title_examples` and `title_drafts` data tables and seeds one example title per product type.
- **Write** reads the tagged products (or the IDs in `product_ids`), picks up to five approved titles from the same product type as examples, asks the model for a title, then checks it in code: every model code must be a whole token from the product data, every number must be in the data, plus length, banned words and variant rules. A failed title falls back to a tidied version of the current one. It posts a before-and-after card to Slack and removes the tag.
- **Review** checks Slack's signature on every tap and ignores taps on old cards. Approve sends the title to Push, Edit opens a modal with the title filled in, Reject marks the draft.
- **Push** reads the live title first, so a title someone changed in Shopify since the draft is left alone. Otherwise it writes the title with `productUpdate`, saves it as an example and updates the card.

The full walkthrough is in the guide: [Product Title Optimisation With AI](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.45.
- A Shopify app with the `read_products` and `write_products` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- An AI model. The template uses Ollama Cloud with `gemma4:31b`; any chat model sub-node works.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Push | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post the card, Open the edit modal, Show rejection on card, Update the card | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Ollama Chat Model | Ollama | Base URL `https://ollama.com` and your API key |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Write settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `queue_tag` | The tag that queues a product for a new title (`retitle`) |
| `product_ids` | Product IDs to retitle instead of the tagged ones, for a test batch. Leave it `[]` to use the tag |
| `batch_size` | The most products per run |
| `model` | The model name on the Ollama Chat Model sub-node |
| `max_length` | The longest title allowed, in characters |
| `mpn_namespace`, `mpn_key` | The metafield that holds the model number (MPN), on the product or its first variant |
| `slack_channel` | Where the cards go, such as `#review-titles` |
| `banned_words` | Words a title must not contain |
| `colour_words` | Colours that must stay in the title of a single-variant product |
| `formulas` | The attribute order per product type, plus a `default` |

**Push settings**: `store_domain`, and `update_seo_title` (false by default; set it to true to write the SEO title as well).

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get two data tables and three seed rows in `title_examples`. Replace the seed rows with a few titles you like from your own catalogue, one or two per product type; running Setup again keeps your tables and doesn't duplicate the seeds.

## Test on 10 products

1. Put ten product IDs (the number at the end of the product's admin URL) in `product_ids`, and point `slack_channel` at a test channel.
2. Open **Run now** and click **Execute workflow**. Each product gets a card with the current and proposed titles, the character count, and either "written by the model" or the reason it fell back.
3. Publish the workflow so **Slack button click** answers, then tap **Approve**, **Edit** and **Reject** on a few cards. Approved and edited titles appear in Shopify and in `title_examples`.
4. Do this on a development store first: Push and the tag removal write to Shopify.

## Schedule

Publish the workflow. Write runs every 3 hours, in the workflow's time zone (Workflow settings > Timezone), and the Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: Push runs as a sub-workflow, which doesn't count towards n8n Cloud's quota. Expect 240 schedule runs a month plus one webhook run per Slack tap.

## Troubleshooting

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions show up and stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### A tap does nothing the second time

That's on purpose. **Get pending draft** only finds drafts that are still pending, so a second tap, or a tap on an old card, stops there.

### Edit doesn't open the modal

Slack's `trigger_id` lasts 3 seconds. Keep **Open the edit modal** straight after **Route the click**, with nothing slow in between.

### Most titles fall back

Read the reason on the card. `code not in source` means the model wrote a model code, or a hyphenated spec like `4-Port`, that isn't a whole word in the product data; check the MPN metafield is filled in and that `mpn_namespace` and `mpn_key` point at it. `too long` means the formula asks for more than `max_length` allows.

### The card says the title wasn't changed

Someone changed the title in Shopify after the draft was written, so Push left it alone. Tag the product again for a fresh draft.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py ai-product-titles --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`title_examples`, `title_drafts`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`, and a unique key on the columns the workflow upserts on. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "AI product titles" n8n template in ./ai-product-titles.

1. Read ai-product-titles/README.md, SETUP.md and ai-product-titles/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py ai-product-titles
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
5. Run the Setup lane and check its output with me.
6. Test on about 5 products with nothing written to my store yet (dry_run on where the template has it, and no Slack card approved), show me what it produced and check it with me before anything writes to my store.
7. Stop and ask me whenever something doesn't match the README.
```
