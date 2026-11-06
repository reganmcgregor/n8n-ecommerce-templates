# Setup

The credentials the templates in this repo use. Each template's README says which ones it needs and which nodes they go on. Create them once in n8n (Overview > Credentials > Create credential) and reuse them across templates. Or let [the script](#create-the-credentials-from-your-terminal) create them for you.

## Shopify

The templates call the Shopify Admin GraphQL API (version 2026-10) with an access token they fetch at the start of each run, using the [client credentials grant](https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant). Since January 2026, new custom apps are made in the Shopify Dev Dashboard and don't show a permanent admin token, which is why the templates fetch one. A token lasts 24 hours.

### Create the app

1. Open the [Shopify Dev Dashboard](https://dev.shopify.com/dashboard) with the account that owns your store, and create an app.
2. Give it the Admin API scopes the template needs. Read-only templates need `read_products`. Templates that create or change products also need `write_products`, and the README lists any others (add products to Shopify also needs `read_inventory`, `write_inventory`, `read_publications`, `write_publications` and `read_locations`; Shopify collections SEO needs `read_publications` and `write_publications`; category page SEO needs `read_online_store_navigation`; ecommerce internal linking needs `read_online_store_navigation` and `read_content`, plus `read_themes` if you turn on its theme check; automated inventory management needs `read_inventory`, `write_inventory`, `read_locations` and `write_online_store_navigation` (`urlRedirectCreate` makes the 301 when a discontinued product is archived); Shopify product images needs `read_files` and `write_files` (`fileUpdate` writes alt text and detaches old images); product data enrichment needs `read_metaobjects`, `write_metaobjects`, `read_metaobject_definitions` and `write_metaobject_definitions` to write Shopify's standard product attributes).
3. Release a version and install the app on your store. The app and the store must belong to the same Shopify organisation, or the token request is refused.
4. Copy the app's **Client ID** and **Client secret** from its settings.

Test write templates on a development store before you point them at your live one.

### The n8n credential

Create a **Custom Auth** credential (the HTTP Request node's generic Custom Auth type) with:

```json
{"body": {"client_id": "<your client ID>", "client_secret": "<your client secret>"}}
```

Select it on each `Get Shopify token` node. Set `store_domain` in the template's settings to your permanent `your-store.myshopify.com` domain, not your custom domain. The token nodes have Retry On Fail on (3 tries, 2 seconds apart) because the token endpoint sometimes drops the first connection; keep it on if you rebuild them.

If you already have an Admin API access token from a custom app made before 2026, you can skip the token node: delete it and put your token straight into the `X-Shopify-Access-Token` header of the GraphQL requests, ideally through a Header Auth credential rather than as plain text.

## Slack

1. Go to [api.slack.com/apps](https://api.slack.com/apps), click **Create New App**, choose **From scratch**, and pick your workspace.
2. Under **OAuth & Permissions**, add the bot token scope `chat:write`. Add `chat:write.public` too if you want it to post to public channels it hasn't joined. Templates that upload images to Slack (Shopify product images posts a contact sheet on every card) also need `files:write`.
3. Click **Install to Workspace** and copy the **Bot User OAuth Token** (it starts with `xoxb-`).
4. In n8n, create a **Slack API** credential and paste the token as the Access Token.
5. In Slack, invite the bot to the channel the template posts to: type `/invite @your-bot-name` in the channel.

Messages come from the bot, not from you.

### Buttons (Interactivity)

Templates with Approve buttons need Slack to send each tap to n8n:

1. In your Slack app, open **Interactivity & Shortcuts**, turn it on, and set the Request URL to the production URL of the template's webhook node (the README names it). The workflow must be published for that URL to answer.
2. Under **Basic Information**, copy the **Signing Secret**.
3. In n8n, create a **Crypto** credential and paste the signing secret as the Hmac Secret. Select it on the template's signature node, so taps that didn't come from your Slack app are ignored.

A Slack app has one Interactivity URL. If another workflow already uses it, route the taps from that workflow, or make a second Slack app.

## AI model (Ollama Cloud)

The templates with an AI step use one Chat Model sub-node, set to the Ollama node with Ollama Cloud, so they don't depend on any one paid provider.

1. Create an account at [ollama.com](https://ollama.com) and make an API key under your account's settings.
2. In n8n, create an **Ollama** credential with Base URL `https://ollama.com` and your API key.
3. Select it on the template's Ollama Chat Model sub-node and pick a model.

To use another provider, swap the Chat Model sub-node for that provider's (OpenAI, Anthropic, OpenRouter and so on). The chain or agent it's attached to doesn't change.

The competitor price monitoring, ecommerce internal linking and automated inventory management templates have no AI step. Add products to Shopify uses one Basic LLM Chain for the title and short description. AI product titles uses one Basic LLM Chain for the title. AI product descriptions uses one Basic LLM Chain for the intro, and asks for plain paragraphs rather than JSON, so it needs no parser. Shopify collections SEO uses one to name each proposed collection, and category page SEO one to write each intro and its meta tags. Those two ask for a small JSON reply and read it in a Code node rather than a Structured Output Parser, because models on Ollama Cloud sometimes wrap JSON in a code fence or leave a trailing comma (even with Output Format set to JSON), and a parser rejects that.

Product data enrichment uses one Basic LLM Chain to extract the attributes, plus an optional one that reads text from product images. Shopify product images uses two Basic LLM Chains that send a photo as the user message (Message Type **Image (Binary)**), so it needs a vision-capable model; `gemma4:31b` on Ollama Cloud is one. With Output Format JSON, the chain sometimes hands back the parsed object and sometimes `text` holding JSON in a code fence, so the template reads both. Shopify collection sorting has no chat model; its optional blend mode uses embeddings (below).

## Embeddings (optional)

The Shopify collection sorting template can blend meaning into its keyword score (`match_mode: "blend"`). It calls an embeddings endpoint from a Code node, so there's no credential to create:

1. Install [Ollama](https://ollama.com) where n8n can reach it and run `ollama pull nomic-embed-text`.
2. Set `embed_url` in **Sort settings** to `http://localhost:11434/api/embed`, or `http://host.docker.internal:11434/api/embed` when n8n runs in Docker and Ollama on the host.

Any OpenAI-style `/v1/embeddings` API works too: set `embed_url`, `embed_model` and `embed_api_key`, and clear `query_prefix` and `doc_prefix`. The key sits in the workflow in plain text, so don't share the workflow with it filled in.

## AliExpress Open Platform

Used by the add products to Shopify template for AliExpress listings, through the free Dropshipping API.

1. Sign up at [openservice.aliexpress.com](https://openservice.aliexpress.com) as a developer, create an app with the Dropshipping solution, and give it a callback URL (any HTTPS page you control).
2. Copy the **App Key** and **App Secret** from the app's page.
3. In n8n, create a **Crypto** credential and paste the App Secret as the Hmac Secret. Select it on the template's three AliExpress Sign nodes. The App Key goes in the `aliexpress_auth` data table.
4. Authorise once to get the first access token: the template's README has the steps.

New apps start in test status: refresh tokens last 48 hours and refreshing doesn't extend them, so you re-authorise every two days until AliExpress approves the app.

## DataForSEO

Used for Google searches (competitor discovery), and for search volumes, keyword difficulty and rank checks (Shopify collections SEO).

1. Sign up at [dataforseo.com](https://dataforseo.com) and top up your balance. The [minimum payment is US$50](https://dataforseo.com/help-center/minimum-payment), and it's pay as you go after that.
2. Open the API Access page in your dashboard. Your **API login** and **API password** are there. The API password isn't your account password.
3. In n8n, create a **Basic Auth** credential with the API login as the user and the API password as the password.

Each response reports its own cost, and the templates save it so you can see what a run spent. A query with a search operator such as `site:` is billed at five times the price of a plain one (US$0.01 against US$0.002 in November 2026), which is why the product images template searches for the brand and model alone and filters the results in code.

## Firecrawl

Used only for pages that block a plain request.

1. Sign up at [firecrawl.dev](https://www.firecrawl.dev) and copy your API key (it starts with `fc-`). The free plan includes 1,000 credits a month, and one page costs one credit.
2. In n8n, create a **Header Auth** credential with Name `Authorization` and Value `Bearer <your API key>`.
3. Select it on the template's `Firecrawl scrape` node.

If you'd rather not use it, set `use_firecrawl` to false in the template's settings.

## Create the credentials from your terminal

`scripts/create-credentials.py` creates every credential a template needs through n8n's public API, so you never paste a secret into a chat or a file. It uses Python 3's standard library only. Run it in your own terminal from the repo root:

```bash
python3 scripts/create-credentials.py shopify-collections-seo
```

It asks for your n8n URL and an n8n API key, then for each credential in the template's `credentials.json`. Secrets are typed with nothing shown on screen and sent straight to your n8n. It prints only the names and IDs it created, and which nodes each one goes on. Add `--supabase` to create the Postgres credential for `workflow-supabase.json` too. If a credential with the same name and type already exists, it asks before creating another. `--only postgres` creates just the Supabase credential, for when you switch an installed template to Supabase later, and setting `N8N_URL` and `N8N_API_KEY` in your environment skips those two questions. It refuses a Supabase direct-connection string (IPv6 only) or one that still has the `[YOUR-PASSWORD]` placeholder.

You need an n8n API key: in n8n, open **Settings > n8n API**, create a key and copy it. Self-hosted n8n has the API on by default (unless `N8N_PUBLIC_API_DISABLED` is set). On n8n Cloud, the API [isn't available during the free trial](https://docs.n8n.io/api/authentication/), so on a trial create the credentials by hand as described above.

## Supabase (optional)

Every template also ships as `workflow-supabase.json`, which keeps its tables in a Supabase (Postgres) database instead of n8n Data Tables. Use it when you'd rather query, back up or share the data outside n8n, or you're near the Data Tables size limit.

1. Create a project at [supabase.com](https://supabase.com). The [free plan](https://supabase.com/pricing) includes a 500 MB database; free projects pause after a week without activity, and you restore them from the dashboard.
2. Click **Connect** and copy the **Session pooler** connection string (`postgresql://postgres.<project>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`), with your database password in place of `[YOUR-PASSWORD]`. If the password contains `/`, `?` or `#`, URL-encode those characters (or reset the password to letters and numbers). Use the session pooler rather than the direct connection, which is [IPv6 only unless you pay for the IPv4 add-on](https://supabase.com/docs/guides/database/connecting-to-postgres), or the transaction pooler (port 6543), which doesn't support the prepared statements n8n uses.
3. Create the n8n credential with `python3 scripts/create-credentials.py <template> --supabase`, or by hand as a **Postgres** credential: Host, Database (`postgres`), User (`postgres.<project>`), Password and Port (5432) from the connection string, SSL **Require**, and **Ignore SSL Issues** on, because Supabase signs its database certificates with its own certificate authority and n8n rejects them otherwise.
4. Run the template's Setup lane, or paste its `supabase/schema.sql` into Supabase's SQL editor.

The table nodes run plain SQL with query parameters, so they also work on any other Postgres database.

