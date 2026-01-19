# Backend API - New Bot Endpoints Added

## Summary

Added **4 new endpoints** to `/api/v1/bot/` for Chatwoot AI bot integration.

---

## New Endpoints

### 1. Get User Game Credentials

```
GET /api/v1/bot/user/{user_id}/credentials
```

**Headers:**
- `Authorization: Bot <token>`

**Query Params:**
- `game_name` (optional) - Filter by specific game

**Response:**
```json
{
  "success": true,
  "credentials": [
    {
      "game_id": "uuid",
      "game_name": "juwa",
      "display_name": "Juwa",
      "game_username": "player123",
      "game_password": "xK9mP2nL",
      "balance": 150.00
    }
  ]
}
```

---

### 2. Get User Referral Info

```
GET /api/v1/bot/user/{user_id}/referral
```

**Headers:**
- `Authorization: Bot <token>`

**Response:**
```json
{
  "success": true,
  "referral_code": "ABC123",
  "commission_percent": 5,
  "tier_name": "Starter",
  "tier_level": 0,
  "active_referrals": 5,
  "pending_earnings": 25.00,
  "confirmed_earnings": 100.00,
  "total_earnings": 125.00,
  "tiers": [
    {"tier": 0, "name": "Starter", "min_refs": 0, "commission": 5},
    {"tier": 1, "name": "Bronze", "min_refs": 10, "commission": 10},
    {"tier": 2, "name": "Silver", "min_refs": 25, "commission": 15},
    {"tier": 3, "name": "Gold", "min_refs": 50, "commission": 20},
    {"tier": 4, "name": "Platinum", "min_refs": 100, "commission": 25},
    {"tier": 5, "name": "Diamond", "min_refs": 200, "commission": 30}
  ],
  "rules": [
    "Share your referral code with friends",
    "They enter it when signing up",
    "Once they make their first deposit, they become 'active'",
    "You earn 5% of ALL their future deposits",
    "Earnings are automatic and lifetime",
    "Get more active referrals to unlock higher commission tiers"
  ]
}
```

---

### 3. Generate Magic Link

```
POST /api/v1/bot/magic-link
```

**Headers:**
- `Authorization: Bot <token>`

**Request:**
```json
{
  "user_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "magic_link": "https://portal.example.com/auth/magic?token=eyJ...",
  "expires_in_seconds": 900,
  "message": "Magic link generated successfully"
}
```

**Notes:**
- Magic link expires in 15 minutes
- Uses JWT token for authentication
- One-time use (if magic_links table exists)

---

### 4. Preview Withdrawal/Cashout Rules

```
POST /api/v1/bot/withdrawal/preview
```

**Headers:**
- `Authorization: Bot <token>`

**Request:**
```json
{
  "user_id": "uuid",
  "game_name": "juwa"
}
```

**Response:**
```json
{
  "success": true,
  "can_withdraw": true,
  "block_reason": null,
  "current_balance": {
    "real": 200.00,
    "bonus": 50.00,
    "total": 250.00
  },
  "last_deposit_amount": 100.00,
  "min_multiplier": 1.0,
  "max_multiplier": 3.0,
  "min_cashout": 100.00,
  "max_cashout": 300.00,
  "payout_amount": 250.00,
  "void_amount": 0.00,
  "void_reason": null,
  "explanation": "Minimum cashout is 1x your last deposit. Maximum cashout is 3x your last deposit. Any amount above 3x will be voided.",
  "game_name": "juwa",
  "game_display_name": "Juwa"
}
```

**Block Reasons:**
- "Withdrawals are locked for this account"
- "No approved deposit found. You must deposit first."
- "Balance $X is below minimum cashout $Y (Nx of last deposit)"

---

## Environment Variables Added

### Backend (.env)

```
# Portal URL for magic links
PORTAL_URL=https://portal.your-domain.com
FRONTEND_URL=https://portal.your-domain.com
```

---

## Complete Bot API Endpoint List

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | GET | `/bot/games` | List all games |
| 2 | GET | `/bot/balance/{user_id}` | Get user balance |
| 3 | POST | `/bot/orders/validate` | Validate order + bonus calc |
| 4 | POST | `/bot/orders/create` | Create deposit order |
| 5 | POST | `/bot/orders/{id}/payment-proof` | Upload payment screenshot |
| 6 | GET | `/bot/orders/{order_id}` | Get order details |
| 7 | GET | `/bot/user/{user_id}/orders` | Get user orders |
| 8 | GET | `/bot/payment-methods` | Get payment tags |
| 9 | POST | `/bot/webhooks/order-status` | Register webhook |
| 10 | **GET** | **`/bot/user/{user_id}/credentials`** | **Get game credentials** ✨ |
| 11 | **GET** | **`/bot/user/{user_id}/referral`** | **Get referral info** ✨ |
| 12 | **POST** | **`/bot/magic-link`** | **Generate magic link** ✨ |
| 13 | **POST** | **`/bot/withdrawal/preview`** | **Preview cashout rules** ✨ |

✨ = New endpoints

---

## Database Tables Used

### game_accounts (existing)
- `game_username` - Player's game username
- `game_password` - Player's game password
- `balance` - Game balance

### users (existing)
- `referral_code` - User's referral code
- `referred_by` - Who referred this user

### magic_links (optional - auto-created if used)
- `link_id` - Unique ID
- `user_id` - User this link is for
- `token_hash` - Hash of the JWT token
- `expires_at` - Expiration timestamp

---

## Authentication

All bot endpoints require:
```
Authorization: Bot <BOT_API_TOKEN>
```

Or:
```
X-Bot-Token: <BOT_API_TOKEN>
```

The token must match `BOT_API_TOKEN` environment variable on the backend.
