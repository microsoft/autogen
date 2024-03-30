using System.Reflection;
using Azure;
using Azure.AI.OpenAI;
using Elsa.Extensions;
using Elsa.Workflows;
using Elsa.Workflows.Contracts;
using Elsa.Workflows.Models;
using Elsa.Workflows.UIHints;
using Microsoft.Extensions.Http.Resilience;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SKDevTeam;

namespace Elsa.SemanticKernel;

//<summary>
// Loads the Semantic Kernel skills and then generates activites for each skill
//</summary>
public class SemanticKernelActivityProvider : IActivityProvider
{
    private readonly IActivityFactory _activityFactory;
    private readonly IActivityDescriber _activityDescriber;

    public SemanticKernelActivityProvider(IActivityFactory activityFactory, IActivityDescriber activityDescriber)
    {
        _activityFactory = activityFactory;
        _activityDescriber = activityDescriber;
    }
    public async ValueTask<IEnumerable<ActivityDescriptor>> GetDescriptorsAsync(CancellationToken cancellationToken = default)
    {
        // get the kernel
        var kernel = KernelBuilder();

        // get a list of skills in the assembly
        var skills = LoadSkillsFromAssemblyAsync("skills", kernel);
        var functionsAvailable = kernel.Plugins.GetFunctionsMetadata();
        
        // create activity descriptors for each skilland function
        var activities = new List<ActivityDescriptor>();
        foreach (var function in functionsAvailable)
        {
            Console.WriteLine($"Creating Activities for Plugin: {function.PluginName}");
            activities.Add(CreateActivityDescriptorFromSkillAndFunction(function, cancellationToken));
        }

        return activities;
    }

    /// <summary>
    /// Creates an activity descriptor from a skill and function.
    /// </summary>
    /// <param name="function">The semantic kernel function</param>
    /// <param name="cancellationToken">An optional cancellation token.</param>
    /// <returns>An activity descriptor.</returns>
    private ActivityDescriptor CreateActivityDescriptorFromSkillAndFunction(KernelFunctionMetadata function, CancellationToken cancellationToken = default)
    {
        // Create a fully qualified type name for the activity 
        var thisNamespace = GetType().Namespace;
        var fullTypeName = $"{thisNamespace}.{function.PluginName}.{function.Name}";
        Console.WriteLine($"Creating Activity: {fullTypeName}");

        // create inputs from the function parameters - the SemanticKernelSkill activity will be the base for each activity
        var inputs = new List<InputDescriptor>();
        foreach (var p in function.Parameters) { inputs.Add(CreateInputDescriptorFromSKParameter(p)); }
        inputs.Add(CreateInputDescriptor(typeof(string), "SkillName", function.PluginName, "The name of the skill to use (generated, do not change)"));
        inputs.Add(CreateInputDescriptor(typeof(string), "FunctionName", function.Name, "The name of the function to use (generated, do not change)"));
        inputs.Add(CreateInputDescriptor(typeof(int), "MaxRetries", KernelSettings.DefaultMaxRetries, "Max Retries to contact AI Service"));

        return new ActivityDescriptor
        {
            Kind = ActivityKind.Task,
            Category = "Semantic Kernel",
            Description = function.Description,
            Name = function.Name,
            TypeName = fullTypeName,
            Namespace = $"{thisNamespace}.{function.PluginName}",
            DisplayName = $"{function.PluginName}.{function.Name}",
            Inputs = inputs,
            Outputs = new[] {new OutputDescriptor()},
            Constructor = context =>
            {
                // The constructor is called when an activity instance of this type is requested.

                // Create the activity instance.
                var activityInstance = _activityFactory.Create<SemanticKernelSkill>(context);

                // Customize the activity type name.
                activityInstance.Type = fullTypeName;

                // Configure the activity's URL and method properties.
                activityInstance.SkillName = new Input<string?>(function.PluginName);
                activityInstance.FunctionName = new Input<string?>(function.Name);

                return activityInstance;
            }
        };

    }
    /// <summary>
    /// Creates an input descriptor for a single line string
    /// </summary>
    /// <param name="name">The name of the input field</param>
    /// <param name="description">The description of the input field</param>
    private InputDescriptor CreateInputDescriptor(Type inputType, string name, Object defaultValue, string description)
    {
        var inputDescriptor = new InputDescriptor
        {
            Description = description,
            DefaultValue = defaultValue,
            Type = inputType,
            Name = name,
            DisplayName = name,
            IsSynthetic = true, // This is a synthetic property, i.e. it is not part of the activity's .NET type.
            IsWrapped = true, // This property is wrapped within an Input<T> object.
            UIHint = InputUIHints.SingleLine,
            ValueGetter = activity => activity.SyntheticProperties.GetValueOrDefault(name),
            ValueSetter = (activity, value) => activity.SyntheticProperties[name] = value!,
        };
        return inputDescriptor;
    }

    /// <summary>
    /// Creates an input descriptor from an sk funciton parameter definition.
    /// </summary>
    /// <param name="parameter">The function parameter.</param>
    /// <returns>An input descriptor.</returns>
    private InputDescriptor CreateInputDescriptorFromSKParameter(KernelParameterMetadata parameter)
    {
        var inputDescriptor = new InputDescriptor
        {
            Description = string.IsNullOrEmpty(parameter.Description) ? parameter.Name : parameter.Description,
            DefaultValue = parameter.DefaultValue == null ? string.Empty : parameter.DefaultValue,
            Type = typeof(string),
            Name = parameter.Name,
            DisplayName = parameter.Name,
            IsSynthetic = true, // This is a synthetic property, i.e. it is not part of the activity's .NET type.
            IsWrapped = true, // This property is wrapped within an Input<T> object.
            UIHint = InputUIHints.MultiLine,
            ValueGetter = activity => activity.SyntheticProperties.GetValueOrDefault(parameter.Name),
            ValueSetter = (activity, value) => activity.SyntheticProperties[parameter.Name] = value!,

        };
        return inputDescriptor;
    }

    ///<summary>
    /// Gets a list of the skills in the assembly
    ///</summary>
    private IEnumerable<string> LoadSkillsFromAssemblyAsync(string assemblyName, Kernel kernel)
    {
        var skills = new List<string>();
        var assembly = Assembly.Load(assemblyName);
        Type[] skillTypes = assembly.GetTypes().ToArray();
        foreach (Type skillType in skillTypes)
        {
            if (skillType.Namespace.Equals("Microsoft.AI.DevTeam"))
            {
                skills.Add(skillType.Name);
                var functions = skillType.GetFields();
                foreach (var function in functions)
                {
                    string field = function.FieldType.ToString();
                    if (field.Equals("Microsoft.AI.DevTeam.SemanticFunctionConfig"))
                    {
                        var promptTemplate = SemanticFunctionConfig.ForSkillAndFunction(skillType.Name, function.Name);
                        var skfunc = kernel.CreateFunctionFromPrompt(
                            promptTemplate.PromptTemplate, new OpenAIPromptExecutionSettings { MaxTokens = 8000, Temperature = 0.4, TopP = 1 });

                        Console.WriteLine($"SKActivityProvider Added SK function: {skfunc.Metadata.PluginName}.{skfunc.Name}");
                    }
                }
            }
        }
        return skills;
    }

    /// <summary>
    /// Gets a semantic kernel instance
    /// </summary>
    /// <returns>Microsoft.SemanticKernel.IKernel</returns>
    private Kernel KernelBuilder()
    {
        var kernelSettings = KernelSettings.LoadSettings();

        var clientOptions = new OpenAIClientOptions();
        clientOptions.Retry.NetworkTimeout = TimeSpan.FromMinutes(5);
        var openAIClient = new OpenAIClient(new Uri(kernelSettings.Endpoint), new AzureKeyCredential(kernelSettings.ApiKey), clientOptions);
        var builder = Kernel.CreateBuilder();
        builder.Services.AddLogging( c=> c.AddConsole().AddDebug().SetMinimumLevel(LogLevel.Debug));
        builder.Services.AddAzureOpenAIChatCompletion(kernelSettings.DeploymentOrModelId, openAIClient);
        builder.Services.ConfigureHttpClientDefaults(c=>
        {
            c.AddStandardResilienceHandler().Configure( o=> {
                o.Retry.MaxRetryAttempts = 5;
                o.Retry.BackoffType = Polly.DelayBackoffType.Exponential;
            });
        });
        return builder.Build();
    }
}

