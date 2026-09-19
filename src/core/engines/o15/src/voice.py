class BrandVoiceBuilder:
    def build(self, dna):
        return {
            "voice": {
                "primary":"Clear",
                "secondary":"Practical",
                "supporting":["Confident","Modern","Helpful"]
            },
            "do": [
                "Use concrete language.",
                "Lead with customer outcome.",
                "Explain before exaggerating.",
                "Use proof where available.",
                "Keep calls to action direct."
            ],
            "dont": [
                "Do not use hype as a substitute for evidence.",
                "Do not fabricate testimonials or statistics.",
                "Do not create fake urgency or scarcity.",
                "Do not overcomplicate simple ideas."
            ],
            "tone_by_context": {
                "education":"clear + practical",
                "sales":"confident + evidence-led",
                "support":"helpful + calm",
                "social":"modern + conversational",
            }
        }
