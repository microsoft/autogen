using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Agents;
/// <summary>
/// Default interface methods for an event handler for Input and Output that writes or reads from the console
/// Can be used inside your agents by inheriting from this interface
/// public class MyAgent : BaseAgent, IHandleConsole
/// </summary>
public interface IHandleConsole : IHandle<Output>, IHandle<Input>, IProcessIO
{
    /// <summary>
    /// Prototype for Publish Message Async method
    /// </summary>
    /// <param name="message"></param>
    /// <param name="topic"></param>
    /// <param name="messageId"></param>
    /// <param name="cancellationToken"></param>
    /// <returns>ValueTask</returns>
    ValueTask PublishMessageAsync(object message, TopicId topic, string? messageId = null, CancellationToken cancellationToken = default);

    /// <summary>
    /// Receives events of type Output and writes them to the console
    /// then runs the ProcessOutputAsync method which you should implement in your agent
    /// </summary>
    /// <param name="item"></param>
    /// <param name="messageContext"></param>
    /// <returns>ValueTask</returns>
    async ValueTask IHandle<Output>.HandleAsync(Output item, MessageContext messageContext)
    {
        // Assuming item has a property `Message` that we want to write to the console
        var messageType = item.GetType().Name;
        Console.WriteLine($"--------- {messageType} -----------");
        Console.WriteLine(item.Message);
        Console.WriteLine($"--------- End of {messageType} -----------");
        await ProcessOutputAsync(item.Message);

        var evt = new OutputWritten
        {
            Route = "console"
        };
        await PublishMessageAsync(evt, new TopicId("OutputWritten"), null, cancellationToken: CancellationToken.None).ConfigureAwait(false);
    }

    /// <summary>
    /// Receives events of type Input and reads from the console, then runs the ProcessInputAsync method
    /// which you should implement in your agent
    /// </summary>
    /// <param name="item"></param>
    /// <param name="messageContext"></param>
    /// <returns></returns>
    async ValueTask IHandle<Input>.HandleAsync(Input item, MessageContext messageContext)
    {
        Console.WriteLine("Please enter input:");
        string content = Console.ReadLine() ?? string.Empty;

        var messageType = item.GetType().Name;
        Console.WriteLine($"--------- {messageType} -----------");
        await ProcessInputAsync(content);
        Console.WriteLine($"--------- End of {messageType} -----------");

        var evt = new InputProcessed
        {
            Route = "console"
        };
        await PublishMessageAsync(evt, new TopicId("InputProcessed"), null, cancellationToken: CancellationToken.None).ConfigureAwait(false);
    }
}
