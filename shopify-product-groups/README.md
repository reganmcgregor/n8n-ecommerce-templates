# Shopify product groups

An n8n template that shows separate Shopify products as one family on the storefront, like Shopify Plus combined listings, on any plan. A cable sold as one product per length and colour gets a Length row and a Colour row on every member's page, each option a link to the right product, and colour dots on its product cards. No AI model and no paid API.

- **Setup** creates the `group_overrides` and `group_changes` data tables, a **Product group** metaobject (`name`, `group_options`, `products`, `members_json`, `managed`) and two product metafields: `custom.product_group` and `custom.option_values`.
- **Group** (hourly) reads your active products and finds each series: same vendor, same product type and the same title once the option values (a length, a colour, a capacity) and the SKU are taken out. It writes one Product group per series, links each product to it, and keeps every member's option values and stock in the group's `members_json`. It compares with what Shopify holds, so a run with nothing new writes nothing, and it posts to Slack when something changed.

The full walkthrough is in the guide: [How to Create Shopify Combined Listings Without Plus](https://www.reganmcgregor.com.au/shopify-combined-listings/).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.
- A Shopify app with the `read_products`, `write_products`, `read_metaobject_definitions`, `write_metaobject_definitions`, `read_metaobjects` and `write_metaobjects` scopes, and its client ID and secret.
- A Slack app with a bot token (`chat:write`), for the summary.
- The two theme blocks in [`liquid/`](liquid), so the groups show on your store. Without them the groups are written but nothing renders.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token for Setup, Get Shopify token for Group | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post summary | Slack API | Your bot token |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.

## Settings

**Setup settings**: `store_domain` (your permanent `*.myshopify.com` domain), `namespace` (where the two product fields live, `custom` by default) and `group_type` (the metaobject type, `product_group`).

**Group settings**:

| Setting | What it does |
|---|---|
| `store_domain`, `namespace`, `group_type` | As in Setup settings |
| `slack_channel` | Where the summary goes |
| `dry_run` | True: work out the changes and post them to Slack, write nothing. False: write to Shopify |
| `match_on` | What a series must share besides its title: `vendor` and `product_type` by default |
| `strip_sku` | Take each product's SKUs out of its title first, so model codes like N6PATC2MBL don't split a series |
| `min_members` | The fewest products a series needs (2) |
| `report_hour` | The run in this hour also posts near misses and duplicates, even when nothing changed |
| `options` | The options to read, in row order. Each has a `name` and a `pattern` (a regular expression) or a list of `words`; `colour_attribute: true` reads the colour and swatch from Shopify's standard Color attribute first; `aliases` maps one value to another (`Gray` to `Grey`) |

The default options are Length (`0.5m`, `2 m`, `6ft`), Colour (Shopify's Color attribute, then 20 colour words) and Capacity (`16GB`, `2TB`). Rename `Colour` to `Color` if your store writes it that way, and change `colour_option` at the top of both snippets to match.

## How a series is found

1. Each SKU is taken out of the product's title.
2. Each option is read in turn and its value taken out of the title too: a colour from the Color attribute or a colour word, a length or capacity from its pattern. A pattern that matches twice in one title is ignored, so "2 x 16GB" doesn't become a capacity.
3. What's left of the title, with the vendor and product type, is the series key. "StarTech.com 2m Blue Cat6 Snagless Ethernet Cable N6PATC2MBL" becomes "StarTech.com Cat6 Snagless Ethernet Cable".
4. An option counts when the series has two or more values for it. A product missing one of them is a **near miss** and stays out; two products with the same values are **duplicates** and only the first is linked. Both are listed in Slack.
5. Members are sorted by each option in row order, numbers numerically.

`group_overrides` wins over the rules. A row with a product's `handle` and a `group_name` puts it in the series with that name (or starts one), with `option_values` such as `{"Colour": "Black"}` for values its title doesn't have. `group_name` of `exclude` keeps a product out of every group.

Groups you make yourself in the admin, with **Kept by n8n** off, are never changed or deleted, and their products are left alone.

## Add the theme blocks

The [`liquid/`](liquid) folder has two snippets, tested on Horizon 4.4. Each goes into a **Custom Liquid** block in the theme editor (no theme code files are edited):

| File | Template and place |
|---|---|
| `series-picker.liquid` | Product template, Product information, above the buy buttons |
| `card-colours.liquid` | Collection and search templates, at the end of the product card |

The picker reads the group's `members_json` (every member, no 50-product limit), or its `products` list when `members_json` is empty, so a group you make by hand works too. Every option is a plain link, so it works without JavaScript and search engines can follow it. Each snippet prints nothing for a product with no group. If you changed `namespace`, replace `custom` in the snippets to match.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get two data tables, the Product group metaobject (Settings > Metafields and metaobjects > Product group) and the two product fields. Running it again reports them as already there.

## Test it

1. Run **Run Group now** with `dry_run` true. Read the Slack summary: the groups it would write, with their options and sizes, plus near misses and duplicates.
2. Fix what's wrong with a row in `group_overrides`, or by changing the options, and run it again.
3. Set `dry_run` to false and run it. The groups and product fields fill in and the picker appears. A second run finds nothing to change.

Do this on a development store first: the Group lane writes to Shopify once `dry_run` is false.

## Schedule

Publish the workflow. Group runs every hour, which keeps the sold-out flags in `members_json` close to your stock. A run with nothing to change reads your products and stops: one request per 100 products. Set an Error Workflow too, so a crashed run reaches you.

## Troubleshooting

### A product isn't in its series

Slack lists it as a near miss (one of the series' options isn't in its title) or a duplicate (another product already has the same values). Add a `group_overrides` row with its option values, or fix the title.

### Two different products ended up in one series

Their titles are the same once the option words go, for example two camera generations that differ only by a colour. Keep one out with a `group_overrides` row (`group_name` `exclude`), or give it its own `group_name`.

### The picker doesn't show

Check the product's **Product group** field in the admin. If it's set, check the block is on the product template you're viewing, and that `namespace` in the snippet matches. A metaobject definition made by hand with **Active-draft status** on needs every entry set to Active, or Liquid reads it as empty.

### Shopify refused some links

The Slack summary lists them under Failed with Shopify's message, and `group_changes` has a row for each.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres (below), or clear old `group_changes` rows.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py shopify-product-groups --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`group_overrides`, `group_changes`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. `group_overrides.handle` is unique. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Shopify product groups" n8n template in ./shopify-product-groups.

1. Read shopify-product-groups/README.md, SETUP.md and shopify-product-groups/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py shopify-product-groups
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. Ask me how my product titles name lengths, colours, sizes or capacities, and help me write the options list from a few of my real titles.
5. Run the Setup lane and check its output with me.
6. Walk me through adding the two Custom Liquid blocks in shopify-product-groups/liquid in my theme editor, on a copy of my theme, in preview only.
7. Run the Group lane with dry_run true, read the Slack summary with me, and add group_overrides rows for anything it got wrong before anything writes to my store.
8. Stop and ask me whenever something doesn't match the README.
```
