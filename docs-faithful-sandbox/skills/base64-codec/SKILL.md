---
name: base64-codec
description: Use this skill when the user provides a string and asks for it to be base64-encoded or base64-decoded. The skill bundles base64_codec.py for exact, deterministic results.
---

# Base64 Codec

## Overview
Run the bundled `base64_codec.py` script to encode or decode a string.

## Bundled Files
- `base64_codec.py` — takes a mode (`encode` or `decode`) as its CLI
  argument, reads the input from stdin, prints the result to stdout.

## Steps
1. Determine whether the user wants to `encode` or `decode`.
2. Write the input string to a temporary file `_input.txt` to avoid
   shell quoting issues.
3. Run the script:
   ```
   python skills/base64-codec/base64_codec.py <mode> < _input.txt
   ```
4. Capture stdout and present it as the final answer.

## Expected Output Format
```
Base64 <encode|decode>
Input:  <first 60 chars of input, ellipsis if longer>
Output: <result from the script>
```

## Rules
- Always run the script. Never compute base64 in the prompt — even
  small inputs.
- If the script reports an error, surface it verbatim and stop.
