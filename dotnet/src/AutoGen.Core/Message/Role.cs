// Copyright (c) Microsoft Corporation. All rights reserved.
// Role.cs

using System;

namespace AutoGen.Core;

public readonly struct Role : IEquatable<Role>
{
    private readonly string label;

    internal Role(string name)
    {
        label = name;
    }

    public static Role User { get; } = new Role("user");

    public static Role Assistant { get; } = new Role("assistant");

    public static Role System { get; } = new Role("system");

    public static Role Function { get; } = new Role("function");

    public bool Equals(Role other)
    {
        return label.Equals(other.label, StringComparison.OrdinalIgnoreCase);
    }

    public override string ToString()
    {
        return label;
    }

    public override bool Equals(object? obj)
    {
        return obj is Role other && Equals(other);
    }

    public override int GetHashCode()
    {
        return label.GetHashCode();
    }

    public static bool operator ==(Role left, Role right)
    {
        return left.Equals(right);
    }

    public static bool operator !=(Role left, Role right)
    {
        return !(left == right);
    }
}
