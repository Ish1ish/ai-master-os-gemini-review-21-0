import tempfile
import os


def golden_end_to_end():
    from .runtime_adapter import RuntimeAdapter
    with tempfile.TemporaryDirectory() as td:
        runner=RuntimeAdapter(td)
        try:
            result=runner.run(
                "EVAL-GOLDEN-001",
                "EVAL-PROJECT",
                "Find a lean AI business opportunity around onboarding friction",
            )
        finally:
            runner.close()
        assert result["status"]=="COMPLETE"
        assert result["market"]["engine_id"]=="E-02"
        assert result["analytics"]["engine_id"]=="E-12"
        assert result["memory"]["status"]=="WRITTEN"
        assert result["monitoring"]["status"]=="COMPLETE"
        return {
            "run_id":result["run_id"],
            "status":result["status"],
            "market_engine":result["market"]["engine_id"],
            "analytics_engine":result["analytics"]["engine_id"],
            "memory_status":result["memory"]["status"],
            "monitoring_status":result["monitoring"]["status"],
        }
