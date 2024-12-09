import litellm



data={
    'messages':[
        {'role':'system','content':"You are a customer support agent for ACME Inc.Always answer in a sentence or less.Follow the following routine with the user:1. First, ask probing questions and understand the user's problem deeper.\n - unless the user has already provided a reason.\n2. Propose a fix (make one up).\n3. ONLY if not satesfied, offer a refund.\n4. If accepted, search for the ID and then execute refund."},
        {'role':'user','content':'I want refund.'},
        {'role':'assistant','content':"I'm here to help! Could you tell me more about the product or service you're looking to get a refund for? Maybe provide some details like when you purchased it and if there are any specific issues you've encountered?"},
        {'role':'user','content':'my shoe is too small.'},
        {'tool_calls': [{'type': 'function','function': {'name': 'transfer_to_issues_and_repairs', 'arguments': '{}'}}], 'role': 'assistant', 'content': '', 'name': 'TriageAgent'},
        {'content': 'Transfered to IssuesAndRepairsAgent. Adopt persona immediately.', 'role': 'tool', 'tool_call_id': '1f3c1a43-78b3-494f-a642-ef877ae64813'}
    ],
    'stream':False,
    'tools':[
        {'type': 'function', 'function': {'name': 'execute_refund', 'description': '', 'parameters': {'type': 'object', 'properties': {'item_id': {'description': 'item_id', 'title': 'Item Id', 'type': 'string'}, 'reason': {'default': 'not provided', 'description': 'reason', 'title': 'Reason', 'type': 'string'}}, 'required': ['item_id']}}},
        {'type': 'function', 'function': {'name': 'look_up_item', 'description': 'Use to find item ID.\nSearch query can be a description or keywords.', 'parameters': {'type': 'object', 'properties': {'search_query': {'description': 'search_query', 'title': 'Search Query', 'type': 'string'}}, 'required': ['search_query']}}},
        {'type': 'function', 'function': {'name': 'transfer_back_to_triage', 'description': 'Call this if the user brings up a topic outside of your purview,\nincluding escalating to human.', 'parameters': {'type': 'object', 'properties': {}}}}
    ]



}

import asyncio
asyncio.run(litellm.acompletion(model="ollama_chat/qwen2.5:14b-instruct-q4_K_M",
                               temperature=0.3,**data))