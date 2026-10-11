from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"

@dataclass
class AgentConfig:
    company_name: str = "Home Credit India"
    customer_name: str = "Rahul Sharma"
    agent_name: str = "Aisha"
    agent_gender: str = "Female"
    language_to_speak: str = "Hindi"
    max_loan_limit: int = 7500000
    min_tenure_years: int = 3
    max_tenure_years: int = 15
    additional_context_from_rag: str = (
        "The pre-approved Loan Against Property offer is up to ₹75,00,000. "
        "The specification does not state a minimum property value, processing fee, or processing timeline. "
        "Exact interest rates are provided by a senior loan expert."
    )
    system_prompt_path: Path = PROMPTS_DIR / "system_prompt_master.md"

    def get_system_prompt(self) -> str:
        built_in_prompts = {
            PROMPTS_DIR / "system_prompt_master.md",
            PROMPTS_DIR / "system_prompt_hindi.md",
        }
        prompt_path = self.system_prompt_path
        if prompt_path in built_in_prompts:
            prompt_name = "system_prompt_hindi.md" if self.language_to_speak.lower() == "hindi" else "system_prompt_master.md"
            prompt_path = PROMPTS_DIR / prompt_name
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "Home Credit LAP AI Voice Agent System Prompt"
