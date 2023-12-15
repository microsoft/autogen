// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

namespace AutoGen.Extension
{
    public static class MessageExtension
    {
        public static string FormatMessage(this Message message)
        {
            // write result
            var result = $"Message from {message.From}\n";
            // write a seperator
            result += new string('-', 20) + "\n";
            result += message.Content + "\n";
            result += new string('-', 20) + "\n";

            return result;
        }
    }
}
