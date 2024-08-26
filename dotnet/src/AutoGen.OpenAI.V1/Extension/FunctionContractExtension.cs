// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionContractExtension.cs

using System;
using System.Collections.Generic;
using Azure.AI.OpenAI;
using Json.Schema;
using Json.Schema.Generation;

namespace AutoGen.OpenAI.V1.Extension;

public static class FunctionContractExtension
{
    /// <summary>
    /// Convert a <see cref="FunctionContract"/> to a <see cref="FunctionDefinition"/> that can be used in gpt funciton call.
    /// </summary>
    /// <param name="functionContract">function contract</param>
    /// <returns><see cref="FunctionDefinition"/></returns>
    public static FunctionDefinition ToOpenAIFunctionDefinition(this FunctionContract functionContract)
    {
        var functionDefinition = new FunctionDefinition
        {
            Name = functionContract.Name,
            Description = functionContract.Description,
        };
        var requiredParameterNames = new List<string>();
        var propertiesSchemas = new Dictionary<string, JsonSchema>();
        var propertySchemaBuilder = new JsonSchemaBuilder().Type(SchemaValueType.Object);
        foreach (var param in functionContract.Parameters ?? [])
        {
            if (param.Name is null)
            {
                throw new InvalidOperationException("Parameter name cannot be null");
            }

            var schemaBuilder = new JsonSchemaBuilder().FromType(param.ParameterType ?? throw new ArgumentNullException(nameof(param.ParameterType)));
            if (param.Description != null)
            {
                schemaBuilder = schemaBuilder.Description(param.Description);
            }

            if (param.IsRequired)
            {
                requiredParameterNames.Add(param.Name);
            }

            var schema = schemaBuilder.Build();
            propertiesSchemas[param.Name] = schema;

        }
        propertySchemaBuilder = propertySchemaBuilder.Properties(propertiesSchemas);
        propertySchemaBuilder = propertySchemaBuilder.Required(requiredParameterNames);

        var option = new System.Text.Json.JsonSerializerOptions()
        {
            PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase
        };

        functionDefinition.Parameters = BinaryData.FromObjectAsJson(propertySchemaBuilder.Build(), option);

        return functionDefinition;
    }
}
