# Eval 06: Existing Project Routing

## Initial prompt to give the agent

> In this existing repository, map the billing area before planning a change that adds retry-safe payment capture and a billing audit trail.

## Skill instruction

> Start with the normal Superpowers workflow and let it choose the correct route.

## Expected outcome (assertions)

```yaml
project: eval-existing-06
project_should_exist: true
expect_memory_config: true
min_total_nodes: 4
max_total_nodes: 16
min_leaf_count: 1
min_decisions: 1
min_skill_inferred_ratio: 0.2
validate_passes: true
no_cycles: true
expected_concepts:
  - billing
  - payment
  - audit
expected_node_types:
  - existing_module
min_file_refs: 2
require_scan_metadata: true
```

## Notes

- This scenario should trigger freshness/exploration behavior before deep decomposition.
- The graph should contain existing-project boundary mapping, not only greenfield-style feature leaves.
