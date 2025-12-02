"""Rate limiting for WebSocket messages using token bucket algorithm"""
import time
from typing import Dict, List


class RateLimiter:
    """In-memory token bucket rate limiter for per-user message limiting"""
    
    def __init__(self, messages_per_window: int = 3, window_seconds: float = 1.0, cooldown_seconds: float = 2.0) -> None:
        """
        Initialize rate limiter with configurable limits.
        
        Args:
            messages_per_window: Number of messages allowed in the window
            window_seconds: Time window in seconds
            cooldown_seconds: Cooldown period after exceeding limit
        """
        self.MESSAGES_PER_WINDOW = messages_per_window
        self.WINDOW_SECONDS = window_seconds
        self.COOLDOWN_SECONDS = cooldown_seconds
        
        # Structure: {user_id: {"timestamps": [t1, t2, ...], "blocked_until": float | None}}
        self.user_limits: Dict[str, dict] = {}
    
    def is_rate_limited(self, user_id: str) -> tuple[bool, str | None]:
        """
        Check if user has exceeded rate limit.
        
        Returns:
            (is_limited, error_message)
            - is_limited: True if user should be blocked
            - error_message: User-friendly error message or None if allowed
        """
        now = time.time()
        
        # Initialize user if not tracked yet
        if user_id not in self.user_limits:
            self.user_limits[user_id] = {
                "timestamps": [],
                "blocked_until": None
            }
        
        user_data = self.user_limits[user_id]
        
        # Check if user is in cooldown period
        if user_data["blocked_until"] is not None:
            if now < user_data["blocked_until"]:
                retry_after = int(user_data["blocked_until"] - now) + 1
                return True, f"Rate limited. Try again in {retry_after} second(s)."
            else:
                # Cooldown expired, reset
                user_data["blocked_until"] = None
                user_data["timestamps"] = []
        
        # Remove timestamps older than window
        cutoff = now - self.WINDOW_SECONDS
        user_data["timestamps"] = [ts for ts in user_data["timestamps"] if ts > cutoff]
        
        # Check if under limit
        if len(user_data["timestamps"]) < self.MESSAGES_PER_WINDOW:
            # Allow message and record timestamp
            user_data["timestamps"].append(now)
            return False, None
        else:
            # Exceeded limit - activate cooldown
            user_data["blocked_until"] = now + self.COOLDOWN_SECONDS
            retry_after = self.COOLDOWN_SECONDS
            return True, f"Too many messages. Try again in {retry_after} second(s)."
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get current rate limit stats for a user (for monitoring)"""
        if user_id not in self.user_limits:
            return {
                "user_id": user_id,
                "messages_in_window": 0,
                "limit": self.MESSAGES_PER_WINDOW,
                "is_blocked": False,
                "blocked_until": None
            }
        
        user_data = self.user_limits[user_id]
        now = time.time()
        
        # Clean up old timestamps
        cutoff = now - self.WINDOW_SECONDS
        valid_timestamps = [ts for ts in user_data["timestamps"] if ts > cutoff]
        
        is_blocked = (
            user_data["blocked_until"] is not None 
            and now < user_data["blocked_until"]
        )
        
        return {
            "user_id": user_id,
            "messages_in_window": len(valid_timestamps),
            "limit": self.MESSAGES_PER_WINDOW,
            "is_blocked": is_blocked,
            "blocked_until": user_data["blocked_until"]
        }
    
    def reset_user(self, user_id: str) -> None:
        """Reset rate limit for a user (admin function)"""
        if user_id in self.user_limits:
            self.user_limits[user_id] = {
                "timestamps": [],
                "blocked_until": None
            }
    
    def cleanup_old_entries(self, max_idle_seconds: int = 3600) -> int:
        """
        Clean up user entries that haven't had activity in max_idle_seconds.
        Useful for long-running servers to prevent memory bloat.
        
        Returns: Number of users cleaned up
        """
        now = time.time()
        users_to_remove = []
        
        for user_id, user_data in self.user_limits.items():
            if user_data["timestamps"]:
                last_activity = max(user_data["timestamps"])
            else:
                last_activity = 0
            
            if (now - last_activity) > max_idle_seconds:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.user_limits[user_id]
        
        return len(users_to_remove)


# Global rate limiter instance
rate_limiter = RateLimiter()
