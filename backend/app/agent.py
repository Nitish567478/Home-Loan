from datetime import datetime
import json
from typing import Dict, Any, Optional, Tuple
from .config import AgentConfig
from .state_machine import VoiceAgentStateMachine, QualificationState
from .rag_engine import RAGEngine

class VoiceAgent:
    """
    Main Voice Agent orchestrator responsible for:
    1. Template variable injection (company_name, customer_name, agent_name, agent_gender, current_date, etc.)
    2. Synchronized state machine processing
    3. Multi-turn conversation management
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.state_machine = VoiceAgentStateMachine(config=self.config)
        self.rag_engine = RAGEngine(custom_context=self.config.additional_context_from_rag)

    def render_system_prompt(self, customer_utterance: Optional[str] = None) -> str:
        now = datetime.now()
        raw_prompt = self.config.get_system_prompt()
        history = self.state_machine.state.history
        latest_customer_utterance = customer_utterance
        if latest_customer_utterance is None:
            latest_customer_utterance = next(
                (entry["text"] for entry in reversed(history) if entry["speaker"] == "customer"),
                "",
            )
        
        replacements = {
            "{{company_name}}": self.config.company_name,
            "{{customer_name}}": self.config.customer_name,
            "{{agent_name}}": self.config.agent_name,
            "{{agent_gender}}": self.config.agent_gender,
            "{{current_date}}": now.strftime("%d-%B-%Y"),
            "{{current_day}}": now.strftime("%A"),
            "{{current_time}}": now.strftime("%I:%M %p"),
            "{{additional_context_from_rag}}": self.config.additional_context_from_rag,
            "{{language_to_speak}}": self.config.language_to_speak,
            "{{conversation_history}}": json.dumps(history, ensure_ascii=False),
            "{{customer_utterance}}": json.dumps(latest_customer_utterance, ensure_ascii=False),
        }

        rendered = raw_prompt
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, str(value))
        return rendered

    def reset_session(self):
        self.state_machine.reset()

    def update_config(self, new_config_dict: Dict[str, Any]):
        for k, v in new_config_dict.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        self.state_machine.config = self.config
        self.rag_engine.custom_context = self.config.additional_context_from_rag

    def process_customer_turn(self, utterance: str) -> Dict[str, Any]:
        """
        Process a single utterance from the caller, run state extraction and validation,
        and generate the agent's vocal response and updated state.
        """
        product_context = self.rag_engine.query(utterance)
        agent_reply, updated_state = self.state_machine.process_turn(
            utterance,
            context={"product_context": product_context},
        )
        
        return {
            "agent_reply": agent_reply,
            "state": updated_state.to_dict(),
            "rendered_prompt": self.render_system_prompt(customer_utterance=utterance),
            "config": {
                "company_name": self.config.company_name,
                "customer_name": self.config.customer_name,
                "agent_name": self.config.agent_name,
                "agent_gender": self.config.agent_gender,
                "language_to_speak": self.config.language_to_speak,
                "additional_context_from_rag": self.config.additional_context_from_rag,
            }
        }
