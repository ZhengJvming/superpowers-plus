# Eval 03: Data Pipeline

## Initial prompt to give the agent

> I need an ETL pipeline. It pulls data from a Postgres database, cleans and transforms it, then writes it to a data warehouse. It should run nightly and alert on failures.

## Skill instruction

> Use the `pyramid-decomposition` skill.

## Expected outcome (assertions)

```yaml
project: eval-pipeline-03
min_total_nodes: 8
max_total_nodes: 20
min_leaf_count: 5
min_decisions: 4
min_skill_inferred_ratio: 0.3
validate_passes: true
no_cycles: true
expected_concepts:
  - extract
  - transform
  - load
  - schedule
  - alert
  - schema
  - retry
```

## Notes

- This scenario should surface explicit dependency edges in extract -> transform -> load style flows.
- The skill should infer schema and retry strategy as explicit concerns.
