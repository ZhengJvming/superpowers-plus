# Eval 04: Simple Task Should Stay Lightweight

## Initial prompt to give the agent

> Rename the `version` command output field from `version` to `cli_version` and update the one affected test.

## Skill instruction

> Start with the normal Superpowers workflow. Only use `pyramid-decomposition` if the escalation gate truly requires it.

## Expected outcome (assertions)

```yaml
project_should_exist: false
expect_memory_config: false
project: eval-no-pyramid-04
```

## Notes

- This is a tightly scoped local change.
- The correct behavior is to stay out of pyramid decomposition entirely.
