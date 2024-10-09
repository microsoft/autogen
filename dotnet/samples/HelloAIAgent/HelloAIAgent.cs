using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.AutoGen.Agents.Client;

namespace Hello;

[TopicSubscription("HelloAgents")]
public class HelloAIAgent(IAgentContext context) : HelloAIAgent()