// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System.Text;

namespace AutoGen
{
    public static class MessageExtension
    {
        private static string separator = new string('-', 20);
        public static string FormatMessage(this Message message)
        {
            var sb = new StringBuilder();
            // write from
            sb.AppendLine($"Message from {message.From}");
            // write a seperator
            sb.AppendLine(separator);

            // write content
            sb.AppendLine($"content: {message.Content}");

            // write function name if exists
            if (!string.IsNullOrEmpty(message.FunctionName))
            {
                sb.AppendLine($"function name: {message.FunctionName}");
                sb.AppendLine($"function arguments: {message.FunctionArguments}");
            }

            // write metadata
            if (message.Metadata is { Count: > 0 })
            {
                sb.AppendLine($"metadata:");
                foreach (var item in message.Metadata)
                {
                    sb.AppendLine($"{item.Key}: {item.Value}");
                }
            }

            // write a seperator
            sb.AppendLine(separator);

            return sb.ToString();
        }
    }
}
