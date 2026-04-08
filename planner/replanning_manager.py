from typing import Any, Dict, Set, Tuple


class ReplanningManager:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.failed_pairs: Set[Tuple[str, str]] = set()

    def register_failure(self, action: Dict[str, Any], reason: str) -> None:
        if action["type"] == "assign":
            self.failed_pairs.add((action["box_id"], action["pallet_id"]))

    def should_retry(self, retry_count: int) -> bool:
        return retry_count < self.max_retries

    def is_blacklisted(self, box_id: str, pallet_id: str) -> bool:
        return (box_id, pallet_id) in self.failed_pairs

    def build_blacklist(self) -> Dict[str, Any]:
        return {
            "failed_assignments": list(self.failed_pairs)
        }

    def reset_episode(self) -> None:
        self.failed_pairs.clear()