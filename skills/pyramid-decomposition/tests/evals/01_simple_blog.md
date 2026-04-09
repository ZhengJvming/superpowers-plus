# Eval 01: Simple Blog

## Initial prompt to give the agent

> I want to build a simple blog. Users can sign up, write posts, and read posts. That's it.

## Skill instruction

> Use the `pyramid-decomposition` skill to break this down.

## Expected outcome (assertions)

```yaml
project: eval-blog-01
min_total_nodes: 6
max_total_nodes: 15
min_leaf_count: 4
min_decisions: 3
min_skill_inferred_ratio: 0.3
validate_passes: true
no_cycles: true
expected_concepts:
  - signup
  - post
  - read
  - auth
  - storage
```

## Notes

- The prompt explicitly gives signup, write posts, and read posts.
- The skill should infer at least authentication and storage structure.
