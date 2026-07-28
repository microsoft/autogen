from autogen.enterprise.token_cost_middleware import TokenCostMiddleware, TokenPricing


def test_costs_are_positive_and_callback_called():
    seen = []

    def cb(rec):
        seen.append(rec.total_cost_usd)

    mw = TokenCostMiddleware(on_record=cb)
    ctx = mw.on_request("Hello world" * 10, model="gpt-4o")
    rec = mw.on_response("Answer" * 20, ctx)

    assert rec.input_tokens > 0 and rec.output_tokens > 0
    assert rec.total_cost_usd >= rec.input_cost_usd
    assert seen and seen[0] == rec.total_cost_usd
