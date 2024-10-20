// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// IOrchestrator.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Core;

public class OrchestrationContext
{
    public IEnumerable<IAgent> Candidates { get; set; } = Array.Empty<IAgent>();

    public IEnumerable<IMessage> ChatHistory { get; set; } = Array.Empty<IMessage>();
}

public interface IOrchestrator
{
    /// <summary>
    /// Return the next agent as the next speaker. return null if no agent is selected.
    /// </summary>
    /// <param name="context">orchestration context, such as candidate agents and chat history.</param>
    /// <param name="cancellationToken">cancellation token</param>
    public Task<IAgent?> GetNextSpeakerAsync(
        OrchestrationContext context,
        CancellationToken cancellationToken = default);
}
