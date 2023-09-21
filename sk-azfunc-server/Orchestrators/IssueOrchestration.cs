using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.DurableTask;
using Microsoft.DurableTask.Client;
using Microsoft.Extensions.Logging;
using static SK.DevTeam.SubIssueOrchestration;

namespace SK.DevTeam
{
    [System.Diagnostics.CodeAnalysis.SuppressMessage("Usage", "CA2007: Do not directly await a Task", Justification = "Durable functions")]
    public static class IssueOrchestration
    {
        [Function("IssueOrchestrationStart")]
        public static async Task<string> HttpStart(
            [HttpTrigger(AuthorizationLevel.Anonymous, "post", Route = "doit")] HttpRequestData req,
            [DurableClient] DurableTaskClient client,
            FunctionContext executionContext)
        {
            ILogger logger = executionContext.GetLogger("IssueOrchestration_HttpStart");
            var request = await req.ReadFromJsonAsync<IssueOrchestrationRequest>();
            string instanceId = await client.ScheduleNewOrchestrationInstanceAsync(
                nameof(IssueOrchestration), request);

            logger.LogInformation("Started orchestration with ID = '{instanceId}'.", instanceId);
            return "";
        }

        [Function(nameof(IssueOrchestration))]
        public static async Task<List<string>> RunOrchestrator(
            [OrchestrationTrigger] TaskOrchestrationContext context, IssueOrchestrationRequest request)
        {
            var logger = context.CreateReplaySafeLogger(nameof(IssueOrchestration));
            var outputs = new List<string>();

            var newGHBranchRequest = new GHNewBranch
            {
                Org = request.Org,
                Repo = request.Repo,
                Branch = request.Branch,
                Number = request.Number
            };

            var newBranch = await context.CallActivityAsync<bool>(nameof(PullRequestActivities.CreateBranch), newGHBranchRequest);

            var readmeTask = await context.CallSubOrchestratorAsync<bool>(nameof(ReadmeAndSave), new RunAndSaveRequest
            {
                Request = request,
                InstanceId = context.InstanceId
            });

            var newPR = await context.CallActivityAsync<bool>(nameof(PullRequestActivities.CreatePR), newGHBranchRequest);

            var planTask = await context.CallSubOrchestratorAsync<SkillResponse<string>>(nameof(CreatePlan), request);
            var plan = JsonSerializer.Deserialize<DevLeadPlanResponse>(planTask.Output);

            var implementationTasks = plan.steps.SelectMany(s => s.subtasks.Select(st =>
                        context.CallSubOrchestratorAsync<bool>(nameof(ImplementAndSave), new RunAndSaveRequest
                        {
                            Request = new IssueOrchestrationRequest
                            {
                                Number = request.Number,
                                Org = request.Org,
                                Repo = request.Repo,
                                Input = st.prompt,
                            },
                            InstanceId = context.InstanceId
                        })));

            await Task.WhenAll(implementationTasks);
            return outputs;
        }
    }
}