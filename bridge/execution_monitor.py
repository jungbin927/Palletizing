from typing import Any, Dict, List


class ExecutionMonitor:
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def record(
        self,
        symbolic_action: Dict[str, Any],
        execution_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        log = {
            "action": symbolic_action,
            "success": execution_result.get("success", False),
            "reason": execution_result.get("reason"),
            "position": execution_result.get("position"),
            "orientation": execution_result.get("orientation"),
            "support_ratio": execution_result.get("support_ratio"),
        }
        self.logs.append(log)
        return log

    def latest(self) -> Dict[str, Any]:
        return self.logs[-1] if self.logs else {}

    def get_all(self) -> List[Dict[str, Any]]:
        return self.logs