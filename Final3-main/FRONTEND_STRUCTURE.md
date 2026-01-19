# 🎮 Gaming Platform - Complete Frontend Structure

## 📱 CLIENT INTERFACE (Mobile-First)

### **Primary Navigation** (Bottom Nav Bar)
```
┌─────────────────────────────────────────────────────┐
│  [🏠 Home] [💰 Wallet] [🎮 Games] [👥 Referrals] [👤 Profile]  │
└─────────────────────────────────────────────────────┘
```

### **1. Home** (`/client/home`)
**File:** `ClientHome.js`
**Features:**
- Balance overview card
  - Total Balance
  - Bonus Balance
  - Play Credits
- Welcome credit banner (if unclaimed)
- Quick action buttons
  - Add Funds
  - Withdraw
  - Load Game
- Recent transactions preview
- Game accounts overview

---

### **2. Wallet** (`/client/wallet`)
**File:** `ClientWallet.js`
**Features:**
- Balance breakdown
  - Cash Balance (withdrawable)
  - Bonus Balance
  - Play Credits
  - Pending Loads
- Action buttons
  - Add Funds
  - Withdraw
- Transaction history
  - Deposits
  - Withdrawals
  - Game loads
  - Game redeems
  - Bonuses
- Filters by type and date

**Sub-pages:**
- **Add Funds** (`/client/wallet/add`)
  - **File:** `AddFunds.js`
  - 3-step process:
    1. Enter amount + select quick amounts
    2. Choose payment method (GCash, PayMaya, Bank)
    3. Upload proof of payment
  
- **Withdraw** (`/client/wallet/withdraw`)
  - **File:** `Withdraw.js`
  - 2-step process:
    1. Enter amount + select payment method
    2. Enter account details

---

### **3. Games** (`/client/games`)
**File:** `ClientGames.js`
**Features:**
- Available games list
  - Game cards with thumbnails
  - Game details (name, description)
  - Platform indicators
- Game account management
  - Create account button
  - View existing accounts
  - Account credentials
  - Current balance
- Quick actions per game:
  - **Load** - Transfer from wallet to game
  - **Redeem** - Cash out from game to wallet
  - **View** - See game details
- Business rules enforcement
  - $5 max load limit indicator
  - Wagering requirement display
  - Balance validation

---

### **4. Referrals** (`/client/referrals`)
**File:** `PortalReferrals.js` (shared with portal)
**Features:**
- Personal referral code display
- Copy code button
- Share link generator
- Referral stats
  - Total referrals
  - Active referrals
  - Earnings from referrals
- Referred users list
  - Username
  - Join date
  - Status
  - Commission earned
- Earnings history

---

### **5. Profile** (`/client/profile`)
**File:** `ClientProfile.js`
**Features:**
- **Profile Info Tab**
  - Username (read-only)
  - Display name (editable)
  - Email (editable)
  - Save changes button
  
- **Security Tab**
  - Current password
  - New password
  - Confirm new password
  - Change password button
  
- User avatar
- Role badge (if admin)
- Logout button

---

## 💼 ADMIN INTERFACE (Desktop Dashboard)

### **Sidebar Navigation**
```
┌─────────────────────┐
│   GAMING PLATFORM   │
├─────────────────────┤
│ 📊 Dashboard        │
│ ✅ Approvals        │
│ 📋 Orders           │
│ 👥 Clients          │
│ 🎮 Games            │
│ ⚙️  Rules           │
│ 🎁 Referrals        │
│ 🎫 Promo Codes      │
│ 💰 Balance Control  │
│ 📊 Reports          │
│ 🔧 System           │
│ 📜 Audit Logs       │
└─────────────────────┘
```

---

### **1. Dashboard** (`/admin`)
**File:** `AdminDashboard.js`
**Features:**
- **Key Metrics Cards**
  - Total Revenue
  - Active Users
  - Pending Approvals
  - Today's Transactions
  
- **Charts & Graphs**
  - Revenue trend
  - User growth
  - Transaction volume
  
- **Recent Activity**
  - Latest orders
  - New registrations
  - Recent withdrawals
  
- **Quick Actions**
  - Approve pending orders
  - Create client
  - View reports

---

### **2. Approvals** (`/admin/approvals`)
**File:** `AdminApprovals.js`
**Features:**
- **Pending Deposits**
  - Order ID
  - Username
  - Amount
  - Payment method
  - Proof image
  - Actions: Approve / Reject
  
- **Pending Withdrawals**
  - Order ID
  - Username
  - Amount
  - Withdrawal method
  - Account details
  - Actions: Approve / Reject
  
- **Filters**
  - By type (deposit/withdrawal)
  - By date range
  - By amount
  - By user
  
- **Bulk Actions**
  - Select multiple
  - Approve all
  - Reject all

---

### **3. Orders** (`/admin/orders`)
**File:** `AdminOrders.js`
**Features:**
- **All Orders List**
  - Order ID
  - Type (wallet_load, withdrawal_wallet, withdrawal_game)
  - Username
  - Amount
  - Status
  - Created date
  - Actions
  
- **Filters**
  - Status (pending, approved, rejected)
  - Order type
  - Date range
  - User search
  - Amount range
  
- **Order Details Modal**
  - Full order information
  - User details
  - Payment proof
  - Status history
  - Admin notes
  - Action buttons

---

### **4. Clients** (`/admin/clients`)
**File:** `AdminClients.js`
**Features:**
- **Users List**
  - Username
  - Display name
  - Email
  - Balance
  - Status (active/suspended)
  - Join date
  - Last active
  - Actions
  
- **Search & Filter**
  - Search by username/email
  - Filter by status
  - Filter by role
  - Sort options
  
- **Quick Actions**
  - View details
  - Edit user
  - Suspend/Activate
  - Manual balance adjustment
  - View transactions
  
- **Create Client** (`/admin/clients/new`)
  - **File:** `AdminClientCreate.js`
  - Username
  - Password
  - Email
  - Initial balance
  - Referral code
  
- **Client Detail** (`/admin/clients/:clientId`)
  - **File:** `AdminClientDetail.js`
  - Full profile
  - Balance details
  - Transaction history
  - Game accounts
  - Referrals
  - Activity log
  - Edit profile
  - Manual balance control

---

### **5. Games** (`/admin/games`)
**File:** `AdminGames.js`
**Features:**
- **Games List**
  - Game name
  - Display name
  - Category
  - Status (active/inactive)
  - Total accounts
  - Total balance
  - Actions
  
- **Add New Game**
  - Game name
  - Display name
  - Description
  - Category
  - Thumbnail URL
  - API configuration
  
- **Edit Game**
  - Update details
  - Toggle active status
  - Configure API endpoints
  
- **Game Statistics**
  - Total accounts
  - Total loaded
  - Total redeemed
  - Active players

---

### **6. Rules** (`/admin/rules`)
**File:** `AdminRulesEngine.js`
**Features:**
- **Global Business Rules**
  - Maximum load limit ($5 default)
  - Minimum wagering (3x default)
  - Maximum balance (5x default)
  - Auto-approval thresholds
  
- **Rule Configuration**
  - Enable/disable rules
  - Set thresholds
  - Configure notifications
  
- **Per-Client Rules Override**
  - Custom limits per user
  - VIP settings
  - Restriction management

---

### **7. Referrals** (`/admin/referrals`)
**File:** `AdminReferrals.js`
**Features:**
- **Referral Overview**
  - Total referrals system-wide
  - Active referral codes
  - Commission earned
  - Top referrers
  
- **Referral List**
  - Referrer username
  - Referral code
  - Total referrals
  - Total commissions
  - Status
  
- **Commission Settings**
  - Commission percentage
  - Minimum payout
  - Auto-payout settings

---

### **8. Promo Codes** (`/admin/promo-codes`)
**File:** `AdminPromoCodes.js`
**Features:**
- **Create Promo Code**
  - Code (alphanumeric, uppercase)
  - Credit amount ($1-$10,000)
  - Max redemptions (optional)
  - Expiry date (days until expiration)
  - Description (internal note)
  
- **Active Codes List**
  - Code
  - Amount
  - Redeemed / Max
  - Expiry date
  - Status
  - Actions: Edit / Deactivate / Delete
  
- **Redemption History**
  - Username
  - Code used
  - Amount
  - Date redeemed

---

### **9. Balance Control** (`/admin/balance-control`) ⭐ NEW
**File:** `AdminBalanceControl.js`
**Features:**
- **Manual Balance Adjustment**
  - Search user
  - Current balance display
  - Adjustment type (add/subtract)
  - Amount input
  - Reason (required)
  - Confirmation
  
- **Adjustment History**
  - Username
  - Previous balance
  - Adjustment amount
  - New balance
  - Reason
  - Admin who made change
  - Timestamp
  
- **Audit Trail**
  - All changes logged
  - Cannot be deleted
  - Exportable report

---

### **10. Reports** (`/admin/reports`)
**File:** `AdminReports.js`
**Features:**
- **Financial Reports**
  - Revenue summary
  - Deposits vs Withdrawals
  - Game loads/redeems
  - Commission paid
  
- **User Reports**
  - New registrations
  - Active users
  - User retention
  - Top players
  
- **Game Reports**
  - Most popular games
  - Load volume per game
  - Redeem volume per game
  - Profitability
  
- **Export Options**
  - CSV download
  - PDF download
  - Date range selection
  - Custom filters

---

### **11. System** (`/admin/system`)
**File:** `AdminSystem.js`
**Sub-sections:**

#### **11.1 Webhooks** (`/admin/system/webhooks`)
**File:** `SystemWebhooks.js`
- Configure webhook URLs
- Test webhooks
- View webhook logs
- Retry failed webhooks

#### **11.2 API Access** (`/admin/system/api-access`)
**File:** `SystemAPIAccess.js`
- API keys management
- Generate new keys
- Revoke keys
- API usage statistics

#### **11.3 Documentation** (`/admin/system/documentation`)
**File:** `SystemDocumentation.js`
- API documentation
- Integration guides
- Code examples
- Changelog

#### **11.4 Rewards** (`/admin/system/rewards`)
**File:** `AdminRewards.js`
- Configure reward tiers
- Set bonus amounts
- Loyalty programs
- Achievement system

#### **11.5 Automations** (`/admin/system/automations`)
**File:** `AdminOperationsPanel.js`
- Auto-approval rules
- Scheduled tasks
- Notification triggers
- Batch operations

#### **11.6 Payment Methods** (`/admin/system/payment-methods`)
**File:** `AdminPaymentPanel.js`
- Enable/disable payment methods
- Configure GCash, PayMaya, Banks
- Set fees and limits
- Upload QR codes

#### **11.7 Telegram Bots** (`/admin/system/telegram-bots`)
**File:** `TelegramBots.js`
- Configure bot tokens
- Set chat IDs
- Webhook setup
- Test bot connection
- Bot permissions (granular control)

#### **11.8 Payment QR** (`/admin/system/payment-qr`)
**File:** `AdminPaymentQR.js`
- Upload QR codes
- Manage payment accounts
- QR code rotation
- Account verification

#### **11.9 Wallet Loads** (`/admin/system/wallet-loads`)
**File:** `AdminWalletLoads.js`
- Configure load settings
- Min/max amounts
- Processing fees
- Auto-credit rules

---

### **12. Audit Logs** (`/admin/audit-logs`)
**File:** `AdminAuditLogs.js`
**Features:**
- **Activity Log**
  - Timestamp
  - Admin user
  - Action type
  - Target (user/order/game)
  - Details
  - IP address
  
- **Filters**
  - By admin
  - By action type
  - By date range
  - By target
  
- **Export**
  - CSV download
  - Compliance reports

---

## 🔄 PORTAL INTERFACE (Legacy - Desktop)

### **Navigation Menu**
```
┌──────────────────────┐
│  🏠 Dashboard        │
│  💰 Wallet           │
│  🎮 Load Game        │
│  🎁 Rewards          │
│  👥 Referrals        │
│  💸 Withdrawals      │
│  📊 Transactions     │
│  🔐 Security         │
└──────────────────────┘
```

### **Portal Pages** (Desktop UI - Old Design)
1. **Dashboard** (`/portal`) - `PortalDashboard.js`
2. **Wallet** (`/portal/wallet`) - `PortalWallet.js`
3. **Load Game** (`/portal/load-game`) - `PortalGames.js`
4. **Rewards** (`/portal/rewards`) - `PortalRewards.js`
5. **Referrals** (`/portal/referrals`) - `PortalReferrals.js`
6. **Withdrawals** (`/portal/withdrawals`) - `PortalWithdrawals.js`
7. **Transactions** (`/portal/transactions`) - `PortalTransactions.js`
8. **Credentials** (`/portal/credentials`) - `PortalCredentials.js`
9. **Security** (`/portal/security`) - `PortalSecuritySettings.js`

---

## 🔐 PUBLIC PAGES

### **Authentication**
1. **Login** (`/login`) - `Login.js`
   - Username/password
   - Signup link
   - Demo credentials
   
2. **Admin Login** (`/admin/login`) - `AdminLogin.js`
   - Admin-only login
   - No signup link
   - Admin credentials
   
3. **Register** (`/register`) - `Register.js`
   - Username
   - Email
   - Password
   - Confirm password
   - Referral code (optional)

### **Public Access**
4. **Public Games** (`/games`) - `PublicGamesNew.js`
   - Browse games
   - Hero slider
   - Download links
   - No login required

---

## 📊 FEATURE MATRIX

| Feature | Client UI | Admin UI | Portal UI |
|---------|-----------|----------|-----------|
| Dashboard | ✅ | ✅ | ✅ |
| Wallet Management | ✅ | ✅ (view only) | ✅ |
| Add Funds | ✅ | ❌ | ✅ |
| Withdraw | ✅ | ❌ | ✅ |
| Game Accounts | ✅ | ✅ (manage) | ✅ |
| Load/Redeem Games | ✅ | ❌ | ✅ |
| Referrals | ✅ | ✅ (manage) | ✅ |
| Profile Settings | ✅ | ❌ | ✅ |
| Order Approvals | ❌ | ✅ | ❌ |
| User Management | ❌ | ✅ | ❌ |
| Reports | ❌ | ✅ | ❌ |
| System Config | ❌ | ✅ | ❌ |
| Balance Control | ❌ | ✅ | ❌ |
| Promo Codes | ✅ (use) | ✅ (create) | ✅ (use) |
| Audit Logs | ❌ | ✅ | ❌ |

---

## 🎨 UI/UX Design Systems

### **Client UI (Mobile-First)**
- **Theme:** Dark (Black background, Violet/Indigo accents)
- **Layout:** Bottom navigation bar, card-based
- **Typography:** Clean, modern sans-serif
- **Icons:** Lucide React
- **Responsive:** Mobile-optimized, scales to desktop
- **Animations:** Smooth transitions, micro-interactions

### **Admin UI (Desktop)**
- **Theme:** Dark (Black/Gray with purple accents)
- **Layout:** Sidebar navigation, table-heavy
- **Components:** Data tables, charts, modals
- **Icons:** Lucide React
- **Responsive:** Desktop-first, tablet support

### **Portal UI (Legacy Desktop)**
- **Theme:** Dark/Mixed
- **Layout:** Top navigation or sidebar
- **Components:** Cards, forms, tables
- **Status:** Being phased out in favor of Client UI

---

## 🔗 URL Structure Summary

```
/                          → Redirect to /login or /client/home
/login                     → Client login
/admin/login               → Admin login
/register                  → User registration
/games                     → Public games page

/client/*                  → New mobile-first client UI
  /home                    → Dashboard
  /wallet                  → Wallet overview
  /wallet/add              → Add funds
  /wallet/withdraw         → Withdraw
  /games                   → Game accounts
  /referrals               → Referrals
  /profile                 → Profile & settings

/admin/*                   → Admin dashboard
  /                        → Dashboard
  /approvals               → Approve orders
  /orders                  → All orders
  /clients                 → User management
  /games                   → Game management
  /rules                   → Business rules
  /referrals               → Referral system
  /promo-codes             → Promo codes
  /balance-control         → Manual balance
  /reports                 → Analytics
  /system/*                → System config
  /audit-logs              → Activity log

/portal/*                  → Legacy desktop UI
  /                        → Dashboard
  /wallet                  → Wallet
  /load-game               → Games
  /rewards                 → Rewards
  /referrals               → Referrals
  /withdrawals             → Withdrawals
  /transactions            → History
  /security                → Settings
```

---

## 📱 Mobile Navigation Flow (Client UI)

```
Login → Client Home
         ↓
    Bottom Nav Bar
         ↓
    ┌────┴────┬────────┬─────────┬─────────┐
    ↓         ↓        ↓         ↓         ↓
  Home    Wallet    Games   Referrals  Profile
    │         │        │         │         │
    │    ┌────┴───┐    │         │    ┌────┴────┐
    │    ↓        ↓    │         │    ↓         ↓
    │  Add      Withdraw│         │  Edit    Change
    │  Funds            │         │  Info    Password
    │                   │         │
    │              ┌────┴────┬────┴────┐
    │              ↓         ↓         ↓
    │           Create    Load    Redeem
    │           Account
```

---

## 🖥️ Admin Navigation Flow

```
Admin Login → Admin Dashboard
               ↓
          Sidebar Menu
               ↓
    ┌──────────┼───────────────────────────┐
    ↓          ↓          ↓         ↓      ↓
Approvals  Clients    Games    Orders  System
    │          │          │         │      │
    │     ┌────┴────┐     │         │  ┌───┴───┬────────┐
    │     ↓         ↓     │         │  ↓       ↓        ↓
    │   View     Create   │         │ Webhooks  API  Telegram
    │   Detail   Client   │         │  
    │                     │         │
    │               ┌─────┴─────┐   │
    │               ↓           ↓   │
    │            Add Game   Edit Game
```

---

## 🎯 Total Page Count

- **Client UI:** 6 pages (mobile-first)
- **Admin UI:** 25+ pages (desktop dashboard)
- **Portal UI:** 14 pages (legacy desktop)
- **Public Pages:** 4 pages
- **Total:** 49+ unique pages

---

**Last Updated:** January 17, 2026
**Version:** 1.0.0
**Status:** ✅ Production Ready
