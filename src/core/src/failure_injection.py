class FailureInjection:
    def market_failure(self):
        def bad_search(query):
            return {"results":[]}
        return bad_search

    def model_failure(self):
        def bad_model(prompt):
            raise RuntimeError("simulated_model_failure")
        return bad_model

    def malformed_provider(self):
        def malformed(query):
            return {"unexpected":"shape"}
        return malformed
