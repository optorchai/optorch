"""prometheus metrics for identity operations"""

from prometheus_client import Counter, Histogram, Gauge
import logging

logger = logging.getLogger(__name__)


login_attempts = Counter(
    "optorch_auth_login_attempts_total",
    "Total login attempts",
    ["provider", "result"]  # result: success/failure/error
)

login_duration = Histogram(
    "optorch_auth_login_duration_seconds",
    "Login operation duration",
    ["provider"]
)

token_issuance = Counter(
    "optorch_auth_token_issued_total",
    "Total tokens issued",
    ["token_type"]  # access/refresh
)

token_validation = Counter(
    "optorch_auth_token_validation_total",
    "Total token validations",
    ["result"]  # valid/invalid/expired
)

refresh_token_usage = Counter(
    "optorch_auth_refresh_token_usage_total",
    "Refresh token usage",
    ["result"]  # success/failure
)

# authorization metrics
authz_checks = Counter(
    "optorch_authz_checks_total",
    "Authorization checks",
    ["provider", "decision"]  # decision: permit/deny
)

authz_duration = Histogram(
    "optorch_authz_check_duration_seconds",
    "Authorization check duration",
    ["provider"]
)

policy_evaluations = Counter(
    "optorch_authz_policy_evaluations_total",
    "Policy evaluations",
    ["provider", "result"]  # result: allow/deny/error
)

license_validations = Counter(
    "optorch_license_validations_total",
    "License validations",
    ["result"]  # valid/invalid/expired
)

license_constraint_checks = Counter(
    "optorch_license_constraint_checks_total",
    "License constraint checks",
    ["constraint_type", "result"]  # constraint_type: datetime/count/spatial
)

active_sessions = Gauge(
    "optorch_auth_active_sessions",
    "Number of active sessions"
)

failed_login_attempts = Counter(
    "optorch_auth_failed_login_attempts_total",
    "Failed login attempts by user",
    ["user_id", "reason"]  # reason: invalid_credentials/account_locked/rate_limited
)

locked_accounts = Gauge(
    "optorch_auth_locked_accounts",
    "Number of locked accounts"
)


class IdentityMetrics:
    """wrapper for identity metrics with convenience methods"""
    
    @staticmethod
    def record_login_attempt(provider: str, success: bool, duration: float = 0.0) -> None:
        """record login attempt"""
        result = "success" if success else "failure"
        login_attempts.labels(provider=provider, result=result).inc()
        
        if duration > 0:
            login_duration.labels(provider=provider).observe(duration)
    
    @staticmethod
    def record_token_issued(token_type: str) -> None:
        """record token issuance"""
        token_issuance.labels(token_type=token_type).inc()
    
    @staticmethod
    def record_token_validation(valid: bool, expired: bool = False) -> None:
        """record token validation"""
        if expired:
            result = "expired"
        elif valid:
            result = "valid"
        else:
            result = "invalid"
        
        token_validation.labels(result=result).inc()
    
    @staticmethod
    def record_authz_check(provider: str, decision: str, duration: float = 0.0) -> None:
        """record authorization check"""
        authz_checks.labels(provider=provider, decision=decision).inc()
        
        if duration > 0:
            authz_duration.labels(provider=provider).observe(duration)
    
    @staticmethod
    def record_policy_evaluation(provider: str, result: str) -> None:
        """record policy evaluation"""
        policy_evaluations.labels(provider=provider, result=result).inc()
    
    @staticmethod
    def record_license_validation(valid: bool, expired: bool = False) -> None:
        """record license validation"""
        if expired:
            result = "expired"
        elif valid:
            result = "valid"
        else:
            result = "invalid"
        
        license_validations.labels(result=result).inc()
    
    @staticmethod
    def record_constraint_check(constraint_type: str, passed: bool) -> None:
        """record license constraint check"""
        result = "pass" if passed else "fail"
        license_constraint_checks.labels(constraint_type=constraint_type, result=result).inc()
    
    @staticmethod
    def update_active_sessions(count: int) -> None:
        """update active session count"""
        active_sessions.set(count)
    
    @staticmethod
    def record_failed_login(user_id: str, reason: str) -> None:
        """record failed login attempt"""
        failed_login_attempts.labels(user_id=user_id, reason=reason).inc()
    
    @staticmethod
    def update_locked_accounts(count: int) -> None:
        """update locked account count"""
        locked_accounts.set(count)
