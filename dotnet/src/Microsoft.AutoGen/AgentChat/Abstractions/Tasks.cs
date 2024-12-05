// Copyright (c) Microsoft Corporation. All rights reserved.
// Tasks.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public struct TaskResult(List<AgentMessage> messages)
{
    public List<AgentMessage> Messages { get; } = messages;
    public string? StopReason = null;
}

public class TaskFrame : StreamingFrame<TaskResult>
{
    public TaskFrame(TaskResult response)
    {
        this.Response = response;
        this.Type = TaskFrame.FrameType.Response;
    }

    public TaskFrame(AgentMessage message)
    {
        this.InternalMessage = message;
        this.Type = TaskFrame.FrameType.InternalMessage;
    }
}

public interface ITaskRunner
{
    async ValueTask<TaskResult> RunAsync(string task, CancellationToken cancellationToken = default)
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

    IAsyncEnumerable<TaskFrame> StreamAsync(string task, CancellationToken cancellationToken = default);
}
