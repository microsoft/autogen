// Copyright (c) Microsoft Corporation. All rights reserved.
// Messages.cs

using System.Collections;
using System.Diagnostics;
using System.Text;
using Microsoft.Extensions.AI;

namespace Microsoft.AutoGen.AgentChat.Abstractions;

// Needed abstractions
// TODO: These should come from Protos for x-lang support

public abstract class BaseMessage
{
    public required string Source { get; set; }
}

public abstract class AgentMessage : BaseMessage
{
    public Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage()
        => ToCompletionClientMessage(role: ChatRole.Assistant);

    public abstract Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role);
}

/// <summary>
/// Messages for agent-to-agent communication.
/// </summary>
public abstract class ChatMessage : AgentMessage
{
}

// Leaf Classes
public class TextMessage : ChatMessage
{
    public required string Content { get; set; }

    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        return new Microsoft.Extensions.AI.ChatMessage(role, this.Content) { AuthorName = this.Source };
    }
}

public struct MultiModalData
{
    public enum Type
    {
        String, Image
    }

    public static MultiModalData CheckTypeAndCreate(AIContent item)
    {
        if (item is TextContent text)
        {
            return new MultiModalData(text);
        }
        else if (item is ImageContent image)
        {
            return new MultiModalData(image);
        }
        else
        {
            throw new ArgumentException("Only TextContent and ImageContent are allowed in MultiModalMessage");
        }
    }

    public MultiModalData(string text)
    {
        ContentType = Type.String;
        AIContent = new TextContent(text);
    }

    public MultiModalData(ImageContent image)
    {
        ContentType = Type.Image;
        AIContent = image;
    }

    public MultiModalData(TextContent textContent)
    {
        ContentType = Type.String;
        AIContent = textContent;
    }

    public Type ContentType { get; }

    // TODO: Make this into a real enum?
    public AIContent AIContent { get; }
}

public class MultiModalMessage : ChatMessage, IList<AIContent>
{
    public AIContent this[int index] { get => throw new NotImplementedException(); set => throw new NotImplementedException(); }

    public List<MultiModalData> Content { get; private set; } = new List<MultiModalData>();

    public int Count => this.Content.Count;

    public bool IsReadOnly => false;

    public void Add(AIContent item)
    {
        this.Content.Add(MultiModalData.CheckTypeAndCreate(item));
    }

    public void Clear()
    {
        this.Content.Clear();
    }

    public bool Contains(AIContent item)
    {
        return this.Content.Any(x => x.AIContent == item);
    }

    public void CopyTo(AIContent[] array, int arrayIndex)
    {
        if (array == null)
        {
            throw new ArgumentNullException(nameof(array));
        }

        if (arrayIndex < 0 || arrayIndex >= array.Length)
        {
            throw new ArgumentOutOfRangeException(nameof(arrayIndex));
        }

        if (array.Length - arrayIndex < this.Content.Count)
        {
            throw new ArgumentException("The number of elements in the source is greater than the available space from arrayIndex to the end of the destination array.");
        }

        for (var i = 0; i < this.Content.Count; i++)
        {
            array[arrayIndex + i] = this.Content[i].AIContent;
        }
    }

    public IEnumerator<AIContent> GetEnumerator()
    {
        return this.Content.Select(x => x.AIContent).GetEnumerator();
    }

    public int IndexOf(AIContent item)
    {
        return this.Content.FindIndex(x => x.AIContent == item);
    }

    public void Insert(int index, AIContent item)
    {
        this.Content.Insert(index, MultiModalData.CheckTypeAndCreate(item));
    }

    public bool Remove(AIContent item)
    {
        int targetIndex = Content.FindIndex(x => x.AIContent == item);
        if (targetIndex == -1)
        {
            return false;
        }

        this.Content.RemoveAt(targetIndex);
        return true;
    }

    public void RemoveAt(int index)
    {
        this.Content.RemoveAt(index);
    }

    IEnumerator IEnumerable.GetEnumerator()
    {
        return GetEnumerator();
    }

    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        StringBuilder contentBuilder = new StringBuilder();
        foreach (MultiModalData item in this.Content)
        {
            if (item.ContentType == MultiModalData.Type.String)
            {
                contentBuilder.AppendLine(item.AIContent.RawRepresentation as string ?? "");
            }
            else if (item.ContentType == MultiModalData.Type.Image)
            {
                contentBuilder.AppendLine("[Image]");
            }
        }

        return new Microsoft.Extensions.AI.ChatMessage(role, contentBuilder.ToString()) { AuthorName = this.Source };
    }
}

public class HandoffMessage : ChatMessage // TODO: Should this be InternalMessage?
{
    public required string Target { get; set; }

    public required string Content { get; set; }

    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Assistant, "HandoffMessage can only come from agents in the Assistant Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Assistant, this.Content) { AuthorName = this.Source };
    }
}

// TODO: Should this be part of the Autogen "Core" (and what does that even mean on the .NET side?)
//public partial class FunctionCall { }
public partial class FunctionExecutionResult { }

public class ToolCallMessage : AgentMessage
{
    public List<FunctionCallContent> Content { get; private set; } = new List<FunctionCallContent>();

    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Assistant, "ToolCallMessage can only come from agents in the Assistant Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Assistant, (IList<AIContent>)this.Content) { AuthorName = this.Source };
    }
}

public class ToolCallResultMessage : AgentMessage
{
    public List<FunctionResultContent> Content { get; private set; } = new List<FunctionResultContent>();

    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Tool, "ToolCallResultMessage can only come from agents in the Tool Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Tool, (IList<AIContent>)this.Content) { AuthorName = this.Source };
    }
}

public class StopMessage : ChatMessage
{
    public required string Content { get; set; }

    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Assistant, "StopMessage can only come from agents in the Assistant Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Assistant, this.Content) { AuthorName = this.Source };
    }
}

public static class CompletionChatMessageExtensions
{
    public static Microsoft.Extensions.AI.ChatMessage Flatten(this Microsoft.Extensions.AI.ChatMessage msg)
    {
        if (msg.Contents.Count == 1 && msg.Contents[0] is TextContent)
        {
            return msg;
        }

        StringBuilder contentBuilder = new StringBuilder();
        foreach (AIContent content in msg.Contents)
        {
            if (content is TextContent textContent)
            {
                contentBuilder.AppendLine(textContent.Text);
            }
            else if (content is ImageContent)
            {
                contentBuilder.AppendLine("[Image]");
            }
            else
            {
                contentBuilder.AppendLine($"[{content.GetType().Name}]");
            }
        }

        return new Microsoft.Extensions.AI.ChatMessage(msg.Role, contentBuilder.ToString())
        {
            AuthorName = msg.AuthorName,
            AdditionalProperties = msg.AdditionalProperties
        };
    }
}
