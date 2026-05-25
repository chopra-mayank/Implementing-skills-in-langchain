---
name: markdown-formatter
description: Use this skill when the user provides raw, unformatted text (meeting notes, transcripts, brain dumps, free-form summaries) and asks for it to be cleaned up as a well-structured Markdown document with headings, bullet lists, and short paragraphs.
---

# Markdown Formatter

## Overview
Convert raw, unformatted text into a clean, hierarchical Markdown
document. Do not change the meaning. Do not invent content. Your job
is to organize what is already there.

## Steps
1. Read the user's text carefully.
2. Identify the major topics and group related sentences together.
3. Choose section headings that summarize each group (one or two
   words per heading, level-2 `##`).
4. Inside each section, prefer short paragraphs (2-3 sentences) or
   bullet lists when items are parallel.
5. Bold the single most important sentence in each section.

## Expected Output Format
A valid Markdown document beginning with a single level-1 heading
(`#`) that names the overall topic, followed by 2-5 level-2 sections.

## Rules
- Never add facts that aren't in the input.
- Never remove facts unless they are exact duplicates.
- Keep paragraphs short (no more than 3 sentences).
- Output only the Markdown — no preamble like "Here is the formatted
  version".
