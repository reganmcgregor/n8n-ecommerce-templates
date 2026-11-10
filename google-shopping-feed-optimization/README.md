# Google Shopping feed optimisation

An n8n template that pre-checks every Shopify product against Google's rules before Google sees it, fills the Google & YouTube app's own fields, holds any product that would fail off the Google & YouTube channel with a Slack card to fix it, sends product highlights, product details and material to Merchant Center through a supplemental data source, and reads back Merchant Center's verdict every morning. There's no AI model: every check is a rule.

- **Setup** creates the `feed_fields` (the field map) and `feed_status` data tables, seeds eleven field-map rows, registers your Google Cloud project with Merchant Center, creates a supplemental data source and links it to the Google & YouTube app's primary data source.
- **Check** (daily, by hand, or a recheck from Slack) reads your products, compares each Google attribute with its Shopify source, fills the app's `mm-google-shopping` metafields (MPN from the SKU, condition `new`), pre-checks every required field (including the GS1 check digit on the barcode and a Shopify category), keeps products tagged `no-google` off the channel, publishes passing products to the Google & YouTube channel and unpublishes failing ones, posts a card per held product, and sends changed supplemental values with `productInputs.insert`. `dry_run` is on until you turn it off.
- **Review** checks Slack's signature on every click. **Edit** opens a modal with only the flagged Shopify fields (barcode, SKU, brand, title), prefilled with the suggested fix; saving writes them to the Shopify product, never to a Google field, and rechecks that product. **Recheck** reruns Check for one product.
- **Read back** (daily, an hour after Check) lists Merchant Center's processed products, works out approved, limited, disapproved or pending per product in your country for Shopping ads and free listings, posts a card for each disapproval with Google's "How to fix" link, closes cards Google has cleared, and posts a summary.

The full walkthrough is in the guide: [How to Automate Google Shopping Feed Optimisation With n8n](GUIDE_URL).

## What you need

- n8n with Data Tables (self-hosted or Cloud). Tested on n8n 2.46.
- Shopify with the free [Google & YouTube app](https://apps.shopify.com/google) connected to Merchant Center.
- A Shopify app with the `read_products`, `write_products`, `read_publications` and `write_publications` scopes, and its client ID and secret.
- A Google Cloud project with the Merchant API enabled, an OAuth client (Web application) and an n8n **Google OAuth2 API** credential with the scope `https://www.googleapis.com/auth/content`, signed in as a Merchant Center admin. Set the OAuth consent screen to **In production** (or Internal on Google Workspace): a project left in Testing gets refresh tokens that expire after 7 days.
- A Slack app with a bot token (`chat:write`), Interactivity turned on, and its signing secret.
- No Google Ads account and no AI model.

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Review | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Register this Google Cloud project, List data sources, Create the supplemental source, Link it to the primary source, Send to Merchant Center, Read Merchant Center | Google OAuth2 API | Client ID and secret, scope `https://www.googleapis.com/auth/content`, then **Sign in with Google** |
| Post or update the card, Post it again, Post the summary, Open loading modal, Show the fields, Tell the reviewer, Post or update the read-back card, Post the read-back card again, Post the read-back summary | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Setup settings**:

| Setting | What it does |
|---|---|
| `merchant_id` | Your Merchant Center account ID (top right in Merchant Center) |
| `developer_email` | Optional. A Merchant Center user's email: Google gives that user the API developer role and sends them API notices. Leave it blank to register the project without changing anyone's access |
| `primary_data_source` | Leave blank when the account has one primary source. Otherwise the ID of the Google & YouTube app's source (Setup lists them in its error if it can't choose) |
| `supplemental_name` | The supplemental source's name (`n8n supplemental`) |

**Check settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `admin_handle` | The part of your admin URL after `admin.shopify.com/store/` |
| `sales_channel` | The Google & YouTube app's name as Shopify lists it under Sales channels (or its handle, `google`) |
| `merchant_id` | As above |
| `supplemental_data_source` | The supplemental source's full name, `accounts/<id>/dataSources/<id>`, from Setup's **Build the rule** output |
| `feed_label` | The feed label on the app's products (Merchant Center > Products > a product) |
| `content_language` | The products' language (`en`) |
| `offer_id_template` | How the app builds item IDs: `shopify_ZZ_{product_id}_{variant_id}`. Copy the two letters from an item ID in your account |
| `product_query` | Which products to check, in Shopify's search syntax (`status:active`) |
| `exclude_tag` | Products with this tag stay off the Google & YouTube channel with no card (`no-google`). Leave it empty to turn exclusions off |
| `page_size` | Products per Shopify request (10); lower it if you add many detail fields |
| `product_ids` | Leave as it is: a recheck from Slack fills it |
| `highlights_metafield` | The metafield holding each product's highlights: a list of single-line text, multi-line text (one per line) or rich text with bullets |
| `detail_fields` | One entry per spec shoppers see under product details: `metafield`, `name`, `section` and an optional `unit` |
| `currency` | Shown on the cards |
| `review_channel` | The Slack channel ID (`C...`) for review cards; `chat.update` needs the ID, not the name |
| `log_channel` | Where the daily summaries go |
| `timezone` | For the times on the cards |
| `supplemental_enabled` | false to skip the supplemental source |
| `dry_run` | true until you've read a Pre-check output. Nothing is written or saved while it's on |

**Read-back settings**: `merchant_id`, `country` (the two-letter country you sell to), `contexts` (`SHOPPING_ADS` and `FREE_LISTINGS`), `offer_id_pattern` (a regular expression whose two groups are the Shopify product and variant IDs), `review_channel`, `log_channel`, `admin_handle` and `timezone`.

**Review settings**: `store_domain`.

The field map lives in the `feed_fields` table. Each row has a `field`, a `kind` (`shopify_native` is checked only, `app_metafield` is written to the app's metafield in `target`, `supplemental` goes to the supplemental source), a `source`, `required`, a `rule` (`max_len:150`, `min_image_px:500`, `not:Unbranded`, `gtin;alt:mpn+brand`, `min_items:2;max_items:10;max_len:150`) and `active`. Set `active` to false to drop a row, or point `mpn` at another source. The `google_product_category` row holds any product without a Shopify category ("Uncategorized" counts as none), because the Google & YouTube app turns that category into Google's product category; set `required` to false if you'd rather let Google guess.

## Run Setup

Fill in **Setup settings**, open **Run once to set up** and click **Execute workflow**. It takes just over five minutes, because Google asks you to wait after registering a Cloud project (a project that's already registered answers `409 ALREADY_EXISTS`, which the node ignores). You get the two tables, eleven rows in `feed_fields`, and a supplemental source called `n8n supplemental` linked to the app's primary source (Merchant Center > Settings > Data sources). Running it again is safe: it reuses the tables, updates the rows, finds the existing supplemental source and doesn't link it twice. Copy `supplemental` from **Build the rule**'s output into **Check settings**.

## Test

1. Point `product_query` at a few products (`status:active AND tag:feed-test`), set `review_channel` and `log_channel` to a test channel, and keep `dry_run` on.
2. Open **Run the check** and click **Execute workflow**. Open **Pre-check**: each product has a `state` (`live`, `held`, `excluded` or `off`) and, when held, `missing` with the problem and any suggested fix.
3. Set `dry_run` to false and run it again. Held products come off the Google & YouTube channel and get a card; passing ones go on; the app's MPN and condition fields are filled; changed highlights and details go to Merchant Center.
4. Publish the workflow so **Slack button click** answers, then tap **Edit** on a card, save, and watch the card turn into "Fixed: on Google".
5. Next morning (or by hand with **Read back now**), the read-back posts its summary and a card for anything Google disapproved.
6. Do this on a development store first: Check and Review write to Shopify.

## Schedule

Publish the workflow. Check runs at 6am and Read back at 7am, in the workflow's time zone (Workflow settings > Timezone), and the Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: about 60 schedule runs a month plus one per Slack click (a recheck runs as a sub-workflow).

## Troubleshooting

### Setup stops at Plan the link

`Set primary_data_source in Setup settings` means the account has no primary source or more than one. The error lists the ones it found; put the Google & YouTube app's ID in `primary_data_source`. None at all means the app hasn't finished connecting to Merchant Center.

### Merchant API calls answer 401

`GCP_NOT_REGISTERED` means Google hasn't finished registering the Cloud project: wait five minutes and run Setup again. `The caller does not have access to the accounts` means the Google account you signed in with isn't a user on that Merchant Center account.

### Check stops at Build the query

`No sales channel called "Google & YouTube"` means the app isn't installed or `sales_channel` doesn't match. The error lists the channels it found.

### Supplemental values never appear in Merchant Center

Check the supplemental source is in the primary source's rule (Merchant Center > Settings > Data sources > the app's source). Then check `feed_label`, `content_language` and `offer_id_template` match a real item exactly. **Send to Merchant Center** answers `404 The resource with name Product was not found` for an offer Merchant Center doesn't have (a wrong ID, or a product the app hasn't synced yet); **Accepted?** drops those and the next run tries again.

### Every product shows as pending

New products, and new images, sit in "Pending initial review" for up to a few days. The read-back counts them as pending, not disapproved.

### A card disappeared

If someone deletes a card, the next update answers `message_not_found` and **Post it again** posts a fresh one.

### Nothing happens when I click a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signed by Slack?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### Shopify didn't save the fix

The card's thread says why. `GTIN barcode checksum validation failed` means the barcode typed in the modal isn't a valid GTIN: the template saves barcodes with type `GTIN`, so Shopify checks the digits too.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres (next section).

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py google-shopping-feed-optimization --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates `feed_fields` and `feed_status` if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. It's also faster at scale: in our test, Read back saved 1,466 products' verdicts in 6 seconds on Supabase against 2 minutes on Data Tables. `feed_fields` has a unique key on `channel` and `field`, and `feed_status` on `product_id`. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Google Shopping feed optimisation" n8n template in ./google-shopping-feed-optimization.

1. Read google-shopping-feed-optimization/README.md, SETUP.md and google-shopping-feed-optimization/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Check with me that the Google & YouTube app is installed on my Shopify store and connected to Merchant Center, and that I have a Google Cloud project with the Merchant API enabled and an OAuth client. Walk me through any that are missing, one step at a time.
3. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
4. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py google-shopping-feed-optimization
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists, and remind me to open the Google credential in n8n and click Sign in with Google.
5. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. For detail_fields, ask which product metafields hold the specs my shoppers compare.
6. Run the Setup lane and check its output with me, including the supplemental source in Merchant Center.
7. Run the Check lane on about 5 products with dry_run on, show me the Pre-check output and check it with me before anything writes to my store.
8. Stop and ask me whenever something doesn't match the README.
```
