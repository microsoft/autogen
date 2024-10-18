### AutoGen.SourceGenerator

This package carries a source generator that adds support for type-safe function definition generation. Simply mark a method with `Function` attribute, and the source generator will generate a function definition and a function call wrapper for you.

### Get start

First, add the following to your project file and set `GenerateDocumentationFile` property to true

```xml
<PropertyGroup>
    <!-- This enables structural xml document support -->
    <GenerateDocumentationFile>true</GenerateDocumentationFile>
</PropertyGroup>
```
```xml
<ItemGroup>
    <PackageReference Include="AutoGen.SourceGenerator" />
</ItemGroup>
```

> Nightly Build feed: https://devdiv.pkgs.visualstudio.com/DevDiv/_packaging/AutoGen/nuget/v3/index.json

Then, for the methods you want to generate function definition and function call wrapper, mark them with `Function` attribute:

> Note: For the best of performance, try using primitive types for the parameters and return type.

```csharp
// file: MyFunctions.cs

using AutoGen;

// a partial class is required
// and the class must be public
public partial class MyFunctions
{
    /// <summary>
    /// Add two numbers.
    /// </summary>
    /// <param name="a">The first number.</param>
    /// <param name="b">The second number.</param>
    [Function]
    public Task<string> AddAsync(int a, int b)
    {
        return Task.FromResult($"{a} + {b} = {a + b}");
    }
}
```

The source generator will generate the following code based on the method signature and documentation. It helps you save the effort of writing function definition and keep it up to date with the actual method signature.

```csharp
// file: MyFunctions.generated.cs
public partial class MyFunctions
{
    private class AddAsyncSchema
    {
		public int a {get; set;}
		public int b {get; set;}
    }

    public Task<string> AddAsyncWrapper(string arguments)
    {
        var schema = JsonSerializer.Deserialize<AddAsyncSchema>(
            arguments, 
            new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            });
        return AddAsync(schema.a, schema.b);
    }

    public FunctionDefinition AddAsyncFunction
    {
        get => new FunctionDefinition
		{
			Name = @"AddAsync",
            Description = """
Add two numbers.
""",
            Parameters = BinaryData.FromObjectAsJson(new
            {
                Type = "object",
                Properties = new
				{
				    a = new
				    {
					    Type = @"number",
					    Description = @"The first number.",
				    },
				    b = new
				    {
					    Type = @"number",
					    Description = @"The second number.",
				    },
                },
                Required = new []
				{
				    "a",
				    "b",
				},
            },
            new JsonSerializerOptions
			{
				PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
			})
        };
    }
}
```

For more examples, please check out the following project
- [AutoGen.BasicSamples](../samples/AutoGen.BasicSamples/)
- [AutoGen.SourceGenerator.Tests](../../test/AutoGen.SourceGenerator.Tests/)
