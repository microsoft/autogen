// Copyright (c) Microsoft Corporation. All rights reserved.
// Error.cs

using System.Text.Json.Serialization;

namespace AutoGen.Mistral
{
    public class Error
    {
        public Error(string type, string message, string? param = default(string), string? code = default(string))
        {
            Type = type;
            Message = message;
            Param = param;
            Code = code;
        }

        [JsonPropertyName("type")]
        public string Type { get; set; }

        /// <summary>
        /// Gets or Sets Message
        /// </summary>
        [JsonPropertyName("message")]
        public string Message { get; set; }

        /// <summary>
        /// Gets or Sets Param
        /// </summary>
        [JsonPropertyName("param")]
        public string? Param { get; set; }

        /// <summary>
        /// Gets or Sets Code
        /// </summary>
        [JsonPropertyName("code")]
        public string? Code { get; set; }
    }
}
