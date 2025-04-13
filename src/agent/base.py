import tomllib


class BaseAgent:
    def _load_prompt(self, prompt_source: str, prompt_name: str) -> str:
        with open(f'src/agent/settings/{prompt_source}', 'rb') as f:
            config_dict = tomllib.load(f)
        return config_dict[prompt_name]['default']
