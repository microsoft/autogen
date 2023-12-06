// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System;
using System.Collections.Generic;
using Azure.AI.OpenAI;

namespace AutoGen.Extension
{
    public static class MessageExtension
    {
        private const string FunctionNamePropertyName = "Name";
        private const string FunctionDescriptionPropertyName = "Arguments";
        public static void SetFunctionCall(this Microsoft.SemanticKernel.AI.ChatCompletion.ChatMessage message, FunctionCall? functionCall)
        {
            if (message == null)
            {
                throw new ArgumentNullException(nameof(message));
            }

            if (functionCall == null)
            {
                return;
            }

            if (string.IsNullOrEmpty(functionCall.Name))
            {
                throw new ArgumentNullException(nameof(functionCall.Name));
            }

            if (string.IsNullOrEmpty(functionCall.Arguments))
            {
                throw new ArgumentNullException(nameof(functionCall.Arguments));
            }

            if (message.AdditionalProperties == null)
            {
                message.AdditionalProperties = new Dictionary<string, string>();
            }

            message.AdditionalProperties[FunctionNamePropertyName] = functionCall.Name;
            message.AdditionalProperties[FunctionDescriptionPropertyName] = functionCall.Arguments;
        }

        public static FunctionCall? GetFunctionCall(this Microsoft.SemanticKernel.AI.ChatCompletion.ChatMessage message)
        {
            if (message == null)
            {
                throw new ArgumentNullException(nameof(message));
            }

            if (message.AdditionalProperties?.TryGetValue(FunctionNamePropertyName, out var functionName) == true &&
                               message.AdditionalProperties.TryGetValue(FunctionDescriptionPropertyName, out var functionDescription))
            {
                return new FunctionCall(functionName, functionDescription);
            }
            else
            {
                return null;
            }
        }

        public static string? GetFrom(this Microsoft.SemanticKernel.AI.ChatCompletion.ChatMessage message)
        {
            if (message == null)
            {
                throw new ArgumentNullException(nameof(message));
            }

            if (message.AdditionalProperties == null)
            {
                return null;
            }

            if (message.AdditionalProperties.TryGetValue("From", out var from))
            {
                return from;
            }
            else
            {
                return null;
            }
        }

        public static void SetFrom(this Microsoft.SemanticKernel.AI.ChatCompletion.ChatMessage message, string? from)
        {
            if (message == null)
            {
                throw new ArgumentNullException(nameof(message));
            }

            if (string.IsNullOrEmpty(from))
            {
                return;
            }

            if (message.AdditionalProperties == null)
            {
                message.AdditionalProperties = new Dictionary<string, string>();
            }

            message.AdditionalProperties["From"] = from;
        }
    }
}
