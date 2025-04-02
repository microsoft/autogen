// Copyright (c) Microsoft Corporation. All rights reserved.
// Tools.cs

using System.ComponentModel;
using System.Reflection;
using Microsoft.Extensions.AI;

namespace Microsoft.AutoGen.AgentChat.Abstractions;

// TODO: This likely should live as a "Component" in an Agent-building ClassLib?
// It seems like it could have applicability beyond AgentChat.

public static class ReflectionExtensions
{
    public static AIFunctionParameterMetadata ToAIFunctionMetadata(this ParameterInfo pi)
    {
        return new AIFunctionParameterMetadata(pi.Name!)
        {
            Description = pi.GetCustomAttribute<DescriptionAttribute>()?.Description,

            ParameterType = pi.ParameterType,

            HasDefaultValue = pi.HasDefaultValue,
            IsRequired = !pi.HasDefaultValue,
            DefaultValue = pi.DefaultValue,

            // Schema = JSONSchema of type
        };
    }

    public static AIFunctionReturnParameterMetadata ToAIFunctionReturnMetadata(this ParameterInfo rpi)
    {
        return new AIFunctionReturnParameterMetadata
        {
            Description = rpi.GetCustomAttribute<DescriptionAttribute>()?.Description,

            ParameterType = rpi.ParameterType

            //Schema = JSONSchema of type
        };
    }
}

public class ParameterSchema(string name, Type type, bool isRequired = false, object? defaultValue = default)
{
    public string Name { get; } = name;
    public Type Type { get; } = type;
    public bool IsRequired { get; } = isRequired;

    public object? DefaultValue { get; } = defaultValue;

    public static implicit operator ParameterSchema(ParameterInfo parameterInfo)
    {
        Type parameterType = parameterInfo.ParameterType;
        return ParameterSchema<object>.Create(parameterType, parameterInfo.Name!, parameterInfo.HasDefaultValue, parameterInfo.DefaultValue);
    }

    public static implicit operator ParameterSchema(AIFunctionParameterMetadata parameterMetadata)
    {
        Type parameterType = parameterMetadata.ParameterType!; // TODO: Deal with missing ParameterTypes
        return ParameterSchema<object>.Create(parameterType,
                                              parameterMetadata.Name,
                                              parameterMetadata.IsRequired,
                                              parameterMetadata.DefaultValue);
    }
}

// TODO: Can this be obviated by AIFunctionParameter?
public class ParameterSchema<T>(string name, bool isRequired = false, T? defaultValue = default)
    : ParameterSchema(name, typeof(T), isRequired, defaultValue)
{
    public static ParameterSchema Create(Type type, string name, bool isRequired = false, object? defaultValue = default)
    {
        Type parameterSchemaType = typeof(ParameterSchema<>).MakeGenericType(type);
        ParameterSchema? maybeResult = Activator.CreateInstance(parameterSchemaType, name, isRequired, defaultValue) as ParameterSchema;
        return maybeResult!;
    }
}

/// <summary>
/// A tool that can be executed by agents.
/// </summary>
public interface ITool
{
    public string Name { get; }
    public string Description { get; }

    public IEnumerable<ParameterSchema> Parameters { get; }
    public Type ReturnType { get; }

    // TODO: State serialization

    // TODO: Can we somehow make this a ValueTask?
    public Task<object> ExecuteAsync(IEnumerable<object> parameters, CancellationToken cancellationToken = default);

    /// <summary>
    /// This tool represented as an <see cref="AIFunction"/>.
    /// </summary>
    public AIFunction AIFunction
    {
        get
        {
            return CallableTool.CreateAIFunction(this.Name, this.Description, this.ExecuteAsync);
        }
    }
}

public static class TypeExtensions
{
    private static ISet<Type> TaskTypes = new HashSet<Type>([typeof(Task<>), typeof(ValueTask<>)]);

    public static Type UnwrapReturnIfAsync(this Type type)
    {
        if (type.IsGenericType && TaskTypes.Contains(type.GetGenericTypeDefinition()))
        {
            return type.GetGenericArguments()[0];
        }
        else if (type == typeof(Task) || type == typeof(ValueTask))
        {
            return typeof(void);
        }
        else
        {
            return type;
        }
    }
}

/// <summary>
/// Projects a <see cref="AIFunction"/> as an <see cref="ITool"/>.
/// </summary>
/// <param name="aiFunction">The <see cref="AIFunction"/> to wrap.</param>
public class AIFunctionTool(AIFunction aiFunction) : ITool
{
    /// <inheritdoc cref="ITool.AIFunction" />
    public AIFunction AIFunction { get; } = aiFunction;

    /// <inheritdoc cref="ITool.Name" />
    public string Name => this.AIFunction.Metadata.Name;

    /// <inheritdoc cref="ITool.Description" />
    public string Description => this.AIFunction.Metadata.Description;

    /// <inheritdoc cref="ITool.Parameters" />
    public IEnumerable<ParameterSchema> Parameters => from rawParameter in this.AIFunction.Metadata.Parameters
                                                      select (ParameterSchema)rawParameter;

    /// <inheritdoc cref="ITool.ReturnType" />
    public Type ReturnType => this.AIFunction.Metadata.ReturnParameter.ParameterType!; // TODO: Deal with missing return types

    /// <inheritdoc cref="ITool.ExecuteAsync" />
    public Task<object> ExecuteAsync(IEnumerable<object> parameters, CancellationToken cancellationToken = default)
        => this.ExecuteAsync(parameters, cancellationToken);
}

/// <summary>
/// Projects a <c>delegate</c> as a <see cref="ITool"/> by wrapping it in <see cref="AIFunction"/>.
/// </summary>
/// <param name="name">The name of the tool.</param>
/// <param name="description">The description of the tool.</param>
/// <param name="callable">The <c>delegate</c> to wrap.</param>
public class CallableTool(string name, string description, Delegate callable)
    : AIFunctionTool(CreateAIFunction(name, description, callable))
{
    internal static AIFunction CreateAIFunction(string name, string description, Delegate callable)
    {
        MethodInfo methodInfo = callable.Method;

        IEnumerable<AIFunctionParameterMetadata> parameters =
            from parameterInfo in methodInfo.GetParameters()
            select parameterInfo.ToAIFunctionMetadata();

        AIFunctionReturnParameterMetadata returnParameter = methodInfo.ReturnParameter.ToAIFunctionReturnMetadata();

        AIFunctionFactoryCreateOptions createOptions = new()
        {
            Name = name,
            Description = description,
            Parameters = parameters.ToList(),
            ReturnParameter = returnParameter,
            // SerializerOptions = TODO: How do we maintain consistency with Python?
        };

        return AIFunctionFactory.Create(callable, createOptions);
    }
}
