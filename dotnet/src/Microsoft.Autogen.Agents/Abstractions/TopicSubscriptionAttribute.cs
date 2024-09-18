namespace Microsoft.AutoGen.Agents.Abstractions;

[AttributeUsage(AttributeTargets.All)]
public class TopicSubscriptionAttribute(string topic) : Attribute
{
    public string Topic { get; } = topic;
}
