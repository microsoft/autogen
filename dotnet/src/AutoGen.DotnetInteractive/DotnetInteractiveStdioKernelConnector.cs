// Copyright (c) Microsoft Corporation. All rights reserved.
// DotnetInteractiveStdioKernelConnector.cs

using AutoGen.DotnetInteractive.Extension;
using Microsoft.DotNet.Interactive;
using Microsoft.DotNet.Interactive.Commands;
using Microsoft.DotNet.Interactive.Connection;

namespace AutoGen.DotnetInteractive;

public class DotnetInteractiveStdioKernelConnector
{
    private string workingDirectory;
    private InteractiveService interactiveService;
    private string kernelName;
    private List<SubmitCode> setupCommands = new List<SubmitCode>();

    internal DotnetInteractiveStdioKernelConnector(string workingDirectory, string kernelName = "root-proxy")
    {
        this.workingDirectory = workingDirectory;
        this.interactiveService = new InteractiveService(workingDirectory);
        this.kernelName = kernelName;
    }

    public DotnetInteractiveStdioKernelConnector RestoreDotnetInteractive()
    {
        this.interactiveService.RestoreDotnetInteractive();

        return this;
    }

    public DotnetInteractiveStdioKernelConnector AddPythonKernel(
        string venv,
        string kernelName = "python")
    {
        var magicCommand = $"#!connect jupyter --kernel-name {kernelName} --kernel-spec {venv}";
        var connectCommand = new SubmitCode(magicCommand);

        this.setupCommands.Add(connectCommand);

        return this;
    }

    public async Task<Kernel> BuildAsync(CancellationToken ct = default)
    {
        var compositeKernel = new CompositeKernel();
        var url = KernelHost.CreateHostUri(this.kernelName);
        var cmd = new string[]
            {
                    "dotnet",
                    "tool",
                    "run",
                    "dotnet-interactive",
                    $"[cb-{this.kernelName}]",
                    "stdio",
                    //"--default-kernel",
                    //"csharp",
                    "--working-dir",
                    $@"""{workingDirectory}""",
            };

        var connector = new StdIoKernelConnector(
            cmd,
            this.kernelName,
            url,
            new DirectoryInfo(this.workingDirectory));

        var rootProxyKernel = await connector.CreateRootProxyKernelAsync();

        rootProxyKernel.KernelInfo.SupportedKernelCommands.Add(new(nameof(SubmitCode)));

        var dotnetKernel = await connector.CreateProxyKernelAsync(".NET");
        foreach (var setupCommand in this.setupCommands)
        {
            var setupCommandResult = await rootProxyKernel.SendAsync(setupCommand, ct);
            setupCommandResult.ThrowOnCommandFailed();
        }

        //// Get proxies for each subkernel present inside the dotnet - interactive tool.
        //var requestKernelInfoCommand = new RequestKernelInfo(rootProxyKernel.KernelInfo.RemoteUri);
        //var result =
        //    await rootProxyKernel.SendAsync(
        //        requestKernelInfoCommand,
        //        ct).ConfigureAwait(false);

        //var subKernels = result.Events.OfType<KernelInfoProduced>();

        //foreach (var kernelInfoProduced in result.Events.OfType<KernelInfoProduced>())
        //{
        //    var kernelInfo = kernelInfoProduced.KernelInfo;
        //    if (kernelInfo is not null && !kernelInfo.IsProxy && !kernelInfo.IsComposite)
        //    {
        //        var proxyKernel = await connector.CreateProxyKernelAsync(kernelInfo).ConfigureAwait(false);
        //        proxyKernel.SetUpValueSharingIfSupported();
        //        compositeKernel.Add(proxyKernel);
        //    }
        //}

        ////compositeKernel.DefaultKernelName = "csharp";
        //compositeKernel.Add(rootProxyKernel);

        return rootProxyKernel;
    }
}
