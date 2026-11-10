# Instagram product posts

An n8n template that turns your Shopify products into Instagram posts. Each post is the real product photo in your own frame, with a caption written from the product data. A person approves it in Slack, then a paced queue posts it through the official Instagram API, so nothing goes out twice or in a burst. No AI touches the image, and no price goes on it.

- **Setup** creates the `instagram_posts` and `instagram_token` data tables.
- **Connect** is a form (only signed-in n8n users can open it) where you paste the access token from your Meta app. It checks the token with Instagram and saves it with your account id.
- **Draft** (every morning, and after each Approve or Skip) keeps up to `max_waiting` drafts in Slack. Each product gets one post, ever, oldest products first. A vision model checks the main photo (a box shot or a spec sheet gets a warning), a chat model writes the headline, product line, hook, body, three facts and hashtags, and **Check the post** builds the caption in a fixed shape with your price line.
- **Frame** is a web page that draws the post at 1080 x 1350 (4:5) from the saved row. **Render** screenshots it with Firecrawl and keeps the JPEG in Shopify Files.
- **Review** checks Slack's signature on every click. Approve books a slot, Edit opens a modal (a new headline redraws the image), Skip means the product never gets a post, Cancel takes a scheduled post back to a draft.
- **Book** gives an approved post the next slot after your last scheduled or posted one: a week divided by `posts_per_week`, jittered, inside posting hours.
- **Publish** (every 15 minutes) posts one due post a run: it creates the media container, waits until Instagram has processed it, publishes it and reads back the link.
- **Token** (Mondays) refreshes your token, which lasts 60 days, and warns you if the refresh fails.
- **Report** (Mondays) says what posted last week, what's scheduled and when the queue runs out, and how long drafts have waited.

The full walkthrough is in the guide: [How to Automate Instagram Posts for Shopify Products With n8n](https://www.reganmcgregor.com.au/automate-instagram-posts-shopify/).

## What you need

- n8n with Data Tables on a public HTTPS URL (Slack and Firecrawl both reach webhooks). Tested on n8n 2.46.
- A Shopify app with `read_products`, `read_files` and `write_files`, and its client ID and secret.
- An Instagram professional account (Business or Creator) and a Meta app with the Instagram API with Instagram Login. No Facebook Page needed. Steps are in [SETUP.md](../SETUP.md#instagram).
- A Slack app with a bot token (`chat:write`, plus `chat:write.public` to post in channels the bot hasn't joined), Interactivity turned on, and its signing secret.
- An AI model with vision. The template uses Ollama Cloud with `gemma4:31b` for both the photo check and the words.
- Firecrawl for the frame screenshots (one credit per image; the free plan covers a few posts a week).

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Render | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post or update the card, Open the edit modal, Post to the log, Warn the log channel, Post the report | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Look at the photo, Ollama Chat Model | Ollama | Base URL `https://ollama.com` and your API key |
| Screenshot the frame | Header Auth | Name `Authorization`, Value `Bearer <Firecrawl API key>` |

The Instagram token isn't an n8n credential: it changes every time it's refreshed, so the **Connect** form saves it in the `instagram_token` table and the Token lane keeps it current. Anyone who can open your n8n instance can read that table, so keep the instance private.

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. Fill in the settings (below), then run **Run once to set up**.
4. Publish the workflow, so **Frame page**, **Slack button click** and the token form answer.
5. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).
6. Open the production URL of **Save your Instagram token** (open the node, then **Production URL**), sign in to n8n if asked, and paste your token. The page says which account it connected.

## Settings

**Draft settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `store_url` | Your public store address, used for the product link if Shopify hasn't given one |
| `store_name`, `store_description` | How the model and the caption refer to your store |
| `language`, `style_rules` | The language to write in, and any house rules ("Metres rather than yards or feet.") |
| `locale` | How prices are written, such as `en-AU` or `en-US` (the currency comes from Shopify) |
| `slack_channel` | Where the cards go, such as `#instagram` |
| `product_query` | Which products to post, in Shopify search syntax (`product_type:Camera`, `tag:instagram`). Keep `status:active published_status:published` |
| `max_products` | The most products read per run |
| `skip_words` | Products whose title matches never get a post (mounts, cables, spare parts) |
| `max_waiting` | How many drafts can wait in Slack at once |
| `min_photo_px` | The smallest main photo (short side) worth posting |
| `utm` | Added to the product link, so Instagram visits show up separately in your analytics |
| `closing_line`, `closing_line_no_price` | The price line. `{price}` and `{store}` are filled in |
| `max_hashtags` | The most hashtags in a caption |
| `banned_words` | Words that put a warning on the card |
| `keep_terms` | Terms the checks write in a fixed form (PoE, 4K, Wi-Fi) |
| `chat_model`, `vision_model` | Model names on Ollama |
| `require_approval` | On: a person approves every post. Off: drafts are booked straight away (keep it on until you trust the checks) |

**Card settings**: `timezone` for the times on the cards. **Frame settings**: `store_name`, `store_url_text`, `logo_url`, `font` (any Google Font), and the four colours. **Render settings**: `store_domain`, `frame_page_url` (the production URL of **Frame page**).

**Book settings**:

| Setting | What it does |
|---|---|
| `timezone` | Your time zone, for posting hours |
| `posts_per_week` | Your pace. 3 to 5 a week is a good start |
| `post_from`, `post_until` | Posting hours |
| `first_slot_after` | Nothing posts before this date and time. Set it ahead while you test, or for a launch |

**Publish settings**: `api_base` (the Instagram API host and version) and `log_channel`. **Token settings**: `log_channel` and `warn_days`. **Report settings**: `log_channel`, `review_channel`, `timezone`, `old_draft_days`.

## Test it

1. Point `slack_channel` and the log channels at a test channel, set `max_waiting` to 2 and `product_query` to a tag on two or three products.
2. Open **Draft posts now** and click **Execute workflow**. Each product gets a card with the framed image, headline and product line (with character counts), the caption, the alt text and any warnings.
3. Open `frame_page_url?id=<post id>` in a browser to adjust the frame. Tap **Edit**, change the headline and save: the image is drawn again.
4. Tap **Approve**. The card shows the booked time. Tap **Cancel** to take it back.
5. For a real post, use an account you don't mind posting to, approve one card, and run **Publish due posts now** once the slot has passed (or set `first_slot_after` to now). The card turns into "On Instagram" with an Open post button.

## Schedule

Publish the workflow. Draft runs every morning at 8, Publish every 15 minutes, Token and Report on Mondays, in the workflow's time zone (Workflow settings > Timezone). The webhooks and the form only work while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: Publish runs 96 times a day and stops at once when nothing is due. Each post adds a few more (draft, render, card, a click or two, book, publish).

## Troubleshooting

### The token form says "That token did not work"

Generate a new token in your Meta app (Instagram > API setup with Instagram login > Generate token) and paste the whole thing. The account must be a Business or Creator account added to the app.

### A post says "Post failed"

Read the reason on the card. "Only photo or video can be accepted as media type" or a media error usually means Instagram couldn't fetch a JPEG: check the image URL on the card opens in a browser. Try again books a new slot.

### Nothing posts

Check the weekly report: if nothing is scheduled, drafts are waiting for approval. If posts are scheduled but the slot has passed, check the Publish lane's executions and that the token form has been filled in.

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### The image never appears

Open the frame URL in a browser first. If it shows, check Firecrawl's credits and the **Screenshot the frame** output. If Shopify was still processing the image, the card says so; edit and save to draw it again.

### No new drafts appear

Draft only fills free slots in `max_waiting`. Approve or Skip the waiting cards. A product also needs a main photo at least `min_photo_px`, a price and a description, and it must not have had a post before.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py instagram-automation --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates `instagram_posts` and `instagram_token` if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. `instagram_posts` has a unique key on the product, so a product can't get two posts. Supabase stores the token in a table too, so turn on row-level security if anything else reads that database. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal, and the Instagram token goes into the template's own form.

```text
Help me set up the "Instagram product posts" n8n template in ./instagram-automation.

1. Read instagram-automation/README.md, SETUP.md and instagram-automation/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py instagram-automation
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through the Instagram section of SETUP.md: professional account, Meta app, Instagram Login, generating a token. Tell me to paste the token into the template's "Save your Instagram token" form myself, not into this chat.
5. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer.
6. Run the Setup lane, publish the workflow, and set my Slack app's Request URL with me.
7. Run Draft on 2 or 3 products and check the cards with me. Approve one and Cancel it before anything posts for real.
8. Stop and ask me whenever something doesn't match the README.
```
