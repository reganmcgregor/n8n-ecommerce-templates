# Shopify product videos

An n8n template that finds YouTube videos of each tagged product by its model number, searching the manufacturer's own channel first and then all of YouTube. It checks in code that the title names that exact model and that YouTube lets the video be embedded, then asks you in Slack. Approved videos go into a **Videos** list on the product, and one Custom Liquid section (in [`videos-section.liquid`](videos-section.liquid)) shows them below the product details, so the gallery stays photos only. The YouTube player loads only when a shopper presses play. Once a month it removes any video YouTube no longer serves. No AI model.

- **Setup** creates the `brand_channels`, `video_candidates` and `video_runs` data tables, the **Product video** entry type (a metaobject with title, YouTube ID, URL, channel, coverage and type), and the **Model number (MPN)** (`custom.mpn`), **Manufacturer page** (`custom.manufacturer_url`) and **Videos** (`custom.videos`, a list of Product video entries) product fields. It then looks up the YouTube channel for each brand handle in its settings.
- **Find** takes up to `batch_size` products tagged `find-videos` an hour (or the IDs in `product_ids`). It searches each of the brand's channels for the model, then all of YouTube for the brand and the quoted model, and can also search Google through DataForSEO and read the manufacturer's product page for embedded videos. It reads every video's details in one call and drops anything that:
  - doesn't name the exact model in its title (C440 never matches C440-W);
  - can't be embedded or is private;
  - is live, a Short, too short, too long or in another language.

  It labels each video's type (setup, review, unboxing, comparison, demo), keeps the best few with a mix of types, and posts one Slack card per video. A product whose search worked loses its tag; one whose search failed keeps it for the next run.
- **Review** answers Slack at once, then checks the signature, age and approver list. It ignores clicks on cards that are already decided. Approve needs a coverage choice (this product, a comparison, a brief mention) and starts Publish for that product. Reject is permanent: the video is never offered again.
- **Publish** claims each approved video so two runs can't publish it twice. It checks the video still has the title and channel you approved, saves it as a Product video entry with `metaobjectUpsert`, then rebuilds the product's Videos list from the table with `metafieldsSet` (manufacturer channel videos first, then in the order you approved them) and replies in the card's thread. A video is marked live only once Shopify's list holds it. `dry_run` is on until you turn it off.
- **Check** runs on the first of the month. It re-reads every live video; any that was deleted, made private or can no longer be embedded comes off the product's Videos list (the field is cleared when none are left) and its entry is deleted, then it posts one summary. Optionally it tags products again for Find when their last search found nothing.

The full walkthrough is in the guide: [How to Add YouTube Videos to Shopify Product Pages Automatically](https://www.reganmcgregor.com.au/add-video-to-shopify-product-page/).

## What you need

- n8n with Data Tables (self-hosted or Cloud) on a public HTTPS URL, because Slack has to reach the webhook. Tested on n8n 2.46.
- A Shopify app with the `read_products`, `write_products`, `read_metaobjects`, `write_metaobjects`, `read_metaobject_definitions` and `write_metaobject_definitions` scopes, and its client ID and secret.
- A theme with a Custom Liquid section (Horizon and the other free Shopify themes have one).
- A YouTube Data API v3 key from a Google Cloud project. It's free: the default quota allows 100 searches a day, plus 10,000 units a day for everything else (a details call for up to 50 videos costs 1).
- A Slack app with a bot token (`chat:write`; invite the bot to your review channel, or add `chat:write.public`), Interactivity turned on, and its signing secret.
- Optional: DataForSEO, if you want Google's results as well as YouTube's own search (about US$0.002 a search).
- Products with a model number. Setup creates the `custom.mpn` field; fill it in by hand, in the bulk editor, or by CSV import with a column headed `Model number (MPN) (product.metafields.custom.mpn)`. Products without one fall back to the first word of the title that has a digit in it, and their videos always go to review as "Not sure yet".

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token for Setup, Get Shopify token, Get Shopify token for Publish, Get Shopify token for Check | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Look up the channel, Search YouTube, Get video details, Check it again, Check the live videos | Query Auth | Name `key`, Value = your YouTube Data API key |
| Post the card, Show approved, Show rejected, Reply: not added, Reply: live, Reply: failed, Post the summary | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Search Google (optional) | Basic Auth | Your DataForSEO API login and password |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Setup settings**: `store_domain`, the namespaces and keys of the three product fields, `video_type` (the entry type, `product_video`), and `brand_channels`. Give `brand_channels` one entry per YouTube channel:

- `vendor`: exactly as your products' Vendor field (case doesn't matter).
- `handle`: the channel's `@handle` from its URL.
- `domains`: the brand's websites, comma separated, for the optional page search.
- `url_pattern` (optional): the brand's product page URL with `{model}` where the model goes.

A brand can have several channels, such as a support channel and regional ones (TP-Link has `@tpsupport`, `@TPLinkANZ` and more). Videos on channels you don't list still turn up in the open search; they're just not labelled as the manufacturer's.

**Find settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `find_tag` | The tag that queues a product (`find-videos`) |
| `product_ids` | Product IDs (numbers or `gid://` IDs) to search instead of the tagged ones, for a test batch. Leave it `[]` to use the tag |
| `batch_size` | Products per run. Each product uses one search per listed channel plus one open search, and YouTube allows 100 searches a day, so 2 an hour with one channel per brand is 96 searches a day |
| `channel_results`, `open_results` | Results to read from the channel search and the open search |
| `max_videos_per_product` | The most cards per product (3) |
| `min_seconds`, `max_seconds` | Length limits (30 seconds to 30 minutes) |
| `language`, `region_code` | The audio language to keep (`en`), and the country YouTube ranks results for |
| `model_prefixes` | Family names that can be left off the model in a video title, such as `["Tapo", "VIGI"]` so `VIGI C440` also matches `C440`. The vendor name is always optional |
| `ignore_suffixes` | Colour codes that can be left off the model, such as `BK` and `WH`. Leave out single letters like `W`, which often mean a different model (wireless) |
| `use_manufacturer_page` | true to read the manufacturer's product page for embedded YouTube videos |
| `use_dataforseo` | true to search Google as well (needs the DataForSEO credential) |
| `search_location`, `search_language` | DataForSEO's location and language |
| `mpn_namespace`, `mpn_key`, `page_namespace`, `page_key`, `videos_namespace`, `videos_key` | The three product fields, as in Setup settings. Find reads the Videos field so it never offers a video the product already has |
| `user_agent` | Sent to manufacturer sites. Name your store and give a URL |
| `slack_channel` | Where the cards go |

**Review settings**: `slack_app_id` (blank accepts any) and `approver_ids` (Slack user IDs; empty means anyone in the channel).

**Publish settings**: `store_domain`, `dry_run` (true until you've checked **What would be added**), `videos_namespace` and `videos_key` (the Videos field, `custom.videos`), `video_type` (the entry type, `product_video`) and `batch_size`. Keep the first three the same as in Setup settings.

**Check settings**: `store_domain`, `log_channel`, `research_after_days` (0 is off), `find_tag`, and `videos_namespace` and `videos_key` as in Setup settings.

## Show the videos on your product page

Setup stores the videos; the theme shows them. In Shopify admin, open **Online Store > Themes > Customize**, switch the page selector at the top to **Products > Default product**, click **Add section** below the product information, choose **Custom Liquid**, and paste the contents of [`videos-section.liquid`](videos-section.liquid) into its Liquid box. Save.

The section reads `product.metafields.custom.videos` and prints nothing on products without videos, so it's safe on every product. Each video shows its YouTube thumbnail with a play button, its title linked to YouTube, and "By" the channel name (plus "Comparison" or "Brief mention" when that's what the reviewer chose). Nothing loads from YouTube until a shopper presses play; then it swaps in a `youtube-nocookie.com` player. If you changed `videos_namespace` or `videos_key`, change the first line of the section to match.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get three data tables, the **Product video** entry type under **Settings > Custom data > Metaobject definitions**, the three pinned product fields under **Settings > Custom data > Products**, and one `brand_channels` row per channel with its ID and name. A row with a `note` and no `channel_id` means the handle wasn't found: fix the handle, delete the row and run Setup again. Running Setup again is safe. A field or entry type that already exists answers `TAKEN`.

## Test on a few products

1. Fill in the model number on three to five products, put their IDs in `product_ids`, and point `slack_channel` at a test channel.
2. Open **Run now** and click **Execute workflow**. Open **Check the videos**: for each product it shows `found`, `kept` and why the rest were dropped.
3. Publish the workflow so **Slack button click** answers, then approve one card and reject another. With `dry_run` on, Publish stops at **What would be added**: read the request.
4. Set `dry_run` to false and run **Publish now**. The video shows in the product's **Videos** field in Shopify admin (and under **Content > Metaobjects > Product video**), and the card's thread says where.
5. Add the Videos section to your product template (next section) and open the product page.
5. Do this on a development store first: Setup, Find (the tag removal) and Publish write to Shopify.

## Schedule

Publish the workflow. Find runs every hour, the Publish backstop every hour at half past, and Check at 6am on the first of the month, in the workflow's time zone (Workflow settings > Timezone). The Review webhook only works while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: Publish after an approval runs as a sub-workflow, which doesn't count towards n8n Cloud's quota. Expect about 1,450 schedule runs a month plus one webhook run per Slack click. Slow Find down once the backlog is done.

## Troubleshooting

### Nothing happens when I click a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### A product gets no cards

Read its row in `video_runs`. `found` is how many videos the searches returned; `dropped` says why each one went. Mostly `model not named` means the titles use a different form of the model: add the family name to `model_prefixes`, or check the model number on the product. `error: no model number` means the product has neither a model number nor a title word with a digit in it.

### Searches fail with quotaExceeded

YouTube allows 100 searches a day on the free quota, and it resets at midnight Pacific time. Lower `batch_size`, list fewer channels per brand, or run Find less often. The products keep their tag and are searched again the next day. You can ask for more with Google's quota extension request form for YouTube API Services (it's free, and takes a review).

### A video wasn't added

Read the reply in the card's thread, or `error` in `video_candidates`. `Its title or channel changed since review` means the creator changed it after you approved it; delete the row and Find will offer it again. `Shopify didn't save the video list` comes with Shopify's own error: usually the Videos field doesn't exist yet (run Setup) or the app is missing the metaobject scopes.

### A row is stuck on `publishing`

A Publish run stopped part way. Set its `status` back to `approved` and run **Publish now**.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres (next section).

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py shopify-product-videos --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`brand_channels`, `video_candidates`, `video_runs`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. `video_candidates` has a unique key on `product_id` and `video_id`, so a video is never offered twice for the same product. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Shopify product videos" n8n template in ./shopify-product-videos.

1. Read shopify-product-videos/README.md, SETUP.md and shopify-product-videos/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py shopify-product-videos
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Help me fill in brand_channels in Setup settings: ask which brands I sell, find each brand's official YouTube channels (support and regional ones too) and their @handles, and confirm each one with me.
5. Walk me through every other settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
6. Run the Setup lane and check its output with me.
7. Walk me through adding shopify-product-videos/videos-section.liquid as a Custom Liquid section on my product template (README, "Show the videos on your product page"), one click at a time.
8. Test on about 3 products with nothing written to my store yet (dry_run on in Publish settings): show me the cards and the dry-run output, and check them with me before anything writes to my store.
9. Stop and ask me whenever something doesn't match the README.
```
