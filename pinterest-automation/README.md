# Pinterest product pins

An n8n template that writes a Pinterest pin for each Shopify product from its own data, asks you in Slack before anything posts, and books approved pins at a steady pace through Zernio, so nothing goes out twice or in a burst. The image is always the real product photo: padded to 2:3 for a product's first pin, then placed in a fixed HTML frame with a headline, then with a customer review. No AI touches the image.

- **Setup** creates the `pins` and `pin_reviews` data tables, adds one sample review, and lists your Pinterest boards with their ids.
- **Draft** (every morning, and after each Approve or Skip) keeps up to `max_waiting` drafts waiting in Slack, one pin per product at a time. It matches each product to a board, picks the product's next pin from `pin_sequence` (photo, headline frame, review frame, second photo) once the last one has been up `next_pin_after_days`, looks at the photo with a vision model for the alt text, writes the title and description for Pinterest search, checks them in code and posts a card.
- **Frame** is a web page that draws a headline or review pin at 1000 x 1500 from the saved row. **Render** screenshots it with Firecrawl and keeps the JPEG in Shopify Files.
- **Review** checks Slack's signature on every click. Approve books a slot, Edit opens a modal (a new headline redraws the frame), Skip drops the pin (on a first pin, the whole product), Cancel takes a scheduled pin back to a draft.
- **Book** gives an approved pin the next slot after your last scheduled or posted pin, by your `pace`, jittered and inside posting hours, and schedules it in Zernio.
- **Sync** (hourly) asks Zernio about pins whose slot has passed and turns the card into "Pinned" with the link, or "Pin failed" with Try again.

The full walkthrough is in the guide: [Pinterest Automation for Shopify](https://www.reganmcgregor.com.au/pinterest-automation-shopify/).

## What you need

- n8n with Data Tables on a public HTTPS URL (Slack and Firecrawl both reach webhooks). Tested on n8n 2.46.
- A Shopify app with `read_products` and `write_files`, and its client ID and secret.
- A Pinterest business account with your website claimed and your boards made, connected to a [Zernio](https://zernio.com) account (free for one or two connected accounts, API included).
- A Slack app with a bot token (`chat:write`, plus `chat:write.public` to post in channels the bot hasn't joined), Interactivity turned on, and its signing secret.
- An AI model with vision. The template uses Ollama Cloud with `gemma4:31b` for both the photo check and the words.
- Firecrawl for the frame screenshots (the free plan covers a few frames a day; one credit per frame).

[SETUP.md](../SETUP.md) shows how to create each credential.

## Credentials

| Node | Credential type | What goes in it |
|---|---|---|
| Get Shopify token, Get Shopify token for Render | Custom Auth | `{"body": {"client_id": "...", "client_secret": "..."}}` |
| Post or update the card, Open the edit modal, Post to the log | Slack API | Your bot token |
| Sign the request | Crypto | Hmac Secret = your Slack app's Signing Secret |
| Look at the photo, Ollama Chat Model | Ollama | Base URL `https://ollama.com` and your API key |
| Screenshot the frame | Header Auth | Name `Authorization`, Value `Bearer <Firecrawl API key>` |
| List Pinterest boards, Schedule on Pinterest, Delete from Zernio, Ask Zernio | Header Auth | Name `Authorization`, Value `Bearer <Zernio API key>` |

## Import

1. In n8n, create a workflow, open the `...` menu and choose **Import from File**, then pick `workflow.json`.
2. Open each node in the table above and select (or create) its credential.
3. Publish the workflow, so **Frame page** and **Slack button click** answer.
4. In your Slack app, under **Interactivity & Shortcuts**, set the Request URL to the production URL of **Slack button click** (open the node, then **Production URL**).

## Settings

**Setup settings**: `zernio_account_id` (Zernio > Accounts > your Pinterest account) and `sample_review_handle` (the handle of one of your products, so the sample review lands on a pin you can see).

**Draft settings**:

| Setting | What it does |
|---|---|
| `store_domain` | Your permanent `*.myshopify.com` domain |
| `store_url` | Your public store address, used for the pin link if Shopify hasn't given a product URL |
| `store_name`, `store_description` | How the model refers to your store ("an online store for ...") |
| `language`, `style_rules` | The language to write in, and any house rules ("Metres rather than yards or feet.") |
| `slack_channel` | Where the cards go, such as `#pins` |
| `frame_page_url` | The production URL of **Frame page** |
| `product_query` | Which products to consider, in Shopify search syntax. Keep `published_status:published` |
| `max_products` | The most products read per run |
| `boards` | Your boards: `key`, `name`, `board_id` (from Setup), `match` (any of `title_words`, `product_types`, `categories`; first board that matches wins) and two to four `phrases` people search on Pinterest |
| `skip_words` | Products whose title matches never get a pin (mounts, cables, spare parts) |
| `pin_sequence` | The order of a product's pins: `photo`, `headline`, `review`, `photo_2`. A step the product can't make is skipped |
| `max_waiting` | How many drafts can wait in Slack at once |
| `next_pin_after_days` | Days between a product's pins |
| `min_photo_px` | The smallest photo (short side) worth pinning |
| `review_min_rating`, `review_max_chars`, `review_sources` | Which reviews can go on a review frame. Remove `sample` from `review_sources` once your own reviews are in |
| `image_template` | The wsrv.nl address that pads the photo to 2:3 |
| `utm` | Added to every pin link, so these pins show up separately in your analytics |
| `closing_line` | The last sentence of every description |
| `banned_words` | Words that put a warning on the card |
| `keep_terms` | Terms the checks write in a fixed form (PoE, 4K, Wi-Fi) |
| `chat_model`, `vision_model` | Model names on Ollama |

**Card settings**: `timezone` for the times on the cards. **Frame settings**: `store_name`, `store_url_text`, `logo_url`, `font` (any Google Font), and the four colours. **Render settings**: `store_domain`, `frame_page_url`. **Review settings**: the Zernio API address.

**Book settings**:

| Setting | What it does |
|---|---|
| `zernio_account_id` | Your Pinterest account in Zernio |
| `timezone` | Your time zone, for posting hours |
| `pace` | Pins a week by weeks since your first pin. The default is 7 a week, then 14 from week 4 |
| `max_per_week` | A hard cap, whatever `pace` says |
| `post_from`, `post_until` | Posting hours |
| `first_slot_after` | Nothing posts before this date. Set it a few weeks out while you test |

**Sync settings**: `log_channel` for one line per pin that went live.

## Run Setup

Open **Run once to set up** and click **Execute workflow**. You get two data tables, one sample review in `pin_reviews`, and the output of **List Pinterest boards**: copy each board's `id` into `boards` in **Draft settings**. Running Setup again keeps your tables and doesn't add a second sample.

Add your own reviews to `pin_reviews` (source `own`, word for word, with the rating), or replace **Get reviews** with your review app's API. A pin with the sample review can never be booked: Approve answers "This pin uses the sample review" and nothing is scheduled.

## Test it

1. Set `first_slot_after` to a date a few weeks away, `max_waiting` to 3, and point `slack_channel` at a test channel.
2. Open **Draft pins now** and click **Execute workflow**. Each product gets a card with the 2:3 image, title, description, alt text, board and link, and any warnings.
3. Tap **Edit** and change the title, then **Approve**. The card shows the booked time. Check the post in Zernio's calendar, then tap **Cancel**: the post is deleted and the pin goes back to a draft.
4. To see the frames, set `next_pin_after_days` to 0, mark a pin `posted` in the `pins` table, and run Draft again. Open `frame_page_url?id=<pin id>` in a browser to adjust the frame.
5. Put `first_slot_after` back to empty (or your launch date) when you're happy.

## Schedule

Publish the workflow. Draft runs every morning at 8 and Sync every hour at 7 minutes past, in the workflow's time zone (Workflow settings > Timezone). The Frame and Review webhooks only work while the workflow is published. Set an Error Workflow too, so a crashed run reaches you.

Executions: each pin is a few runs (draft, card, render for a frame, a click or two, book, sync). At one or two pins a day that's a few hundred executions a month, whatever the size of your catalogue.

## Troubleshooting

### Nothing happens when I tap a button

Check the Interactivity Request URL is the production URL of **Slack button click** and the workflow is published. If executions stop at **Signature valid?**, the Crypto credential on **Sign the request** doesn't hold this app's signing secret.

### Approve says the pin is already scheduled, posted or skipped

That's on purpose: only a draft or a failed pin can be booked, so a second tap or an old card can't book a pin twice.

### The frame image never appears

Open the frame URL in a browser first (`frame_page_url?id=<pin id>`). If it shows, check Firecrawl's credits and the **Screenshot the frame** output. If Shopify was still processing the image, the card says so; edit and save to draw it again.

### No new drafts appear

Draft only fills free slots in `max_waiting`, and only one pin per product waits at a time. Approve or Skip the waiting cards. A product also needs a board match, a photo at least `min_photo_px`, a price and a description.

### A pin says "Pin failed"

Read the reason on the card. Try again books a new slot. "Zernio has no post with this id" means it was deleted in Zernio.

### Data table writes start failing

All data tables on an instance share a 200 MiB limit by default. Self-hosters can raise `N8N_DATA_TABLES_MAX_SIZE_BYTES`; otherwise move the tables to Postgres.

## Use Supabase instead of Data Tables

`workflow-supabase.json` is the same workflow with every Data table node swapped for a Postgres node on your Supabase database, for when you'd rather keep the data in a database you can query, back up and share with other tools. The nodes keep their names, so everything above applies.

1. Create a Supabase project and copy its **Session pooler** connection string (Connect > Session pooler). [SETUP.md](../SETUP.md#supabase-optional) has the details.
2. Create the Postgres credential: run `python3 scripts/create-credentials.py pinterest-automation --supabase` from the repo root, or create it by hand as SETUP.md describes.
3. Import `workflow-supabase.json` instead of `workflow.json`, and select the Postgres credential on every table node (the script lists them).
4. Run **Run once to set up**. It creates the tables (`pins`, `pin_reviews`) if they don't exist. You can also run [`supabase/schema.sql`](supabase/schema.sql) in Supabase's SQL editor first.

Each table has the same columns as the data table, plus `id`, `createdAt` and `updatedAt`. `pins` has a unique key on product, pin kind and photo, so the same pin can't be saved twice. The free plan includes a 500 MB database, and free projects pause after a week without activity; restore one from the Supabase dashboard if that happens.

## Set it up with an AI agent

Paste this into Claude Code, Codex or Cursor, opened in a clone of this repo. It never needs your secrets: you type those into a script in your own terminal.

```text
Help me set up the "Pinterest product pins" n8n template in ./pinterest-automation.

1. Read pinterest-automation/README.md, SETUP.md and pinterest-automation/workflow.json. Ask me whether I want n8n Data Tables (workflow.json) or Supabase (workflow-supabase.json).
2. Import the workflow into my n8n. Use the n8n MCP server if one is connected; otherwise tell me exactly where to click in n8n.
3. Never ask me for a password, token, API key or secret, and don't accept one if I paste it. Tell me to run this in my own terminal from the repo root:
   python3 scripts/create-credentials.py pinterest-automation
   (add --supabase for the Supabase version). Then put each credential it created on the nodes it lists.
4. Walk me through every settings node one value at a time: say what the value does, suggest one for my store, and wait for my answer. Help me choose boards and two to four Pinterest search phrases for each.
5. Run the Setup lane, then copy my board ids from its output into Draft settings with me.
6. Set first_slot_after a few weeks out, run Draft on 3 products, and check the cards with me. Approve one, check it in Zernio, then Cancel it, before anything posts for real.
7. Stop and ask me whenever something doesn't match the README.
```
