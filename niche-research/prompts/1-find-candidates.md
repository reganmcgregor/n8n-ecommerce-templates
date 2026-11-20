# Prompt 1: Find 20 to 30 niche ideas

Paste this into Claude Code from the folder that holds `scorecard.yaml`. Replace the two lines in square brackets first.

```text
You're helping me find a niche for a new online store. Read scorecard.yaml in this folder first: it sets the country, the currency and the rules every niche will be scored against later.

About me: [what you know, what you like, what you've sold before, how much you can spend on stock]
Ideas I already have: [list them, or write "none"]

Build a list of 20 to 30 candidate niches for an ecommerce store selling physical products, using organic search only. Use four methods and say which method found each niche:

1. Buckets. Break these into specific product categories: prosumer and hobby gear, trade and workshop supplies, bulky or awkward-to-ship products, products that are legal but taboo or need a licence or compliance mark, and accessories that go with a bigger purchase.
2. Weak-incumbent mining. With the SEO data tool, find stores in my country with a Domain Rating of 35 or less that get at least 3,000 organic visits a month from product and category pages. For each one, pull its organic competitors and repeat once. Each cluster of stores is a niche. This method usually finds niches nobody would brainstorm, so spend the most effort here.
3. SERP harvesting. For 10 seed keywords from methods 1 and 2, list the stores ranking on page one (organic results only) and add any niche they reveal.
4. Supply side. Search for wholesale distributors in my country that offer open trade accounts or dealer programmes, and note the product ranges they carry.

For every candidate, record:
- niche name and 4 to 6 seed keywords a shopper would search (product terms, not brand names alone, and no term that means something else, like "smart switch", which is mostly a phone app)
- the method that found it
- the best weak incumbent found (domain, DR, monthly organic traffic, monthly traffic value in USD)
- one line on why it might fit me

Add one negative control: a niche you'd expect to be hard to win, like graphics cards.

Don't score anything yet. Save the list to candidates.md as a table, then tell me how many you found by each method and which ones I should cut before research because they fail a kill check in scorecard.yaml.
```
