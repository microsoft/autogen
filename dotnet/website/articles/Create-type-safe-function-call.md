## Type-safe function call

`AutoGen` provides a source generator to easness the trouble of manually craft function definition and function call wrapper from a function. To use this feature, simply add the `AutoGen.SourceGenerator` package to your project and decorate your function with [`Function`](../api/AutoGen.FunctionAttribute.yml) attribute.

```xml
<ItemGroup>
    <PackageReference Include="AutoGen.SourceGenerator" />
</ItemGroup>
```

```xml
<PropertyGroup>
    <!-- This enables structural xml document support -->
    <GenerateDocumentationFile>true</GenerateDocumentationFile>
</PropertyGroup>
```

> [!NOTE]
> It's recommended to enable structural xml document support by setting `GenerateDocumentationFile` property to true in your project file. This allows source generator to leverage the documentation of the function when generating the function definition.

Then, for the methods you want to generate function definition and function call wrapper, mark them with `Function` attribute:

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/TypeSafeFunctionCallCodeSnippet.cs?name=code_snippet_3)]

> [!NOTE]
> A `public partial` class is required for the source generator to generate code.

> [!TIP]
> For the best of performance, try using primitive types for the parameters and return type.

The source generator will generate the following code based on the method signature and documentation. It helps you save the effort of writing function definition and keep it up to date with the actual method signature.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/TypeSafeFunctionCallCodeSnippet.cs?name=code_snippet_1)]

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/TypeSafeFunctionCallCodeSnippet.cs?name=code_snippet_2)]
