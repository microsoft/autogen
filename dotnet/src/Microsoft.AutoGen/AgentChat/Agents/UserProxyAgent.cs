// Copyright (c) Microsoft Corporation. All rights reserved.
// UserProxyAgent.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

using UserInputAsyncFn = System.Func<string, System.Threading.Tasks.ValueTask<string>>;
using UserInputFn = System.Func<string, string>;

namespace Microsoft.AutoGen.AgentChat.Agents;

internal static class UserProxyExtensions
{
    public static UserInputAsyncFn ToAsync(this UserInputFn? fn)
    {
        return fn != null ? async (prompt) => fn(prompt) : StandardInput;
    }

    public static async ValueTask<string> StandardInput(string prompt)
    {
        await Console.Out.WriteAsync(prompt);
        return await Console.In.ReadLineAsync() ?? string.Empty;
    }

    public static HandoffMessage? GetLatestHandoff<T>(this T item) where T : IEnumerable<ChatMessage>
    {
        return item.OfType<HandoffMessage>().LastOrDefault();
    }
}

public class UserProxyAgent : ChatAgentBase
{
    public override IEnumerable<Type> ProducedMessageTypes => [typeof(TextMessage), typeof(HandoffMessage)];
    private UserInputAsyncFn userInputFn;

    public const string DefaultDescription = "A human user";
    public UserProxyAgent(string name, string description = DefaultDescription, UserInputAsyncFn? userInputFn = null)
        : base(name, description)
    {
        this.userInputFn = userInputFn ?? UserProxyExtensions.StandardInput;
    }

    //[MethodImpl.AggressiveInlining] 
    private Response FormatResponse(string result, HandoffMessage? handoff)
    {
        ChatMessage responseMessage =
            handoff == null ?
            new TextMessage { Content = result, Source = this.Name } :
            new HandoffMessage { Context = result, Source = this.Name, Target = handoff.Source };

        return new Response { Message = responseMessage };
    }

    public override async ValueTask<Response> HandleAsync(IEnumerable<ChatMessage> item, CancellationToken cancellationToken)
    {
        try
        {
            HandoffMessage? handoff = item.GetLatestHandoff();
            string prompt = handoff != null ?
                $"Handoff received from {handoff.Source}. Enter your response: " :
                "Enter your response: ";

            string response = await this.userInputFn(prompt);
            return this.FormatResponse(response, handoff);
        }
        catch (TaskCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            throw new IOException($"Failed to get user input: {ex.Message}", ex);
        }
    }

    public override ValueTask ResetAsync(CancellationToken cancellationToken)
    {
        return ValueTask.CompletedTask;
    }
}
