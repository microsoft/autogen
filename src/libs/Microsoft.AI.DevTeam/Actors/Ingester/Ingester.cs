using Microsoft.SemanticKernel;
using Octokit;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;

public class Ingester : SemanticPersona, IIngestRepo
{
    protected override string MemorySegment => "code-analysis";
    private readonly IManageGithub _ghService;
    private readonly IKernel _kernel;
    private readonly IAnalyzeCode _codeAnalyzer;
    public Ingester([PersistentState("state", "messages")] IPersistentState<SemanticPersonaState> state, IManageGithub ghService, IKernel kernel, IAnalyzeCode codeAnalyzer) : base(state)
    {
        _ghService = ghService;
        _kernel = kernel;
        _codeAnalyzer = codeAnalyzer;
    }

    public async Task IngestionFlow(string org, string repo, string branch)
    {
        var suffix = $"{org}-{repo}";
        var language = await _ghService.GetMainLanguage(org, repo);
        var files = await _ghService.GetFiles(org, repo, branch, Language.Filters[language]);

        var pm = GrainFactory.GetGrain<IManageProduct>(0, suffix);
        var dev = GrainFactory.GetGrain<IDevelopCode>(0, suffix);
        var devLead = GrainFactory.GetGrain<ILeadDevelopment>(0, suffix);
        
        foreach (var file in files)
        {
            var codeAnalysis = await _codeAnalyzer.Analyze(file.Content);
            codeAnalysis.ToList().ForEach(async c =>
                await _kernel.Memory.SaveInformationAsync(MemorySegment, c.CodeBlock, Guid.NewGuid().ToString(), c.Meaning));

            Task.WaitAll(new[] {
                pm.BuildUnderstanding(file.Content),
                dev.BuildUnderstanding(file.Content),
                devLead.BuildUnderstanding(file.Content)});
        }
    }
}

public static class Language
{
    public static Dictionary<string, Func<RepositoryContent, bool>> Filters = new Dictionary<string, Func<RepositoryContent, bool>> {
        {"C#", f => f.Name.EndsWith(".cs") }
    };
}