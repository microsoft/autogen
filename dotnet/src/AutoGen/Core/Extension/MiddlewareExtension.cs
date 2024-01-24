// Copyright (c) Microsoft Corporation. All rights reserved.
// MiddlewareExtension.cs

using System.Collections.Generic;
using System.Threading.Tasks;
using System.Threading;
using System;

namespace AutoGen;

public static class MiddlewareExtension
{

    /// <summary>
    /// Register a auto reply hook to an agent. The hook will be called before the agent generate the reply.
    /// If the hook return a non-null reply, then that non-null reply will be returned directly without calling the agent.
    /// Otherwise, the agent will generate the reply.
    /// This is useful when you want to override the agent reply in some cases.
    /// </summary>
    /// <param name="agent"></param>
    /// <param name="replyFunc"></param>
    /// <returns></returns>
    /// <exception cref="Exception">throw when agent name is null.</exception>
    public static IAgent RegisterReply(
        this IAgent agent,
        Func<IEnumerable<Message>, CancellationToken, Task<Message?>> replyFunc)
    {
        return agent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var reply = await replyFunc(messages, ct);

            if (reply != null)
            {
                return reply;
            }

            return await agent.GenerateReplyAsync(messages, options, ct);
        });
    }

    /// <summary>
    /// Print formatted message to console.
    /// </summary>
    public static IAgent RegisterPrintFormatMessageHook(this IAgent agent)
    {
        return agent.RegisterPostProcess(async (conversation, reply, ct) =>
        {
            Console.WriteLine(reply.FormatMessage());

            return reply;
        });
    }

    /// <summary>
    /// Register a post process hook to an agent. The hook will be called before the agent return the reply and after the agent generate the reply.
    /// This is useful when you want to customize arbitrary behavior before the agent return the reply.
    /// 
    /// One example is <see cref="RegisterPrintFormatMessageHook(IAgent)"/>, which print the formatted message to console before the agent return the reply.
    /// </summary>
    /// <exception cref="Exception">throw when agent name is null.</exception>
    public static IAgent RegisterPostProcess(
        this IAgent agent,
        Func<IEnumerable<Message>, Message, CancellationToken, Task<Message>> postprocessFunc)
    {
        return agent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var reply = await agent.GenerateReplyAsync(messages, options, ct);

            return await postprocessFunc(messages, reply, ct);
        });
    }

    /// <summary>
    /// Register a pre process hook to an agent. The hook will be called before the agent generate the reply. This is useful when you want to modify the conversation history before the agent generate the reply.
    /// </summary>
    /// <exception cref="Exception">throw when agent name is null.</exception>
    public static IAgent RegisterPreProcess(
        this IAgent agent,
        Func<IEnumerable<Message>, CancellationToken, Task<IEnumerable<Message>>> preprocessFunc)
    {
        return agent.RegisterMiddleware(async (messages, options, agent, ct) =>
        {
            var newMessages = await preprocessFunc(messages, ct);

            return await agent.GenerateReplyAsync(newMessages, options, ct);
        });
    }

    /// <summary>
    /// Register a middleware to an existing agent and return a new agent with the middleware.
    /// </summary>
    /// <param name="agent"></param>
    /// <param name="func"></param>
    /// <returns></returns>
    public static MiddlewareAgent RegisterMiddleware(
        this IAgent agent,
        Func<IEnumerable<Message>, GenerateReplyOptions?, IAgent, CancellationToken, Task<Message>> func)
    {
        if (agent.Name == null)
        {
            throw new Exception("Agent name is null.");
        }

        var middlewareAgent = new MiddlewareAgent(agent);
        middlewareAgent.Use((messages, options, next, ct) => func(messages, options, agent, ct));

        return middlewareAgent;
    }
}
