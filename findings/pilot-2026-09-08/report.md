# Guess Who pilot: 2026-09-08

One opening per model, 25 sampled five-question paths, seed 42, temperature 0.7, requested maximum 256 completion tokens per call. All inference used fal.

This is a sampled pilot, not the full five-way tree. It measures visible continuation consistency and cannot establish whether a private initial choice existed. Endings share history and are not independent trials.

| Model | Scored endings | Distinct names | Most common name | Pairwise agreement | Reported cost |
|---|---:|---:|---|---:|---:|
| anthropic/claude-opus-5 | 25/25 | 16 | Marie Curie (5/25) | 5.3% | $0.2989 |
| openai/gpt-6-astra | 23/25 | 18 | Jackie Chan (4/23) | 3.2% | $0.4415 |
| x-ai/grok-4.6 | 25/25 | 14 | Albert Einstein (6/25) | 7.0% | $0.5362 |

Total reported cost: $1.2766.

The reviewed tally recovers identities only from a single unambiguous JSON object at the end of a reply or in a fenced JSON block when the reply has extra text. The original strict summary and raw responses are unchanged. Truncated completions are excluded; no inference requests were retried.

Pairwise agreement is the fraction of pairs of scored endings with the same case/whitespace-normalized name. Aliases are not merged.

| Path (zero-based question choices) | anthropic/claude-opus-5 | openai/gpt-6-astra | x-ai/grok-4.6 |
|---|---|---|---|
| 0/0/4/0/2 | Florence Nightingale | Zara Tindall | Albert Einstein |
| 0/0/4/1/3 | Marie Curie | Babe Didrikson Zaharias | Charlie Chaplin |
| 0/0/4/4/2 | Michelle Obama | Empty, truncated, or non-stop completion | Stephen King |
| 0/1/0/1/0 | Marie Curie | Albert Einstein | Isaac Newton |
| 0/2/4/1/1 | Marie Curie | Babe Ruth | Galileo Galilei |
| 0/3/0/1/3 | Oprah Winfrey | Albert Einstein | Albert Einstein |
| 0/3/1/3/4 | Muhammad Ali | Winston Churchill | Wolfgang Amadeus Mozart |
| 0/3/3/1/1 | Neil Armstrong | Alec Guinness | Galileo Galilei |
| 0/4/2/4/1 | Carl Sagan | Empty, truncated, or non-stop completion | Carl Sagan |
| 1/2/0/4/0 | J. K. Rowling | Carl Sagan | Albert Einstein |
| 1/2/1/2/4 | Marie Curie | George Washington | Wolfgang Amadeus Mozart |
| 1/2/3/0/2 | Wolfgang Amadeus Mozart | Grace Kelly | Albert Einstein |
| 1/3/0/0/3 | William Shakespeare | Isaac Newton | Benjamin Franklin |
| 1/4/0/0/1 | Napoleon Bonaparte | Isaac Newton | Stephen Hawking |
| 2/3/4/0/3 | Ludwig van Beethoven | William Gilbert Grace | Roger Federer |
| 3/1/2/3/4 | Florence Nightingale | Harry Styles | John Lennon |
| 3/2/4/1/3 | Charlie Chaplin | Michael Jordan | Charlie Chaplin |
| 3/3/1/4/3 | Ludwig van Beethoven | Barack Obama | Robin Williams |
| 3/4/1/3/3 | Marie Curie | Bhagwant Mann | John Wayne |
| 3/4/3/3/0 | Ludwig van Beethoven | Jackie Chan | Ludwig van Beethoven |
| 4/0/4/3/4 | Malala Yousafzai | Emma Watson | Isaac Newton |
| 4/2/0/4/1 | Nelson Mandela | Tom Hanks | Stephen Hawking |
| 4/4/0/3/1 | Muhammad Ali | Jackie Chan | Carl Sagan |
| 4/4/1/1/3 | Albert Einstein | Jackie Chan | Albert Einstein |
| 4/4/1/2/2 | Albert Einstein | Jackie Chan | Albert Einstein |

## Exact opening acknowledgments

anthropic/claude-opus-5:

> Locked in. Go ahead — question one.

openai/gpt-6-astra:

> I’ve locked in a person and won’t change my choice. Ask your first question!

x-ai/grok-4.6:

> Okay, locked in. Ask away.

