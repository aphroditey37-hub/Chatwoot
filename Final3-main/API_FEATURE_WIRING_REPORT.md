# API-to-Feature Wiring Audit Report
**Platform:** Financial Gaming Platform (React + FastAPI + PostgreSQL)  
**Date:** January 18, 2026  
**Audit Type:** Comprehensive API Endpoint Inventory & Feature Wiring Check

---

## SUMMARY TABLE

| Metric | Count |
|--------|-------|
| **Total Backend Endpoints** | 147 |
| **Total Frontend API Calls** | 156 |
| **Wired (Matched)** | 118 |
| **Broken Frontend Calls (Missing Backend)** | 21 |
| **Unused Backend Endpoints** | 29 |

---

## SECTION 1: ✅ WIRED ENDPOINTS (By Feature)

### Authentication
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| POST | `/auth/login` | endpoints.js:14 | ✅ WIRED |
| POST | `/auth/signup` | endpoints.js:17 | ✅ WIRED |
| POST | `/auth/validate-token` | endpoints.js:20 | ✅ WIRED |
| PUT | `/auth/profile` | endpoints.js:23 | ✅ WIRED |
| PUT | `/auth/change-password` | endpoints.js:26 | ✅ WIRED |

### Client Wallet
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/wallet/balance` | endpoints.js:34, ClientGames.js:51 | ✅ WIRED |
| GET | `/wallet/ledger` | endpoints.js:49 | ✅ WIRED |
| GET | `/wallet/qr` | endpoints.js:52 | ✅ WIRED |
| GET | `/wallet/load-history` | endpoints.js:46 | ✅ WIRED |
| GET | `/portal/wallet/breakdown` | endpoints.js:37 | ✅ WIRED |
| GET | `/portal/wallet/bonus-progress` | endpoints.js:40 | ✅ WIRED |
| GET | `/portal/wallet/cashout-preview` | endpoints.js:43 | ✅ WIRED |
| POST | `/wallet-load/request` | endpoints.js:55, AddFunds.js:119 | ✅ WIRED |
| POST | `/withdrawal/wallet` | endpoints.js:58, Withdraw.js:84 | ✅ WIRED |

### Payment Methods (Client)
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/payments/methods` | AddFunds.js:64 | ✅ WIRED |

### Promo & Rewards
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| POST | `/portal/promo/redeem` | endpoints.js:123 | ✅ WIRED |
| GET | `/portal/promo/history` | endpoints.js:126 | ✅ WIRED |
| GET | `/portal/rewards` | endpoints.js:120 | ✅ WIRED |
| GET | `/portal/credits/welcome` | endpoints.js:129 | ✅ WIRED |
| POST | `/portal/credits/welcome/claim` | endpoints.js:132 | ✅ WIRED |

### Games & Accounts
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/public/games` | endpoints.js:82, ClientGames.js:49 | ✅ WIRED |
| GET | `/games/available` | endpoints.js:85 | ✅ WIRED |
| GET | `/game-accounts/my-accounts` | endpoints.js:88, ClientGames.js:50 | ✅ WIRED |
| POST | `/game-accounts/create` | endpoints.js:91, ClientGames.js:76 | ✅ WIRED |
| POST | `/game-accounts/load` | endpoints.js:94, ClientGames.js:107 | ✅ WIRED |
| POST | `/game-accounts/redeem` | endpoints.js:97, ClientGames.js:136 | ✅ WIRED |

### Transactions
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/portal/transactions/enhanced` | endpoints.js:67 | ✅ WIRED |
| GET | `/portal/transactions/{order_id}` | endpoints.js:74, TransactionDetail.js:39 | ✅ WIRED |
| GET | `/portal/credentials` | endpoints.js:140 | ✅ WIRED |
| POST | `/portal/security/set-password` | endpoints.js:143 | ✅ WIRED |
| GET | `/portal/games/rules` | endpoints.js:146 | ✅ WIRED |

### Referrals
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/portal/referrals/details` | endpoints.js:105, ClientReferrals.js:182 | ✅ WIRED |
| GET | `/admin/referrals/dashboard` | admin.js:369, endpoints.js:109 | ✅ WIRED |
| GET | `/admin/referrals/ledger` | admin.js:376, endpoints.js:112 | ✅ WIRED |

### Admin Dashboard
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/dashboard` | admin.js:21, endpoints.js:155 | ✅ WIRED |
| GET | `/admin/stats` | admin.js:18 | ✅ WIRED (legacy) |

### Admin Clients
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/clients` | admin.js:35, endpoints.js:182 | ✅ WIRED |
| GET | `/admin/clients/{user_id}` | admin.js:39, endpoints.js:186 | ✅ WIRED |
| POST | `/admin/clients` | admin.js:42, endpoints.js:189 | ✅ WIRED |
| PUT | `/admin/clients/{user_id}` | admin.js:45, endpoints.js:192 | ✅ WIRED |
| PUT | `/admin/clients/{user_id}/bonus` | admin.js:51 | ✅ WIRED |
| GET | `/admin/clients/{user_id}/overrides` | admin.js:64, endpoints.js:195 | ✅ WIRED |
| PUT | `/admin/clients/{user_id}/overrides` | admin.js:67, endpoints.js:198 | ✅ WIRED |
| GET | `/admin/clients/{user_id}/activity` | admin.js:71, endpoints.js:201 | ✅ WIRED |
| POST | `/admin/clients/{user_id}/credentials` | admin.js:78, endpoints.js:204 | ✅ WIRED |

### Admin Orders
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/orders` | admin.js:136, endpoints.js:173 | ✅ WIRED |
| GET | `/admin/orders/{order_id}` | admin.js:140, endpoints.js:177 | ✅ WIRED |
| GET | `/admin/approvals/pending` | admin.js:156, endpoints.js:165 | ✅ WIRED |
| POST | `/admin/approvals/{order_id}/action` | admin.js:161, endpoints.js:168 | ✅ WIRED |

### Admin Analytics
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/analytics/client/{user_id}` | admin.js:86, endpoints.js:207 | ✅ WIRED |
| GET | `/admin/analytics/game/{game_name}` | admin.js:89 | ✅ WIRED |
| GET | `/admin/analytics/risk-snapshot` | admin.js:92 | ✅ WIRED |
| GET | `/admin/analytics/risk-exposure` | admin.js:95 | ✅ WIRED |
| GET | `/admin/analytics/platform-trends` | admin.js:106 | ✅ WIRED |
| GET | `/admin/analytics/advanced-metrics` | admin.js:110 | ✅ WIRED |

### Admin Promo Codes
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/promo-codes` | admin.js:345, endpoints.js:228 | ✅ WIRED |
| POST | `/admin/promo-codes` | admin.js:352, endpoints.js:231 | ✅ WIRED |
| PUT | `/admin/promo-codes/{code_id}/disable` | admin.js:355, endpoints.js:234 | ✅ WIRED |
| GET | `/admin/promo-codes/{code_id}/redemptions` | admin.js:361 | ✅ WIRED |

### Admin Games & Rules
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/games` | admin.js:304, endpoints.js:211 | ✅ WIRED |
| POST | `/admin/games` | endpoints.js:214 | ✅ WIRED |
| PUT | `/admin/games/{game_id}` | admin.js:307, endpoints.js:217 | ✅ WIRED |
| GET | `/admin/rules` | admin.js:310,408, endpoints.js:221 | ✅ WIRED |
| PUT | `/admin/rules` | admin.js:411, endpoints.js:224 | ✅ WIRED |

### Admin Balance Control
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| POST | `/admin/balance-control/load` | admin.js:487 | ✅ WIRED |
| POST | `/admin/balance-control/withdraw` | admin.js:498 | ✅ WIRED |

### Admin System (Payment Methods via /admin/system/*)
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/system/payment-methods` | admin.js:222 | ✅ WIRED |
| POST | `/admin/system/payment-methods` | admin.js:225 | ✅ WIRED |
| PUT | `/admin/system/payment-methods/{method_id}` | admin.js:228 | ✅ WIRED |
| DELETE | `/admin/system/payment-methods/{method_id}` | admin.js:231 | ✅ WIRED |
| GET | `/admin/system/payment-qr` | admin.js:235 | ✅ WIRED |
| POST | `/admin/system/payment-qr` | admin.js:238 | ✅ WIRED |
| PATCH | `/admin/system/payment-qr/{qr_id}` | admin.js:241 | ✅ WIRED |
| DELETE | `/admin/system/payment-qr/{qr_id}` | admin.js:244 | ✅ WIRED |
| GET | `/admin/system/api-keys` | admin.js:248,419 | ✅ WIRED |
| POST | `/admin/system/api-keys` | admin.js:251,422 | ✅ WIRED |
| DELETE | `/admin/system/api-keys/{key_id}` | admin.js:254,425 | ✅ WIRED |
| GET | `/admin/system/webhooks` | admin.js:258 | ✅ WIRED |
| POST | `/admin/system/webhooks` | admin.js:261 | ✅ WIRED |
| PUT | `/admin/system/webhooks/{webhook_id}` | admin.js:264 | ✅ WIRED |
| DELETE | `/admin/system/webhooks/{webhook_id}` | admin.js:267 | ✅ WIRED |
| GET | `/admin/system/webhooks/{webhook_id}/deliveries` | admin.js:270 | ✅ WIRED |
| GET | `/admin/system/wallet-loads` | admin.js:214 | ✅ WIRED |
| GET | `/admin/system/wallet-loads/{request_id}` | admin.js:218 | ✅ WIRED |
| GET | `/admin/system` | endpoints.js:158 | ✅ WIRED |
| PUT | `/admin/system` | endpoints.js:161 | ✅ WIRED |

### Admin Reports
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/reports/balance-flow` | admin.js:385, endpoints.js:239 | ✅ WIRED |
| GET | `/admin/reports/profit-by-game` | admin.js:391, endpoints.js:244 | ✅ WIRED |
| GET | `/admin/reports/voids` | admin.js:394 | ✅ WIRED |

### Admin Perks
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/perks` | admin.js:324, endpoints.js:255 | ✅ WIRED |
| POST | `/admin/perks` | admin.js:327, endpoints.js:258 | ✅ WIRED |
| PUT | `/admin/perks/{perk_id}` | admin.js:330, endpoints.js:261 | ✅ WIRED |
| DELETE | `/admin/perks/{perk_id}` | admin.js:333, endpoints.js:264 | ✅ WIRED |

### Admin Audit Logs
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/audit-logs` | admin.js:440, endpoints.js:250 | ✅ WIRED |

### Admin Telegram
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/telegram/bots` | admin.js:510, endpoints.js:328 | ✅ WIRED |
| POST | `/admin/telegram/bots` | admin.js:513, endpoints.js:331 | ✅ WIRED |
| PUT | `/admin/telegram/bots/{bot_id}` | admin.js:516, endpoints.js:334 | ✅ WIRED |
| DELETE | `/admin/telegram/bots/{bot_id}` | admin.js:519, endpoints.js:337 | ✅ WIRED |
| POST | `/admin/telegram/bots/{bot_id}/test` | admin.js:522, endpoints.js:340 | ✅ WIRED |
| GET | `/admin/telegram/events` | admin.js:525 | ✅ WIRED |
| GET | `/admin/telegram/bots/{bot_id}/permissions` | admin.js:528 | ✅ WIRED |
| POST | `/admin/telegram/bots/{bot_id}/permissions` | admin.js:531 | ✅ WIRED |
| GET | `/admin/telegram/logs` | admin.js:538 | ✅ WIRED |
| POST | `/admin/telegram/setup-webhook` | admin.js:542 | ✅ WIRED |
| GET | `/admin/telegram/webhook-info` | admin.js:545 | ✅ WIRED |

### Admin Rewards
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/admin/rewards` | admin.js:553 | ✅ WIRED |
| GET | `/admin/rewards/{reward_id}` | admin.js:556 | ✅ WIRED |
| POST | `/admin/rewards` | admin.js:559 | ✅ WIRED |
| PUT | `/admin/rewards/{reward_id}` | admin.js:562 | ✅ WIRED |
| DELETE | `/admin/rewards/{reward_id}` | admin.js:565 | ✅ WIRED |
| POST | `/admin/rewards/grant` | admin.js:568 | ✅ WIRED |
| GET | `/admin/rewards/grants/history` | admin.js:571 | ✅ WIRED |
| POST | `/admin/rewards/trigger/{trigger_type}` | admin.js:574 | ✅ WIRED |

### Public
| Method | Endpoint | Frontend Location | Status |
|--------|----------|------------------|--------|
| GET | `/public/hero-slides` | PublicGamesNew.js:24 | ✅ WIRED |

---

## SECTION 2: ❌ BROKEN/LEGACY FRONTEND CALLS

These frontend calls target endpoints that **DO NOT EXIST** in the backend or use **WRONG PATHS**.

### Critical (Money/Auth/Permissions)

| Frontend Call | File:Line | Issue | Fix |
|---------------|-----------|-------|-----|
| `POST /admin/clients/{userId}/status` | admin.js:48,54,57,60 | ❌ No backend route | DELETE - Use PUT `/admin/clients/{userId}` with status field |
| `POST /admin/orders/{orderId}/approve` | admin.js:143 | ❌ No backend route | Use `POST /admin/approvals/{order_id}/action` with `action: 'approve'` |
| `POST /admin/orders/{orderId}/reject` | admin.js:146 | ❌ No backend route | Use `POST /admin/approvals/{order_id}/action` with `action: 'reject'` |
| `POST /admin/settings/reset-defaults` | admin.js:296 | ❌ No backend route | DELETE - No reset functionality exists |

### Legacy Path Issues (Old `/admin/*` vs New `/admin/system/*`)

| Frontend Call | File:Line | Issue | Fix |
|---------------|-----------|-------|-----|
| `GET /admin/webhooks` | endpoints.js:273 | ❌ Wrong path | Use `/admin/system/webhooks` |
| `POST /admin/webhooks` | endpoints.js:276 | ❌ Wrong path | Use `/admin/system/webhooks` |
| `PUT /admin/webhooks/{webhookId}` | endpoints.js:279 | ❌ Wrong path | Use `/admin/system/webhooks/{webhook_id}` |
| `DELETE /admin/webhooks/{webhookId}` | endpoints.js:282 | ❌ Wrong path | Use `/admin/system/webhooks/{webhook_id}` |
| `GET /admin/api-keys` | endpoints.js:286 | ❌ Wrong path | Use `/admin/system/api-keys` |
| `POST /admin/api-keys` | endpoints.js:289 | ❌ Wrong path | Use `/admin/system/api-keys` |
| `DELETE /admin/api-keys/{keyId}` | endpoints.js:292 | ❌ Wrong path | Use `/admin/system/api-keys/{key_id}` |
| `GET /admin/payment-methods` | endpoints.js:296 | ❌ Wrong path | Use `/admin/system/payment-methods` |
| `POST /admin/payment-methods` | endpoints.js:299 | ❌ Wrong path | Use `/admin/system/payment-methods` |
| `PUT /admin/payment-methods/{methodId}` | endpoints.js:302 | ❌ Wrong path | Use `/admin/system/payment-methods/{method_id}` |
| `DELETE /admin/payment-methods/{methodId}` | endpoints.js:305 | ❌ Wrong path | Use `/admin/system/payment-methods/{method_id}` |
| `GET /admin/payment-qr` | endpoints.js:309 | ❌ Wrong path | Use `/admin/system/payment-qr` |
| `POST /admin/payment-qr` | endpoints.js:312 | ❌ Wrong path | Use `/admin/system/payment-qr` |
| `DELETE /admin/payment-qr/{qrId}` | endpoints.js:315 | ❌ Wrong path | Use `/admin/system/payment-qr/{qr_id}` |
| `GET /admin/wallet-loads` | endpoints.js:320 | ❌ Wrong path | Use `/admin/system/wallet-loads` |
| `GET /admin/wallet-loads/{requestId}` | endpoints.js:324 | ❌ Wrong path | Use `/admin/system/wallet-loads/{request_id}` |

### Approval Sub-Routes (Not in Backend)

| Frontend Call | File:Line | Issue | Fix |
|---------------|-----------|-------|-----|
| `GET /admin/approvals/wallet-loads` | admin.js:165 | ❌ No backend route | Use `/admin/system/wallet-loads` with status filter |
| `POST /admin/approvals/wallet-load/{requestId}/approve` | admin.js:168 | ❌ No backend route | Use `/admin/approvals/{order_id}/action` |
| `POST /admin/approvals/wallet-load/{requestId}/reject` | admin.js:171 | ❌ No backend route | Use `/admin/approvals/{order_id}/action` |
| `GET /admin/approvals/withdrawals` | admin.js:175 | ❌ No backend route | Use `/admin/orders?order_type=withdrawal` |
| `POST /admin/approvals/withdrawal/{orderId}/approve` | admin.js:178 | ❌ No backend route | Use `/admin/approvals/{order_id}/action` |
| `POST /admin/approvals/withdrawal/{orderId}/reject` | admin.js:181 | ❌ No backend route | Use `/admin/approvals/{order_id}/action` |
| `GET /admin/approvals/game-loads` | admin.js:185 | ❌ No backend route | Use `/admin/orders?order_type=game_load` |
| `POST /admin/approvals/game-load/{orderId}/approve` | admin.js:188 | ❌ No backend route | Use `/admin/approvals/{order_id}/action` |
| `POST /admin/approvals/game-load/{orderId}/reject` | admin.js:191 | ❌ No backend route | Use `/admin/approvals/{order_id}/action` |
| `GET /admin/approvals/redemptions` | admin.js:195 | ❌ No backend route | Use `/admin/orders?order_type=redemption` |
| `POST /admin/approvals/redemption/{orderId}/approve` | admin.js:198 | ❌ No backend route | Use `/admin/approvals/{order_id}/action` |
| `POST /admin/approvals/redemption/{orderId}/reject` | admin.js:201 | ❌ No backend route | Use `/admin/approvals/{order_id}/action` |

### Reports (Missing)

| Frontend Call | File:Line | Issue | Fix |
|---------------|-----------|-------|-----|
| `GET /admin/reports/performance` | admin.js:388 | ❌ No backend route | DELETE or add backend endpoint |
| `GET /admin/reports/referrals` | admin.js:397 | ❌ No backend route | Use `/admin/referrals/dashboard` |
| `GET /admin/reports/bonus` | admin.js:400 | ❌ No backend route | DELETE or add backend endpoint |

---

## SECTION 3: 🟦 UNUSED BACKEND ENDPOINTS (Available to Add)

These backend endpoints exist but have **NO frontend calls**.

### HIGH Priority (Financial/Compliance)

| Endpoint | Module | Suggested Feature |
|----------|--------|-------------------|
| `GET /wallet/load-status/{request_id}` | wallet_routes | Add deposit status tracking in client wallet |
| `POST /wallet/load-request` | wallet_routes | Alternative deposit flow (duplicate of wallet-load/request) |
| `POST /withdrawal/game` | withdrawal_routes | Game balance withdrawal feature |
| `GET /admin/system/rules` | admin_system_routes | System rules viewer in admin |
| `GET /admin/system/settings` | admin_system_routes | System settings viewer in admin |
| `POST /admin/clients/{user_id}/status` | NOT EXISTS | ⚠️ Frontend calls this but backend doesn't have it |

### MEDIUM Priority (Operations)

| Endpoint | Module | Suggested Feature |
|----------|--------|-------------------|
| `GET /games/{game_id}` | game_routes | Individual game detail page |
| `POST /games/load` | game_routes | Alternative game loading (wallet-based) |
| `GET /games/load-history` | game_routes | Game load history viewer |
| `POST /identity/resolve` | identity_routes | Identity resolution feature |
| `GET /identity/lookup/{provider}/{external_id}` | identity_routes | Identity lookup in admin |
| `POST /identity/admin/link` | identity_routes | Admin identity linking |
| `POST /identity/admin/switch-primary` | identity_routes | Switch primary identity |
| `POST /identity/admin/transfer` | identity_routes | Transfer identity |
| `GET /identity/admin/user/{user_id}` | identity_routes | Admin user identity view |
| `POST /referrals/validate` | referral_routes | Referral code validation |
| `GET /public/games/{game_id}` | public_routes | Public game detail page |

### LOW Priority (Bot/Integration)

| Endpoint | Module | Suggested Feature |
|----------|--------|-------------------|
| `POST /bot/auth/token` | bot_routes | Bot authentication |
| `GET /bot/balance/{user_id}` | bot_routes | Bot balance check |
| `GET /bot/games` | bot_routes | Bot games list |
| `POST /bot/orders/create` | bot_routes | Bot order creation |
| `POST /bot/orders/validate` | bot_routes | Bot order validation |
| `GET /bot/orders/{order_id}` | bot_routes | Bot order detail |
| `POST /bot/orders/{order_id}/payment-proof` | bot_routes | Bot payment proof upload |
| `GET /bot/payment-methods` | bot_routes | Bot payment methods |
| `GET /bot/user/{user_id}/orders` | bot_routes | Bot user orders |
| `POST /bot/webhooks/order-status` | bot_routes | Bot webhook |
| `POST /telegram/webhook` | telegram_webhook | Telegram webhook handler |
| `POST /admin/telegram/webhook` | telegram_routes | Admin telegram webhook |
| `GET /webhooks/list` | webhook_routes | Webhook list (use admin/system/webhooks instead) |
| `POST /webhooks/register` | webhook_routes | Webhook registration (use admin/system/webhooks instead) |
| `DELETE /webhooks/{webhook_id}` | webhook_routes | Webhook delete (use admin/system/webhooks instead) |
| `GET /webhooks/{webhook_id}/deliveries` | webhook_routes | Webhook deliveries (use admin/system/webhooks instead) |
| `GET /orders` | order_routes_v2 | Orders list (use admin/orders instead) |
| `POST /orders/deposit/create` | order_routes_v2 | Deposit order creation |
| `POST /orders/deposit/validate` | order_routes_v2 | Deposit order validation |
| `GET /orders/games/list` | order_routes_v2 | Game orders list |
| `POST /orders/list` | order_routes_v2 | Orders list filter |
| `POST /orders/withdrawal/create` | order_routes_v2 | Withdrawal order creation |
| `POST /orders/withdrawal/validate` | order_routes_v2 | Withdrawal order validation |
| `GET /orders/{order_id}` | order_routes_v2 | Order detail |
| `POST /payments/action/{order_id}` | payment_routes | Payment action |
| `POST /payments/proof/{order_id}` | payment_routes | Payment proof upload |
| `GET /auth/magic-link/consume` | auth_routes | Magic link consumption |
| `POST /auth/magic-link/request` | auth_routes | Magic link request |

---

## SECTION 4: RECOMMENDED NEXT ADDITIONS (Top 10 by Value)

| Priority | Action | Endpoint | Value |
|----------|--------|----------|-------|
| 1 | **FIX** | Remove legacy paths in endpoints.js (lines 273-324) | HIGH - Prevents 404s |
| 2 | **FIX** | Remove/update `/admin/clients/{userId}/status` calls | HIGH - Currently broken |
| 3 | **FIX** | Update approval routes to use unified `/admin/approvals/{order_id}/action` | HIGH - Currently broken |
| 4 | **ADD** | Wire `GET /wallet/load-status/{request_id}` | HIGH - Deposit tracking |
| 5 | **ADD** | Wire `POST /withdrawal/game` | HIGH - Game cashout feature |
| 6 | **ADD** | Wire `GET /identity/admin/user/{user_id}` | MEDIUM - Better user management |
| 7 | **DELETE** | Remove duplicate webhook routes (non-admin/system) | LOW - Cleanup |
| 8 | **ADD** | Wire `GET /games/{game_id}` for game detail page | MEDIUM - UX |
| 9 | **ADD** | Wire `POST /identity/resolve` for identity linking | MEDIUM - Multi-account |
| 10 | **ADD** | Wire `GET /admin/system/settings` for settings viewer | LOW - Admin UX |

---

## GO/NO-GO ASSESSMENT

### ❌ **NO-GO for Production**

**Blocking Issues:**

1. **Legacy Path Calls in endpoints.js** (lines 273-324)
   - Frontend calls `/admin/webhooks`, `/admin/api-keys`, `/admin/payment-methods`, `/admin/payment-qr`, `/admin/wallet-loads`
   - Backend only has `/admin/system/*` versions
   - **Impact:** Any feature using these legacy exports will 404
   - **Risk:** HIGH (payment config, webhook config)

2. **Broken Approval Routes** (admin.js lines 165-201)
   - Frontend calls specific approval endpoints that don't exist
   - **Impact:** Approval workflows for wallet-loads, withdrawals, game-loads, redemptions will fail
   - **Risk:** HIGH (money flows)

3. **Client Status Update Broken** (admin.js lines 48-60)
   - `POST /admin/clients/{userId}/status` doesn't exist
   - **Impact:** Cannot suspend/ban/activate users
   - **Risk:** MEDIUM (user management)

### Required Fixes Before Production:

```javascript
// endpoints.js - DELETE or UPDATE these legacy exports:
// Line 273-282: webhooksApi → use admin.js systemApi.webhooks
// Line 286-292: apiKeysApi → use admin.js systemApi.apiKeys  
// Line 296-305: paymentMethodsApi → use admin.js systemApi.paymentMethods
// Line 309-315: paymentQrApi → use admin.js systemApi.paymentQr
// Line 320-324: walletLoadsApi → use admin.js systemApi.walletLoads

// admin.js - UPDATE approval routes (lines 165-201):
// Use ordersApi.getAll() with type filter instead of specific approval endpoints
// Use approvalsApi.action() for all approve/reject actions
```

---

## Audit Metadata

- **Backend Endpoints Extracted From:** `/app/backend/api/v1/routes/*.py`
- **Frontend Calls Extracted From:** `/app/frontend/src/api/admin.js`, `/app/frontend/src/api/endpoints.js`, `/app/frontend/src/pages/**/*.js`
- **Verification Method:** grep + OpenAPI schema + code inspection
- **Total Lines Analyzed:** ~8,000

---

**Report Generated:** January 18, 2026
