# Hypothesis Tracking

Use structured hypothesis records during debugging so repeated guesses do not erase evidence.

## Format

For each hypothesis, record:

- `HYPOTHESIS`: the specific claim being tested
- `EVIDENCE`: the observed facts that motivated it
- `STATUS`: `open`, `rejected`, or `confirmed`
- `OUTCOME`: what the test showed
- `NOTES`: follow-up implications or unknowns

## Scratchpad Protocol

1. Before testing a hypothesis, write it to scratchpad:

```bash
python3 ../memory-management/scripts/run_memory_cli.py scratch write \
  --key "hypothesis-1" \
  --value "HYPOTHESIS: ... | EVIDENCE: ... | STATUS: open"
```

2. After the test, update the same logical thread with a new scratch entry or rewrite summary.
3. Use `scratch list` before forming a new hypothesis so you do not repeat rejected theories.
4. When a hypothesis is confirmed and worth keeping, promote it:

```bash
python3 ../memory-management/scripts/run_memory_cli.py scratch promote \
  --key "hypothesis-1" \
  --node <node-id> \
  --as decision
```

## Escalation Signal

If 3 or more hypotheses are rejected, treat that evidence chain as escalation input:
- summarize all rejected hypotheses into `must_persist`
- carry that summary into `brainstorming` or `pyramid-decomposition`
- do not continue blind fix attempts
