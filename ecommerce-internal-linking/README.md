# Ecommerce internal linking

An n8n template that keeps a Shopify store's structural internal links true every day, with no AI model. It writes six link fields from your main menu, your collection rules and your vendors, your theme shows them as breadcrumbs, sub-collection links, brand links, linked spec values and "Shop more like this" links, and a weekly audit tells you what nothing links to.

- **Setup** creates the `link_findings` and `link_changes` data tables and six metafield definitions, pinned so they show in the admin: `custom.parent_collection` and `custom.sub_collections` on collections, `custom.brand`, `custom.primary_collection`, `custom.spec_links` and `custom.related_collections` on products.
- **Link** (daily) works out every collection's parent and children (menu nesting first, then "type is X and ..." collections under the collection whose only rule is "type is X"), and every product's brand page, primary collection, spec links (which collection each spec value links to) and related collections. It compares that with what Shopify holds, logs every difference with its old value, posts a summary to Slack, and writes the differences only when `dry_run` is false.
- **Audit** (weekly) counts the links into every published collection from your menus, the six fields, sibling links, collection descriptions, pages and blog posts, and reports orphans, weak pages, children their parent doesn't list, menu links to empty collections, broken links, links that go through a redirect, products in no published collection or with no primary collection, and vendors with no brand page. Optionally it checks your live theme for the settings and blocks that hide links.

The full walkthrough is in the guide: [How to Improve and Automate Internal Linking on Shopify](https://www.reganmcgregor.com.au/ecommerce-internal-linking/).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.
- A Shopify app with the `read_products`, `write_products`, `read_online_store_navigation` and `read_content` scopes, and its client ID and secret. Add `read_themes` only if you turn on `check_theme`.
- A Slack app with a bot token (`chat:write`).
- The theme blocks in [`liquid/`](liquid), so the fields show on your store. Without them the fields are filled but nothing renders.

No AI model and no paid API. [SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token for Setup, Get Shopify token for Link, Get Shopify token for Audit | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post link summary, Post audit report | Slack API | Your bot token |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.

## Settings

**Setup settings**: `store_domain` (your permanent `*.myshopify.com` domain) and `namespace` (where the six fields live, `custom` by default).

**Link settings**:

| Setting | What it does |
|---|---|
| `store_domain`, `namespace` | As in Setup settings |
| `tree_menu` | The menu whose nesting is your category tree (`main-menu`) |
| `skip_handles` | Collections never linked (`frontpage` and `all`) |
| `min_products` | A child needs at least this many products to be listed under its parent |
| `max_children` | The most sub-collection links on one page (24) |
| `max_related` | The most "Shop more like this" links on one product (6) |
| `write_collection_links`, `write_brand`, `write_primary`, `write_spec_links`, `write_related` | Turn each kind of link field on or off |
| `dry_run` | True: plan, log and report only. False: write to Shopify |
| `slack_channel` | Where the summary goes |

**Audit settings**:

| Setting | What it does |
|---|---|
| `store_domain`, `namespace`, `tree_menu` | As in Link settings |
| `skip_menus` | Menus that aren't shown anywhere (a backup copy), so their links don't count |
| `ignore` | Collections the audit never reports (`frontpage` and `all`) |
| `theme_linked` | Handles your theme links in code (a homepage row, the footer), which store data can't show |
| `max_pills` | Must match `max_children` in Link settings |
| `weak_below` | A collection outside the menu with fewer links than this is reported as weak |
| `check_product_fields` | Report products with no primary collection |
| `check_theme` | Read the live theme's collection and product templates (needs `read_themes`) |
| `slack_channel` | Where the report goes |

## How the links are worked out

- **Parent and children.** The tree menu's nesting comes first, in menu order. A smart collection outside the menu whose rules are "type is X and something else" (all conditions) goes under the collection whose only rule is "type is X". Anything else outside the menu has no parent.
- **Brand.** The collection whose only rule is "vendor is X", matched to the product's vendor without case, as Shopify matches it. The audit lists vendors that have none.
- **Primary collection.** The deepest collection in the tree that the product is in, skipping collections with a vendor rule (the brand link already covers those). Ties go to menu order, so the breadcrumb doesn't change between runs.
- **Spec links.** A smart collection whose rules are one product metafield or standard product attribute condition, plus at most "type is X", is the page for that spec value ("Resolution is 4MP" is 4MP Security Cameras). For each spec, the product links to the spec collection it is in (one with a type rule first, then the smallest, at least two products), even when that collection is also its breadcrumb. Saved as JSON keyed by the metafield: `{"custom.resolution": "4mp-security-cameras"}`.
- **Related collections.** Every other published collection the product is in, except its primary collection's own trail and brand pages, with at least two products, smallest first, up to `max_related`.

## Add the theme blocks

The [`liquid/`](liquid) folder has seven snippets, tested on Horizon 4.4. Each goes into a **Custom Liquid** block in the theme editor (no theme code files are edited):

| File | Template and place |
|---|---|
| `collection-breadcrumbs.liquid` | Collection template, heading section, above the title |
| `sub-collection-links.liquid` | Collection template, heading section, under the description |
| `shop-by-brand.liquid` | Collection template, under the sub-collection links |
| `product-breadcrumbs.liquid` | Product template, product information, at the top |
| `product-brand-link.liquid` | Product template, product information, under the title |
| `spec-table.liquid` | Product template, product information, under the description (list your specs in its first line) |
| `shop-more-like-this.liquid` | Product template, product information, under the specs table |

Each prints nothing when its field is empty. If you changed `namespace`, replace `custom` in the snippets to match. On Horizon, also untick **Auto load products on scroll** on the collection template's products section, or nothing links to page 2 of a collection.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get two data tables and six metafield definitions (Settings > Metafields and metaobjects > Collections and Products). Running it again keeps everything and reports the fields as already there.

## Test it

1. Run **Run Audit now** first. The report shows where your store stands before anything is written.
2. Run **Run Link now** with `dry_run` true. Read the Slack summary and the `link_changes` table: each row has the old and new value of one field.
3. Set `dry_run` to false and run it again. The fields fill in and the blocks start showing links. A second run finds nothing to change.
4. Run the audit again. The orphans the Link lane fixed are gone.

Do this on a development store first: the Link lane writes to Shopify once `dry_run` is false.

## Schedule

Publish the workflow. Link runs every day at 05:00 and Audit every Monday at 06:00, in the workflow's time zone (Workflow settings > Timezone). Set an Error Workflow too, so a crashed run reaches you.

Executions: about 30 Link runs and 4 Audit runs a month. Each run reads 100 collections and 100 products per request.

## Troubleshooting

### Link stops with "No menu with the handle"

`tree_menu` doesn't match a menu handle. Open Content > Menus, open your header menu, and copy the handle from its URL or the handle field.

### A collection has no parent

It isn't in the tree menu and its rules aren't "type is X and ...", or there's no collection whose only rule is "type is X". Add it to the menu, or set its parent by hand and turn `write_collection_links` off.

### A product has no brand

No collection has "vendor is X" as its only rule for that vendor. The audit lists these under Vendors with no brand page. Make one (Collections > Create collection > Smart, Vendor is equal to the vendor name).

### The audit lists products with no primary collection

They're only in collections outside the tree (a tag collection, a manual collection). Add their category to the menu, or set `check_product_fields` to false if you don't use the product breadcrumb.

### Shopify refused some links

**Any errors?** stops the run with Shopify's message, which names the field and the reason. The rows in `link_changes` show what that run planned.

### Pages or posts past the first 250 aren't checked

**Read pages, posts and redirects** reads the first 250 of each. Add pagination to it if you have more.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres (below), or clear old `link_changes` rows.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py ecommerce-internal-linking --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`link_findings`, `link_changes`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Ecommerce internal linking" n8n template in ./ecommerce-internal-linking.

1. Read ecommerce-internal-linking/README.md, SETUP.md and ecommerce-internal-linking/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py ecommerce-internal-linking
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. Ask me for my header menu's handle for tree_menu.
5. Run the Setup lane and check its output with me.
6. Walk me through adding the seven Custom Liquid blocks in ecommerce-internal-linking/liquid in my theme editor, on a copy of my theme, in preview only.
7. Run the Audit lane, then the Link lane with dry_run true, show me the link_changes rows and check them with me before anything writes to my store.
8. Stop and ask me whenever something doesn't match the README.
```
