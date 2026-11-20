# Prompt 2: Research each niche with one subagent per niche

Run this after `candidates.md` exists and you've cut anything you don't want to look at.

```text
Read scorecard.yaml and candidates.md. For each niche in candidates.md, start a subagent that researches that one niche, and run them in parallel, five at a time. Give each subagent the brief below with the niche name and its seed keywords filled in. Each subagent writes research/<niche-slug>.md and returns a one-line summary.

--- Subagent brief ---
Research the niche "<NICHE>" for an online store in the country set in scorecard.yaml, using the seed keywords: <KEYWORDS>. Collect evidence only; don't score it. Every number needs its source (tool and endpoint, or URL) and the date you pulled it. If a number isn't available, write "not found". Never estimate a number and present it as measured.

1. Kill checks. Is it legal to sell these products in the country? Do Shopify's Acceptable Use Policy and the Shopify Payments restricted businesses list allow them? Note any compliance mark or licence the products need. Link the source for each answer.

2. Money (do this before step 4). For each seed keyword: monthly volume, keyword difficulty, traffic potential and CPC, all from the same tool (volume sources disagree, so don't mix them). Then the total volume. Find the weak incumbents: sites with a Domain Rating of 35 or less that rank on page one for any seed keyword, with their whole-site organic traffic and traffic value in USD for the country (for example Ahrefs batch-analysis by domain). Pull 5 years of Google Trends for the two biggest keywords and compare the average of the last 52 weeks with the first 52 weeks. Say which of the three money proofs in scorecard.yaml pass.

3. Buyers. Work out value per visit (traffic value divided by traffic) for the three niche stores with the most organic traffic, leaving out big-box retailers and publishers. List spec-led or brand-led searches (model numbers, brands, "best X for Y"), and find two or three places where enthusiasts talk about these products (forums, subreddits, Facebook groups) with a rough size for each.

4. Results page. For every seed keyword, list the organic results on page one (usually 8 to 10; ask the tool for organic results only, because Shopping, People Also Ask and AI Overview blocks also take positions and cost credits) with domain, Domain Rating, referring domains to the ranking page and estimated traffic. Mark each one as marketplace, big-box retailer (count franchises of one as big-box), specialist store, brand site, publisher or service. Report the lowest DR on page one, the median DR, how many pages rank on 5 or fewer referring domains, and how many slots marketplaces and big-box retailers hold.

5. Awkwardness. On Amazon in this country, search the two highest-volume seed keywords: count the organic listings and the sponsored listings on page one, and flag a count of zero as something to check by hand. Note anything that makes the niche harder for others: size or weight, licences, compliance marks, products that are legal but taboo, products that need help to choose, advertising restrictions.

6. Margins and suppliers. Find one store selling 10 to 12 products in this niche that shows both a reference price and the current price, scrape the pairs, and give the median discount. Prefer a store that labels the manufacturer's RRP, and say which kind of reference price it is (RRP, or the store's own "was" price). Pick one popular product, search for that exact SKU (one search of 20 results), and list the stores in the country selling it and their prices. That's a floor, not a full count. Then find suppliers I could open an account with as a new business: distributors with open trade accounts, brand dealer or stockist programmes, wholesale feeds (CSV, XML or API), and direct import. For each, note what they ask for (business number, trade form, minimum order) and whether stock and prices come as a feed. If a supplier's trade terms aren't public, write "enquiry needed" and move on. Say whether the distributors also sell to the public online, and whether they rank.

7. Freight. Typical carton size and weight for the core products from spec sheets, and a shipping cost against a typical order value only if a carrier rate calculator gives you one.

Finish the file with "What I couldn't find" and "What would change my mind about this niche".
--- End of brief ---

When every subagent has finished, list any niche where a subagent hit an error or wrote "not found" for more than three of the steps, so I can rerun it.
```
