# Business Rules Configuration

## Overview
This document describes where deposit and withdrawal rules are configured and how they are applied.

## Rule Priority
Rules are resolved with priority: **CLIENT > GAME > GLOBAL**

1. **Client-level rules** (highest priority) - per-user custom rules in `client_rules` table
2. **Game-level rules** - per-game config in `games.deposit_rules` and `games.withdrawal_rules` JSONB columns
3. **Global rules** (lowest priority) - system defaults in `system_settings` table

---

## Deposit Rules

### Business Requirement
> "For deposit, GAME balance must be less than $X in that game"

### Configuration Location
| Source | Column/Field | Example |
|--------|--------------|---------|
| Per-game | `games.deposit_rules->>'block_if_balance_above'` | `5.0` |
| Global | `system_settings.deposit_block_balance` | `5.0` |

### Implementation Files
| File | Function | Line |
|------|----------|------|
| `game_account_routes.py` | `load_game_account()` | 180-195 |
| `rules_service.py` | `resolve_deposit_rules()` | 146-220 |

### Rule Logic
```python
# Get threshold from per-game config, fallback to global
game_balance_threshold = deposit_rules.get('block_if_balance_above', 5.0)

# Check GAME balance (not wallet balance)
if current_game_balance > game_balance_threshold:
    raise HTTPException(
        status_code=400,
        detail="Cannot load. Current game balance exceeds maximum allowed."
    )
```

---

## Withdrawal Rules

### Business Requirement
> "Must reach at least N× and max M×; excess balance voided"

### Configuration Location
| Source | Column/Field | Example |
|--------|--------------|---------|
| Per-game | `games.withdrawal_rules->>'min_multiplier_of_deposit'` | `3.0` |
| Per-game | `games.withdrawal_rules->>'max_multiplier_of_deposit'` | `5.0` |
| Global | `system_settings.min_cashout_multiplier` | `1.0` |
| Global | `system_settings.max_cashout_multiplier` | `3.0` |

### Implementation Files
| File | Function | Line |
|------|----------|------|
| `game_account_routes.py` | `redeem_from_game()` | 310-450 |
| `rules_service.py` | `resolve_withdrawal_rules()` | 260-385 |

### Rule Logic
```python
# Get multipliers from per-game config
min_multiplier = withdrawal_rules.get('min_multiplier_of_deposit', 3.0)
max_multiplier = withdrawal_rules.get('max_multiplier_of_deposit', 5.0)

# Reference: total loaded since last withdrawal
total_loaded = SUM(game_loads.amount) WHERE created_at > last_withdrawal

# Calculate limits
min_cashout = total_loaded * min_multiplier  # e.g., $100 * 3 = $300
max_cashout = total_loaded * max_multiplier  # e.g., $100 * 5 = $500

# RULE 1: Minimum multiplier check
if current_game_balance < min_cashout:
    raise HTTPException("Minimum cashout not met")

# RULE 2: Maximum multiplier - VOID excess (don't block)
if current_game_balance > max_cashout:
    voided_amount = current_game_balance - max_cashout
    payout_amount = max_cashout  # User gets capped amount
    # Excess is voided and recorded in order metadata
```

### Void Recording
Void amounts are recorded in:
1. `orders.metadata.voided_amount` - The dollar amount voided
2. `orders.metadata.void_reason` - "EXCEEDS_MAX_MULTIPLIER"
3. `audit_logs` - Separate audit entry with full details

---

## Database Schema

### games table (per-game rules)
```sql
games (
    game_id UUID PRIMARY KEY,
    game_name VARCHAR(100),
    deposit_rules JSONB DEFAULT '{
        "min_amount": 10.0,
        "max_amount": 1000.0,
        "block_if_balance_above": 5.0
    }',
    withdrawal_rules JSONB DEFAULT '{
        "min_amount": 20.0,
        "max_amount": 1000.0,
        "min_multiplier_of_deposit": 3.0,
        "max_multiplier_of_deposit": 5.0,
        "require_full_balance": true
    }'
)
```

### Example Game Configuration
```sql
-- Set custom rules for a game
UPDATE games SET
    deposit_rules = '{
        "min_amount": 5.0,
        "max_amount": 500.0,
        "block_if_balance_above": 10.0
    }'::jsonb,
    withdrawal_rules = '{
        "min_amount": 10.0,
        "max_amount": 500.0,
        "min_multiplier_of_deposit": 2.0,
        "max_multiplier_of_deposit": 4.0
    }'::jsonb
WHERE game_name = 'puzzle_master';
```

---

## Applied Endpoints

| Endpoint | Rules Applied |
|----------|---------------|
| `POST /api/v1/games/load` | Deposit: game balance check |
| `POST /api/v1/game-accounts/load` | Deposit: game balance check |
| `POST /api/v1/game-accounts/redeem` | Withdrawal: min/max multiplier, void |
| `POST /api/v1/withdrawal/game` | Withdrawal: min/max multiplier, void |

---

## Testing Scenarios

### Deposit Blocked (Game Balance > X)
```bash
# Given: User has $10 in game, threshold is $5
# When: User tries to deposit
# Then: Blocked with error "Cannot load. Current game balance ($10.00) exceeds maximum allowed ($5.00)"
```

### Withdrawal Below Minimum
```bash
# Given: User loaded $100, current balance $200, min_multiplier=3
# Min cashout = $100 * 3 = $300
# When: User tries to withdraw $200
# Then: Blocked with "Minimum cashout not met. Required: $300 (3x)"
```

### Withdrawal Above Maximum (Void Applied)
```bash
# Given: User loaded $100, current balance $700, max_multiplier=5
# Max cashout = $100 * 5 = $500
# When: User withdraws
# Then: Payout = $500, Voided = $200, recorded in order metadata
```
