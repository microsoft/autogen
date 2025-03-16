// Copyright (c) Microsoft Corporation. All rights reserved.
// Messages.cs

using System.Collections;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Json.Serialization.Metadata;
using Microsoft.AutoGen.AgentChat.GroupChat;
using Microsoft.Extensions.AI;

namespace Microsoft.AutoGen.AgentChat.Abstractions;

/// <summary>
/// The base class for all messages that can be sent between agents.
/// </summary>
/// <remarks>
/// This functions as a combination of both <c>BaseMessage</c> and <c>AgentMessage</c> on the Python side.
/// </remarks>
public abstract class AgentMessage
{
    /// <summary>
    /// The name of the agent that sent this message.
    /// </summary>
    public required string Source { get; set; }

    /// <summary>
    /// The <see cref="IChatClient"/> usage incurred when producing this message.
    /// </summary>
    public RequestUsage? ModelUsage { get; set; }

    // IMPORTANT NOTE: Unlike the ITypeMarshal<AgentMessage, WireProtocol.AgentMessage> implementation in ProtobufTypeMarshal,
    // the .ToWire() call on this is intended to be used for directly converting a concrete message type to its leaf representation.
    // In the context of Protobuf these may not be the same due to discriminated union types being real types, as opposed to
    // a runtime union restriction.
    //public IMessage ToWire()
    //{
    //    return this switch
    //    {
    //        ChatMessage chatMessage => ProtobufTypeMarshal.Convert<ChatMessage, WireProtocol.ChatMessage>(chatMessage),
    //        AgentEvent agentEvent => ProtobufTypeMarshal.Convert<AgentEvent, WireProtocol.AgentEvent>(agentEvent),
    //        _ => throw new InvalidOperationException($"Unknown type {this.GetType().Name}"),
    //    };
    //}
}

/// <summary>
/// Events emitted by agents and teams when they work, not used for agent-to-agent communication.
/// </summary>
public abstract class AgentEvent : AgentMessage
{
    public Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage()
        => ToCompletionClientMessage(role: ChatRole.Assistant);

    /// <summary>
    /// Converts the <see cref="AgentEvent"/> to a <see cref="Microsoft.Extensions.AI.ChatMessage"/>.
    /// </summary>
    /// <remarks>
    /// This should usually be <see cref="ChatRole.Assistant"/>
    /// </remarks>
    /// <param name="role">The role of the agent that is sending the message.</param>
    /// <returns>
    /// A <see cref="Microsoft.Extensions.AI.ChatMessage"/> that represents the <see cref="AgentEvent"/>.
    /// </returns>
    public abstract Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role);
}

/// <summary>
/// Messages for agent-to-agent communication.
/// </summary>
public abstract class ChatMessage : AgentMessage
{
    /// <summary>
    /// Converts the <see cref="ChatMessage"/> to a <see cref="Microsoft.Extensions.AI.ChatMessage"/>.
    /// </summary>
    /// <param name="role">The role of the agent that is sending the message.</param>
    /// <returns>
    /// A <see cref="Microsoft.Extensions.AI.ChatMessage"/> that represents the <see cref="ChatMessage"/>.
    /// </returns>
    public abstract Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role);
}

// Leaf Classes

/// <summary>
/// A text message.
/// </summary>
public class TextMessage : ChatMessage
{
    /// <summary>
    /// The content of the message.
    /// </summary>
    public required string Content { get; set; }

    /// <inheritdoc cref="ChatMessage.ToCompletionClientMessage(ChatRole)" />/>
    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        return new Microsoft.Extensions.AI.ChatMessage(role, this.Content) { AuthorName = this.Source };
    }
}

/// <summary>
/// The data inside of a multi-modal message. Can be either a <c>string</c> or an Image.
/// </summary>
/// <remarks>
/// This presents an API surface around the types that are supported by AgentChat, rather
/// than allowing any <see cref="Microsoft.Extensions.AI.AIContent"/>.
/// </remarks>
public struct MultiModalData
{
    /// <summary>
    /// Supported <c>Type</c>s of <see cref="Microsoft.Extensions.AI.AIContent"/>.
    /// </summary>
    public enum Type
    {
        String, Image
    }

    /// <summary>
    /// Checks the type of the <see cref="AIContent"/> and wraps it in a <see cref="MultiModalData"/> instance if
    /// it is a supported type.
    /// </summary>
    /// <param name="item">The <see cref="AIContent"/> to wrap.</param>
    /// <returns>A <see cref="MultiModalData"/> instance wrapping the <paramref name="item"/>.</returns>
    /// <exception cref="ArgumentException">
    /// Thrown if the <paramref name="item"/> is not a <see cref="TextContent"/> or <see cref="ImageContent"/>.
    /// </exception>
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

    /// <summary>
    /// Initializes a new instance of the <see cref="MultiModalData"/> with a <see cref="string"/>.
    /// </summary>
    /// <param name="text">The text to wrap.</param>
    public MultiModalData(string text)
    {
        ContentType = Type.String;
        AIContent = new TextContent(text);
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="MultiModalData"/> with a <see cref="TextContent"/>.
    /// </summary>
    /// <param name="textContent">The <see cref="TextContent"/> to wrap.</param>
    public MultiModalData(TextContent textContent)
    {
        ContentType = Type.String;
        AIContent = textContent;
    }

    /// <summary>
    /// Initializes a new instance of the <see cref="MultiModalData"/> with an <see cref="ImageContent"/>.
    /// </summary>
    /// <param name="image">The image to wrap.</param>
    public MultiModalData(ImageContent image)
    {
        ContentType = Type.Image;
        AIContent = image;
    }

    /// <summary>
    /// Gets the <see cref="AIContent"/> wrapped by this instance.
    /// </summary>
    public Type ContentType { get; }

    /// <summary>
    /// Gets the <see cref="AIContent"/> wrapped by this instance.
    /// </summary>
    public AIContent AIContent { get; }
}

/// <summary>
/// A multi-modal message.
/// </summary>
public class MultiModalMessage : ChatMessage, IList<AIContent>
{
    /// <inheritdoc cref="IList{T}.this" />"
    public AIContent this[int index]
    {
        get => this.Content[index].AIContent;
        set => this.Content[index] = MultiModalData.CheckTypeAndCreate(value);
    }

    /// <summary>
    /// The contents of the message.
    /// </summary>
    public List<MultiModalData> Content { get; private set; } = new List<MultiModalData>();

    /// <inheritdoc cref="ICollection{AIContent}.Count" />
    public int Count => this.Content.Count;

    /// <inheritdoc cref="ICollection{AIContent}.IsReadOnly" />
    public bool IsReadOnly => false;

    /// <summary>
    /// Adds a range of <see cref="MultiModalData"/> to the message. The type does not need
    /// to be checked because it was already validated when the <see cref="MultiModalData"/>
    /// was created.
    /// </summary>
    /// <param name="items">The items to add.</param>
    internal void AddRangeUnchecked(IEnumerable<MultiModalData> items)
    {
        this.Content.AddRange(items);
    }

    /// <summary>
    /// Checks and adds a range of <see cref="AIContent"/> to the message.
    /// </summary>
    /// <param name="items">The items to add.</param>
    public void AddRange(IEnumerable<AIContent> items)
    {
        foreach (AIContent item in items)
        {
            this.Content.Add(MultiModalData.CheckTypeAndCreate(item));
        }
    }

    /// <summary>
    /// Adds a range of <see cref="string"/> to the message.
    /// </summary>
    /// <param name="textItems">The items to add.</param>
    public void AddRange(IEnumerable<TextContent> textItems)
    {
        foreach (TextContent item in textItems)
        {
            this.Add(item);
        }
    }

    /// <summary>
    /// Adds a range of <see cref="string"/> to the message.
    /// </summary>
    /// <param name="textItems">The items to add.</param>
    public void AddRange(IEnumerable<string> textItems)
    {
        foreach (string item in textItems)
        {
            this.Add(item);
        }
    }

    /// <summary>
    /// Adds a range of <see cref="ImageContent"/> to the message.
    /// </summary>
    /// <param name="images">The items to add.</param>
    public void AddRange(IEnumerable<ImageContent> images)
    {
        foreach (ImageContent image in images)
        {
            this.Add(image);
        }
    }

    /// <summary>
    /// Checks and adds an <see cref="AIContent"/> to the message.
    /// </summary>
    /// <param name="item">The item to add.</param>
    public void Add(AIContent item)
    {
        this.Content.Add(MultiModalData.CheckTypeAndCreate(item));
    }

    /// <summary>
    /// Adds a <see cref="string"/> to the message.
    /// </summary>
    /// <param name="text">The text to add.</param>
    public void Add(string text)
    {
        this.Content.Add(new(text));
    }

    /// <summary>
    /// Adds a <see cref="TextContent"/> to the message.
    /// </summary>
    /// <param name="image">The image to add.</param>
    public void Add(ImageContent image)
    {
        this.Content.Add(new(image));
    }

    /// <summary>
    /// Adds a <see cref="TextContent"/> to the message.
    /// </summary>
    /// <param name="text">The <see cref="TextContent"/> to add.</param>
    public void Add(TextContent text)
    {
        this.Content.Add(new(text));
    }

    /// <inheritdoc cref="ICollection{AIContent}.Clear" />
    public void Clear()
    {
        this.Content.Clear();
    }

    /// <inheritdoc cref="ICollection{AIContent}.Contains" />
    public bool Contains(AIContent item)
    {
        return this.Content.Any(x => x.AIContent == item);
    }

    /// <inheritdoc cref="ICollection{AIContent}.CopyTo" />
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

    /// <inheritdoc cref="IEnumerable{AIContent}.GetEnumerator" />
    public IEnumerator<AIContent> GetEnumerator()
    {
        return this.Content.Select(x => x.AIContent).GetEnumerator();
    }

    /// <inheritdoc cref="IList{AIContent}.IndexOf" />
    public int IndexOf(AIContent item)
    {
        return this.Content.FindIndex(x => x.AIContent == item);
    }

    /// <inheritdoc cref="IList{String}.IndexOf(String)"/>
    public int IndexOf(string text)
    {
        return this.Content.FindIndex(x => x.ContentType == MultiModalData.Type.String && ((TextContent)x.AIContent).Text == text);
    }

    /// <inheritdoc cref="IList{AIContent}.Insert" />/>
    public void Insert(int index, AIContent item)
    {
        this.Content.Insert(index, MultiModalData.CheckTypeAndCreate(item));
    }

    /// <inheritdoc cref="IList{String}.Insert(int, String)"/>
    public void Insert(int index, string text)
    {
        this.Content.Insert(index, new(text));
    }

    /// <inheritdoc cref="IList{TextContent}.Insert(int, TextContent)"/>
    public void Insert(int index, TextContent text)
    {
        this.Content.Insert(index, new(text));
    }

    /// <inheritdoc cref="IList{ImageContent}.Insert(int, ImageContent)"/>
    public void Insert(int index, ImageContent image)
    {
        this.Content.Insert(index, new(image));
    }

    /// <inheritdoc cref="ICollection{AIContent}.Remove" />
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

    /// <inheritdoc cref="IList{AIContent}.RemoveAt" />
    public void RemoveAt(int index)
    {
        this.Content.RemoveAt(index);
    }

    /// <inheritdoc cref="IEnumerable.GetEnumerator" />
    IEnumerator IEnumerable.GetEnumerator()
    {
        return GetEnumerator();
    }

    /// <inheritdoc cref="ChatMessage.ToCompletionClientMessage(ChatRole)" />/>
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

/// <summary>
/// A message requesting stop of a conversation.
/// </summary>
public class StopMessage : ChatMessage
{
    public required string Content { get; set; }

    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Assistant, "StopMessage can only come from agents in the Assistant Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Assistant, this.Content) { AuthorName = this.Source };
    }
}

/// <summary>
/// A message requesting handoff of a conversation to another agent.
/// </summary>
public class HandoffMessage : ChatMessage
{
    /// <summary>
    /// The name of the target agent to handoff to.
    /// </summary>
    public required string Target { get; set; }

    /// <summary>
    /// The handoff message to the target agent.
    /// </summary>
    public required string Context { get; set; }

    /// <inheritdoc cref="ChatMessage.ToCompletionClientMessage(ChatRole)" />/>
    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Assistant, "HandoffMessage can only come from agents in the Assistant Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Assistant, this.Context) { AuthorName = this.Source };
    }
}

/// <summary>
/// A request to call a function.
/// </summary>
public class FunctionCall
{
    // TODO: Should this be part of the Autogen "Core" (and what does that even mean on the .NET side?)
    // It is unfortuante that we have to duplicate this type, but in order to be compatible with Python, it is necessary for
    // us to be able to process incoming FunctionCalls with parameters in the form of a JSON string. This means that without
    // knowing the target function, and unless the types are specified inline in the JSON, we cannot deserialize them in a
    // generic manner (or we need to have a central registry of function calls, which is undesirable).
    // The solution, for now, is to keep the representation as JSON and provide a helper that binds the JSON to a candidate
    // schema.

    /// <summary>
    /// An identifier representing this specific request. Responses will include this identifier.
    /// </summary>
    public required string Id { get; set; }

    /// <summary>
    /// The arguments to pass to the function in JSON format.
    /// </summary>
    public string? Arguments { get; set; }

    /// <summary>
    /// The name of the function to call.
    /// </summary>
    public required string Name { get; set; }
}

/// <summary>
/// The result of a function call.
/// </summary>
public class FunctionExecutionResult
{
    /// <summary>
    /// The identifier of the request that this result is for.
    /// </summary>
    public required string Id { get; set; }

    /// <summary>
    /// The name of the function that was called.
    /// </summary>
    public required string Name { get; set; }

    /// <summary>
    /// The result of calling the function.
    /// </summary>
    public required string Content { get; set; }
}

/// <summary>
/// An event signaling a request to use tools.
/// </summary>
public class ToolCallRequestEvent : AgentEvent
{
    /// <summary>
    /// The tool calls.
    /// </summary>
    public List<FunctionCall> Content { get; private set; } = new List<FunctionCall>();

    /// <inheritdoc cref="AgentEvent.ToCompletionClientMessage(ChatRole)" />/>
    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Assistant, "ToolCallMessage can only come from agents in the Assistant Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Assistant, (IList<AIContent>)this.Content) { AuthorName = this.Source };
    }
}

/// <summary>
/// An event signaling the execution of tool calls.
/// </summary>
public class ToolCallExecutionEvent : AgentEvent
{
    /// <summary>
    /// The tool call results.
    /// </summary>
    public List<FunctionExecutionResult> Content { get; private set; } = new List<FunctionExecutionResult>();

    /// <inheritdoc cref="AgentEvent.ToCompletionClientMessage(ChatRole)" />/>
    public override Microsoft.Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Tool, "ToolCallResultMessage can only come from agents in the Tool Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Tool, (IList<AIContent>)this.Content) { AuthorName = this.Source };
    }
}

/// <summary>
/// A message summarizing the results of tool calls.
/// </summary>
public class ToolCallSummaryMessage : ChatMessage
{
    /// <summary>
    /// Summary of the tool call results.
    /// </summary>
    public required string Content { get; set; }

    public override Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        Debug.Assert(role == ChatRole.Assistant, "ToolCallSummaryMessage can only come from agents in the Assistant Role");
        return new Microsoft.Extensions.AI.ChatMessage(ChatRole.Assistant, this.Content) { AuthorName = this.Source };
    }
}

/// <summary>
/// An event signaling that the user proxy has requested user input. Published prior to invoking the
/// input callback.
/// </summary>
public class UserInputRequestedEvent : AgentEvent
{
    /// <summary>
    /// Identifier for the user input request.
    /// </summary>
    public required string RequestId { get; set; }

    /// <inheritdoc cref="AgentEvent.ToCompletionClientMessage(ChatRole)" />/>
    public override Extensions.AI.ChatMessage ToCompletionClientMessage(ChatRole role)
    {
        throw new Exception("UserInputRequestedEvent should not be sent to the completion client");
    }
}

public static class CompletionChatMessageExtensions
{
    /// <summary>
    /// Flattens a <see cref="Microsoft.Extensions.AI.ChatMessage"/> into a single <see cref="Microsoft.Extensions.AI.ChatMessage"/>
    /// containing all of the content in the original message as a single string.
    /// </summary>
    /// <remarks>
    /// </remarks>
    /// <param name="msg">
    /// The <see cref="Microsoft.Extensions.AI.ChatMessage"/> to flatten.
    /// </param>
    /// <returns>
    /// A new <see cref="Microsoft.Extensions.AI.ChatMessage"/> that is a flattened version of the input.
    /// </returns>
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

public static class MessageSerializationHelpers
{
    internal sealed class TypeNode(Type type)
    {
        public Type Type { get; } = type;
        public TypeNode? Parent { get; set; }
        public TypeNode Root => this.Parent?.Root ?? this;
        public List<TypeNode> Children { get; } = new List<TypeNode>();

        public IEnumerable<Type> ChildrenTransitiveClosure
        {
            get
            {
                return this.Children.Select(c => c.Type)
                                    .Concat(Children.SelectMany(c => c.ChildrenTransitiveClosure));
            }
        }
    }

    internal sealed class TypeTree
    {
        private static IEnumerable<Type> GetDerivedTypes(Type type)
        {
            // Across all assemblies
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                // Get all types in the assembly
                foreach (var derivedType in assembly.GetTypes().Where(t => type.IsAssignableFrom(t) && t != type))
                {
                    yield return derivedType;
                }
            }
        }

        private TypeNode EnsureTypeNode(Type type)
        {
            if (!this.TypeNodes.TryGetValue(type, out TypeNode? currentNode))
            {
                currentNode = this.TypeNodes[type] = new TypeNode(type);
            }

            return currentNode;
        }

        private void EnsureType(Type type)
        {
            TypeNode? currentNode = this.EnsureTypeNode(type);

            while (currentNode != null &&
                   currentNode.Parent == null &&
                   !this.RootTypes.Contains(currentNode.Type))
            {
                Type parentType = currentNode.Type.BaseType
                                  ?? throw new InvalidOperationException("We should never have a non-Root, underived base");

                TypeNode parentNode = this.EnsureTypeNode(parentType);
                currentNode.Parent = parentNode;
                parentNode.Children.Add(currentNode);

                currentNode = parentNode;
            }
        }

        public HashSet<Type> RootTypes { get; }
        public Dictionary<Type, TypeNode> TypeNodes { get; } = new Dictionary<Type, TypeNode>();

        public TypeTree(params Type[] rootTypes)
        {
            this.RootTypes = new HashSet<Type>();
            foreach (var rootType in rootTypes)
            {
                // Check that there are no other types that this type derives from in the root types
                // or vice versa
                if (this.RootTypes.Any(t => t.IsAssignableFrom(rootType) || rootType.IsAssignableFrom(t)))
                {
                    throw new ArgumentException($"Root types cannot be derived from each other: {rootType.Name}");
                }

                this.RootTypes.Add(rootType);

                this.EnsureType(rootType);

                foreach (var derivedType in GetDerivedTypes(rootType))
                {
                    this.EnsureType(derivedType);
                }
            }
        }
    }

    internal static readonly TypeTree MessageTypeTree = new(typeof(AgentMessage), typeof(GroupChatEventBase));

    internal sealed class MessagesTypeInfoResolver : DefaultJsonTypeInfoResolver
    {
        public override JsonTypeInfo GetTypeInfo(Type type, JsonSerializerOptions options)
        {
            JsonTypeInfo baseTypeInfo = base.GetTypeInfo(type, options);

            if (MessageTypeTree.TypeNodes.TryGetValue(type, out TypeNode? typeNode) &&
                typeNode.Children.Any()) // Only add polymorphism info if there are derived children
            {
                if (baseTypeInfo.PolymorphismOptions == null)
                {
                    baseTypeInfo.PolymorphismOptions = new JsonPolymorphismOptions();
                }

                baseTypeInfo.PolymorphismOptions.IgnoreUnrecognizedTypeDiscriminators = true;
                baseTypeInfo.PolymorphismOptions.UnknownDerivedTypeHandling = JsonUnknownDerivedTypeHandling.FailSerialization;

                foreach (Type childType in typeNode.ChildrenTransitiveClosure)
                {
                    if (childType.IsAbstract || childType.IsInterface || childType.IsGenericTypeDefinition)
                    {
                        // Can only deserialize concrete, complete types.
                        continue;
                    }

                    baseTypeInfo.PolymorphismOptions.DerivedTypes.Add(new JsonDerivedType(childType, childType.FullName ?? childType.Name));
                }
            }

            return baseTypeInfo;
        }
    }
}
