# n8n ecommerce templates

Free n8n templates for running an online store: monitoring competitor prices, adding products, writing product titles and building collections. Each one is a single n8n canvas with a lane per job, keeps its state in n8n Data Tables, and asks you in Slack before it changes anything in your store.

| Template | What it does |
| --- | --- |
| [Competitor price monitoring](competitor-price-monitoring/) | Finds who else sells your exact products by model number, reads their prices from structured data, and posts a weekly Slack report of every product where a competitor is cheaper. No AI model needed. |
| [Add products to Shopify](add-products-to-shopify/) | Brings a wholesaler's CSV price list (and, optionally, AliExpress listings) into one table, finds what you don't sell yet, writes the copy with AI and creates Shopify drafts you approve in Slack. |
| [AI product titles](ai-product-titles/) | Rewrites the Shopify product titles you tag to a formula per product type, checks every model number in code, and learns from the titles you approve. |
| [Shopify collections SEO](shopify-collections-seo/) | Finds the collections your catalogue can support and shoppers search for, creates them as smart collections, gives every brand a page and proposes retiring collections that run out of stock. |
| [Category page SEO](category-page-seo/) | Writes each collection's intro and meta tags from its live products, links it to its parent, children and siblings, sorts buyable products first and audits internal links weekly. |

## Getting started

1. Read [SETUP.md](SETUP.md) for the credentials the templates share: a Shopify app, a Slack app and an AI model.
2. Open a template's folder and follow its README: import `workflow.json`, add the credentials, fill in the settings node, run the Setup lane once, then test on a few products before turning on the schedules.
3. Test anything that writes to Shopify on a development store first. Templates that change your store have a `dry_run` setting or a Slack approval step, and a red note on the nodes that write.

## Requirements

- n8n with Data Tables. Every template was built and tested on n8n 2.45. Self-hosting the free Community Edition is recommended: no execution limits, and the schedules cost nothing when there's nothing to do. n8n Cloud works too.
- Shopify, through a Dev Dashboard app using the client credentials grant (Admin GraphQL API 2026-10).
- Slack, for the review cards and reports.
- An AI model for the templates that write copy. They default to Ollama Cloud, and any n8n chat model sub-node can replace it.

## Licence

[MIT](LICENSE). Use, change and share the templates freely; keep the copyright notice.
