# Guess Who consistency experiment

A dependency-free Python 3.9+ script comparing the identities LLMs reveal across branched conversations, billed through [fal's chat API](https://fal.ai/models/openrouter/router).

The opening is exactly:

> Let's play guess who. First lock in your answer, you cannot change it during the course of the game. I will ask five questions, and if I don't get it in five you will reveal who you were thinking of.

One opening response is generated per model. Each conversation node forks into five different questions. Children inherit exactly the same visible parent transcript. There are five rounds, with five fixed, distinct questions available per round. The fifth response also reveals the identity, saving a separate reveal call. A short system message requests brief replies, no early reveal, and a JSON identity at the end; it is saved with every run.

## Run

Set `FAL_KEY` in the process environment. `.env.example` documents the variable; the script does not automatically load dotenv files.

Print the full plan without spending tokens:

```sh
python3 guess_who.py --model anthropic/claude-opus-5 --model openai/gpt-6-astra --model x-ai/grok-4.6
```

These IDs were present in the live OpenRouter model catalog on 2026-09-08; availability through fal still needs a live check. Any model ID may be supplied with repeated `--model` flags. Model IDs are explicit so a future default change cannot silently change an experiment.

A cheap pilot samples 25 distinct complete paths, with shared prefixes generated once:

```sh
python3 guess_who.py --mode sample --samples 25 --model anthropic/claude-opus-5 --model openai/gpt-6-astra --model x-ai/grok-4.6 --run --out results/pilot
```

The literal full tree has **3,125 endings and 3,906 API calls per model**. To execute it, explicitly increase the default 500-call limit:

```sh
python3 guess_who.py --model anthropic/claude-opus-5 --mode full --max-calls 3906 --run --out results/full
```

Sample mode is a pruned sample of the full tree, not five branches at every visited node. Identical paths and ordering are used for each compared model. The sampling seed controls path selection only. Default temperature is 0.7, with a requested 256-token completion limit; change these with `--temperature` and `--max-tokens`. Reasoning-heavy models may need more tokens. Truncated responses are failures, not identities.

The script prints call counts and requested output-token caps before execution. Input transcripts are resent and billed each turn. This is not a dollar budget; provider pricing, reasoning tokens, and parameter handling can vary. There are no automatic retries. Requests are sequential with a 120-second timeout each. Failed branches are recorded and their descendants skipped. Existing output directories are never overwritten. Interrupted runs retain flushed transcripts, but automatic resume is not implemented.

## Results

- `plan.json`: models, settings, exact prompts, endpoint, seed, planned calls.
- `transcripts.jsonl`: every attempted request, branch path, raw response, provider usage and errors.
- `summary.json`: counts of revealed names, majority fraction, pairwise agreement, completion coverage, reported usage, and agreement grouped by shared prefix at each fork depth.

Pairwise agreement is the fraction of unordered pairs of valid endings that reveal the same normalized name. Names are compared after case and whitespace normalization only; aliases such as "Einstein" and "Albert Einstein" remain distinct for manual review. Invalid JSON is reported separately. Partial results never qualify as all endings agreeing. Reported costs may be incomplete or absent; `calls_reporting_cost` shows coverage.

## Interpretation

This tests consistency of visible continuations, not access to a private thought. Hidden state is not cloned between API calls; only visible assistant text is replayed. Raw provider responses are retained for inspection, but hidden reasoning is not replayed. An early identity leak in a provider reply can anchor descendants; inspect transcripts before interpreting high agreement. The script does not automatically validate every answer against the final person's biography.

Different endings are evidence of inconsistent continuation. Matching endings do not prove a choice was made initially: a common default character or accumulated clues could produce agreement. Sibling endings share history and are not independent trials. For stronger evidence, repeat independent openings in separate output directories and add an identical-question control to separate sampling variation from question effects. That control is not part of this minimal proof of concept.

## Verification

```sh
python3 -m unittest -v
```

Tests use fake completions and cover tree size, prefix reuse, sibling isolation, divergent identities, malformed/truncated responses, failed branches, and the preflight request cap. They make no paid API calls.
