"""
Games API Integration Service
Handles interaction with automation.joycegames.vip API

Production-hardened with:
- Strict token validation (no demo fallback)
- Configurable timeouts with exponential backoff retries
- Structured logging for observability
- Safe error handling
"""
import httpx
import os
import asyncio
import time
from typing import Optional, Dict, Any

from api.v1.core.structured_logging import (
    log_games_api_request,
    log_games_api_response,
    get_correlation_id,
    games_api_logger
)
from api.v1.core.exception_handler import GamesAPIError, ConfigurationError


class GamesAPIClient:
    """
    Production-ready client for interacting with Games API.
    
    Features:
    - Fails fast if AUTOMATION_TOKEN is missing
    - Configurable request timeout (default 15s)
    - Exponential backoff retries for transient failures
    - Structured logging for all operations
    """
    
    # Default configuration
    DEFAULT_TIMEOUT_SECONDS = 15.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BASE_RETRY_DELAY = 1.0  # seconds
    
    # Retryable status codes
    RETRYABLE_STATUS_CODES = {502, 503, 504, 429}
    
    def __init__(self, api_token: Optional[str] = None):
        self.base_url = os.getenv("AUTOMATION_BASE_URL", "https://automation.joycegames.vip")
        
        # STRICT: No fallback token - fail fast if not configured
        self.token = api_token or os.getenv("AUTOMATION_TOKEN")
        if not self.token:
            raise ConfigurationError(
                message="AUTOMATION_TOKEN is required for Games API integration",
                config_key="AUTOMATION_TOKEN"
            )
        
        # Timeout configuration (in seconds)
        timeout_ms = os.getenv("AUTOMATION_TIMEOUT_MS")
        if timeout_ms:
            self.timeout = float(timeout_ms) / 1000.0
        else:
            self.timeout = self.DEFAULT_TIMEOUT_SECONDS
        
        # Retry configuration
        self.max_retries = int(os.getenv("AUTOMATION_MAX_RETRIES", str(self.DEFAULT_MAX_RETRIES)))
        self.base_retry_delay = float(os.getenv("AUTOMATION_RETRY_DELAY", str(self.DEFAULT_BASE_RETRY_DELAY)))
        
        # Endpoints
        self.create_endpoint = os.getenv("AUTOMATION_CREATE_ENDPOINT", "/api/game/create-account/")
        self.load_endpoint = os.getenv("AUTOMATION_LOAD_ENDPOINT", "/api/game/recharge/")
        self.redeem_endpoint = os.getenv("AUTOMATION_REDEEM_ENDPOINT", "/api/game/redeem/")
        self.balance_endpoint = os.getenv("AUTOMATION_GET_USER_BALANCE_ENDPOINT", "/api/game/get-balance/{game_id}/{user_id}/")
        
    async def __aenter__(self):
        # Configure httpx client with proper timeouts
        timeout_config = httpx.Timeout(
            connect=5.0,  # Connection timeout
            read=self.timeout,  # Read timeout
            write=10.0,  # Write timeout
            pool=5.0  # Pool timeout
        )
        self.client = httpx.AsyncClient(timeout=timeout_config)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'client'):
            await self.client.aclose()
    
    def _should_retry(self, status_code: int) -> bool:
        """Determine if request should be retried based on status code."""
        return status_code in self.RETRYABLE_STATUS_CODES
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        import random
        delay = self.base_retry_delay * (2 ** attempt)
        # Add jitter (±25%)
        jitter = delay * 0.25 * (random.random() * 2 - 1)
        return min(delay + jitter, 30.0)  # Cap at 30 seconds
            
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        operation: str = "unknown",
        game_id: str = "",
        user_id: str = ""
    ) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.
        
        Args:
            method: HTTP method (GET/POST)
            endpoint: API endpoint
            data: Request payload
            operation: Operation name for logging
            game_id: Game ID for logging
            user_id: User ID for logging
            
        Returns:
            API response as dict
            
        Raises:
            GamesAPIError: On unrecoverable API errors
        """
        if not hasattr(self, 'client'):
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        url = f"{self.base_url}{endpoint}"
        params = {"token": self.token}
        correlation_id = get_correlation_id()
        
        # Log the request
        log_games_api_request(
            operation=operation,
            game_id=game_id,
            user_id=user_id,
            amount=data.get("amount") if data else None,
            correlation_id=correlation_id
        )
        
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.max_retries + 1):
            start_time = time.monotonic()
            
            try:
                if method == "GET":
                    response = await self.client.get(url, params=params)
                elif method == "POST":
                    response = await self.client.post(url, json=data, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response_time_ms = (time.monotonic() - start_time) * 1000
                
                # Check for retryable status codes
                if response.status_code >= 400:
                    if self._should_retry(response.status_code) and attempt < self.max_retries:
                        backoff = self._calculate_backoff(attempt)
                        games_api_logger.warning(
                            "games_api.retry",
                            extra={
                                "operation": operation,
                                "status_code": response.status_code,
                                "attempt": attempt + 1,
                                "max_retries": self.max_retries,
                                "backoff_seconds": backoff,
                                "correlation_id": correlation_id
                            }
                        )
                        await asyncio.sleep(backoff)
                        continue
                    
                    # Non-retryable error or max retries exceeded
                    response.raise_for_status()
                
                # Success - parse response
                result = response.json() if response.text.strip() else {"success": True}
                
                # Log success
                log_games_api_response(
                    operation=operation,
                    game_id=game_id,
                    user_id=user_id,
                    success=True,
                    response_time_ms=response_time_ms,
                    correlation_id=correlation_id
                )
                
                return result
                
            except httpx.TimeoutException as e:
                response_time_ms = (time.monotonic() - start_time) * 1000
                last_exception = e
                
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    games_api_logger.warning(
                        "games_api.timeout_retry",
                        extra={
                            "operation": operation,
                            "attempt": attempt + 1,
                            "max_retries": self.max_retries,
                            "backoff_seconds": backoff,
                            "correlation_id": correlation_id
                        }
                    )
                    await asyncio.sleep(backoff)
                    continue
                
                # Max retries exceeded
                log_games_api_response(
                    operation=operation,
                    game_id=game_id,
                    user_id=user_id,
                    success=False,
                    response_time_ms=response_time_ms,
                    correlation_id=correlation_id,
                    error=f"Timeout after {self.max_retries + 1} attempts"
                )
                raise GamesAPIError(
                    message=f"Games API timeout after {self.max_retries + 1} attempts",
                    original_error=e,
                    is_timeout=True
                )
                
            except httpx.HTTPStatusError as e:
                response_time_ms = (time.monotonic() - start_time) * 1000
                log_games_api_response(
                    operation=operation,
                    game_id=game_id,
                    user_id=user_id,
                    success=False,
                    response_time_ms=response_time_ms,
                    correlation_id=correlation_id,
                    error=f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                )
                raise GamesAPIError(
                    message=f"Games API error: HTTP {e.response.status_code}",
                    original_error=e,
                    is_timeout=False
                )
                
            except Exception as e:
                response_time_ms = (time.monotonic() - start_time) * 1000
                log_games_api_response(
                    operation=operation,
                    game_id=game_id,
                    user_id=user_id,
                    success=False,
                    response_time_ms=response_time_ms,
                    correlation_id=correlation_id,
                    error=str(e)
                )
                raise GamesAPIError(
                    message=f"Games API request failed: {str(e)}",
                    original_error=e,
                    is_timeout=False
                )
        
        # Should not reach here, but handle edge case
        raise GamesAPIError(
            message="Games API request failed after all retries",
            original_error=last_exception,
            is_timeout=isinstance(last_exception, httpx.TimeoutException)
        )
            
    async def create_account(
        self,
        game_id: str,
        username_hint: str,
        account: Optional[str] = None,
        nickname: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new game account."""
        data = {
            "game_id": game_id,
            "username_hint": username_hint
        }
        if account:
            data["account"] = account
        if nickname:
            data["nickname"] = nickname
        if password:
            data["password"] = password
            
        return await self._make_request(
            method="POST",
            endpoint=self.create_endpoint,
            data=data,
            operation="create_account",
            game_id=game_id,
            user_id=username_hint
        )
        
    async def get_balance(self, game_id: str, user_id: str) -> Dict[str, Any]:
        """Get player balance for a specific game."""
        endpoint = self.balance_endpoint.format(game_id=game_id, user_id=user_id)
        return await self._make_request(
            method="GET",
            endpoint=endpoint,
            operation="get_balance",
            game_id=game_id,
            user_id=user_id
        )
        
    async def recharge(
        self,
        game_id: str,
        user_id: str,
        amount: float,
        remark: str
    ) -> Dict[str, Any]:
        """Add credits to player game account."""
        data = {
            "game_id": game_id,
            "user_id": user_id,
            "amount": str(amount),
            "remark": remark
        }
        return await self._make_request(
            method="POST",
            endpoint=self.load_endpoint,
            data=data,
            operation="recharge",
            game_id=game_id,
            user_id=user_id
        )
        
    async def redeem(
        self,
        game_id: str,
        user_id: str,
        amount: float,
        remark: str
    ) -> Dict[str, Any]:
        """Withdraw credits from player game account."""
        data = {
            "game_id": game_id,
            "user_id": user_id,
            "amount": str(amount),
            "remark": remark
        }
        return await self._make_request(
            method="POST",
            endpoint=self.redeem_endpoint,
            data=data,
            operation="redeem",
            game_id=game_id,
            user_id=user_id
        )

