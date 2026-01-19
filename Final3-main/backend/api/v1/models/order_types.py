"""
Order Types and Flow Management
Properly distinguish between wallet_load, game_load, and withdrawal

CANONICAL STATUS CONSTANTS - Use these everywhere
"""
from enum import Enum


class OrderType(str, Enum):
    """Order type classification"""
    WALLET_LOAD = "wallet_load"  # Payment IN - Add money to wallet (no game)
    GAME_LOAD = "game_load"      # Load game from wallet (has game, calls API)
    WITHDRAWAL_WALLET = "withdrawal_wallet"  # Withdraw from wallet balance
    WITHDRAWAL_GAME = "withdrawal_game"      # Withdraw from game (redeem first)
    # Legacy types (for backwards compatibility with existing data)
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class OrderStatus(str, Enum):
    """
    Canonical order status values.
    
    State machine:
    PENDING_APPROVAL -> APPROVED -> COMPLETED
                    \-> REJECTED
                    \-> FAILED
    
    Legacy mappings (for query compatibility):
    - 'pending_review', 'awaiting_payment_proof', 'initiated' -> PENDING_APPROVAL
    - 'APPROVED_EXECUTED', 'confirmed' -> APPROVED
    """
    PENDING_APPROVAL = "pending_approval"  # Waiting for admin/telegram approval
    APPROVED = "approved"                   # Approved, balance updated
    COMPLETED = "completed"                 # Fully processed (game load success, etc.)
    FAILED = "failed"                       # Failed after approval (API error, etc.)
    REJECTED = "rejected"                   # Admin rejected
    CANCELLED = "cancelled"                 # User cancelled
    
    @classmethod
    def pending_statuses(cls) -> list:
        """Status values that represent pending orders (includes legacy)"""
        return [
            cls.PENDING_APPROVAL.value,
            "pending_review",        # legacy
            "awaiting_payment_proof", # legacy
            "initiated"              # legacy
        ]
    
    @classmethod
    def approved_statuses(cls) -> list:
        """Status values that represent approved orders (includes legacy)"""
        return [
            cls.APPROVED.value,
            cls.COMPLETED.value,
            "APPROVED_EXECUTED",     # legacy
            "confirmed"              # legacy
        ]


# Flow definitions
FLOWS = {
    "wallet_load": {
        "description": "User deposits money to wallet",
        "requires_game": False,
        "telegram_approval": True,
        "api_action": None,
        "balance_operation": "credit_wallet"
    },
    "game_load": {
        "description": "User loads game from wallet balance",
        "requires_game": True,
        "telegram_approval": False,  # Instant if balance available
        "api_action": "recharge",
        "balance_operation": "debit_wallet_credit_game"
    },
    "withdrawal_wallet": {
        "description": "User withdraws from wallet to bank",
        "requires_game": False,
        "telegram_approval": True,
        "api_action": None,
        "balance_operation": "debit_wallet_pending",
        "refund_on_fail": True
    },
    "withdrawal_game": {
        "description": "User withdraws from game to bank",
        "requires_game": True,
        "telegram_approval": True,
        "api_action": "redeem",  # Redeem from game first
        "balance_operation": "credit_wallet_then_debit",
        "refund_on_fail": False  # Already in wallet
    }
}
