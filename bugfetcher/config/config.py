import os
import json
from typing import Dict

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path

    def load(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}

    def save(self, config: Dict) -> None:
        with open(self.config_path, 'w') as f:
            json.dump(config, f)