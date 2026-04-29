class PriceMap:
    _PRICES_PER_1K = {
        # Local/Open (Explicitly $0.0)
        "ollama": (0.0, 0.0),
        "llama_cpp": (0.0, 0.0),
        "llama": (0.0, 0.0),
        "phi": (0.0, 0.0),

        # OpenAI
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4o": (0.005, 0.015),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-4": (0.03, 0.06),
        "gpt-3.5": (0.0005, 0.0015),
        "o1-preview": (0.015, 0.06),
        "o1-mini": (0.003, 0.012),
        "o3-mini": (0.0011, 0.0044),
        "o1": (0.015, 0.06),
        "o3": (0.015, 0.06),

        # Anthropic
        "claude-3-7-sonnet": (0.003, 0.015),
        "claude-3-5-sonnet": (0.003, 0.015),
        "claude-3-5-haiku": (0.001, 0.005),
        "claude-3-opus": (0.015, 0.075),
        "claude-3-sonnet": (0.003, 0.015),
        "claude-3-haiku": (0.00025, 0.00125),
        "claude-4-sonnet": (0.003, 0.015),
        "claude-4-opus": (0.015, 0.075),

        # Gemini
        "gemini-2.5-pro": (0.0035, 0.0105),
        "gemini-2.5-flash": (0.0001, 0.0004),
        "gemini-2.0-flash": (0.0001, 0.0004),
        "gemini-1.5-pro": (0.0035, 0.0105),
        "gemini-1.5-flash": (0.000075, 0.0003),
        "gemini": (0.0001, 0.0004),

        # DeepSeek
        "deepseek-r1": (0.00014, 0.00219),
        "deepseek-coder": (0.00014, 0.00028),
        "deepseek": (0.00014, 0.00219),

        # Mistral
        "mistral-large": (0.002, 0.006),
        "mistral-nemo": (0.00015, 0.00015),
        "codestral": (0.0002, 0.0006),
        "mixtral": (0.0007, 0.0007),
        "ministral": (0.0002, 0.0006),
        "pixtral": (0.0002, 0.0006),
        "mistral": (0.0002, 0.0002),
    }

    # Sort keys by length descending to match longest substring first
    _SORTED_KEYS = sorted(_PRICES_PER_1K.keys(), key=len, reverse=True)

    @classmethod
    def calculate(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        model_name = model.lower()
        
        for key in cls._SORTED_KEYS:
            if key in model_name:
                prompt_cost, completion_cost = cls._PRICES_PER_1K[key]
                return (prompt_tokens * (prompt_cost / 1000.0)) + (completion_tokens * (completion_cost / 1000.0))
                
        return 0.0
