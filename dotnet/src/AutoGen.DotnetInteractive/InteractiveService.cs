// Copyright (c) Microsoft Corporation. All rights reserved.
// InteractiveService.cs

using System.Diagnostics;
using System.Reactive.Linq;
using System.Reflection;
using AutoGen.DotnetInteractive.Extension;
using Microsoft.DotNet.Interactive;
using Microsoft.DotNet.Interactive.Commands;
using Microsoft.DotNet.Interactive.Connection;
using Microsoft.DotNet.Interactive.Events;
using Microsoft.DotNet.Interactive.Utility;

namespace AutoGen.DotnetInteractive;

public class InteractiveService : IDisposable
{
    private Kernel? kernel;
    private bool disposedValue;
    private string? installingDirectory;

    /// <summary>
    /// Install dotnet interactive tool to <paramref name="installingDirectory"/>
    /// and create an instance of <see cref="InteractiveService"/>.
    /// 
    /// When using this constructor, you need to call <see cref="StartAsync(string, CancellationToken)"/> to install dotnet interactive tool
    /// and start the kernel.
    /// </summary>
    /// <param name="installingDirectory">dotnet interactive installing directory</param>
    public InteractiveService(string installingDirectory)
    {
        this.installingDirectory = installingDirectory;
    }

    /// <summary>
    /// Create an instance of <see cref="InteractiveService"/> with a running kernel.
    /// When using this constructor, you don't need to call <see cref="StartAsync(string, CancellationToken)"/> to start the kernel.
    /// </summary>
    /// <param name="kernel"></param>
    public InteractiveService(Kernel kernel)
    {
        this.kernel = kernel;
    }

    public Kernel? Kernel => this.kernel;

    public async Task<bool> StartAsync(string workingDirectory, CancellationToken ct = default)
    {
        if (this.kernel != null)
        {
            return true;
        }

        this.kernel = await this.CreateKernelAsync(workingDirectory, true, ct);
        return true;
    }

    public async Task<string?> SubmitCommandAsync(SubmitCode cmd, CancellationToken ct)
    {
        if (this.kernel == null)
        {
            throw new ArgumentException("Kernel is not running");
        }

        return await this.kernel.RunSubmitCodeCommandAsync(cmd.Code, cmd.TargetKernelName, ct);
    }

    public async Task<string?> SubmitPowershellCodeAsync(string code, CancellationToken ct)
    {
        var command = new SubmitCode(code, targetKernelName: "pwsh");
        return await this.SubmitCommandAsync(command, ct);
    }

    public async Task<string?> SubmitCSharpCodeAsync(string code, CancellationToken ct)
    {
        var command = new SubmitCode(code, targetKernelName: "csharp");
        return await this.SubmitCommandAsync(command, ct);
    }

    public bool RestoreDotnetInteractive()
    {
        if (this.installingDirectory is null)
        {
            throw new ArgumentException("Installing directory is not set");
        }

        // write RestoreInteractive.config from embedded resource to this.workingDirectory
        var assembly = Assembly.GetAssembly(typeof(InteractiveService))!;
        var resourceName = "AutoGen.DotnetInteractive.RestoreInteractive.config";
        using (var stream = assembly.GetManifestResourceStream(resourceName)!)
        using (var fileStream = File.Create(Path.Combine(this.installingDirectory, "RestoreInteractive.config")))
        {
            stream.CopyTo(fileStream);
        }

        // write dotnet-tool.json from embedded resource to this.workingDirectory

        resourceName = "AutoGen.DotnetInteractive.dotnet-tools.json";
        using (var stream2 = assembly.GetManifestResourceStream(resourceName)!)
        using (var fileStream2 = File.Create(Path.Combine(this.installingDirectory, "dotnet-tools.json")))
        {
            stream2.CopyTo(fileStream2);
        }

        var psi = new ProcessStartInfo
        {
            FileName = "dotnet",
            Arguments = $"tool restore --configfile RestoreInteractive.config",
            WorkingDirectory = this.installingDirectory,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        using var process = new Process { StartInfo = psi };
        process.OutputDataReceived += this.PrintProcessOutput;
        process.ErrorDataReceived += this.PrintProcessOutput;
        process.Start();
        process.BeginErrorReadLine();
        process.BeginOutputReadLine();
        process.WaitForExit();

        return process.ExitCode == 0;
    }

    private async Task<Kernel> CreateKernelAsync(string workingDirectory, bool restoreWhenFail = true, CancellationToken ct = default)
    {
#if NETSTANDARD2_0
        var processID = Process.GetCurrentProcess().Id;
#else
        var processID = Environment.ProcessId;
#endif
        try
        {
            var url = KernelHost.CreateHostUriForCurrentProcessId();
            var compositeKernel = new CompositeKernel("cbcomposite");
            var cmd = new string[]
            {
                    "dotnet",
                    "tool",
                    "run",
                    "dotnet-interactive",
                    $"[cb-{processID}]",
                    "stdio",
                    //"--default-kernel",
                    //"csharp",
                    "--working-dir",
                    $@"""{workingDirectory}""",
            };
            var connector = new StdIoKernelConnector(
                cmd,
                "root-proxy",
                url,
                new DirectoryInfo(workingDirectory));

            // Start the dotnet-interactive tool and get a proxy for the root composite kernel therein.
            using var rootProxyKernel = await connector.CreateRootProxyKernelAsync().ConfigureAwait(false);

            // Get proxies for each subkernel present inside the dotnet-interactive tool.
            var requestKernelInfoCommand = new RequestKernelInfo(rootProxyKernel.KernelInfo.RemoteUri);
            var result =
                await rootProxyKernel.SendAsync(
                    requestKernelInfoCommand,
                    ct).ConfigureAwait(false);

            var subKernels = result.Events.OfType<KernelInfoProduced>();

            foreach (var kernelInfoProduced in result.Events.OfType<KernelInfoProduced>())
            {
                var kernelInfo = kernelInfoProduced.KernelInfo;
                if (kernelInfo is not null && !kernelInfo.IsProxy && !kernelInfo.IsComposite)
                {
                    var proxyKernel = await connector.CreateProxyKernelAsync(kernelInfo).ConfigureAwait(false);
                    proxyKernel.SetUpValueSharingIfSupported();
                    compositeKernel.Add(proxyKernel);
                }
            }

            //compositeKernel.DefaultKernelName = "csharp";
            compositeKernel.Add(rootProxyKernel);

            return compositeKernel;
        }
        catch (CommandLineInvocationException) when (restoreWhenFail)
        {
            var success = this.RestoreDotnetInteractive();

            if (success)
            {
                return await this.CreateKernelAsync(workingDirectory, false, ct);
            }

            throw;
        }
    }

    private void PrintProcessOutput(object sender, DataReceivedEventArgs e)
    {
        if (!string.IsNullOrEmpty(e.Data))
        {
            Console.WriteLine(e.Data);
        }
    }

    public bool IsRunning()
    {
        return this.kernel != null;
    }

    protected virtual void Dispose(bool disposing)
    {
        if (!disposedValue)
        {
            if (disposing)
            {
                this.kernel?.Dispose();
            }

            disposedValue = true;
        }
    }

    public void Dispose()
    {
        // Do not change this code. Put cleanup code in 'Dispose(bool disposing)' method
        Dispose(disposing: true);
        GC.SuppressFinalize(this);
    }
}
