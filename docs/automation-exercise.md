# Automation Developer Exercise

## Goal

Implement an end-to-end scenario on a sample e-commerce site (eBay) covering:

- Product search with price filtering
- Adding items to cart
- Verifying cart total

Demonstrate clean architecture: Page Object Model, OOP, Data-Driven.

## Time Frame

3–4 hours net implementation + 20–30 min for walkthrough/demo.

---

## General Requirements

- **Framework:** Playwright
- **Language:** Python
- **Reports:** Allure Reports / Extent Reports / Report Portal
- OOP design throughout
- POM (Page Object Model) architecture
- Data-Driven: test inputs loaded from external file (JSON / CSV / YAML)

---

## Project Description

Implement 4 core functions:

1. Authentication (login)
2. Search with price condition
3. `addItemsToCart`
4. `assertCartTotalNotExceeds`

---

### 4.1 Search with Price Condition

**Example signature (TypeScript/Playwright for reference):**

```typescript
// Returns up to N links to items where price <= maxPrice
async function searchItemsByNameUnderPrice(
  query: string,
  maxPrice: number,
  limit = 5,
): Promise<string[]>;
```

**Behavior:**

- Search by `query`
- If the page has a price filter (min/max), use it to narrow results
- Use XPath to extract the first `limit` items whose price is <= `maxPrice`
- **Edge case - fewer than 5 items on current page:**
  - If pagination exists ("Next" button or page navigation), go to the next page and keep collecting until reaching 5 or pages run out
  - If no pagination, return however many items were found (even 0 is valid)
- **Return:** array of URLs (up to 5 results meeting the price condition)
- If fewer found, return what's available (0 is acceptable)

**Usage example:**

```typescript
const urls = await searchItemsByNameUnderPrice("shoes", 220, 5);
```

---

### 4.2 Add Items to Cart

**Signature:**

```typescript
async function addItemsToCart(urls: string[]): Promise<void>;
```

**Behavior:**

- Loop over each URL and open the item page
- If variants need to be selected (size / color / quantity), pick random values from available options
- Click "Add to cart"
- Return to the search screen / tab
- Save a screenshot log for each item added

---

### 4.3 Verify Cart Total

**Signature:**

```typescript
async function assertCartTotalNotExceeds(
  budgetPerItem: number,
  itemsCount: number,
): Promise<void>;
```

**Behavior:**

- Open the cart
- Read the subtotal / grand total as displayed on the site
- Calculate threshold: `budgetPerItem * itemsCount`
- Assert that the total does not exceed the threshold
- Save a Screenshot / Trace of the cart page

---

### Full Scenario Example

```typescript
// Step 1 - get up to 5 links
const urls = await searchItemsByNameUnderPrice("shoes", 220, 5);

// Step 2 - add all to cart
await addItemsToCart(urls);

// Step 3 - assert cart total <= 220 * number of items
await assertCartTotalNotExceeds(220, urls.length);
```

---

## Bug Exercise (20 minutes)

A team member used an AI tool to write test code, but it isn't working as expected and they've come to you for help.

Review the code with **static analysis only** (no tools, no running the code), identify the issues, and propose fixes.

**Task:**

- Write findings in a file called `ReadMeAIBugs`
- Identify **at least 3 bugs**
- Explain each bug in detail
- Propose a fix for each problematic code section

---

## Submission

- Link to GitHub repo (with access to the repository)
- `README` containing:
  - How to run (commands, prerequisites)
  - Brief architecture explanation
  - Limitations / assumptions (e.g. Login Stub / Guest mode, currency)
- Run report (Allure / HTML / JUnit XML)

---

## Evaluation Criteria

| Area                                                                                         | Weight |
| -------------------------------------------------------------------------------------------- | ------ |
| Architecture & code quality (POM, OOP, SRP, Utils)                                           | 45%    |
| Robustness & smart locators (dynamic handling, variant selection, pagination, price parsing) | 35%    |
| Data-Driven (config, ENV, profiles)                                                          | 15%    |
| Reports & documentation (clear README, reports, screenshots)                                 | 15%    |
