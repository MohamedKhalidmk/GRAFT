<!-- Sources: original (docs/reference/REFERENCES.md) -->
<!-- GRAFT G53, the passage index with reading (docs/design/graft_passage_index_design.md, section "Reading"). Placeholders:
{asks_left} asks Qwen may still make, {open_tokens} the most text one OPEN line adds. The rule is appended after the
benchmark's question while asks remain; the last call (no asks left, or no OPEN lines) gets the plain question. -->
If a passage above seems to be cut off or missing something you need to answer, you may open more of the original
text instead of answering. Reply with only lines of this form, nothing else:
OPEN P<number> AROUND   (the text just before and just after passage P<number>)
OPEN P<number> SESSION  (the rest of the session or chunk that passage P<number> comes from)
At most 3 lines per reply; each line adds at most {open_tokens} tokens. You may ask {asks_left} more time(s). If the
passages already hold what you need, answer the question as instructed.
