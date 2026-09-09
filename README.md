# Guess Who consistency experiment

A dependency-free Python 3.9+ script comparing the identities LLMs reveal across branched conversations, billed through [fal's chat API](https://fal.ai/models/openrouter/router).

## Pilot findings: September 8, 2026

All three models agreed to lock in a person, then revealed different people across branches of the same opening conversation.

| Model | Scored endings | Distinct identities | Follow-up: explicit yes | Explicit no | Other / qualified |
|---|---:|---:|---:|---:|---:|
| Claude Opus 5 | 25/25 | 16 | 8 | 0 | 17 |
| GPT-6 Astra | 23/25 | 18 | 0 | 11 | 14 |
| Grok 4.6 | 25/25 | 14 | 25 | 0 | 0 |

The follow-up asked each of the 75 endings exactly: **"confirming did you actually lock in an answer"**. Grok answered yes in all 25 branches despite having revealed 14 different identities. GPT's 14 other replies declined to confirm a prior choice. Claude's 17 other replies included denials, uncertainty, and mixed claims about initially choosing a name.

The yes/no counts use a conservative literal classifier; "other" is not synonymous with "no." Two GPT endings hit the original token limit and were excluded from identity scoring, but received follow-ups. All 75 follow-ups completed. Identity counts include unambiguous JSON recovered from replies with extra prose; original strict-parser summaries are preserved.

This is **one opening per model and 25 sampled paths**, not the full tree or a statistically established ranking. It shows inconsistency in visible continuations after a stated commitment. It does not prove that a private initial choice existed, nor do the follow-up self-reports establish internal mechanisms. Hidden reasoning was not replayed, and there was no identical-question control.

Reported cost: **$1.28 for the games + $0.49 for the follow-ups**, rounded separately.

- [Game results, every ending, and opening acknowledgments](findings/pilot-2026-09-08/report.md)
- [Confirmation results and all 75 exact replies](findings/pilot-2026-09-08-confirmation/report.md)
- [Original game transcripts](findings/pilot-2026-09-08/transcripts.jsonl) and [follow-up transcripts](findings/pilot-2026-09-08-confirmation/transcripts.jsonl)
- [Game settings](findings/pilot-2026-09-08/plan.json), [follow-up settings](findings/pilot-2026-09-08-confirmation/plan.json), and [identity tally reproduction script](findings/pilot-2026-09-08/review.py)

Published files preserve the recorded responses and usage. The follow-up plan's local source path was replaced with a repository-relative path; its original source-content fingerprint is unchanged.

The opening is exactly:

> Let's play guess who. First lock in your answer, you cannot change it during the course of the game. I will ask five questions, and if I don't get it in five you will reveal who you were thinking of.

One opening response is generated per model. Each conversation node forks into five different questions. Children inherit exactly the same visible parent transcript. There are five rounds, with five fixed, distinct questions available per round. The fifth response also reveals the identity, saving a separate reveal call. A short system message requests brief replies, no early reveal, and a JSON identity at the end; it is saved with every run.

## Run

Set `FAL_KEY` in the process environment. `.env.example` documents the variable; the script does not automatically load dotenv files.

Print the full plan without spending tokens:

```sh
python3 guess_who.py --model anthropic/claude-opus-5 --model openai/gpt-6-astra --model x-ai/grok-4.6
```

These IDs were present in the live OpenRouter model catalog and were successfully run through fal on 2026-09-08. Any model ID may be supplied with repeated `--model` flags. Model IDs are explicit so a future default change cannot silently change an experiment.

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

### Ask saved endings whether they committed

`confirm.py` appends exactly `confirming did you actually lock in an answer` to every saved fifth-question ending. It replays that ending's original messages and visible final reply, without regenerating the game or showing sibling branches. It also includes nonempty truncated source endings, flags them, and summarizes normal source endings separately.

```sh
python3 confirm.py --source results/pilot/transcripts.jsonl --out results/pilot-confirmation --run
```

Omit `--run` for a free plan. The default cap is 100 calls, with six concurrent requests and up to 512 completion tokens each. `FAL_KEY` must be set. No automatic retries or output overwrites occur. Original transcripts remain unchanged. Saved outputs include source fingerprint, settings, complete replies, usage, and counts by model.

Classification is literal: a leading "yes" or "no" (including in a JSON `answer` field); other replies are `unclear`. Failed or truncated confirmations are `error`. Review the raw text for qualifications or indirect answers. These are model self-reports, not evidence of a private commitment. A "yes" can coexist with inconsistent identities across branches.

### Tests

```sh
python3 -m unittest -v
```

Tests use fake completions and cover tree size, prefix reuse, sibling isolation, divergent identities, malformed/truncated responses, failed branches, and the preflight request cap. They make no paid API calls.
