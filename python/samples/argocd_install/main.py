from dotenv import load_dotenv
import os
import asyncio
from pathlib import Path

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent, CodeExecutorAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

# Load environment variables
load_dotenv("./.env")

async def main() -> None:
    """Main function to run Autogen agents and execute tasks sequentially."""
    
    # Initialize Model Client
    model_client = AzureOpenAIChatCompletionClient(
        model=os.getenv("model"),
        azure_endpoint=os.getenv("AZURE_API_BASE"),
        api_key=os.getenv("AZURE_API_KEY"),
        api_version=os.getenv("AZURE_API_VERSION"),
    )

    # Retrieve GitHub credentials from environment variables
    repo_url = os.getenv("REPO_URL", "https://github.com/example/repo")  # Default if not set
    repo_pat = os.getenv("REPO_PAT", "your-pat-token")

    # Setup Code Execution Environment
    work_dir = Path("coding")
    work_dir.mkdir(exist_ok=True)
    #local_executor = LocalCommandLineCodeExecutor(timeout=120, work_dir=work_dir)
    local_executor = LocalCommandLineCodeExecutor(work_dir=work_dir)
    code_executor_agent = CodeExecutorAgent("code_executor", code_executor=local_executor)

    # Define Agents
    assistant = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="""Use the code_executor_agent to solve tasks. 
            When writing code, provide at least one markdown-encoded code block to execute.
            That is, quoting code in ```python or ```sh code blocks).
            """,
        reflect_on_tool_use=True,
    )
    user_proxy = UserProxyAgent("user_proxy")

    # Termination condition
    termination = TextMentionTermination("exit")  # Type 'exit' to end the conversation.

    # Define Team
    team = RoundRobinGroupChat(
        [assistant, user_proxy, code_executor_agent],
        termination_condition=termination
    )
    
    # Task 1: Install ArgoCD on Kubernetes using Helm
    argocd_install_task = """
    Install ArgoCD on Kubernetes using Helm, if not yet installed.
    Install to the 'argocd' namespace.
    Assume kubectl and Helm are pre-configured in the local environment.
    Wait for ArgoCD pods to become responsive.
    """
    await Console(team.run_stream(task=argocd_install_task))
    
    
    # Task 2: Ensure local access to ArgoCD server
    argocd_access_task = """
    Ensure local access to ArgoCD server
    You may need port forwarding and / or a load balancer for ArgoCD server using kubectl. 
    """
    await Console(team.run_stream(task=argocd_access_task))
    
    
    # Task 3: Install ArgoCD CLI and login to server
    argocd_cli_install_task = """
    Ensure the ArgoCD CLI is installed locally. Login to the server.
    """
    await Console(team.run_stream(task=argocd_cli_install_task))
    
    
    # Task 4: Test repo access
    repo_access_task = f"""
    Use this GitHub repository: {repo_url}
    Access the repository with this fine-grained token: {repo_pat}
    
    Test repo read/write access.
    """
    await Console(team.run_stream(task=repo_access_task))
    
    
    # Task 5: Configure ArgoCD to Deploy Argo Workflows via GitOps
    argocd_config_task = f"""
    Use ArgoCD's GitOps capabilities to deploy Argo Workflows (ArgoWF) to the argowf namespace, if not yet installed.
    Store the ArgoWF config files in a GitHub repository for ArgoCD to scan. 
    Store Helm values rather than simple K8s manifests. 
    
    Retrieve the ArgoCD admin secret using:
    ```sh
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{{.data.password}}" | base64 -d
    ```
    
    Use this GitHub repository: {repo_url}
    Access the repository with this fine-grained token: {repo_pat}
    """
    await Console(team.run_stream(task=argocd_config_task))
    
# Run the script
asyncio.run(main())
