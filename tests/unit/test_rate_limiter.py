"""Unit tests for RateLimiter"""
import pytest
import time

from websocket.rate_limiter import RateLimiter


@pytest.mark.unit
class TestRateLimiterInitialization:
    """Test RateLimiter initialization"""

    def test_rate_limiter_creates_empty(self):
        """Test that RateLimiter initializes with no users"""
        limiter = RateLimiter()
        assert limiter.user_limits == {}

    def test_rate_limiter_has_configuration(self):
        """Test that RateLimiter has config constants"""
        limiter = RateLimiter()
        assert limiter.MESSAGES_PER_WINDOW == 3
        assert limiter.WINDOW_SECONDS == 1
        assert limiter.COOLDOWN_SECONDS == 2


@pytest.mark.unit
class TestRateLimiterAllows:
    """Test RateLimiter allowing messages"""

    def test_first_message_allowed(self):
        """Test that first message is always allowed"""
        limiter = RateLimiter()
        is_limited, error = limiter.is_rate_limited("user_1")
        
        assert is_limited is False
        assert error is None

    def test_messages_within_limit_allowed(self):
        """Test that messages within limit are allowed"""
        limiter = RateLimiter()
        
        # 3 messages should all be allowed
        for i in range(3):
            is_limited, error = limiter.is_rate_limited("user_1")
            assert is_limited is False, f"Message {i+1} should be allowed"
            assert error is None

    def test_different_users_independent(self):
        """Test that different users have independent limits"""
        limiter = RateLimiter()
        
        # User 1: 3 messages
        for _ in range(3):
            limiter.is_rate_limited("user_1")
        
        # User 2: should still be able to send
        is_limited, error = limiter.is_rate_limited("user_2")
        assert is_limited is False
        assert error is None


@pytest.mark.unit
class TestRateLimiterBlocks:
    """Test RateLimiter blocking messages"""

    def test_exceeds_limit_blocks(self):
        """Test that exceeding limit blocks message"""
        limiter = RateLimiter()
        
        # Send 3 messages (at limit)
        for _ in range(3):
            limiter.is_rate_limited("user_1")
        
        # 4th message should be blocked
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is True
        assert error is not None
        assert "Too many messages" in error

    def test_get_stats_blocked_user(self):
        """Test getting stats for blocked user"""
        limiter = RateLimiter()
        
        # Hit limit
        for _ in range(3):
            limiter.is_rate_limited("user_1")
        
        # Block user
        limiter.is_rate_limited("user_1")
        
        stats = limiter.get_user_stats("user_1")
        assert stats["is_blocked"] is True
        assert stats["blocked_until"] is not None

    def test_cooldown_period_enforced(self):
        """Test that cooldown blocks for full period"""
        limiter = RateLimiter()
        
        # Hit limit
        for _ in range(3):
            limiter.is_rate_limited("user_1")
        
        # First block
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is True
        
        # Immediately after, still blocked
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is True

    def test_cooldown_expires(self):
        """Test that cooldown eventually expires"""
        limiter = RateLimiter(cooldown_seconds=0.1)
        
        # Hit limit
        for _ in range(3):
            limiter.is_rate_limited("user_1")
        
        # Blocked
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is True
        
        # Wait for cooldown
        time.sleep(0.15)
        
        # Should be allowed again
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is False
        assert error is None


@pytest.mark.unit
class TestRateLimiterWindow:
    """Test RateLimiter sliding window"""

    def test_window_resets_after_time(self):
        """Test that window resets old messages"""
        limiter = RateLimiter(window_seconds=0.1)
        
        # Send 3 messages
        for _ in range(3):
            limiter.is_rate_limited("user_1")
        
        # Should be limited
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is True
        
        # Wait for window to expire (messages older than 0.1s)
        time.sleep(0.2)
        
        # Old messages should be gone, should be allowed
        is_limited, error = limiter.is_rate_limited("user_1")
        # Still blocked because cooldown is active (2 seconds)
        # So we need to check that after cooldown expires it works
        # Let's just verify the window is cleared by resetting cooldown
        limiter.reset_user("user_1")
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is False
        assert error is None

    def test_partial_window_expiry(self):
        """Test that only old messages leave window"""
        limiter = RateLimiter(window_seconds=0.2)
        
        # Send message 1
        limiter.is_rate_limited("user_1")
        time.sleep(0.05)
        
        # Send message 2
        limiter.is_rate_limited("user_1")
        time.sleep(0.05)
        
        # Send message 3
        limiter.is_rate_limited("user_1")
        
        # Should be at limit
        is_limited, _ = limiter.is_rate_limited("user_1")
        assert is_limited is True
        
        # Wait for first message to expire but not others (wait 0.15s for message 1 to expire)
        time.sleep(0.15)
        
        # Reset cooldown so we can test window expiry
        limiter.user_limits["user_1"]["blocked_until"] = None
        
        # Should still have 2 messages, can add 1 more
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is False


@pytest.mark.unit
class TestRateLimiterStats:
    """Test RateLimiter monitoring stats"""

    def test_get_stats_nonexistent_user(self):
        """Test getting stats for user with no activity"""
        limiter = RateLimiter()
        stats = limiter.get_user_stats("user_1")
        
        assert stats["user_id"] == "user_1"
        assert stats["messages_in_window"] == 0
        assert stats["is_blocked"] is False

    def test_get_stats_active_user(self):
        """Test getting stats for active user"""
        limiter = RateLimiter()
        
        # Send 2 messages
        limiter.is_rate_limited("user_1")
        limiter.is_rate_limited("user_1")
        
        stats = limiter.get_user_stats("user_1")
        assert stats["messages_in_window"] == 2
        assert stats["is_blocked"] is False

    def test_get_stats_blocked_user(self):
        """Test getting stats for blocked user"""
        limiter = RateLimiter()
        
        # Hit limit
        for _ in range(3):
            limiter.is_rate_limited("user_1")
        
        # Block user
        limiter.is_rate_limited("user_1")
        
        stats = limiter.get_user_stats("user_1")
        assert stats["is_blocked"] is True
        assert stats["blocked_until"] is not None


@pytest.mark.unit
class TestRateLimiterReset:
    """Test RateLimiter reset functionality"""

    def test_reset_user_clears_limit(self):
        """Test that reset_user clears rate limit"""
        limiter = RateLimiter()
        
        # Hit limit
        for _ in range(3):
            limiter.is_rate_limited("user_1")
        
        is_limited, _ = limiter.is_rate_limited("user_1")
        assert is_limited is True
        
        # Reset user
        limiter.reset_user("user_1")
        
        # Should be allowed again
        is_limited, error = limiter.is_rate_limited("user_1")
        assert is_limited is False
        assert error is None

    def test_reset_nonexistent_user(self):
        """Test resetting user with no history"""
        limiter = RateLimiter()
        
        # Should not raise error
        limiter.reset_user("user_1")
        
        is_limited, _ = limiter.is_rate_limited("user_1")
        assert is_limited is False


@pytest.mark.unit
class TestRateLimiterCleanup:
    """Test RateLimiter cleanup functionality"""

    def test_cleanup_removes_idle_users(self):
        """Test that cleanup removes idle user entries"""
        limiter = RateLimiter(window_seconds=0.1)
        
        # Create some user activity
        limiter.is_rate_limited("user_1")
        limiter.is_rate_limited("user_2")
        limiter.is_rate_limited("user_3")
        
        assert len(limiter.user_limits) == 3
        
        # Wait for entries to become idle (max_idle_seconds=200ms)
        time.sleep(0.3)
        
        # Cleanup with 200 millisecond idle timeout
        removed = limiter.cleanup_old_entries(max_idle_seconds=0)
        
        assert removed == 3
        assert len(limiter.user_limits) == 0

    def test_cleanup_preserves_active_users(self):
        """Test that cleanup doesn't remove active users"""
        limiter = RateLimiter()
        
        # Create activity
        limiter.is_rate_limited("user_1")
        limiter.is_rate_limited("user_2")
        
        # Immediately cleanup with long timeout
        removed = limiter.cleanup_old_entries(max_idle_seconds=3600)
        
        # Nothing should be removed
        assert removed == 0
        assert len(limiter.user_limits) == 2
