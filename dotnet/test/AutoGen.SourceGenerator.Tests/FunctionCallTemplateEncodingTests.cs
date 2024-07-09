// Using directives
using System.Text.Json; // Needed for JsonSerializer
using Xunit; // Needed for Fact and Assert
using AutoGen.SourceGenerator.Template; // Needed for FunctionCallTemplate

namespace AutoGen.SourceGenerator.Tests
{
    public class FunctionCallTemplateEncodingTests
    {
        private readonly JsonSerializerOptions jsonSerializerOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
        };

        [Fact]
        public void FunctionDescription_Should_Encode_DoubleQuotes()
        {
            // Arrange
            var functionContracts = new List<SourceGeneratorFunctionContract>
            {
                new SourceGeneratorFunctionContract
                {
                    Name = "TestFunction",
                    Description = "This is a \"test\" function",
                    Parameters = new SourceGeneratorParameterContract[]
                    {
                        new SourceGeneratorParameterContract
                        {
                            Name = "param1",
                            Description = "This is a \"parameter\" description",
                            Type = "string",
                            IsOptional = false
                        }
                    },
                    ReturnType = "void"
                }
            };

            var template = new FunctionCallTemplate
            {
                NameSpace = "TestNamespace",
                ClassName = "TestClass",
                FunctionContracts = functionContracts
            };

            // Act
            var result = template.TransformText();

            // Assert
            Assert.Contains("Description = @\"This is a \"\"test\"\" function\"", result);
            Assert.Contains("Description = @\"This is a \"\"parameter\"\" description\"", result);
        }

        [Fact]
        public void ParameterDescription_Should_Encode_DoubleQuotes()
        {
            // Arrange
            var functionContracts = new List<SourceGeneratorFunctionContract>
            {
                new SourceGeneratorFunctionContract
                {
                    Name = "TestFunction",
                    Description = "This is a test function",
                    Parameters = new SourceGeneratorParameterContract[]
                    {
                        new SourceGeneratorParameterContract
                        {
                            Name = "param1",
                            Description = "This is a \"parameter\" description",
                            Type = "string",
                            IsOptional = false
                        }
                    },
                    ReturnType = "void"
                }
            };

            var template = new FunctionCallTemplate
            {
                NameSpace = "TestNamespace",
                ClassName = "TestClass",
                FunctionContracts = functionContracts
            };

            // Act
            var result = template.TransformText();

            // Assert
            Assert.Contains("Description = @\"This is a \"\"parameter\"\" description\"", result);
        }
    }
}