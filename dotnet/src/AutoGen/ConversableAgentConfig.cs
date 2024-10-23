// Copyright (c) Microsoft. All rights reserved.

using System.Collections.Generic;

namespace AutoGen;

public class ConversableAgentConfig
{
    public IEnumerable<FunctionContract>? FunctionContracts { get; set; }

    public IEnumerable<ILLMConfig>? ConfigList { get; set; }

    public float? Temperature { get; set; } = 0.7f;

    public int? Timeout { get; set; }
}
