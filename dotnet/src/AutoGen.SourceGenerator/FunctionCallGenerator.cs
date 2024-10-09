// Copyright (c) Microsoft Corporation. All rights reserved.
// FunctionCallGenerator.cs

using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using AutoGen.SourceGenerator.Template;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Text;
using Newtonsoft.Json;

namespace AutoGen.SourceGenerator;

[Generator]
public partial class FunctionCallGenerator : IIncrementalGenerator
{
    private const string FUNCTION_CALL_ATTRIBUTION = "AutoGen.Core.FunctionAttribute";

    public void Initialize(IncrementalGeneratorInitializationContext context)
    {
#if LAUNCH_DEBUGGER
        if (!System.Diagnostics.Debugger.IsAttached)
        {
            System.Diagnostics.Debugger.Launch();
        }
#endif
        var optionProvider = context.AnalyzerConfigOptionsProvider.Select((provider, ct) =>
        {
            var generateFunctionDefinitionContract = provider.GlobalOptions.TryGetValue("build_property.EnableContract", out var value) && value?.ToLowerInvariant() == "true";

            return generateFunctionDefinitionContract;
        });
        // step 1
        // filter syntax tree and search syntax node that satisfied the following conditions
        // - is partial class
        var partialClassSyntaxProvider = context.SyntaxProvider.CreateSyntaxProvider<PartialClassOutput?>(
            (node, ct) =>
            {
                return node is ClassDeclarationSyntax classDeclarationSyntax && classDeclarationSyntax.Modifiers.Any(SyntaxKind.PartialKeyword);
            },
            (ctx, ct) =>
            {
                // first check if any method of the class has FunctionAttribution attribute
                // if not, then return null
                var filePath = ctx.Node.SyntaxTree.FilePath;
                var fileName = Path.GetFileNameWithoutExtension(filePath);

                var classDeclarationSyntax = ctx.Node as ClassDeclarationSyntax;
                var nameSpace = classDeclarationSyntax?.Parent as NamespaceDeclarationSyntax;
                var fullClassName = $"{nameSpace?.Name}.{classDeclarationSyntax!.Identifier}";
                if (classDeclarationSyntax == null)
                {
                    return null;
                }

                if (!classDeclarationSyntax.Members.Any(member => member.AttributeLists.Any(attributeList => attributeList.Attributes.Any(attribute =>
                {
                    return ctx.SemanticModel.GetSymbolInfo(attribute).Symbol is IMethodSymbol methodSymbol && methodSymbol.ContainingType.ToDisplayString() == FUNCTION_CALL_ATTRIBUTION;
                }))))
                {
                    return null;
                }

                // collect methods that has FunctionAttribution attribute
                var methodDeclarationSyntaxes = classDeclarationSyntax.Members.Where(member => member.AttributeLists.Any(attributeList => attributeList.Attributes.Any(attribute =>
                {
                    return ctx.SemanticModel.GetSymbolInfo(attribute).Symbol is IMethodSymbol methodSymbol && methodSymbol.ContainingType.ToDisplayString() == FUNCTION_CALL_ATTRIBUTION;
                })))
                    .Select(member => member as MethodDeclarationSyntax)
                    .Where(method => method != null);

                var className = classDeclarationSyntax.Identifier.ToString();
                var namespaceName = classDeclarationSyntax.GetNamespaceNameFromClassDeclarationSyntax();
                var functionContracts = methodDeclarationSyntaxes.Select(method => CreateFunctionContract(method!, className, namespaceName));

                return new PartialClassOutput(fullClassName, classDeclarationSyntax, functionContracts);
            })
            .Where(node => node != null)
            .Collect();

        var aggregateProvider = optionProvider.Combine(partialClassSyntaxProvider);
        // step 2
        context.RegisterSourceOutput(aggregateProvider,
            (ctx, source) =>
            {
                var groups = source.Right.GroupBy(item => item!.FullClassName);
                foreach (var group in groups)
                {
                    var functionContracts = group.SelectMany(item => item!.FunctionContracts).ToArray();
                    var className = group.First()!.ClassDeclarationSyntax.Identifier.ToString();
                    var namespaceName = group.First()!.ClassDeclarationSyntax.GetNamespaceNameFromClassDeclarationSyntax() ?? string.Empty;
                    var functionTT = new FunctionCallTemplate
                    {
                        NameSpace = namespaceName,
                        ClassName = className,
                        FunctionContracts = functionContracts.ToArray(),
                    };

                    var functionSource = functionTT.TransformText();
                    var fileName = $"{className}.generated.cs";

                    ctx.AddSource(fileName, SourceText.From(functionSource, System.Text.Encoding.UTF8));
                    File.WriteAllText(Path.Combine(Path.GetTempPath(), fileName), functionSource);
                }

                if (source.Left)
                {
                    var overallFunctionDefinition = source.Right.SelectMany(x => x!.FunctionContracts.Select(y => new { fullClassName = x.FullClassName, y = y }));
                    var overallFunctionDefinitionObject = overallFunctionDefinition.Select(
                        x => new
                        {
                            fullClassName = x.fullClassName,
                            functionDefinition = new
                            {
                                x.y.Name,
                                x.y.Description,
                                x.y.ReturnType,
                                Parameters = x.y.Parameters.Select(y => new
                                {
                                    y.Name,
                                    y.Description,
                                    y.JsonType,
                                    y.JsonItemType,
                                    y.Type,
                                    y.IsOptional,
                                    y.DefaultValue,
                                }),
                            },
                        });

                    var json = JsonConvert.SerializeObject(overallFunctionDefinitionObject, formatting: Formatting.Indented);
                    // wrap json inside csharp block, as SG doesn't support generating non-source file
                    json = $@"/* <auto-generated> wrap json inside csharp block, as SG doesn't support generating non-source file
{json}
</auto-generated>*/";
                    ctx.AddSource("FunctionDefinition.json", SourceText.From(json, System.Text.Encoding.UTF8));
                }
            });
    }

    private class PartialClassOutput
    {
        public PartialClassOutput(string fullClassName, ClassDeclarationSyntax classDeclarationSyntax, IEnumerable<SourceGeneratorFunctionContract> functionContracts)
        {
            FullClassName = fullClassName;
            ClassDeclarationSyntax = classDeclarationSyntax;
            FunctionContracts = functionContracts;
        }

        public string FullClassName { get; }

        public ClassDeclarationSyntax ClassDeclarationSyntax { get; }

        public IEnumerable<SourceGeneratorFunctionContract> FunctionContracts { get; }
    }

    private SourceGeneratorFunctionContract CreateFunctionContract(MethodDeclarationSyntax method, string? className, string? namespaceName)
    {
        // get function_call attribute
        var functionCallAttribute = method.AttributeLists.SelectMany(attributeList => attributeList.Attributes)
            .FirstOrDefault(attribute => attribute.Name.ToString() == FUNCTION_CALL_ATTRIBUTION);
        // get document string if exist
        var documentationCommentTrivia = method.GetDocumentationCommentTriviaSyntax();

        var functionName = method.Identifier.ToString();
        var functionDescription = functionCallAttribute?.ArgumentList?.Arguments.FirstOrDefault(argument => argument.NameEquals?.Name.ToString() == "Description")?.Expression.ToString() ?? string.Empty;

        if (string.IsNullOrEmpty(functionDescription))
        {
            // if functionDescription is empty, then try to get it from documentationCommentTrivia
            // firstly, try getting from <summary> tag
            var summary = documentationCommentTrivia?.Content.GetFirstXmlElement("summary");
            if (summary is not null && XElement.Parse(summary.ToString()) is XElement element)
            {
                functionDescription = element.Nodes().OfType<XText>().FirstOrDefault()?.Value;

                // remove [space...][//|///][space...] from functionDescription
                // replace [^\S\r\n]+[\/]+\s* with empty string
                functionDescription = System.Text.RegularExpressions.Regex.Replace(functionDescription, @"[^\S\r\n]+\/[\/]+\s*", string.Empty);
            }
            else
            {
                // if <summary> tag is not exist, then simply use the entire leading trivia as functionDescription
                functionDescription = method.GetLeadingTrivia().ToString();

                // remove [space...][//|///][space...] from functionDescription
                // replace [^\S\r\n]+[\/]+\s* with empty string
                functionDescription = System.Text.RegularExpressions.Regex.Replace(functionDescription, @"[^\S\r\n]+\/[\/]+\s*", string.Empty);
            }
        }

        // get parameters
        var parameters = method.ParameterList.Parameters.Select(parameter =>
        {
            var description = $"{parameter.Identifier}. type is {parameter.Type}";

            // try to get parameter description from documentationCommentTrivia
            var parameterDocumentationComment = documentationCommentTrivia?.GetParameterDescriptionFromDocumentationCommentTriviaSyntax(parameter.Identifier.ToString());
            if (parameterDocumentationComment is not null)
            {
                description = parameterDocumentationComment.ToString();
                // remove [space...][//|///][space...] from functionDescription
                // replace [^\S\r\n]+[\/]+\s* with empty string
                description = System.Text.RegularExpressions.Regex.Replace(description, @"[^\S\r\n]+\/[\/]+\s*", string.Empty);
            }
            var jsonItemType = parameter.Type!.ToString().EndsWith("[]") ? parameter.Type!.ToString().Substring(0, parameter.Type!.ToString().Length - 2) : null;
            return new SourceGeneratorParameterContract
            {
                Name = parameter.Identifier.ToString(),
                JsonType = parameter.Type!.ToString() switch
                {
                    "string" => "string",
                    "string[]" => "array",
                    "System.Int32" or "int" => "integer",
                    "System.Int64" or "long" => "integer",
                    "System.Single" or "float" => "number",
                    "System.Double" or "double" => "number",
                    "System.Boolean" or "bool" => "boolean",
                    "System.DateTime" => "string",
                    "System.Guid" => "string",
                    "System.Object" => "object",
                    _ => "object",
                },
                JsonItemType = jsonItemType,
                Type = parameter.Type!.ToString(),
                Description = description,
                IsOptional = parameter.Default != null,
                // if Default is null or "null", then DefaultValue is null
                DefaultValue = parameter.Default?.ToString() == "null" ? null : parameter.Default?.Value.ToString(),
            };
        });

        return new SourceGeneratorFunctionContract
        {
            ClassName = className,
            Namespace = namespaceName,
            Name = functionName,
            Description = functionDescription?.Trim() ?? functionName,
            Parameters = parameters.ToArray(),
            ReturnType = method.ReturnType.ToString(),
        };
    }
}
