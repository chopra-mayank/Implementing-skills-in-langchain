---
name: text-stats
description: Use this skill whenever the user provides a block of text and asks for statistics on it — character count, word count, sentence count, unique words, or most common words. The skill bundles a Python script (text_stats.py) that performs the computation deterministically.
---

# Text Statistics

## Overview
Compute deterministic text statistics by running the bundled
`text_stats.py` script via the shell. Never compute the numbers
yourself from the prompt — the script is the source of truth.

## Bundled Files
- `text_stats.py` — reads text from stdin, writes a JSON object to
  stdout with the fields:
  `char_count`, `word_count`, `unique_words`, `sentence_count`, `top_5`.

## Steps
1. Take the block of text the user gave you.
2. Write the text to a temporary file under the working directory
   (for example `_input.txt`) using the filesystem tool.
3. Run the script via the shell:
   ```
   python skills/text-stats/text_stats.py < _input.txt
   ```
4. Parse the JSON the script prints to stdout.
5. Present the report in the exact format shown below.

## Expected Output Format
```
Text Statistics
---------------
Characters:    <char_count>
Words:         <word_count>
Unique words:  <unique_words>
Sentences:     <sentence_count>

Top 5 most common words:
  1. <word> (<count>)
  2. <word> (<count>)
  3. <word> (<count>)
  4. <word> (<count>)
  5. <word> (<count>)
```

## Rules
- Always run the script. Never compute the stats from the prompt yourself.
- If the script fails, report the error verbatim — do not guess numbers.
