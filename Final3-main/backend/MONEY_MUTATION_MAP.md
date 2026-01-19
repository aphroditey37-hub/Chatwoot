# Money Mutation Map

## Overview
This document lists every endpoint and service function that modifies financial balances.

**Generated**: 2026-01-17
**Purpose**: Production hardening audit - identify all money-touching code paths

---

## Balance Fields

| Table | Field | Description |
|-------|-------|-------------|
| `users` | `real_balance` | User's cash balance (withdrawable) |
| `users` | `bonus_balance` | User's bonus balance (subject to wagering) |
| `users` | `play_credits` | Play credits (promotional) |
| `game_accounts` | `balance` | User's balance in a specific game |
| `wallet_ledger` | (inserts) | Immutable transaction log |

---

## Money Mutation Endpoints

### 1. CREDIT ROUTES (`credit_routes.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| `POST /credits/welcome/claim` | `UPDATE users.real_balance += credit_amount` | ✅ Yes | ✅ Yes (checks claimed_at) |
|  | `INSERT wallet_ledger` (credit) | ✅ Yes | ✅ Yes |

### 2. GAME ACCOUNT ROUTES (`game_account_routes.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| `POST /game-accounts/load` | `UPDATE users.real_balance -= amount` | ✅ Yes | ❌ No |
|  | `UPDATE game_accounts.balance += amount` | ✅ Yes | ❌ No |
|  | `INSERT game_loads` | ✅ Yes | ❌ No |
|  | `INSERT wallet_ledger` (debit) | ✅ Yes | ❌ No |
| `POST /game-accounts/redeem` | `UPDATE users.real_balance += amount` | ✅ Yes | ❌ No |
|  | `UPDATE game_accounts.balance -= amount` | ✅ Yes | ❌ No |
|  | `INSERT orders` (pending_approval) | ✅ Yes | ❌ No |
|  | `INSERT wallet_ledger` (credit) | ✅ Yes | ❌ No |

### 3. GAME ROUTES (`game_routes.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| `POST /games/load` | `UPDATE users.real_balance -= amount` | ✅ Yes | ❌ No |
|  | `INSERT game_loads` | ✅ Yes | ❌ No |
|  | `INSERT wallet_ledger` (debit) | ✅ Yes | ❌ No |

### 4. WALLET LOAD ROUTES (`wallet_load_routes.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| `POST /wallet-load/request` | `INSERT orders` (pending_approval) | ❌ No | ❌ No |
|  | No balance change until approval | - | - |

### 5. WITHDRAWAL ROUTES (`withdrawal_routes.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| `POST /withdrawal/wallet` | `UPDATE users.real_balance -= amount` | ✅ Yes | ❌ No |
|  | `INSERT orders` (pending_approval) | ✅ Yes | ❌ No |
|  | `INSERT wallet_ledger` (debit) | ✅ Yes | ❌ No |
| `POST /withdrawal/game` | `INSERT orders` (pending_approval) | ✅ Yes | ❌ No |
|  | `INSERT wallet_ledger` (credit from game) | ✅ Yes | ❌ No |

### 6. TELEGRAM WEBHOOK (`telegram_webhook.py`)

| Callback | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| `approve_{order_id}` | `UPDATE users.real_balance += amount` | ✅ Yes | ⚠️ Partial (status check) |
|  | `UPDATE orders.status = 'approved'` | ✅ Yes | ⚠️ Partial |
|  | `INSERT wallet_ledger` (credit) | ✅ Yes | ⚠️ Partial |
| `failed_{order_id}` | `UPDATE users.real_balance += amount` (refund) | ✅ Yes | ⚠️ Partial |
|  | `UPDATE orders.status = 'failed'` | ✅ Yes | ⚠️ Partial |
|  | `INSERT wallet_ledger` (refund credit) | ✅ Yes | ⚠️ Partial |

### 7. PAYMENT ROUTES (`payment_routes.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| Internal approval | `UPDATE users.real_balance += amount` | ❌ No | ❌ No |
|  | `UPDATE users.bonus_balance += bonus` | ❌ No | ❌ No |

### 8. ORDER ROUTES V2 (`order_routes_v2.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| Order processing | `UPDATE users.real_balance -= amount` | ❌ No | ❌ No |
|  | `UPDATE users.bonus_balance -= amount` | ❌ No | ❌ No |

### 9. REWARD ROUTES (`reward_routes.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| Reward grant | `UPDATE users.bonus_balance += amount` | ❌ No | ⚠️ Partial (grant_id check) |

### 10. ADMIN BALANCE CONTROL (`admin_balance_control.py`)

| Endpoint | Operation | Transactional | Idempotent |
|----------|-----------|---------------|------------|
| Manual adjustment | `INSERT orders` (pending_approval) | ❌ No | ❌ No |
|  | Balance change on approval | - | - |

---

## Critical Findings

### ⚠️ Issues to Address

1. **No idempotency keys**: Most endpoints lack idempotency protection
2. **Mixed transaction usage**: Some endpoints use `async with conn.transaction()`, others don't
3. **Refund logic**: Withdrawal failure refunds are in place but not atomic
4. **Double-click risk**: UI can submit same request multiple times

### ✅ Correctly Implemented

1. **Game load flow**: Uses transactions for wallet debit + game credit
2. **Welcome credit**: Has idempotency via `claimed_at` check
3. **Wallet ledger**: Consistently inserted with each balance change
4. **Withdrawal pre-deduct**: Balance deducted before Telegram approval (refund on fail)

---

## Recommended Hardening (Next Steps)

1. Add idempotency keys to all financial endpoints
2. Wrap all balance mutations in explicit transactions
3. Add request deduplication (hash of user_id + amount + timestamp)
4. Implement optimistic locking on balance updates
5. Add balance reconciliation checks

---

## Status Constant Reference

```python
# Canonical (use these)
PENDING_APPROVAL = "pending_approval"
APPROVED = "approved"
COMPLETED = "completed"
FAILED = "failed"
REJECTED = "rejected"

# Legacy (query compatibility only)
"pending_review"        -> PENDING_APPROVAL
"awaiting_payment_proof" -> PENDING_APPROVAL
"initiated"             -> PENDING_APPROVAL
"APPROVED_EXECUTED"     -> APPROVED
"confirmed"             -> APPROVED
```
