// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionContractExtension.cs

using System.Collections.Generic;
using System.Linq;
using AutoGen.Core;
using Google.Cloud.AIPlatform.V1;
using Json.Schema;
using Json.Schema.Generation;
using OpenAPISchemaType = Google.Cloud.AIPlatform.V1.Type;
using Type = System.Type;

namespace AutoGen.Gemini.Extension;

public static class FunctionContractExtension
{
    /// <summary>
    /// Convert a <see cref="FunctionContract"/> to a <see cref="FunctionDeclaration"/> that can be used in gpt funciton call.
    /// </summary>
    public static FunctionDeclaration ToFunctionDeclaration(this FunctionContract function)
    {
        var required = function.Parameters!.Where(p => p.IsRequired)
                    .Select(p => p.Name)
                    .ToList();
        var parameterProperties = new Dictionary<string, OpenApiSchema>();

        foreach (var parameter in function.Parameters ?? Enumerable.Empty<FunctionParameterContract>())
        {
            var schema = ToOpenApiSchema(parameter.ParameterType);
            schema.Description = parameter.Description;
            schema.Title = parameter.Name;
            schema.Nullable = !parameter.IsRequired;
            parameterProperties.Add(parameter.Name!, schema);
        }

        return new FunctionDeclaration
        {
            Name = function.Name,
            Description = function.Description,
            Parameters = new OpenApiSchema
            {
                Required =
                        {
                            required,
                        },
                Properties =
                        {
                            parameterProperties,
                        },
                Type = OpenAPISchemaType.Object,
            },
        };
    }

    private static OpenApiSchema ToOpenApiSchema(Type? type)
    {
        if (type == null)
        {
            return new OpenApiSchema
            {
                Type = OpenAPISchemaType.Unspecified
            };
        }

        var schema = new JsonSchemaBuilder().FromType(type).Build();
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
            foreach (var property in properties)
            {
                openApiSchema.Properties.Add(property.Key, ToOpenApiSchema(property.Value.GetType()));
            }
        }

        return openApiSchema;
    }
}
