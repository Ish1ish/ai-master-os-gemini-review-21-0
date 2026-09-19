class AnalyticsLearning:
    def build_learning(self, diagnosis, experiment_results=None):
        bottleneck = diagnosis.get("primary_bottleneck")
        first = diagnosis.get("recommendations", [{}])[0] if diagnosis.get("recommendations") else {}
        return {
            "learning_type":"analytics_signal",
            "summary":(
                f"Observed bottleneck: {bottleneck['from']} → {bottleneck['to']}."
                if bottleneck else "No dominant funnel bottleneck detected."
            ),
            "next_test":first.get("next_test",""),
            "source":"measured_runtime_events",
        }
