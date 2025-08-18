"""
Redis-based rate limiting for authentication attempts and API calls.
Implements sliding window and fixed window rate limiting strategies.
"""

import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import redis

from .pii_protection import get_structured_logger

logger = get_structured_logger().get_logger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitRule:
    """Rate limit rule configuration"""

    max_attempts: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    block_duration: int = 300  # 5 minutes default block


@dataclass
class RateLimitResult:
    """Rate limit check result"""

    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None


class RedisRateLimiter:
    """Redis-based rate limiter with multiple strategies"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.prefix = "rate_limit:"
        self.block_prefix = "blocked:"

        # Default rate limit rules
        self.default_rules = {
            "auth_login": RateLimitRule(
                5, 300, RateLimitStrategy.SLIDING_WINDOW, 900
            ),  # 5 attempts per 5 min, block 15 min
            "auth_register": RateLimitRule(
                3, 3600, RateLimitStrategy.FIXED_WINDOW, 3600
            ),  # 3 attempts per hour
            "password_reset": RateLimitRule(
                3, 3600, RateLimitStrategy.SLIDING_WINDOW, 3600
            ),  # 3 attempts per hour
            "api_call": RateLimitRule(
                100, 60, RateLimitStrategy.TOKEN_BUCKET, 60
            ),  # 100 calls per minute
            "session_create": RateLimitRule(
                10, 300, RateLimitStrategy.SLIDING_WINDOW, 600
            ),  # 10 sessions per 5 min
        }

        logger.info("Rate limiter initialized", rules_count=len(self.default_rules))

    def _get_key(self, identifier: str, rule_name: str) -> str:
        """Generate Redis key for rate limiting"""
        # Hash identifier for privacy
        hashed_id = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"{self.prefix}{rule_name}:{hashed_id}"

    def _get_block_key(self, identifier: str, rule_name: str) -> str:
        """Generate Redis key for blocking"""
        hashed_id = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"{self.block_prefix}{rule_name}:{hashed_id}"

    def check_rate_limit(
        self,
        identifier: str,
        rule_name: str,
        custom_rule: Optional[RateLimitRule] = None,
    ) -> RateLimitResult:
        """
        Check if request is within rate limit

        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            rule_name: Name of the rate limit rule
            custom_rule: Custom rule to override default

        Returns:
            RateLimitResult with allow/deny decision
        """
        try:
            rule = custom_rule or self.default_rules.get(rule_name)
            if not rule:
                logger.warning("Unknown rate limit rule", rule_name=rule_name)
                return RateLimitResult(True, 999, datetime.utcnow())

            # Check if currently blocked
            block_key = self._get_block_key(identifier, rule_name)
            if self.redis_client.exists(block_key):
                ttl = self.redis_client.ttl(block_key)
                retry_after = max(ttl, 0)
                reset_time = datetime.utcnow() + timedelta(seconds=retry_after)

                logger.info(
                    "Request blocked by rate limiter",
                    rule_name=rule_name,
                    retry_after=retry_after,
                    operation="check_rate_limit",
                )

                return RateLimitResult(False, 0, reset_time, retry_after)

            # Apply rate limiting strategy
            if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._sliding_window_check(identifier, rule_name, rule)
            elif rule.strategy == RateLimitStrategy.FIXED_WINDOW:
                return self._fixed_window_check(identifier, rule_name, rule)
            elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._token_bucket_check(identifier, rule_name, rule)
            else:
                logger.error(
                    "Unknown rate limit strategy", strategy=rule.strategy.value
                )
                return RateLimitResult(True, rule.max_attempts, datetime.utcnow())

        except Exception as e:
            logger.error(
                "Rate limit check failed",
                rule_name=rule_name,
                error_type=type(e).__name__,
                operation="check_rate_limit",
            )
            # Fail open for availability
            return RateLimitResult(True, 999, datetime.utcnow())

    def _sliding_window_check(
        self, identifier: str, rule_name: str, rule: RateLimitRule
    ) -> RateLimitResult:
        """Sliding window rate limiting"""
        key = self._get_key(identifier, rule_name)
        now = time.time()
        window_start = now - rule.window_seconds

        pipe = self.redis_client.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current entries
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiration
        pipe.expire(key, rule.window_seconds)

        results = pipe.execute()
        current_count = results[1] + 1  # +1 for the request we just added

        if current_count > rule.max_attempts:
            # Block the identifier
            self._block_identifier(identifier, rule_name, rule.block_duration)

            reset_time = datetime.utcnow() + timedelta(seconds=rule.block_duration)
            return RateLimitResult(False, 0, reset_time, rule.block_duration)

        remaining = rule.max_attempts - current_count
        reset_time = datetime.utcnow() + timedelta(seconds=rule.window_seconds)

        return RateLimitResult(True, remaining, reset_time)

    def _fixed_window_check(
        self, identifier: str, rule_name: str, rule: RateLimitRule
    ) -> RateLimitResult:
        """Fixed window rate limiting"""
        now = time.time()
        window = int(now // rule.window_seconds)
        key = f"{self._get_key(identifier, rule_name)}:{window}"

        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, rule.window_seconds)
        results = pipe.execute()

        current_count = results[0]

        if current_count > rule.max_attempts:
            # Block the identifier
            self._block_identifier(identifier, rule_name, rule.block_duration)

            reset_time = datetime.utcnow() + timedelta(seconds=rule.block_duration)
            return RateLimitResult(False, 0, reset_time, rule.block_duration)

        remaining = rule.max_attempts - current_count
        window_end = (window + 1) * rule.window_seconds
        reset_time = datetime.fromtimestamp(window_end)

        return RateLimitResult(True, remaining, reset_time)

    def _token_bucket_check(
        self, identifier: str, rule_name: str, rule: RateLimitRule
    ) -> RateLimitResult:
        """Token bucket rate limiting"""
        key = self._get_key(identifier, rule_name)
        now = time.time()

        # Get current bucket state
        bucket_data = self.redis_client.hmget(key, "tokens", "last_refill")
        tokens = float(bucket_data[0] or rule.max_attempts)
        last_refill = float(bucket_data[1] or now)

        # Calculate tokens to add based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = (time_elapsed / rule.window_seconds) * rule.max_attempts
        tokens = min(rule.max_attempts, tokens + tokens_to_add)

        if tokens < 1:
            # Not enough tokens
            reset_time = datetime.utcnow() + timedelta(
                seconds=(1 - tokens) * rule.window_seconds / rule.max_attempts
            )
            retry_after = int((1 - tokens) * rule.window_seconds / rule.max_attempts)

            return RateLimitResult(False, 0, reset_time, retry_after)

        # Consume one token
        tokens -= 1

        # Update bucket state
        pipe = self.redis_client.pipeline()
        pipe.hset(key, mapping={"tokens": tokens, "last_refill": now})
        pipe.expire(key, rule.window_seconds * 2)  # Keep bucket alive
        pipe.execute()

        remaining = int(tokens)
        reset_time = datetime.utcnow() + timedelta(seconds=rule.window_seconds)

        return RateLimitResult(True, remaining, reset_time)

    def _block_identifier(self, identifier: str, rule_name: str, duration: int):
        """Block identifier for specified duration"""
        block_key = self._get_block_key(identifier, rule_name)
        self.redis_client.setex(block_key, duration, "blocked")

        logger.warning(
            "Identifier blocked due to rate limit exceeded",
            rule_name=rule_name,
            duration=duration,
            operation="block_identifier",
        )

    def unblock_identifier(self, identifier: str, rule_name: str) -> bool:
        """Manually unblock an identifier"""
        try:
            block_key = self._get_block_key(identifier, rule_name)
            result = self.redis_client.delete(block_key)

            if result:
                logger.info(
                    "Identifier unblocked",
                    rule_name=rule_name,
                    operation="unblock_identifier",
                )

            return bool(result)

        except Exception as e:
            logger.error(
                "Failed to unblock identifier",
                rule_name=rule_name,
                error_type=type(e).__name__,
                operation="unblock_identifier",
            )
            return False

    def get_rate_limit_status(self, identifier: str, rule_name: str) -> Dict[str, Any]:
        """Get current rate limit status for identifier"""
        try:
            rule = self.default_rules.get(rule_name)
            if not rule:
                return {"error": "Unknown rule"}

            # Check if blocked
            block_key = self._get_block_key(identifier, rule_name)
            blocked_ttl = self.redis_client.ttl(block_key)

            if blocked_ttl > 0:
                return {
                    "blocked": True,
                    "retry_after": blocked_ttl,
                    "rule": rule_name,
                    "max_attempts": rule.max_attempts,
                    "window_seconds": rule.window_seconds,
                }

            # Get current usage
            key = self._get_key(identifier, rule_name)

            if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                now = time.time()
                window_start = now - rule.window_seconds
                self.redis_client.zremrangebyscore(key, 0, window_start)
                current_count = self.redis_client.zcard(key)
            elif rule.strategy == RateLimitStrategy.FIXED_WINDOW:
                window = int(time.time() // rule.window_seconds)
                window_key = f"{key}:{window}"
                current_count = int(self.redis_client.get(window_key) or 0)
            else:  # TOKEN_BUCKET
                bucket_data = self.redis_client.hmget(key, "tokens")
                current_tokens = float(bucket_data[0] or rule.max_attempts)
                current_count = rule.max_attempts - int(current_tokens)

            remaining = max(0, rule.max_attempts - current_count)

            return {
                "blocked": False,
                "current_count": current_count,
                "remaining": remaining,
                "rule": rule_name,
                "max_attempts": rule.max_attempts,
                "window_seconds": rule.window_seconds,
                "strategy": rule.strategy.value,
            }

        except Exception as e:
            logger.error(
                "Failed to get rate limit status",
                rule_name=rule_name,
                error_type=type(e).__name__,
                operation="get_rate_limit_status",
            )
            return {"error": "Failed to get status"}

    def reset_rate_limit(self, identifier: str, rule_name: str) -> bool:
        """Reset rate limit for identifier"""
        try:
            key = self._get_key(identifier, rule_name)
            block_key = self._get_block_key(identifier, rule_name)

            # Delete rate limit data and block
            pipe = self.redis_client.pipeline()
            pipe.delete(key)
            pipe.delete(block_key)

            # For fixed window, also delete window-specific keys
            rule = self.default_rules.get(rule_name)
            if rule and rule.strategy == RateLimitStrategy.FIXED_WINDOW:
                now = time.time()
                for i in range(2):  # Current and previous window
                    window = int(now // rule.window_seconds) - i
                    window_key = f"{key}:{window}"
                    pipe.delete(window_key)

            results = pipe.execute()

            logger.info(
                "Rate limit reset", rule_name=rule_name, operation="reset_rate_limit"
            )

            return any(results)

        except Exception as e:
            logger.error(
                "Failed to reset rate limit",
                rule_name=rule_name,
                error_type=type(e).__name__,
                operation="reset_rate_limit",
            )
            return False

    def add_custom_rule(self, rule_name: str, rule: RateLimitRule):
        """Add custom rate limit rule"""
        self.default_rules[rule_name] = rule
        logger.info(
            "Custom rate limit rule added",
            rule_name=rule_name,
            max_attempts=rule.max_attempts,
            window_seconds=rule.window_seconds,
        )

    def get_blocked_identifiers(self, rule_name: str) -> Dict[str, int]:
        """Get all blocked identifiers for a rule"""
        try:
            pattern = f"{self.block_prefix}{rule_name}:*"
            blocked_keys = self.redis_client.keys(pattern)

            blocked = {}
            for key in blocked_keys:
                ttl = self.redis_client.ttl(key)
                if ttl > 0:
                    # Extract hashed identifier
                    identifier_hash = key.split(":")[-1]
                    blocked[identifier_hash] = ttl

            return blocked

        except Exception as e:
            logger.error(
                "Failed to get blocked identifiers",
                rule_name=rule_name,
                error_type=type(e).__name__,
                operation="get_blocked_identifiers",
            )
            return {}


def create_rate_limiter(redis_client: redis.Redis) -> RedisRateLimiter:
    """Create rate limiter instance"""
    return RedisRateLimiter(redis_client)
