from dataclasses import dataclass
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined


@dataclass
class RenderedPrompt:
    system: str
    user: str


class PromptLoader:
    def __init__(self, prompts_dir: Path):
        self._dir = prompts_dir
        self._env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            undefined=StrictUndefined,
        )

    def get(self, task: str, inputs: dict) -> RenderedPrompt:
        # Find the latest version file: task.v*.md
        matches = sorted(self._dir.glob(f"{task}.v*.md"))
        if not matches:
            raise FileNotFoundError(f"No prompt file found for task '{task}' in {self._dir}")
        filename = matches[-1].name
        template = self._env.get_template(filename)
        rendered = template.render(**inputs)

        system, user = self._split(rendered)
        return RenderedPrompt(system=system.strip(), user=user.strip())

    @staticmethod
    def _split(text: str) -> tuple[str, str]:
        system, user = "", ""
        current = None
        for line in text.splitlines():
            if line.strip() == "## System":
                current = "system"
            elif line.strip() == "## User Template":
                current = "user"
            elif current == "system":
                system += line + "\n"
            elif current == "user":
                user += line + "\n"
        return system, user
