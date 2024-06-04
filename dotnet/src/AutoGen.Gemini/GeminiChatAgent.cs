// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiChatAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;
using Google.Cloud.AIPlatform.V1;
using Google.Protobuf.Collections;
using Json.Schema;
using Json.Schema.Generation;
using OpenAPISchemaType = Google.Cloud.AIPlatform.V1.Type;
using Type = System.Type;
namespace AutoGen.Gemini;

public class GeminiChatAgent : IStreamingAgent
{
    private readonly IGeminiClient client;
    private readonly string? systemMessage;
    private readonly string model;
    private readonly ToolConfig? toolConfig;
    private readonly SafetySetting? safetySettings;
    private readonly string responseMimeType;
    private readonly Tool[]? tools;

    public GeminiChatAgent(
        IGeminiClient client,
        string name,
        string model,
        string? systemMessage = null,
        ToolConfig? toolConfig = null,
        Tool[]? tools = null,
        SafetySetting? safetySettings = null,
        string responseMimeType = "text/plain")
    {
        this.client = client;
        this.Name = name;
        this.systemMessage = systemMessage;
        this.model = model;
        this.toolConfig = toolConfig;
        this.safetySettings = safetySettings;
        this.responseMimeType = responseMimeType;
        this.tools = tools;
    }

    public string Name { get; }

    public Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        var request = BuildChatRequest(messages, options);
        var response = this.client.GenerateContentAsync(request, cancellationToken: cancellationToken).ConfigureAwait(false)
    }

    public IAsyncEnumerable<IStreamingMessage> GenerateStreamingReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException();
    }

    private OpenApiSchema ToOpenApiSchema(Type type)
    {
        if (type == null)
        {
            return new OpenApiSchema
            {
                Type = OpenAPISchemaType.Unspecified
            };
        }

        var schema = new JsonSchemaBuilder().FromType(type).Build()

        var openApiSchema = new OpenApiSchema
        {
            Type = schema.GetJsonType() switch
            {
                SchemaValueType.Array => OpenAPISchemaType.Array,
                SchemaValueType.Boolean => OpenAPISchemaType.Boolean,
                SchemaValueType.Integer => OpenAPISchemaType.Integer,
                SchemaValueType.Number => OpenAPISchemaType.Number,
                SchemaValueType.Object => OpenAPISchemaType.Object,
                SchemaValueType.String => OpenAPISchemaType.String,
                _ => OpenAPISchemaType.Unspecified
            },
        };

        if (schema.GetJsonType() == SchemaValueType.Object && schema.GetProperties() is var properties && properties != null)
        {
            //openApiSchema.Properties.Add(schema.GetProperties().Select(p => new KeyValuePair<string, OpenApiSchema>(p.Key, ToOpenApiSchema(p.Value.GetType()))));
            foreach (var property in properties)
            {
                openApiSchema.Properties.Add(property.Key, ToOpenApiSchema(property.Value.GetType()));
            }
        }

        return openApiSchema;
    }

    private GenerateContentRequest BuildChatRequest(IEnumerable<IMessage> messages, GenerateReplyOptions? options)
    {
        var geminiMessages = messages.Select(m => m switch
        {
            IMessage<Content> contentMessage => contentMessage.Content,
            _ => throw new NotSupportedException($"Message type {m.GetType()} is not supported.")
        });

        var systemMessage = this.systemMessage switch
        {
            null => null,
            string message => new Content
            {
                Parts = { new[] { new Part { Text = message } } },
                Role = "system"
            }
        };

        var request = new GenerateContentRequest()
        {
            Contents = { geminiMessages },
            SystemInstruction = systemMessage,
            Model = this.model,
            ToolConfig = this.toolConfig,
            SafetySettings = { this.safetySettings },
            GenerationConfig = new GenerationConfig
            {
                StopSequences = { options?.StopSequence ?? Enumerable.Empty<string>() },
                ResponseMimeType = this.responseMimeType,
                CandidateCount = 1,
            },
            Tools = { this.tools ?? Enumerable.Empty<Tool>() }
        };

        if (options?.MaxToken.HasValue is true)
        {
            request.GenerationConfig.MaxOutputTokens = options.MaxToken.Value;
        }

        if (options?.Temperature.HasValue is true)
        {
            request.GenerationConfig.Temperature = options.Temperature.Value;
        }

        if (options?.Functions is { Length: > 0 })
        {
            foreach (var function in options.Functions)
            {
                var required = function.Parameters.Where(p => p.IsRequired)
                    .Select(p => p.Name)
                    .ToList();
                var parameterProperties = new Dictionary<string, OpenApiSchema>();

                foreach (var parameter in function.Parameters ?? Enumerable.Empty<FunctionParameterContract>())
                {
                    var schema = ToOpenApiSchema(parameter.ParameterType!);
                    schema.Description = parameter.Description;
                    schema.Title = parameter.Name;
                    schema.Nullable = !parameter.IsRequired;
                    parameterProperties.Add(parameter.Name!, schema);
                }

                request.Tools.Add(new Tool
                {
                    FunctionDeclarations =
                    {
                        new FunctionDeclaration
                        {
                            Name = function.Name,
                            Description = function.Description,
                            Parameters = new OpenApiSchema
                            {
                                Description = function.Description,
                                Title = function.Name,
                                Required =
                                {
                                    required,
                                },
                                Properties =
                                {
                                    parameterProperties,
                                },
                            },
                        },
                    },
                });
            }
        }

        return request;
    }
}
