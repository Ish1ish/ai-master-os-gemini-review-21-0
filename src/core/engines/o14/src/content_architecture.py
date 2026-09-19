class ProductContentBuilder:
    def build(self, product_definition, architecture):
        return {
            "product_content_sections":[
                {"section_id":"CONT-01","name":"Quick Start","purpose":"Move customer from purchase/setup to first useful result."},
                {"section_id":"CONT-02","name":"Core Method / Workflow","purpose":"Explain the central process that creates the outcome."},
                {"section_id":"CONT-03","name":"Templates / Examples","purpose":"Reduce execution friction with reusable examples."},
                {"section_id":"CONT-04","name":"Troubleshooting / FAQ","purpose":"Address predictable blockers and questions."},
                {"section_id":"CONT-05","name":"Next Steps","purpose":"Guide continued use, support, or expansion."},
            ],
            "content_rule":"Every section should contribute to customer success, onboarding, proof, or repeatable use.",
        }
