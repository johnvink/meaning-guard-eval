# Meaning guard eval

A small regression set for dictation cleanup, and the checks Juleep runs before anything is typed. The claim it supports: **an AI tidying up dictated text must not drop a negation, change a number, alter a code token or a dictionary word, or lose a self-correction.** Small local models do all of these sometimes. This repo lets anyone measure how often, for any model.

Juleep is a Mac dictation app (https://juleep.com) whose cleanup runs on the Mac with Qwen3 4B or 1.7B. The guard is written in code, not in the prompt: after the model replies, the reply is compared with the raw transcript, and a failing reply is retried once with a hint naming the problem, then replaced by the raw text. This repo holds the cases, the rules in prose, a reference checker and the results for the models Juleep ships.

## What is here

- `cases.jsonl`: 30 cases. Each line is `{"raw", "level", "must_keep", "must_not_contain", "note"}` and, on two, `"known"` (a documented weakness of the shipped model, not counted as a failure).
- `rules.md`: the guard's rules in prose, close to the Rust source.
- `check.py`: a reference checker in plain Python (no dependencies). It applies the per-case expectations plus the generic rules (negations, numbers, code tokens, format, rewrite limit).
- `run.py`: runs the cases through any OpenAI-compatible local server (llama-server, LM Studio, Ollama with the OpenAI endpoint) with Juleep's cleanup prompt, then checks them.
- `results-qwen3-4b.txt` and `outputs-qwen3-4b.jsonl`: the shipped model's run, from the app's own eval harness on 2026-11-06 (`check.py cases.jsonl outputs-qwen3-4b.jsonl` reproduces the verdicts).

## Results so far

| Model | Clean | Pass on retry | Held (raw text typed) | Known weaknesses |
|---|---|---|---|---|
| Qwen3 4B (Q4_K_M, llama.cpp) | 26 / 30 | 2 | 2 | keeps the first day in "Thursday, no, Friday"; answers a sentence about JSON *in* JSON (caught by the format rule) |
| Qwen3 1.7B (Q4_K_M) | fewer | | | the two above, plus two more self-corrections where both versions were kept (held, raw text typed); full log to be added |

`outputs-qwen3-4b.jsonl` holds the *final* text per case, after the retry or the fall-back to raw words, which is why `check.py` passes 29 of them; `results-qwen3-4b.txt` shows the first replies that were rejected and why.

"Held" means the guard rejected both attempts and the app typed the raw words with a reason in History. Every held case is a sentence a person would still understand; nothing silently changed meaning.

## Run it against another model

Start a local server that speaks the OpenAI chat API, for example:

```sh
llama-server -m your-model.gguf --port 8080
```

Then:

```sh
python3 run.py --url http://localhost:8080/v1 --model your-model --out outputs.jsonl
python3 check.py cases.jsonl outputs.jsonl
```

`run.py` sends each case with Juleep's cleanup prompt for its `level` (light or polished), with fillers removed and corrections kept, and the two example lines the app uses. `check.py` prints one line per case and the totals. To check outputs you produced some other way, write them as JSONL lines `{"raw": ..., "clean": ...}` and run `check.py` on them.

## Adding a case

One JSON line. `must_keep` are substrings that must appear in the cleaned text (case-insensitive); `must_not_contain` are substrings that must not. Keep each case to one thing being tested and say what it is in `note`. Cases that need a dictionary word list `"words"` (see `cases.jsonl` for the shape). Send a pull request; cases where a real model got it wrong are the most useful.

## Licence

MIT. The cases contain no personal text.
