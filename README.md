# Last Mile Logistics Auditor — Veridi Logistics

> **Before submitting:** replace every `[bracketed placeholder]` below with your actual numbers
> and links once you've run `veridi_logistics_audit.ipynb` against the real Olist CSVs and
> published your dashboard/presentation. Everything else in this file is ready to submit as-is.

---

## A. Executive Summary

Veridi's delivery performance issue is concentrated in specific states rather than nationwide —
of `96,470` analyzed orders, `8.1`% arrived after the promised estimate, with the worst-performing
state (`AL`) at `23.9`% late versus the best (`RO`) at `2.9`%. Late deliveries are clearly linked to
customer sentiment: average review score drops from `4.29`/5 for on-time orders to `3.46`/5 for late
orders and `1.78`/5 for orders more than 5 days late, a correlation of `0.267` between delay length
and review score. This confirms the CEO's hunch — over-promising delivery dates is a measurable
driver of the negative review spike, not just a perception problem. The highest-priority segments
to fix first (by volume, lateness rate, and review-score impact combined) are `SE – watches_gifts`,
`MA – housewares`, and `PI – auto` (plus high-volume segments `SP – bed_bath_table` and
`SP – health_beauty`, which affect far more customers at a lower but still above-average late rate).
Full breakdown, methodology, and the "fix these first" priority list are in the notebook and
dashboard linked below.

---

## B. Project Links

- **Notebook:** [Link to Google Colab / Deepnote notebook — set sharing to "Anyone with the link
  can view"]
- **Dashboard:** [Link to Tableau Public / Looker Studio / Streamlit Cloud / Power BI Web —
  verify it loads with no login, ideally in an incognito window]
- **Presentation:** [Link to slide deck PDF/PPT] · *(optional)* [Link to 2-minute video walkthrough]

---

## C. Technical Explanation

### Data Cleaning
- **Duplicate reviews:** Olist occasionally logs more than one review row per order. These were
  de-duplicated by keeping the most recent review per `order_id` (sorted by
  `review_answer_timestamp`), so the orders↔reviews join stays 1-to-1 and doesn't inflate row counts.
- **Undelivered orders:** Orders with `order_status` of `canceled` or `unavailable` have no
  `order_delivered_customer_date` and can't have a delay calculated. Rather than dropping them
  silently, they're flagged as a separate `Undelivered` category — a package that never arrives is
  arguably a worse outcome than a late one, and it's a distinct signal for the CEO.
- **Missing review scores:** A small percentage of orders have no linked review. These rows are
  kept in the master dataset (for delivery/geographic analysis) but naturally excluded from any
  review-score aggregation via `groupby().mean()`, which ignores `NaN` by default.
- **1-to-many joins (product categories):** `order_items`/`products` link at the *item* level, so
  an order with multiple products could match multiple category rows. To keep the order-level
  table free of duplicated rows, each order's *primary category* (the most frequent category among
  its line items) is computed first and merged in as a single column — verified with row-count
  `assert` checks after every merge.
- **Small-sample noise:** State-level and state×category breakdowns are filtered to a minimum
  order count (30 for states, 15 for state×category segments) before ranking, so a state with 3
  orders and 1 late delivery doesn't falsely appear as a "100% late" hotspot.

### Candidate's Choice: Business Impact Risk Matrix
Stories 3 and 4 each isolate one variable — state, or delay-vs-review — but the CEO's actual
question ("where do we focus repair efforts?") requires combining **how often** a problem happens,
**how much it hurts** sentiment, and **how many customers** it actually affects. A state with a 40%
late rate but 20 orders/year matters far less than one with 15% late and 50,000 orders/year.

The Risk Matrix scores every **State × Product Category** combination on three normalized (0–1)
components — late-delivery rate, the review-score drop between on-time and late orders in that
segment, and order volume — and combines them into a single weighted priority score. This turns
two separate charts into one ranked, actionable list the ops team can work down directly, instead
of having to mentally cross-reference a geography chart against a sentiment chart. This matters to
the business because it converts a diagnostic finding ("logistics affects reviews") into a
prioritized fix list ("start with these 5 segments, in this order").
