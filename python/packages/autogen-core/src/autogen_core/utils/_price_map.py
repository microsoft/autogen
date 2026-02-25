class PriceMap:
    @staticmethod
    def calculate(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        cost = 0.0
        model_name = model.lower()
        if "gpt-4o" in model_name:
            prompt_cost = 0.005 / 1000.0
            completion_cost = 0.015 / 1000.0
            cost = (prompt_tokens * prompt_cost) + (completion_tokens * completion_cost)
        elif "gemini-1.5-pro" in model_name:
            prompt_cost = 0.0035 / 1000.0
            completion_cost = 0.0105 / 1000.0
            cost = (prompt_tokens * prompt_cost) + (completion_tokens * completion_cost)
        return cost
