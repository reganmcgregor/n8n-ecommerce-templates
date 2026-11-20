# Niche research with AI agents

Three prompts and a scorecard for finding a profitable ecommerce niche before you build anything. This one isn't an n8n template: it runs in Claude Code (or another AI agent that can use MCP servers), with an SEO data tool doing the measuring.

The agents score each idea against six boxes:

| Box | What the agents check |
| --- | --- |
| Prosumer buyers | Value per visit of the stores already selling, spec and brand-led searches, enthusiast forums |
| Lower volume | Search volume and traffic potential across a keyword set, and the trend |
| Not big-box | How many of the top 10 results marketplaces and big retailers hold |
| A bit awkward | Amazon listing depth and sponsored slots, legality, licences, size and weight |
| Good margins | RRP against street price, stores selling the same SKU, suppliers you can open an account with |
| Weak incumbents | The lowest Domain Rating on page one, and pages ranking on few referring domains |

The full walkthrough is in the guide: [How to Find a Profitable Ecommerce Niche With AI Agents](https://www.reganmcgregor.com.au/find-a-profitable-niche/).

## What's in this folder

| File | What it is |
| --- | --- |
| `scorecard.yaml` | The rules: kill checks, the money gate, the marketplace check, six weighted dimensions with what a 1, 3 and 5 look like, penalties and verdicts. Edit it before you pull any data. |
| `prompts/1-find-candidates.md` | Builds a list of 20 to 30 niches with four methods and saves `candidates.md`. |
| `prompts/2-research-each-niche.md` | Starts one subagent per niche to collect the evidence for every box and saves `research/<niche>.md`. |
| `prompts/3-score-and-rank.md` | Scores every niche against `scorecard.yaml` in a fresh session and saves `scorecard.md`. |

## What you need

- [Claude Code](https://claude.com/product/claude-code) on a Pro plan or higher, or another agent with MCP support (Codex, Gemini CLI, Cursor).
- An SEO data MCP server: [Ahrefs](https://ahrefs.com/seo-mcp) (its Lite plan and up include API and MCP access) or [DataForSEO](https://dataforseo.com/) (pay as you go).
- [Firecrawl](https://www.firecrawl.dev/) or another scraper for price and supplier pages. The free tier covers a small screen.

## How to run it

1. Copy this folder into a new, empty project folder and open Claude Code there.
2. Connect your SEO data and scraping MCP servers, then ask the agent to pull one keyword's volume to check they work.
3. Edit `scorecard.yaml`: your country, the marketplaces and big retailers in it, and anything you'd change in the thresholds. Put today's date in the changelog.
4. Paste prompt 1. Read `candidates.md` and cut anything you'd never sell.
5. Paste prompt 2. Rerun any niche the agent flags as incomplete.
6. Start a fresh session and paste prompt 3.
7. Spot-check the numbers the top three scores rest on in the tools themselves before you act on them.

If you change a rule after seeing the data, add a dated line to the changelog saying why, bump the version and rerun prompt 3.

## Licence

[MIT](../LICENSE).
