// Copyright (c) Microsoft Corporation. All rights reserved.
// BaseState.cs

namespace Microsoft.AutoGen.AgentChat.State;

[AttributeUsage(AttributeTargets.Class, Inherited = true, AllowMultiple = false)]
public sealed class StateSerializableAttribute : Attribute
{
    public StateSerializableAttribute()
    {
    }
}

[StateSerializable]
public abstract class BaseState
{
    public string Type => this.GetType().FullName!;
    public string Version { get; set; } = "1.0.0"; // TODO: More rigorous state versioning?
}
