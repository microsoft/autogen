// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatAgent.cs

using System.Text.RegularExpressions;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.AgentChat.Abstractions;

/// <summary>
/// A valid name for an agent.
/// </summary>
/// <remarks>
/// To ensure parity with Python, we require agent names to be Python identifiers.
/// </remarks>
public struct AgentName
{
    // 
    // TODO: Ensure that only valid C# identifiers can pass the validation on Python?

    /*
     From https://docs.python.org/3/reference/lexical_analysis.html#identifiers:
     ```
    identifier   ::=  xid_start xid_continue*
    id_start     ::=  <all characters in general categories Lu, Ll, Lt, Lm, Lo, Nl, the underscore, and characters with the Other_ID_Start property>
    id_continue  ::=  <all characters in id_start, plus characters in the categories Mn, Mc, Nd, Pc and others with the Other_ID_Continue property>
    xid_start    ::=  <all characters in id_start whose NFKC normalization is in "id_start xid_continue*">
    xid_continue ::=  <all characters in id_continue whose NFKC normalization is in "id_continue*">
     ```

    Note: we are not going to deal with normalization; it would require a lot of effort for likely little gain
    (this will mean that, strictly speaking, .NET will support a subset of the identifiers that Python does)

    The Unicode category codes mentioned above stand for:

    * Lu - uppercase letters
    * Ll - lowercase letters
    * Lt - titlecase letters
    * Lm - modifier letters
    * Lo - other letters
    * Nl - letter numbers*
    * Mn - nonspacing marks
    * Mc - spacing combining marks*
    * Nd - decimal numbers
    * Pc - connector punctuations

    Of these, most are captured by "word characters" in .NET, \w, only needing \p{Nl} and \p{Mc} to be added.
    While Copilot /thinks/ that \p{Pc} is needed, it is not, as it is part of \w in .NET.

    * Other_ID_Start - explicit list of characters in PropList.txt to support backwards compatibility
    * Other_ID_Continue - likewise

    # ================================================

    1885..1886    ; Other_ID_Start # Mn   [2] MONGOLIAN LETTER ALI GALI BALUDA..MONGOLIAN LETTER ALI GALI THREE BALUDA
    2118          ; Other_ID_Start # Sm       SCRIPT CAPITAL P
    212E          ; Other_ID_Start # So       ESTIMATED SYMBOL
    309B..309C    ; Other_ID_Start # Sk   [2] KATAKANA-HIRAGANA VOICED SOUND MARK..KATAKANA-HIRAGANA SEMI-VOICED SOUND MARK

    # Total code points: 6

    The pattern for this in .NET is [\u1185-\u1186\u2118\u212E\u309B-\u309C]

    # ================================================

    00B7          ; Other_ID_Continue # Po       MIDDLE DOT
    0387          ; Other_ID_Continue # Po       GREEK ANO TELEIA
    1369..1371    ; Other_ID_Continue # No   [9] ETHIOPIC DIGIT ONE..ETHIOPIC DIGIT NINE
    19DA          ; Other_ID_Continue # No       NEW TAI LUE THAM DIGIT ONE
    200C..200D    ; Other_ID_Continue # Cf   [2] ZERO WIDTH NON-JOINER..ZERO WIDTH JOINER
    30FB          ; Other_ID_Continue # Po       KATAKANA MIDDLE DOT
    FF65          ; Other_ID_Continue # Po       HALFWIDTH KATAKANA MIDDLE DOT

    # Total code points: 16

    The pattern for this in .NET is [\u00B7\u0387\u1369-\u1371\u19DA\u200C\u200D\u30FB\uFF65]

    # ================================================

    Classes for "IdStart": {Lu, Ll, Lt, Lm, Lo, Nl, '_', Other_ID_Start}
            pattern: [\p{Lu}\p{Ll}\p{Lt}\p{Lm}\p{Lo}\p{Nl}_\u1185-\u1186\u2118\u212E\u309B-\u309C]

    Classes for "IdContinue": {\w, Nl, Mc, Other_ID_Start, Other_ID_Continue}
            pattern: [\w\p{Nl}\p{Mc}_\u1185-\u1186\u2118\u212E\u309B-\u309C\u00B7\u0387\u1369-\u1371\u19DA\u200C\u200D\u30FB\uFF65]

    Match group for identifiers:
            (?<ident>(?:[\p{Lu}\p{Ll}\p{Lt}\p{Lm}\p{Lo}\p{Nl}_\u1185-\u1186\u2118\u212E\u309B-\u309C])(?:[\w\p{Nl}\p{Mc}_\u1185-\u1186\u2118\u212E\u309B-\u309C\u00B7\u0387\u1369-\u1371\u19DA\u200C\u200D\u30FB\uFF65])*)
    */

    private const string IdStartClass = @"[\p{Lu}\p{Ll}\p{Lt}\p{Lm}\p{Lo}\p{Nl}_\u1185-\u1186\u2118\u212E\u309B-\u309C]";
    private const string IdContinueClass = @"[\w\p{Nl}\p{Mc}_\u1185-\u1186\u2118\u212E\u309B-\u309C\u00B7\u0387\u1369-\u1371\u19DA\u200C\u200D\u30FB\uFF65]";

    private static readonly Regex AgentNameRegex = new Regex($"^{IdStartClass}{IdContinueClass}*$", RegexOptions.Compiled | RegexOptions.Singleline);

    public string Value { get; }

    public AgentName(string name)
    {
        AgentName.CheckValid(name);

        this.Value = name;
    }

    public static bool IsValid(string name) => AgentNameRegex.IsMatch(name);

    public static void CheckValid(string name)
    {
        if (!AgentName.IsValid(name))
        {
            throw new ArgumentException($"Agent name '{name}' is not a valid identifier.");
        }
    }

    // Implicit cast to string
    public static implicit operator string(AgentName agentName) => agentName.Value;
}

/// <summary>
/// A response from calling <see cref="IChatAgent"/>'s <see cref="IHandleChat{TIn, Response}.HandleAsync(TIn)"/>."/>
/// </summary>
public class Response
{
    /// <summary>
    /// A chat message produced by the agent as a response.
    /// </summary>
    public required ChatMessage Message { get; set; }

    /// <summary>
    /// Inner messages produced by the agent.
    /// </summary>
    public List<AgentMessage>? InnerMessages { get; set; }
}

/// <summary>
/// Base class for representing a stream of messages interspacing responses (<typeparamref name="TResponse"/>) and
/// internal processing messages (<typeparamref name="TInternalMessage"/>). This functions as a discriminated union.
/// </summary>
/// <typeparam name="TResponse">The response type. Usually <see cref="Response"/>.</typeparam>
/// <typeparam name="TInternalMessage">The ineternal message type. Usually <see cref="AgentMessage"/>.</typeparam>
public class StreamingFrame<TResponse, TInternalMessage>() where TInternalMessage : AgentMessage
{
    public enum FrameType
    {
        InternalMessage,
        Response
    }

    public FrameType Type { get; set; }

    public TInternalMessage? InternalMessage { get; set; }
    public TResponse? Response { get; set; }
}

/// <summary>
/// Base class for representing a stream of messages with internal messages of any <see cref="AgentMessage"/> subtype.
/// </summary>
/// <typeparam name="TResponse">The response type. Usually <see cref="Response"/>.</typeparam>
public class StreamingFrame<TResponse> : StreamingFrame<TResponse, AgentMessage>;

/// <summary>
/// The stream frame for <see cref="IChatAgent"/>'s <see cref="IHandleStream{TIn, ChatStreamFrame}.StreamAsync(TIn)"/>
/// </summary>
public class ChatStreamFrame : StreamingFrame<Response, AgentMessage>;

/// <summary>
/// An agent that can participate in a chat.
/// </summary>
public interface IChatAgent :
                 IHandleChat<IEnumerable<ChatMessage>, Response>,
                 IHandleStream<IEnumerable<ChatMessage>, ChatStreamFrame>,
                 ISaveState
{
    /// <summary>
    /// The name of the agent. This is used by team to uniquely identify the agent.It should be unique within the team.
    /// </summary>
    public AgentName Name { get; }

    /// <summary>
    /// The description of the agent. This is used by team to make decisions about which agents to use.The description
    /// should describe the agent's capabilities and how to interact with it.
    /// </summary>
    public string Description { get; }

    /// <summary>
    /// The types of messages that the agent produces.
    /// </summary>
    public IEnumerable<Type> ProducedMessageTypes { get; } // TODO: Is there a way to make this part of the type somehow? Annotations, or IProduce<>? Do we ever actually access this?

    /// <summary>
    /// Reset the agent to its initialization state.
    /// </summary>
    /// <param name="cancellationToken"></param>
    /// <returns></returns>
    public ValueTask ResetAsync(CancellationToken cancellationToken);
}
