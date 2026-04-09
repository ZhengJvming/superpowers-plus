# Eval 05: Large Task Escalates Into Pyramid

## Initial prompt to give the agent

> Build a multi-tenant internal knowledge platform with ingestion pipelines, semantic search, document permissions, sync from multiple sources, audit trails, and an admin console.

## Skill instruction

> Start with the normal Superpowers workflow and let it choose the correct route.

## Expected outcome (assertions)

```yaml
project: eval-large-05
project_should_exist: true
expect_memory_config: true
min_total_nodes: 12
max_total_nodes: 30
min_leaf_count: 8
min_decisions: 5
min_skill_inferred_ratio: 0.25
validate_passes: true
no_cycles: true
expected_concepts:
  - ingest
  - search
  - permission
  - audit
  - admin
  - tenant
```

## Notes

- This should clearly trip the escalation gate.
- A non-pyramid plan would be a failure of routing, not a success.
