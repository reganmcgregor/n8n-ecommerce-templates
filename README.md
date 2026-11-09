# n8n ecommerce templates

Free n8n templates for running an online store: monitoring competitor prices, adding products, writing product titles and descriptions, syncing inventory, enriching product data and images, building and sorting collections, and internal linking. Each one is a single n8n canvas with a lane per job, keeps its state in n8n Data Tables (or in Supabase, with the `workflow-supabase.json` version), and asks you in Slack before it changes anything in your store.

| Template | What it does |
| --- | --- |
| [Competitor price monitoring](competitor-price-monitoring/) | Finds who else sells your exact products by model number, reads their prices from structured data, and posts a weekly Slack report of every product where a competitor is cheaper. No AI model needed. |
| [Add products to Shopify](add-products-to-shopify/) | Brings a wholesaler's CSV price list (and, optionally, AliExpress listings) into one table, finds what you don't sell yet, writes the copy with AI and creates Shopify drafts you approve in Slack. |
| [AI product titles](ai-product-titles/) | Rewrites the Shopify product titles you tag to a formula per product type, checks every model number in code, and learns from the titles you approve. |
| [AI product descriptions](ai-product-descriptions/) | Writes a short intro for each tagged product from its specs and the maker's page, checks every number in code, and replaces only the intro in Shopify once you approve it in Slack. |
| [Shopify collections SEO](shopify-collections-seo/) | Finds the collections your catalogue can support and shoppers search for, creates them as smart collections, gives every brand a page and proposes retiring collections that run out of stock. |
| [Category page SEO](category-page-seo/) | Writes each collection's intro and meta tags from its live products, links it to its parent, children and siblings, sorts buyable products first and audits internal links weekly. |
| [Product data enrichment](product-data-enrichment/) | Scrapes each product's manufacturer spec page, extracts its attributes with AI, checks every value against a quote from the source, and writes the approved specs to Shopify metafields and Shopify's standard product attributes after a Slack review. |
| [Shopify product images](product-images/) | Finds each product's page on the manufacturer's site, scrapes its images, checks them with a vision model, writes alt text per shot, and pads approved images to white 2048 px squares before uploading them. A weekly lane fixes alt text across the catalogue. |
| [Shopify collection sorting](shopify-collection-sorting/) | Scores every product against its collection's keyword (word matching, or blended with embeddings), puts the best matches first and sold-out, draft and image-less products last, and keeps the order current every 2 hours. |
| [Ecommerce internal linking](ecommerce-internal-linking/) | Fills breadcrumb, sub-collection, brand, spec and related-collection link fields from your menu and collection rules every day, with Liquid snippets to show them on a stock theme, and runs a weekly orphan and broken-link audit. No AI model needed. |
| [Automated inventory management](automated-inventory-management/) | Syncs supplier CSV stock and unit cost into a Shopify location of its own every 3 hours, holds broken feeds, and proposes discontinued products for archive and redirect in Slack. No AI model needed. |
| [Slack approvals](slack-approval-workflow-n8n/) | Human-in-the-loop review for any n8n workflow: Block Kit cards in Slack to approve, edit in a modal or reject with a reason, actionable alerts with Snooze, signed review pages for long lists, and cards that close themselves when the change happens somewhere else first. No AI model needed. |
| [n8n workflow monitoring](n8n-workflow-monitoring/) | Watches every workflow on your n8n instance: one Slack alert per outage instead of one per failure, schedules that stopped firing, runs that finished with nothing in them, a line when each recovers, and a morning all-clear. Reads the n8n API with a read-only key. No AI model needed. |

## Getting started

1. Read [SETUP.md](SETUP.md) for the credentials the templates share: a Shopify app, a Slack app and an AI model.
2. Open a template's folder and follow its README: import `workflow.json`, add the credentials, fill in the settings node, run the Setup lane once, then test on a few products before turning on the schedules.
   - To create the credentials without pasting secrets anywhere, run `python3 scripts/create-credentials.py <template-folder>` in your terminal ([how it works](SETUP.md#create-the-credentials-from-your-terminal)).
   - To set a template up with Claude Code, Codex or Cursor, copy the prompt under **Set it up with an AI agent** in its README.
3. Test anything that writes to Shopify on a development store first. Templates that change your store have a `dry_run` setting or a Slack approval step, and a red note on the nodes that write.

## What's in each folder

| File | What it is |
| --- | --- |
| `workflow.json` | The template, storing its data in n8n Data Tables |
| `workflow-supabase.json` | The same template storing its data in Supabase (Postgres) instead ([setup](SETUP.md#supabase-optional)) |
| `supabase/schema.sql` | The tables for the Supabase version, if you'd rather create them in Supabase's SQL editor |
| `credentials.json` | The credentials the template needs and the nodes they go on, read by `scripts/create-credentials.py` |
| `README.md` | Install, settings, testing, troubleshooting and the AI-agent setup prompt |
| `screenshot.png` | The canvas |

## Requirements

- n8n with Data Tables, or a Supabase (or any Postgres) database for the Supabase versions. Every template was built and tested on n8n 2.45, in both versions. Self-hosting the free Community Edition is recommended: no execution limits, and the schedules cost nothing when there's nothing to do. n8n Cloud works too.
- Shopify, through a Dev Dashboard app using the client credentials grant (Admin GraphQL API 2026-10).
- Slack, for the review cards and reports.
- An AI model for the templates that write copy. They default to Ollama Cloud, and any n8n chat model sub-node can replace it.

## Licence

[MIT](LICENSE). Use, change and share the templates freely; keep the copyright notice.
