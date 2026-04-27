def rule_engine(sku, cost, proposed, demand, competitor):
    violations = []
    
    # Ensure types
    try:
        cost = float(cost)
        proposed = float(proposed)
        competitor = float(competitor) if competitor is not None else None
    except:
        pass # Handle robustly or fail? For now proceed.

    # Rule 1 — Margin threshold
    if proposed < cost * 1.10:
        violations.append("Price below minimum margin rule (10%).")

    # Rule 2 — Max deviation from competitor
    if competitor and abs(proposed - competitor) > competitor * 0.25:
        violations.append("Price deviates >25% from competitor benchmark.")

    # Rule 3 — Anti-dumping rule
    if proposed < cost:
        violations.append("Price cannot be below SKU cost.")

    return violations
