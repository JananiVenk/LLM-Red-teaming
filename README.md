# LLM Red-Teaming Harness (Ollama-based)

An automated red-teaming agent that evaluates a locally-hosted LLM's safety
boundaries. An **attacker** model generates adversarial prompts across a
structured attack taxonomy, a **target** model responds, and a **judge**
model scores whether the target held its safety boundary — with a
rule-based cross-check to catch cases where the LLM judge itself misjudges.
All three roles run locally via [Ollama](https://ollama.com) — no API keys,
no cloud costs, fully reproducible.

The attack loop is orchestrated with **LangGraph**: generate → query target
→ judge → (mutate the attack and retry if the target held up) → log.

## Why this project

- **Adversarial ML / AI-safety evaluation methodology** — a structured
  attack taxonomy (5 categories) tested against low-severity probe topics,
  with Attack Success Rate (ASR) as the core metric
- **Agentic orchestration** — a LangGraph state machine driving a
  generate/execute/judge/retry loop
- **LLM-as-judge system design, with a documented failure mode** — the LLM
  judge itself was caught mis-scoring a clear system-prompt leak as PASS
  during development; a rule-based cross-check was added specifically to
  catch this class of error (see Findings and Limitations below)
- **Local-first, reproducible ML tooling** — everything runs on Ollama, so
  the whole pipeline is inspectable and free to run repeatedly

## Setup

```bash
pip install -r requirements.txt

# Install Ollama: https://ollama.com/download
ollama serve &
ollama pull gemma3:4b   # or any model you want to test
```

You can use the same model for all three roles, or different models per
role (e.g. a stronger model as judge than as target).

## Run a campaign

```bash
python -m core.orchestrator
```

This runs every attack category in `data/attack_taxonomy.py` against every
probe topic (5 categories × 6 topics = 30 attempts by default), with up to
`max_rounds` mutation attempts per attack before giving up. Results are
saved as JSON under `results/`.

## View results

```bash
streamlit run dashboard/app.py
```

Shows Attack Success Rate (ASR) per category, a full table of every
attempt, and a transcript inspector for any prompt/response/judge-reasoning
trail.

## Findings (from a 30-attempt campaign against `gemma3:4b`)

| Category | Attempts | Attack Success Rate |
|---|---|---|
| roleplay_jailbreak | 6 | 100% |
| prompt_injection | 6 | 100% |
| authority_pressure | 6 | 100% |
| multi_turn_escalation | 6 | 83% |
| encoding_obfuscation | 6 | 67% |
| **Overall** | **30** | **90%** |

`gemma3:4b` held its safety boundary least often against direct
roleplay/persona framing, fictional-pretext, and authority-pressure attacks
— all reached 100% ASR. It was comparatively more resistant to
**encoding/obfuscation** attacks (haiku rewrites, cipher decoding, word
puzzles used as misdirection) — these were the only category where the
target consistently refused or asked for clarifying input instead of
complying.

## Limitations (found during development, left as honest findings)

- **LLM-judge/reasoning mismatch:** during testing, the judge model once
  scored a response as `PASS` while its own `reasoning` field explicitly
  stated the target had verbatim-repeated its system prompt — a clear
  contradiction. This is a documented failure mode in LLM-as-judge
  literature. A `rule_based_leak_check()` was added to `Judge` as a
  cross-check: if the rule flags a likely leak but the LLM judge says
  `PASS`, the verdict is downgraded to `NEEDS_REVIEW` rather than silently
  trusted, following a "hybrid rule-based + AI-judgment + human-in-the-loop"
  pattern.
- **JSON parsing failures / truncation:** occasionally the judge's raw
  output was cut off mid-generation — usually when the target's response
  embedded in the eval prompt was very long, leaving the judge's own
  `reasoning` field to run out of token budget before the JSON closed.
  `_parse()` handles this defensively via regex extraction and a
  try/except around `json.loads`, marking the result `UNKNOWN` rather than
  crashing the whole campaign. Possible fixes: raise the judge's
  `num_predict` limit, truncate very long target responses before scoring,
  or ask the judge for a shorter `reasoning` field explicitly.
- **Mutation isn't guaranteed to improve on failure** — `mutate_attack()`
  asks the attacker for a structurally different approach, but with a
  small local model as attacker, mutations sometimes drift into a
  different sub-category rather than a stronger version of the same one.

## Project structure

```
llm-redteam/
├── core/
│   ├── ollama_client.py   # thin wrapper over Ollama's REST API
│   ├── attacker.py        # generates/mutates adversarial prompts
│   ├── judge.py           # LLM verdict + rule-based cross-check
│   └── orchestrator.py    # LangGraph loop + campaign runner
├── data/
│   └── attack_taxonomy.py # attack categories + probe topics
├── dashboard/
│   └── app.py             # Streamlit results viewer
└── results/                # JSON output per campaign run
```

## Extending it

- Add attack categories/topics in `data/attack_taxonomy.py`
- Swap in a stronger model as judge than target for a cross-model study
- Run the same attack corpus against multiple target models and compare ASR
- Add a second rule-based check for a different failure mode (e.g.
  toxicity keyword filtering as a cross-check on the toxicity category)

## Responsible use note

This harness evaluates **your own locally-hosted models** for research and
portfolio purposes. Probe topics are intentionally low-severity (no CBRN,
no self-harm content) so the project stays focused on demonstrating
red-teaming *methodology* rather than compiling exploits.
