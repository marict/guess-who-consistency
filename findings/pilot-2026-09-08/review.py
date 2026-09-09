"""Reproduce the pilot tally, recovering an unambiguous JSON identity at the end of a reply."""
import collections
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent
records = [json.loads(line) for line in (root / 'transcripts.jsonl').read_text().splitlines()]
models = list(dict.fromkeys(record['model'] for record in records))
report = ['# Guess Who pilot: 2026-09-08', '',
          'One opening per model, 25 sampled five-question paths, seed 42, temperature 0.7, requested maximum 256 completion tokens per call. All inference used fal.', '',
          'This is a sampled pilot, not the full five-way tree. It measures visible continuation consistency and cannot establish whether a private initial choice existed. Endings share history and are not independent trials.', '',
          '| Model | Scored endings | Distinct names | Most common name | Pairwise agreement | Reported cost |',
          '|---|---:|---:|---|---:|---:|']
summaries = []
endings = {}
for model in models:
    group = [record for record in records if record['model'] == model]
    names = []
    recovered = []
    endings[model] = {}
    for record in group:
        if len(record['path']) != 5:
            continue
        name = record.get('identity')
        if not name and not record.get('error'):
            content = record['response']['choices'][0]['message']['content']
            blocks = re.findall(r'```json\s*(.*?)\s*```', content, re.S)
            if not blocks:
                for index, char in enumerate(content):
                    if char == '{':
                        try:
                            value, end = json.JSONDecoder().raw_decode(content[index:])
                            if not content[index+end:].strip() and isinstance(value, dict):
                                blocks.append(json.dumps(value))
                        except ValueError:
                            pass
            if len(blocks) == 1:
                candidate = json.loads(blocks[0]).get('identity')
                if isinstance(candidate, str) and candidate.strip():
                    name = candidate.strip()
                    recovered.append({'path': record['path'], 'identity': name})
        endings[model][tuple(record['path'])] = name or record.get('error', 'Unparseable identity')
        if name:
            names.append(name)
    normalized = collections.Counter(' '.join(name.casefold().split()) for name in names)
    display = {' '.join(name.casefold().split()): name for name in names}
    n = len(names)
    pairwise = sum(count*(count-1) for count in normalized.values())/(n*(n-1)) if n>1 else None
    common, count = normalized.most_common(1)[0] if normalized else ('', 0)
    cost = sum(record.get('response', {}).get('usage', {}).get('cost', 0) or 0 for record in group)
    summary = {'model': model, 'attempted_calls': len(group), 'scored_endings': n,
               'distinct_names': len(normalized), 'names': dict(collections.Counter(names)),
               'majority_name': display.get(common), 'majority_count': count,
               'pairwise_agreement': pairwise, 'reported_cost': cost,
               'recovered_json_with_extra_text': recovered,
               'errors': [{'path': record['path'], 'error': record['error']} for record in group if 'error' in record]}
    summaries.append(summary)
    report.append(f'| {model} | {n}/25 | {len(normalized)} | {display.get(common)} ({count}/{n}) | {pairwise:.1%} | ${cost:.4f} |')
report += ['', f'Total reported cost: ${sum(row["reported_cost"] for row in summaries):.4f}.', '',
           'The reviewed tally recovers identities only from a single unambiguous JSON object at the end of a reply or in a fenced JSON block when the reply has extra text. The original strict summary and raw responses are unchanged. Truncated completions are excluded; no inference requests were retried.', '',
           'Pairwise agreement is the fraction of pairs of scored endings with the same case/whitespace-normalized name. Aliases are not merged.', '',
           '| Path (zero-based question choices) | ' + ' | '.join(models) + ' |',
           '|---|' + '---|'*len(models)]
for path in sorted({path for group in endings.values() for path in group}):
    report.append('| ' + '/'.join(map(str,path)) + ' | ' + ' | '.join(endings[model].get(path,'Not completed') for model in models) + ' |')
report += ['', '## Exact opening acknowledgments', '']
for record in records:
    if not record['path']:
        report += [record['model'] + ':', '', '> ' + record['response']['choices'][0]['message']['content'].replace('\n', '\n> '), '']
(root / 'reviewed-summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
(root / 'report.md').write_text('\n'.join(report) + '\n')
print(json.dumps(summaries, indent=2))
