using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Elsa;
using Elsa.Expressions.Models;
using Elsa.Extensions;
using Elsa.Workflows.Core;
using Elsa.Workflows.Core.Contracts;
using Elsa.Workflows.Core.Models;
using Elsa.Workflows.Management.Extensions;
using Elsa.Workflows.Core.Attributes;
using Elsa.Workflows.Core.Models;
using Elsa.Expressions.Models;
using Elsa.Extensions;
using Elsa.Http;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.Memory.Qdrant;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.TextEmbedding;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Microsoft.SemanticKernel.Reliability;
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
        //get a list of skills in the assembly
        var skills = await LoadSkillsFromAssemblyAsync("skills");
        var descriptors = new List<ActivityDescriptor>();
        foreach (var skill in skills)
        {
            //var descriptor = await CreateActivityDescriptors(skill, cancellationToken);
            // descriptors.Add(descriptor);
        }
        return descriptors;
    }

    ///<summary>
    /// Gets a list of the skills in the assembly
    ///</summary>
    private async Task<IEnumerable<string>> LoadSkillsFromAssemblyAsync(string assemblyName)
    {
        var skills = new List<string>();
        var assembly = Assembly.Load(assemblyName);
            //IEnumerable<Type> skillTypes = GetTypesInNamespace(assembly, "skills");
            Type[] skillTypes = assembly.GetTypes().ToArray();
            foreach(Type skillType in skillTypes)
            {
                Console.WriteLine($"Found type: {assembly.FullName}.{skillType.Namespace}.{skillType.Name}");
                if(skillType.Namespace.Equals("Microsoft.SKDevTeam"))
                {
                    skills.Add(skillType.Name);

                    Console.WriteLine($"Added skill: {skillType.Name}");
                }

            }
        return skills;
    }



    private IEnumerable<Type> GetTypesInNamespace(Assembly assembly, string nameSpace)
    {
        return
          assembly.GetTypes()
                  .Where(t => String.Equals(t.Namespace, nameSpace, StringComparison.Ordinal));
    }
}

