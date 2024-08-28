// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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
