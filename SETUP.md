# Setup

The credentials the templates in this repo use. Each template's README says which ones it needs and which nodes they go on. Create them once in n8n (Overview > Credentials > Create credential) and reuse them across templates.

## Shopify

The templates call the Shopify Admin GraphQL API (version 2026-10) with an access token they fetch at the start of each run, using the [client credentials grant](https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant). Since January 2026, new custom apps are made in the Shopify Dev Dashboard and don't show a permanent admin token, which is why the templates fetch one. A token lasts 24 hours.

### Create the app

1. Open the [Shopify Dev Dashboard](https://dev.shopify.com/dashboard) with the account that owns your store, and create an app.
2. Give it the Admin API scopes the template needs. Read-only templates need `read_products`. Templates that create or change products also need `write_products`, and the README lists any others (add products to Shopify also needs `read_inventory`, `write_inventory`, `read_publications`, `write_publications` and `read_locations`; Shopify collections SEO needs `read_publications` and `write_publications`; category page SEO needs `read_online_store_navigation`).
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
2. Under **OAuth & Permissions**, add the bot token scope `chat:write`. Add `chat:write.public` too if you want it to post to public channels it hasn't joined.
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

The competitor price monitoring template has no AI step. Add products to Shopify uses one Basic LLM Chain for the title and short description. AI product titles uses one Basic LLM Chain for the title. Shopify collections SEO uses one to name each proposed collection, and category page SEO one to write each intro and its meta tags; both set the Ollama node's Output Format to JSON so a stray comma can't break the structured output.

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

Each response reports its own cost, and the templates save it so you can see what a run spent.

## Firecrawl

Used only for pages that block a plain request.

1. Sign up at [firecrawl.dev](https://www.firecrawl.dev) and copy your API key (it starts with `fc-`). The free plan includes 1,000 credits a month, and one page costs one credit.
2. In n8n, create a **Header Auth** credential with Name `Authorization` and Value `Bearer <your API key>`.
3. Select it on the template's `Firecrawl scrape` node.

If you'd rather not use it, set `use_firecrawl` to false in the template's settings.
