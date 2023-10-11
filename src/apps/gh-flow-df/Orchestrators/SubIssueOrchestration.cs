using Microsoft.Azure.Functions.Worker;
using Microsoft.DurableTask;
using Microsoft.SKDevTeam;

namespace SK.DevTeam
{
    [System.Diagnostics.CodeAnalysis.SuppressMessage("Usage", "CA2007: Do not directly await a Task", Justification = "Durable functions")]
    public static class SubIssueOrchestration
    {
        public static string IssueClosed = "IssueClosed";
        public static string ContainerTerminated = "ContainerTerminated";

        private static async Task<SkillResponse<string>> CallSkill(TaskOrchestrationContext context, SkillRequest request)
        {
            var newIssueResponse = await context.CallActivityAsync<NewIssueResponse>(nameof(IssuesActivities.CreateIssue), new NewIssueRequest
            {
                IssueRequest = request.IssueRequest,
                Skill = request.Skill,
                Function = request.Function
            });

            var metadata = await context.CallActivityAsync<IssueMetadata>(nameof(MetadataActivities.SaveMetadata), new IssueMetadata
            {
                Number = newIssueResponse.Number,
                InstanceId = context.InstanceId,
                Id = Guid.NewGuid().ToString(),
                CommentId = newIssueResponse.CommentId,
                Org = request.IssueRequest.Org,
                Repo = request.IssueRequest.Repo,
                PartitionKey = $"{request.IssueRequest.Org}{request.IssueRequest.Repo}{newIssueResponse.Number}",
                RowKey = $"{request.IssueRequest.Org}{request.IssueRequest.Repo}{newIssueResponse.Number}",
                Timestamp = DateTimeOffset.UtcNow
            });
            bool issueClosed = await context.WaitForExternalEvent<bool>(IssueClosed);
            var lastComment = await context.CallActivityAsync<string>(nameof(IssuesActivities.GetLastComment), new IssueOrchestrationRequest
            {
                Org = request.IssueRequest.Org,
                Repo = request.IssueRequest.Repo,
                Number = newIssueResponse.Number
            });

            return new SkillResponse<string> { Output = lastComment, SuborchestrationId = context.InstanceId };
        }

        [Function(nameof(CreateReadme))]
        public static async Task<SkillResponse<string>> CreateReadme(
        [OrchestrationTrigger] TaskOrchestrationContext context, IssueOrchestrationRequest request)
        {
            return await CallSkill(context, new SkillRequest
            {
                IssueRequest = request,
                Skill = nameof(PM),
                Function = nameof(PM.Readme)
            });
        }

        [Function(nameof(CreatePlan))]
        public static async Task<SkillResponse<string>> CreatePlan(
        [OrchestrationTrigger] TaskOrchestrationContext context, IssueOrchestrationRequest request)
        {
            return await CallSkill(context, new SkillRequest
            {
                IssueRequest = request,
                Skill = nameof(DevLead),
                Function = nameof(DevLead.Plan)
            });
        }

        [Function(nameof(Implement))]
        public static async Task<SkillResponse<string>> Implement(
        [OrchestrationTrigger] TaskOrchestrationContext context, IssueOrchestrationRequest request)
        {
            return await CallSkill(context, new SkillRequest
            {
                IssueRequest = request,
                Skill = nameof(Developer),
                Function = nameof(Developer.Implement)
            });
        }

        [Function(nameof(ImplementAndSave))]
        public static async Task<bool> ImplementAndSave(
        [OrchestrationTrigger] TaskOrchestrationContext context, RunAndSaveRequest request)
        {
            var implementResult = await context.CallSubOrchestratorAsync<SkillResponse<string>>(nameof(Implement), request.Request);
            await context.CallSubOrchestratorAsync<string>(nameof(AddToPR), new AddToPRRequest
            {
                Output = implementResult.Output,
                IssueOrchestrationId = request.InstanceId,
                SubOrchestrationId = implementResult.SuborchestrationId,
                Extension = "sh",
                RunInSandbox = true,
                Request = request.Request
            });
            return true;
        }

        [Function(nameof(ReadmeAndSave))]
        public static async Task<bool> ReadmeAndSave(
        [OrchestrationTrigger] TaskOrchestrationContext context, RunAndSaveRequest request)
        {
            var readmeResult = await context.CallSubOrchestratorAsync<SkillResponse<string>>(nameof(CreateReadme), request.Request);
            context.CallSubOrchestratorAsync<string>(nameof(AddToPR), new AddToPRRequest
            {
                Output = readmeResult.Output,
                IssueOrchestrationId = request.InstanceId,
                SubOrchestrationId = readmeResult.SuborchestrationId,
                Extension = "md",
                RunInSandbox = false,
                Request = request.Request
            });
            return true;
        }

        [Function(nameof(AddToPR))]
        public static async Task<string> AddToPR(
        [OrchestrationTrigger] TaskOrchestrationContext context, AddToPRRequest request)
        {
            var saveScriptResponse = await context.CallActivityAsync<bool>(nameof(PullRequestActivities.SaveOutput), new SaveOutputRequest
            {
                Output = request.Output,
                IssueOrchestrationId = request.IssueOrchestrationId,
                SubOrchestrationId = request.SubOrchestrationId,
                Extension = request.Extension,
                Directory = "output",
                FileName = request.RunInSandbox ? "run" : "readme"
            });

            if (request.RunInSandbox)
            {
                var newRequest = new RunInSandboxRequest
                {
                    PrRequest = request,
                    SanboxOrchestrationId = context.InstanceId
                };
                var runScriptResponse = await context.CallActivityAsync<bool>(nameof(PullRequestActivities.RunInSandbox), newRequest);
                bool containerTerminated = await context.WaitForExternalEvent<bool>(ContainerTerminated);
            }

            // this is not ideal, as the script might be still running and there might be files that are not yet generated
            var commitResponse = await context.CallActivityAsync<bool>(nameof(PullRequestActivities.CommitToGithub), new GHCommitRequest
            {
                IssueOrchestrationId = request.IssueOrchestrationId,
                SubOrchestrationId = request.SubOrchestrationId,
                Directory = "output",
                Org = request.Request.Org,
                Repo = request.Request.Repo,
                Branch = request.Request.Branch
            });

            return default;
        }
    }
}