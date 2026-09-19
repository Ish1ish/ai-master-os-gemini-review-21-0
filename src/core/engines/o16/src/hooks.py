from typing import Dict, Any, List


class HookGenerator:
    def generate(self, topic: Dict[str, Any], brand_voice: Dict[str, Any],
                 count: int = 5) -> Dict[str, Any]:
        name = topic.get("topic", "")
        hooks = [
            f"The biggest mistake people make with {name.lower()}",
            f"Before you try to solve {name.lower()}, do this first",
            f"If {name.lower()} feels harder than it should, here's why",
            f"3 things to know about {name.lower()}",
            f"A simpler way to think about {name.lower()}",
        ]
        return {
            "topic_id":topic.get("topic_id"),
            "hooks":hooks[:count],
            "voice_anchor":brand_voice.get("voice",{}).get("primary","Clear"),
        }
