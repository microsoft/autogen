using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Elsa.Extensions;
using Elsa.Workflows.Core;
using Elsa.Workflows.Core.Contracts;
using Elsa.Workflows.Core.Models;
using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Orchestration;

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
        SKContext context = kernel.CreateNewContext();
        var functionsAvailable = context.Functions.GetFunctionViews();

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
    private ActivityDescriptor CreateActivityDescriptorFromSkillAndFunction(FunctionView function, CancellationToken cancellationToken = default)
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
    private InputDescriptor CreateInputDescriptorFromSKParameter(ParameterView parameter)
    {
        var inputDescriptor = new InputDescriptor
        {
            Description = string.IsNullOrEmpty(parameter.Description) ? parameter.Name : parameter.Description,
            DefaultValue = string.IsNullOrEmpty(parameter.DefaultValue) ? string.Empty : parameter.DefaultValue,
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
    private IEnumerable<string> LoadSkillsFromAssemblyAsync(string assemblyName, IKernel kernel)
    {
        var skills = new List<string>();
        var assembly = Assembly.Load(assemblyName);
        Type[] skillTypes = assembly.GetTypes().ToArray();
        foreach (Type skillType in skillTypes)
        {
            if (skillType.Namespace.Equals("Microsoft.SKDevTeam"))
            {
                skills.Add(skillType.Name);
                var functions = skillType.GetFields();
                foreach (var function in functions)
                {
                    string field = function.FieldType.ToString();
                    if (field.Equals("Microsoft.SKDevTeam.SemanticFunctionConfig"))
                    {
                        var promptTemplate = Skills.ForSkillAndFunction(skillType.Name, function.Name);
                        var skfunc = kernel.CreateSemanticFunction(
                            promptTemplate, new OpenAIRequestSettings { MaxTokens = 8000, Temperature = 0.4, TopP = 1 });

                        Console.WriteLine($"SKActivityProvider Added SK function: {skfunc.PluginName}.{skfunc.Name}");
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
    private IKernel KernelBuilder()
    {
        var kernelSettings = KernelSettings.LoadSettings();

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder.SetMinimumLevel(kernelSettings.LogLevel ?? LogLevel.Warning);
        });

        var kernel = new KernelBuilder()
        .WithLoggerFactory(loggerFactory)
        .WithAzureChatCompletionService(kernelSettings.DeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey, true, kernelSettings.ServiceId, true)
        .Build();

        return kernel;
    }

}

