// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicConstants.cs

namespace AutoGen.Anthropic.Utils
{
    public static class AnthropicConstants
    {
        public static string Endpoint = "https://api.anthropic.com/v1/messages";

        // Models
        public static string Claude3Opus = "claude-3-opus-20240229";
        public static string Claude3Sonnet = "claude-3-sonnet-20240229";
        public static string Claude3Haiku = "claude-3-haiku-20240307";
        public static string Claude35Sonnet = "claude-3-5-sonnet-20240620";
    }
}

namespace Microsoft.AutoGen.Extensions.Anthropic.Utils
{
    public static class AnthropicConstants
    {
        public static string Endpoint = global::AutoGen.Anthropic.Utils.AnthropicConstants.Endpoint;

        // Models
        public static string Claude3Opus = global::AutoGen.Anthropic.Utils.AnthropicConstants.Claude3Opus;
        public static string Claude3Sonnet = global::AutoGen.Anthropic.Utils.AnthropicConstants.Claude3Sonnet;
        public static string Claude3Haiku = global::AutoGen.Anthropic.Utils.AnthropicConstants.Claude3Haiku;
        public static string Claude35Sonnet = global::AutoGen.Anthropic.Utils.AnthropicConstants.Claude35Sonnet;
    }
}
