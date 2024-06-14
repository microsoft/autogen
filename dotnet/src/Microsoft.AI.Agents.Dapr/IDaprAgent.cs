using Dapr.Actors;
using Microsoft.AI.Agents.Abstractions;

namespace Microsoft.AI.Agents.Dapr;

public interface IDaprAgent : IActor
{
    Task HandleEvent(Event item);
}