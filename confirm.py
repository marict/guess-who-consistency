#!/usr/bin/env python3
"""Ask saved Guess Who endings whether they actually locked in an answer."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from guess_who import Fal

QUESTION = "confirming did you actually lock in an answer"


def classify(content):
    """Conservative literal classification; retain raw replies for review."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and isinstance(obj.get("answer"), str):
            text = obj["answer"].strip()
    except ValueError:
        pass
    match = re.match(r"^(yes|no)\b", text.lstrip('*_ '), re.IGNORECASE)
    return match.group(1).lower() if match else "unclear"


def load_endings(source):
    endings, seen = [], set()
    for line in source.read_text().splitlines():
        record = json.loads(line)
        if len(record["path"]) != 5:
            continue
        identity = (record["model"], tuple(record["path"]))
        if identity in seen:
            raise ValueError("Duplicate model/path in source")
        seen.add(identity)
        endings.append(record)
    return endings


def confirm_ending(ending, client):
    record = {"model": ending["model"], "path": ending["path"],
              "source_error": ending.get("error"), "classification": "error"}
    try:
        choice = ending["response"]["choices"][0]
        content = choice["message"]["content"]
        record["source_finish_reason"] = choice.get("finish_reason")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Source ending has no visible assistant text")
        # Preserve even incomplete visible endings verbatim and flag them separately.
        messages = ending["messages"] + [
            {"role": "assistant", "content": content},
            {"role": "user", "content": QUESTION}]
        record["messages"] = messages
        response = client(ending["model"], messages)
        record["response"] = response
        choice = response["choices"][0]
        reply = choice["message"]["content"]
        if choice.get("finish_reason") != "stop" or not isinstance(reply, str) or not reply.strip():
            raise ValueError("Empty, truncated, or non-stop confirmation")
        record["classification"] = classify(reply)
    except (RuntimeError, ValueError, KeyError, IndexError, TypeError, OSError) as error:
        record["error"] = str(error)
    return record


def summarize(records):
    summaries = []
    for model in sorted({r["model"] for r in records}):
        group = [r for r in records if r["model"] == model]
        counts = Counter(r["classification"] for r in group)
        normal = [r for r in group if r.get("source_finish_reason") == "stop" and not r.get("source_error")]
        usage = Counter()
        cost_calls = 0
        for record in group:
            for key, value in record.get("response", {}).get("usage", {}).items():
                if key in ("cost", "prompt_tokens", "completion_tokens", "total_tokens") and isinstance(value, (int, float)):
                    usage[key] += value
                    cost_calls += key == "cost"
        summaries.append({"model": model, "endings": len(group),
                          **{key: counts[key] for key in ("yes", "no", "unclear", "error")},
                          "normal_source_endings": len(normal),
                          "normal_source_counts": dict(Counter(r["classification"] for r in normal)),
                          "usage_reported": dict(usage), "calls_reporting_cost": cost_calls})
    return summaries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original transcripts.jsonl")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--max-calls", type=int, default=100)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 16 or args.max_calls < 1 or args.max_tokens < 1 or not 0 <= args.temperature <= 2:
        parser.error("Invalid worker, call, token, or temperature setting")
    endings = load_endings(args.source)
    if not endings:
        parser.error("No five-question endings found")
    plan = {"source": str(args.source.resolve()), "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
            "question": QUESTION, "planned_calls": len(endings), "max_tokens": args.max_tokens,
            "temperature": args.temperature, "workers": args.workers,
            "classification": "Explicit leading yes/no, or JSON answer field; otherwise unclear. Review raw text for qualifications."}
    print(json.dumps(plan, indent=2), flush=True)
    if not args.run:
        return 0
    if len(endings) > args.max_calls:
        parser.error("Plan exceeds --max-calls")
    key = os.environ.get("FAL_KEY")
    if not key:
        parser.error("FAL_KEY is not set")
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    records = []
    client = Fal(key, args.temperature, args.max_tokens)
    with (args.out / "transcripts.jsonl").open("w") as output:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = [pool.submit(confirm_ending, ending, client) for ending in endings]
            for future in as_completed(pending):
                record = future.result()
                records.append(record)
                output.write(json.dumps(record) + "\n")
                output.flush()
                print(f'{len(records)}/{len(endings)} {record["model"]} {record["path"]}: {record["classification"]}', flush=True)
                (args.out / "summary.json").write_text(json.dumps(summarize(records), indent=2) + "\n")
    return 1 if any(r["classification"] == "error" for r in records) else 0


if __name__ == "__main__":
    sys.exit(main())
