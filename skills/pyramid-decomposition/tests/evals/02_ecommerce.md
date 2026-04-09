# Eval 02: E-commerce Backend

## Initial prompt to give the agent

> Build an e-commerce backend. Users browse products, add them to a cart, and check out. We need payment, inventory tracking, and order history.

## Skill instruction

> Use the `pyramid-decomposition` skill.

## Expected outcome (assertions)

```yaml
project: eval-ecommerce-02
min_total_nodes: 12
max_total_nodes: 30
min_leaf_count: 8
min_decisions: 6
min_skill_inferred_ratio: 0.3
validate_passes: true
no_cycles: true
expected_concepts:
  - product
  - cart
  - checkout
  - payment
  - inventory
  - order
  - auth
  - tax
```

## Notes

- Cross-leaf dependencies are expected around checkout, payment, and inventory.
- The skill should infer at least authentication and tax or shipping calculation.
