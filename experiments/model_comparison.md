# Model Comparison Experiments

Use **option 4 (Compare all providers)** in the app to send the *exact same prompt* to every provider, then record what you see here.

The goal is **not** to find "the best model". It's to learn that the right model depends on the task, the quality you need, speed, cost, and reliability.

---

## How to score

Rate each response from **1 (poor)** to **5 (excellent)**:

| Criterion | Ask yourself |
|---|---|
| **Accuracy** | Are the facts, code, or answer correct? |
| **Relevance** | Does it answer what was actually asked, without going off-topic? |
| **Completeness** | Does it cover everything the prompt asked for? |
| **Clarity** | Is it easy to read and well organized? |

**Response time** and **token counts** come from the app's output (the summary table at the end of a comparison).

**Cost:** The API doesn't return a price. If you want to estimate it, look up each model's current per-token price on the provider's pricing page and calculate:
`(input_tokens × input price) + (output_tokens × output price)`. Otherwise write "n/a".

**Tips for a fair test**
- Copy and paste the prompt exactly. Don't reword it for one provider.
- Write down the exact model names from your `.env`.
- Run each prompt 2–3 times if you can. LLM outputs vary between runs.
- Write down the date. Models get updated.

---

## Experiment details

- **Date:**
- **OpenAI model:**
- **Gemini model:**
- **Claude model:**

---

## Task 1: General explanation

**Prompt:**
```
Explain how APIs work using a real-world example. Keep it under 200 words and suitable for a beginner.
```

| Provider | Model | Accuracy | Relevance | Completeness | Clarity | Time (s) | In tokens | Out tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|
| OpenAI | | | | | | | | | |
| Gemini | | | | | | | | | |
| Claude | | | | | | | | | |

**Responses (paste or summarize):**
- OpenAI:
- Gemini:
- Claude:

**Observations:**
- Did each model respect the 200-word limit?
- Which example was the easiest to understand, and why?

---

## Task 2: Summarization

**Prompt:**
```
Summarize the following text in exactly 3 bullet points:

Remote work has grown significantly since 2020. Many companies found that productivity stayed stable or even improved when employees worked from home. However, some managers reported challenges with team communication and onboarding new staff. Employees often cite flexibility and saved commuting time as the biggest benefits, while loneliness and blurred work-life boundaries are common complaints. As a result, many organizations now use a hybrid model, with employees in the office two or three days a week.
```

| Provider | Model | Accuracy | Relevance | Completeness | Clarity | Time (s) | In tokens | Out tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|
| OpenAI | | | | | | | | | |
| Gemini | | | | | | | | | |
| Claude | | | | | | | | | |

**Responses (paste or summarize):**
- OpenAI:
- Gemini:
- Claude:

**Observations:**
- Exactly 3 bullets? Any information added that wasn't in the text?

---

## Task 3: Information extraction

**Prompt:**
```
Extract the following fields from the text below and return them as JSON with the keys: name, company, email, meeting_date, topic.

"Hi, this is Sara Malik from BrightPath Logistics. I'd like to schedule a call on March 14th to discuss your warehouse tracking software. You can reach me at sara.malik@brightpath.example."
```

| Provider | Model | Accuracy | Relevance | Completeness | Clarity | Time (s) | In tokens | Out tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|
| OpenAI | | | | | | | | | |
| Gemini | | | | | | | | | |
| Claude | | | | | | | | | |

**Responses (paste or summarize):**
- OpenAI:
- Gemini:
- Claude:

**Observations:**
- Was the output valid JSON? Did any model add extra text around it?

---

## Task 4: Classification

**Prompt:**
```
Classify each customer message as Positive, Negative, or Neutral. Reply with only the number and the label, one per line.

1. "The delivery arrived two days early, great service!"
2. "I've been waiting on hold for 40 minutes."
3. "Can you tell me your opening hours?"
4. "The product is fine, but the packaging was damaged."
```

| Provider | Model | Accuracy | Relevance | Completeness | Clarity | Time (s) | In tokens | Out tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|
| OpenAI | | | | | | | | | |
| Gemini | | | | | | | | | |
| Claude | | | | | | | | | |

**Responses (paste or summarize):**
- OpenAI:
- Gemini:
- Claude:

**Observations:**
- How did each model handle the mixed message (#4)? Did they follow the "only number and label" format?

---

## Task 5: Coding

**Prompt:**
```
Write a Python function called is_palindrome(text) that returns True if the text is a palindrome, ignoring spaces, punctuation and capitalization. Include 3 example calls.
```

| Provider | Model | Accuracy | Relevance | Completeness | Clarity | Time (s) | In tokens | Out tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|
| OpenAI | | | | | | | | | |
| Gemini | | | | | | | | | |
| Claude | | | | | | | | | |

**Responses (paste or summarize):**
- OpenAI:
- Gemini:
- Claude:

**Observations:**
- Run the code yourself. Does it actually work? Test "A man, a plan, a canal: Panama".

---

## Task 6: Reasoning / problem solving

**Prompt:**
```
A shop sells pens for $3 each or a pack of 4 for $10. I need 11 pens. What is the cheapest way to buy them and how much will it cost? Show your reasoning step by step.
```

| Provider | Model | Accuracy | Relevance | Completeness | Clarity | Time (s) | In tokens | Out tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|
| OpenAI | | | | | | | | | |
| Gemini | | | | | | | | | |
| Claude | | | | | | | | | |

**Responses (paste or summarize):**
- OpenAI:
- Gemini:
- Claude:

**Observations:**
- Correct answer: 2 packs (8 pens, $20) + 3 single pens ($9) = **$29**. (Buying 3 packs = 12 pens for $30 costs more.) Did each model get it right?

---

## Overall conclusions

Answer these after all six tasks:

1. Did one provider do well on some tasks but not others?
2. Which provider was fastest on average? Was the fastest also the most accurate?
3. Which provider used the most output tokens? Was the extra length useful, or just padding?
4. For a real app that does mostly *one* of these tasks, which model would you choose, and why (think about quality, speed, and cost)?
5. Did any provider fail or hit errors during testing? How would that affect reliability in production?
