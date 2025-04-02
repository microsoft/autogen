// Copyright (c) Microsoft Corporation. All rights reserved.
// Tasks.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

/// <summary>
/// Result of running a task.
/// </summary>
/// <param name="messages">Messages produced by the task.</param>
public struct TaskResult(List<AgentMessage> messages)
{
    /// <summary>
    /// Message produced by the task.
    /// </summary>
    public List<AgentMessage> Messages { get; } = messages;

    /// <summary>
    /// The reason the task stopped.
    /// </summary>
    public string? StopReason = null;
}

/// <summary>
/// The stream frame for <see cref="ITaskRunner.StreamAsync(string, CancellationToken)"/>.
/// </summary>
public class TaskFrame : StreamingFrame<TaskResult>
{
    /// <summary>
    /// Create a new <see cref="TaskFrame"/> with a response.
    /// </summary>
    /// <param name="response">Result of running a task.</param>
    public TaskFrame(TaskResult response)
    {
        this.Response = response;
        this.Type = TaskFrame.FrameType.Response;
    }

    /// <summary>
    /// Create a new <see cref="TaskFrame"/> with an internal message.
    /// </summary>
    /// <param name="message">The internal message.</param>
    public TaskFrame(AgentMessage message)
    {
        this.InternalMessage = message;
        this.Type = TaskFrame.FrameType.InternalMessage;
    }
}

/// <summary>
/// A task runner.
/// </summary>
public interface ITaskRunner
{
    private static ChatMessage ToMessage(string task) => new TextMessage { Content = task, Source = "user" };

    /// <summary>
    /// Run the task and return the result.
    /// </summary>
    /// <param name="task">The task definition in text form.</param>
    /// <param name="cancellationToken"></param>
    /// <returns>The result of running the task.</returns>
    public async ValueTask<TaskResult> RunAsync(string task, CancellationToken cancellationToken = default) =>
        await this.RunAsync(ToMessage(task)!, cancellationToken);

    /// <summary>
    /// Run the task and return the result.
    /// </summary>
    /// <remarks>
    /// The runner is stateful and a subsequent call to this method will continue from where the previous
    /// call left off.If the task is not specified,the runner will continue with the current task.
    /// </remarks>
    /// <param name="task">The task definition as a message.</param>
    /// <param name="cancellationToken"></param>
    /// <returns>The result of running the task.</returns>
    /// <exception cref="InvalidOperationException">If no response is generated.</exception>
    public async ValueTask<TaskResult> RunAsync(ChatMessage task, CancellationToken cancellationToken = default)
    {
        await foreach (TaskFrame frame in this.StreamAsync(task, cancellationToken))
        {
            if (frame.Type == TaskFrame.FrameType.Response)
            {
                return frame.Response!;
            }
        }

        throw new InvalidOperationException("The stream should have returned the final result.");
    }

    /// <summary>
    /// Run the task and produce a stream of <see cref="TaskFrame"/> and the final <see cref="TaskResult"/>
    /// is the last frame in the stream.
    /// </summary>
    /// <remarks>
    /// The runner is stateful and a subsequent call to this method will continue from where the previous
    /// call left off.If the task is not specified,the runner will continue with the current task.
    /// </remarks>
    /// <param name="task">The task definition as a string.</param>
    /// <param name="cancellationToken"></param>
    /// <returns>A stream of <see cref="TaskFrame"/> containing internal messages and intermediate results followed by
    /// the final <see cref="TaskResult"/></returns>
    public IAsyncEnumerable<TaskFrame> StreamAsync(string task, CancellationToken cancellationToken = default) =>
        this.StreamAsync(ToMessage(task), cancellationToken);

    /// <summary>
    /// Run the task and produce a stream of <see cref="TaskFrame"/> and the final <see cref="TaskResult"/>
    /// is the last frame in the stream.
    /// </summary>
    /// <remarks>
    /// The runner is stateful and a subsequent call to this method will continue from where the previous
    /// call left off.If the task is not specified,the runner will continue with the current task.
    /// </remarks>
    /// <param name="task">The task definition as a message.</param>
    /// <param name="cancellationToken"></param>
    /// <returns>A stream of <see cref="TaskFrame"/> containing internal messages and intermediate results followed by
    /// the final <see cref="TaskResult"/></returns>
    public IAsyncEnumerable<TaskFrame> StreamAsync(ChatMessage? task, CancellationToken cancellationToken = default);
}
