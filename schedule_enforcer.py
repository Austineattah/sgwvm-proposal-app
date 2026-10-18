import datetime
from typing import Dict, Any, Tuple

class ScheduleEnforcer:
    """
    Enforces Pre-Bidding and Final Bidding deadlines per tenant client.
    Automatically locks intake gates when cut-off dates pass.
    """

    @staticmethod
    def parse_iso_datetime(dt_str: str) -> datetime.datetime:
        """Parses ISO formatted date-time string safely."""
        try:
            return datetime.datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return datetime.datetime.max

    @classmethod
    def check_bidding_status(cls, client_config: Dict[str, Any]) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Determines current bidding phase for a given client MDA.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        pre_bidding_cutoff = cls.parse_iso_datetime(
            client_config.get("pre_bidding_cutoff", "2099-12-31T23:59:59+00:00")
        )
        final_bidding_cutoff = cls.parse_iso_datetime(
            client_config.get("final_bidding_cutoff", "2099-12-31T23:59:59+00:00")
        )

        if now > final_bidding_cutoff:
            return "CLOSED / UNDER EVALUATION", False, {"days": 0, "hours": 0, "minutes": 0}
        
        if now > pre_bidding_cutoff:
            remaining = final_bidding_cutoff - now
            metrics = cls._calculate_time_metrics(remaining)
            return "FINAL BIDDING IN PROGRESS", True, metrics

        remaining = pre_bidding_cutoff - now
        metrics = cls._calculate_time_metrics(remaining)
        return "PRE-BIDDING PHASE OPEN", True, metrics

    @staticmethod
    def _calculate_time_metrics(delta: datetime.timedelta) -> Dict[str, int]:
        total_seconds = int(delta.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        return {"days": max(0, days), "hours": max(0, hours), "minutes": max(0, minutes)}
