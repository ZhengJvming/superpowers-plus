# Cross-Module Tracing

Use this when the bug crosses module boundaries or when the symptom appears far away from the source.

## Goal

Identify:
- where bad state enters the system
- which upstream modules feed the failing module
- which downstream modules are impacted by the same bad state

## Protocol

1. Identify the current module or node under investigation.
2. If pyramid memory exists for this project, query dependencies:

```bash
python3 ../memory-management/scripts/run_memory_cli.py query deps --id <node-id>
python3 ../memory-management/scripts/run_memory_cli.py query deps-of --id <node-id>
python3 ../memory-management/scripts/run_memory_cli.py query impact --id <node-id> --direction upstream
python3 ../memory-management/scripts/run_memory_cli.py query impact --id <node-id> --direction downstream
```

3. Map:
- upstream = likely source modules
- downstream = likely symptom spread

4. If multiple independent modules must be investigated in parallel, hand off to `dispatching-parallel-agents`.

## Rule

Do not stop at the first failing module if the evidence suggests the defect was imported from upstream.
