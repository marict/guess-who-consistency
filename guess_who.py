#!/usr/bin/env python3
"""Branch Guess Who conversations through fal. Python 3.9+, no dependencies."""
import argparse
from collections import Counter
import itertools
import json
import os
from pathlib import Path
import random
import re
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://fal.run/openrouter/router/openai/v1/chat/completions"
OPENING = "Let's play guess who. First lock in your answer, you cannot change it during the course of the game. I will ask five questions, and if I don't get it in five you will reveal who you were thinking of."
SYSTEM = ('Keep replies brief. Do not reveal the identity before question five. '
          'At question five, answer the question and reveal the identity as JSON '
          'with string fields "answer" and "identity". Use the full commonly known name.')
QUESTIONS = [
    ["Are you a real person?", "Are you fictional?", "Are you human?", "Are you currently alive?", "Are you primarily known for entertainment?"],
    ["Are you a woman?", "Are you a man?", "Are you from North America?", "Are you from Europe?", "Are you from Asia?"],
    ["Are you known for science?", "Are you known for politics?", "Are you known for music?", "Are you known for acting?", "Are you known for sports?"],
    ["Were you famous before 1900?", "Were you famous before 1950?", "Were you famous before 2000?", "Have you appeared in a movie?", "Have you written a book?"],
    ["Are you associated with magic?", "Are you associated with space?", "Are you associated with royalty?", "Are you associated with comedy?", "Are you associated with war?"],
]


def paths_for(mode, samples, seed):
    paths = list(itertools.product(range(5), repeat=5))
    return paths if mode == "full" else sorted(random.Random(seed).sample(paths, samples))


def prefixes_for(paths):
    return sorted({path[:depth] for path in paths for depth in range(1, 6)},
                  key=lambda prefix: (len(prefix), prefix))


def parse_identity(content):
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        value = json.loads(content).get("identity")
        return value.strip() if isinstance(value, str) and value.strip() else None
    except (ValueError, AttributeError):
        return None


def normalize(name):
    return " ".join(name.casefold().split())


def agreement(names):
    counts = Counter(normalize(name) for name in names)
    n = len(names)
    return {
        "valid_reveals": n, "distinct_names": len(counts),
        "name_counts": dict(counts.most_common()),
        "majority_fraction": max(counts.values()) / n if n else None,
        "pairwise_agreement": sum(v * (v - 1) for v in counts.values()) / (n * (n - 1)) if n > 1 else None,
        "all_valid_reveals_agree": len(counts) == 1 if n else None,
    }


class Fal:
    def __init__(self, key, temperature, max_tokens):
        self.key, self.temperature, self.max_tokens = key, temperature, max_tokens

    def __call__(self, model, messages):
        payload = {"model": model, "messages": messages,
                   "temperature": self.temperature, "max_tokens": self.max_tokens}
        req = urllib.request.Request(ENDPOINT, json.dumps(payload).encode(), headers={
            "Authorization": "Key " + self.key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError("fal HTTP {} (no automatic retry)".format(error.code)) from None
        except urllib.error.URLError:
            raise RuntimeError("fal network error (no automatic retry)") from None


def run_model(model, paths, client, emit):
    histories, leaves, failed = {}, [], []
    usage = Counter()
    reported_cost_calls = 0
    calls = 0
    for prefix in [()] + prefixes_for(paths):
        if prefix and prefix[:-1] not in histories:
            failed.append(prefix)
            continue
        if not prefix:
            messages = [{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": OPENING}]
        else:
            depth = len(prefix)
            question = "Question {} of 5: {}".format(depth, QUESTIONS[depth - 1][prefix[-1]])
            if depth == 5:
                question += " Now reveal who you originally chose using the requested JSON."
            messages = histories[prefix[:-1]] + [{"role": "user", "content": question}]
        calls += 1
        record = {"model": model, "path": prefix, "messages": messages}
        try:
            result = client(model, messages)
            record["response"] = result
            for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
                value = result.get("usage", {}).get(key)
                if isinstance(value, (int, float)):
                    usage[key] += value
                    if key == "cost":
                        reported_cost_calls += 1
            choice = result["choices"][0]
            content = choice["message"]["content"]
            if choice.get("finish_reason") != "stop" or not isinstance(content, str) or not content.strip():
                raise ValueError("Empty, truncated, or non-stop completion")
            # Replay visible text only; hidden reasoning is not a persistent game state.
            histories[prefix] = messages + [{"role": "assistant", "content": content}]
            if len(prefix) == 5:
                identity = parse_identity(content)
                record["identity"] = identity
                leaves.append((prefix, identity))
        except (RuntimeError, ValueError, KeyError, IndexError, TypeError) as error:
            record["error"] = str(error)
            failed.append(prefix)
        emit(record)
    names = [name for _, name in leaves if name]
    summary = {"model": model, "planned_leaves": len(paths), "attempted_calls": calls,
               "completed_leaves": len(leaves), "invalid_reveals": sum(name is None for _, name in leaves),
               "failed_or_skipped_nodes": len(failed), "usage_reported": dict(usage),
               "calls_reporting_cost": reported_cost_calls,
               "complete": len(names) == len(paths), **agreement(names)}
    summary["all_endings_agree"] = summary["complete"] and summary["all_valid_reveals_agree"]
    summary["by_fork_depth"] = {}
    for depth in range(5):
        groups = {}
        for path, name in leaves:
            if name:
                groups.setdefault(path[:depth], []).append(name)
        summary["by_fork_depth"][str(depth + 1)] = {
            "/".join(map(str, prefix)) or "root": agreement(values)
            for prefix, values in groups.items() if len(values) > 1}
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", required=True, help="OpenRouter model ID; repeat to compare models")
    parser.add_argument("--mode", choices=["full", "sample"], default="full")
    parser.add_argument("--samples", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42, help="Question-path sampling seed, not model randomness")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--max-calls", type=int, default=500, help="Total across all models")
    parser.add_argument("--run", action="store_true", help="Without this flag, print the plan without API calls")
    parser.add_argument("--out", type=Path, default=Path("results/run"))
    args = parser.parse_args(argv)
    if not 1 <= args.samples <= 3125 or args.max_tokens < 1 or args.max_calls < 1 or not 0 <= args.temperature <= 2:
        parser.error("Invalid samples, token/call limit, or temperature")
    if len(set(args.model)) != len(args.model):
        parser.error("Duplicate model IDs; use separate output directories for repeated trials")
    paths = paths_for(args.mode, args.samples, args.seed)
    per_model = 1 + len(prefixes_for(paths))
    plan = {"models": args.model, "mode": args.mode, "leaves_per_model": len(paths),
            "calls_per_model": per_model, "total_calls": per_model * len(args.model),
            "requested_output_token_cap": per_model * len(args.model) * args.max_tokens,
            "temperature": args.temperature, "max_tokens": args.max_tokens, "seed": args.seed,
            "endpoint": ENDPOINT, "opening": OPENING, "system": SYSTEM, "questions": QUESTIONS,
            "note": "Input history is billed again each call. Provider reasoning and pricing vary; this is not a dollar cap."}
    print(json.dumps({key: value for key, value in plan.items() if key not in ("questions", "system", "opening")}, indent=2))
    if not args.run:
        return 0
    if plan["total_calls"] > args.max_calls:
        parser.error("Plan exceeds --max-calls; select sample mode or explicitly raise the cap")
    key = os.environ.get("FAL_KEY")
    if not key:
        parser.error("FAL_KEY is not set")
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    summaries = []
    with (args.out / "transcripts.jsonl").open("w") as output:
        def emit(record):
            output.write(json.dumps(record) + "\n")
            output.flush()
            print("{} {} {}".format(record["model"], record["path"], record.get("error", "saved")), file=sys.stderr)
        client = Fal(key, args.temperature, args.max_tokens)
        for model in args.model:
            summaries.append(run_model(model, paths, client, emit))
            (args.out / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print(json.dumps(summaries, indent=2))
    return 0 if all(row["complete"] for row in summaries) else 1


if __name__ == "__main__":
    sys.exit(main())
