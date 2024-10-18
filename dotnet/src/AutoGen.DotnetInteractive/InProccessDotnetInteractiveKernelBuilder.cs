// Copyright (c) Microsoft Corporation. All rights reserved.
// InProccessDotnetInteractiveKernelBuilder.cs

#if NET8_0_OR_GREATER
using AutoGen.DotnetInteractive.Extension;
using Microsoft.DotNet.Interactive;
using Microsoft.DotNet.Interactive.Commands;
using Microsoft.DotNet.Interactive.CSharp;
using Microsoft.DotNet.Interactive.FSharp;
using Microsoft.DotNet.Interactive.Jupyter;
using Microsoft.DotNet.Interactive.PackageManagement;
using Microsoft.DotNet.Interactive.PowerShell;

namespace AutoGen.DotnetInteractive;

/// <summary>
/// Build an in-proc dotnet interactive kernel.
/// </summary>
public class InProccessDotnetInteractiveKernelBuilder
{
    private readonly CompositeKernel compositeKernel;

    internal InProccessDotnetInteractiveKernelBuilder()
    {
        this.compositeKernel = new CompositeKernel();

        // add jupyter connector
        this.compositeKernel.AddKernelConnector(
            new ConnectJupyterKernelCommand()
            .AddConnectionOptions(new JupyterHttpKernelConnectionOptions())
            .AddConnectionOptions(new JupyterLocalKernelConnectionOptions()));
    }

    public InProccessDotnetInteractiveKernelBuilder AddCSharpKernel(IEnumerable<string>? aliases = null)
    {
        aliases ??= ["c#", "C#", "csharp"];
        // create csharp kernel
        var csharpKernel = new CSharpKernel()
            .UseNugetDirective((k, resolvedPackageReference) =>
            {

                k.AddAssemblyReferences(resolvedPackageReference
                    .SelectMany(r => r.AssemblyPaths));
                return Task.CompletedTask;
            })
            .UseKernelHelpers()
            .UseWho()
            .UseMathAndLaTeX()
            .UseValueSharing();

        this.AddKernel(csharpKernel, aliases);

        return this;
    }

    public InProccessDotnetInteractiveKernelBuilder AddFSharpKernel(IEnumerable<string>? aliases = null)
    {
        aliases ??= ["f#", "F#", "fsharp"];
        // create fsharp kernel
        var fsharpKernel = new FSharpKernel()
            .UseDefaultFormatting()
            .UseKernelHelpers()
            .UseWho()
            .UseMathAndLaTeX()
            .UseValueSharing();

        this.AddKernel(fsharpKernel, aliases);

        return this;
    }

    public InProccessDotnetInteractiveKernelBuilder AddPowershellKernel(IEnumerable<string>? aliases = null)
    {
        aliases ??= ["pwsh", "powershell"];
        // create powershell kernel
        var powershellKernel = new PowerShellKernel()
                .UseProfiles()
                .UseValueSharing();

        this.AddKernel(powershellKernel, aliases);

        return this;
    }

    public InProccessDotnetInteractiveKernelBuilder AddPythonKernel(string venv, string kernelName = "python")
    {
        // create python kernel
        var magicCommand = $"#!connect jupyter --kernel-name {kernelName} --kernel-spec {venv}";
        var connectCommand = new SubmitCode(magicCommand);
        var result = this.compositeKernel.SendAsync(connectCommand).Result;

        result.ThrowOnCommandFailed();

        return this;
    }

    public CompositeKernel Build()
    {
        return this.compositeKernel
            .UseDefaultMagicCommands()
            .UseImportMagicCommand();
    }

    private InProccessDotnetInteractiveKernelBuilder AddKernel(Kernel kernel, IEnumerable<string>? aliases = null)
    {
        this.compositeKernel.Add(kernel, aliases);
        return this;
    }
}
#endif
