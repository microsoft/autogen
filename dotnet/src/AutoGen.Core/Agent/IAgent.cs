// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgent.cs

using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public interface IAgentMetaInformation
{
    public string Name { get; }
}

public interface IAgent : IAgentMetaInformation
{
    /// <summary>
    /// Generate reply
    /// </summary>
    /// <param name="messages">conversation history</param>
    /// <param name="options">completion option. If provided, it should override existing option if there's any</param>
    public Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default);
}

public class GenerateReplyOptions
{
    public GenerateReplyOptions()
    {
    }

    /// <summary>
    /// Copy constructor
    /// </summary>
    /// <param name="other">other option to copy from</param>
    public GenerateReplyOptions(GenerateReplyOptions other)
    {
        this.Temperature = other.Temperature;
        this.MaxToken = other.MaxToken;
        this.StopSequence = other.StopSequence?.Select(s => s)?.ToArray();
        this.Functions = other.Functions?.Select(f => f)?.ToArray();
    }

    public float? Temperature { get; set; }

    public int? MaxToken { get; set; }

    public string[]? StopSequence { get; set; }

    public FunctionContract[]? Functions { get; set; }
}
