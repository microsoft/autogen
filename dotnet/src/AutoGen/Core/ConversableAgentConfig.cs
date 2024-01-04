// Copyright (c) Microsoft Corporation. All rights reserved.
// ConversableAgentConfig.cs

using System.Collections.Generic;
using Azure.AI.OpenAI;

namespace AutoGen
{
    public class ConversableAgentConfig
    {
        public IEnumerable<FunctionDefinition>? FunctionDefinitions { get; set; }

        public IEnumerable<ILLMConfig>? ConfigList { get; set; }

        public float? Temperature { get; set; } = 0.7f;

        public int? Timeout { get; set; }
    }
}
