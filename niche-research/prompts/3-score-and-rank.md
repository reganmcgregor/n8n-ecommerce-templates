# Prompt 3: Score and rank

Run this in a fresh session once every `research/<niche>.md` file exists, so the scorer reads the evidence cold instead of remembering how it was gathered.

```text
Read scorecard.yaml, then every file in research/. Score each niche strictly by the rules in scorecard.yaml and nothing else. If a rule doesn't fit the evidence, don't bend it: say so in a "Rule problems" section at the end, and I'll decide whether to change scorecard.yaml.

For each niche:
1. Kill checks: pass or fail, with the source.
2. Money gate: which of the three proofs pass, with the number for each.
3. Marketplace check: how many of the organic results on page one marketplaces and big-box retailers hold, per keyword and in total.
4. A 1 to 5 score for each dimension, following the scoring rules in scorecard.yaml and quoting the number from the research file that decided it. Mark any score that rests on "not found" as provisional.
5. The weighted score out of 5, then each penalty that applies (they multiply together) and the final score.
6. The verdict (opportunity, contested, desert or irrelevant).

Then write scorecard.md with:
- one table: niche, money proofs passed, the six dimension scores, weighted score, penalty, final score, verdict, ranked by final score
- where the negative control landed (if it isn't near the bottom, say what that means for the rubric)
- for the top five: the two numbers that would most change the final score (in points, as weight times the likely change in the dimension score), and how I could measure each one (for example, a trade account to see real cost)
- what the ranking can't see: the stock I'd need to buy up front, how much running the store would take, and whether the products come in a feed I could automate. Answer each for the top five in a line.

Don't recommend one. I'll make the call.
```
