// Copyright (c) Microsoft Corporation. All rights reserved.
// HandlerInvoker.cs

using System.Diagnostics;
using System.Reflection;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Core;

public class HandlerInvoker
{
    private static async ValueTask<object?> TypeEraseAwait<T>(ValueTask<T> vt)
    {
        return await vt;
    }

    public HandlerInvoker(MethodInfo methodInfo, object? target = null)
    {
        // TODO: Check that the MethodInfo params check out?

        Func<object?, MessageContext, object?> invocation;
        if (target != null)
        {
            invocation = (object? message, MessageContext messageContext) => methodInfo.Invoke(target, new object?[] { message, messageContext });
        }
        else if (methodInfo.IsStatic)
        {
            invocation = (object? message, MessageContext messageContext) => methodInfo.Invoke(null, new object?[] { message, messageContext });
        }
        else
        {
            throw new InvalidOperationException("Target must be provided for non-static methods");
        }

        Func<object?, MessageContext, ValueTask<object?>> getResultAsync;
        if (methodInfo.ReturnType.IsAssignableFrom(typeof(ValueTask)))
        {
            getResultAsync = async
            (object? message, MessageContext messageContext) =>
            {
                await (ValueTask)invocation(message, messageContext)!;
                return null;
            };
        }
        else if (
            methodInfo.ReturnType.GetGenericTypeDefinition() == typeof(ValueTask<>)
            )
        {
            getResultAsync = async
            (object? message, MessageContext messageContext) =>
            {
                object valueTask = invocation(message, messageContext)!;

                object? typelessValueTask = typeof(HandlerInvoker)
                    .GetMethod(nameof(TypeEraseAwait), BindingFlags.NonPublic | BindingFlags.Static)!
                    .MakeGenericMethod(methodInfo.ReturnType.GetGenericArguments()[0])
                    .Invoke(null, new object[] { valueTask });

                Debug.Assert(typelessValueTask is ValueTask<object?>);

                return await (ValueTask<object?>)typelessValueTask;
            };
        }
        else
        {
            throw new InvalidOperationException($"Method {methodInfo.Name} must return a ValueTask or ValueTask<T>");
        }

        this.Invocation = getResultAsync;
    }

    private Func<object?, MessageContext, ValueTask<object?>> Invocation { get; }

    public ValueTask<object?> InvokeAsync(object? obj, MessageContext messageContext)
    {
        return this.Invocation(obj, messageContext);
    }
}
