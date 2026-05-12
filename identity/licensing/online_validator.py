"""Online license validation (phone home)"""

import httpx
from datetime import datetime, UTC
from typing import TYPE_CHECKING
from optorch.identity.licensing.models import License

if TYPE_CHECKING:
    from optorch.identity.config import LicenseConfig


class OnlineValidator:
    """Validate license with optorch licensing server"""

    def __init__(self, config: "LicenseConfig"):
        online_config = config.online
        self.url = online_config.get("validation_url", "https://license.optorch.ai/validate")
        self.cache_ttl = online_config.get("cache_ttl", 3600)
        self.cache: dict[str, tuple[bool, datetime]] = {}

    async def validate(self, license: License) -> bool:
        """Check license validity with server"""
        cache_key = license.uid
        if cache_key in self.cache:
            cached_result, cached_at = self.cache[cache_key]
            if (datetime.now(UTC) - cached_at).total_seconds() < self.cache_ttl:
                return cached_result

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.url, json={"license_uid": license.uid, "assignee": license.assignee},)
            result = resp.json()

        is_valid = result.get("valid", False)
        self.cache[cache_key] = (is_valid, datetime.now(UTC))

        return is_valid
