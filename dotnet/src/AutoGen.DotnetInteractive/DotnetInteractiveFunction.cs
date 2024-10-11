// Copyright (c) Microsoft Corporation. All rights reserved.
// DotnetInteractiveFunction.cs

using System.Text;
using Microsoft.DotNet.Interactive.Documents;
using Microsoft.DotNet.Interactive.Documents.Jupyter;

namespace AutoGen.DotnetInteractive;

public partial class DotnetInteractiveFunction : IDisposable
{
    private readonly InteractiveService? _interactiveService = null;
    private string _notebookPath;
    private readonly KernelInfoCollection _kernelInfoCollection = new KernelInfoCollection();

    /// <summary>
    /// Create an instance of <see cref="DotnetInteractiveFunction"/>"
    /// </summary>
    /// <param name="interactiveService">interactive service to use.</param>
    /// <param name="notebookPath">notebook path if provided.</param>
    public DotnetInteractiveFunction(InteractiveService interactiveService, string? notebookPath = null, bool continueFromExistingNotebook = false)
    {
        this._interactiveService = interactiveService;
        this._notebookPath = notebookPath ?? Path.GetTempPath() + "notebook.ipynb";
        this._kernelInfoCollection.Add(new KernelInfo("csharp"));
        this._kernelInfoCollection.Add(new KernelInfo("markdown"));
        if (continueFromExistingNotebook == false)
        {
            // remove existing notebook
            if (File.Exists(this._notebookPath))
            {
                File.Delete(this._notebookPath);
            }

            var document = new InteractiveDocument();

            using var stream = File.OpenWrite(_notebookPath);
            Notebook.Write(document, stream, this._kernelInfoCollection);
            stream.Flush();
            stream.Dispose();
        }
        else if (continueFromExistingNotebook == true && File.Exists(this._notebookPath))
        {
            // load existing notebook
            using var readStream = File.OpenRead(this._notebookPath);
            var document = Notebook.Read(readStream, this._kernelInfoCollection);
            foreach (var cell in document.Elements)
            {
                if (cell.KernelName == "csharp")
                {
                    var code = cell.Contents;
                    this._interactiveService.SubmitCSharpCodeAsync(code, default).Wait();
                }
            }
        }
        else
        {
            // create an empty notebook
            var document = new InteractiveDocument();

            using var stream = File.OpenWrite(_notebookPath);
            Notebook.Write(document, stream, this._kernelInfoCollection);
            stream.Flush();
            stream.Dispose();
        }
    }

    /// <summary>
    /// Run existing dotnet code from message. Don't modify the code, run it as is.
    /// </summary>
    /// <param name="code">code.</param>
    [Function]
    public async Task<string> RunCode(string code)
    {
        if (this._interactiveService == null)
        {
            throw new Exception("InteractiveService is not initialized.");
        }

        var result = await this._interactiveService.SubmitCSharpCodeAsync(code, default);
        if (result != null)
        {
            // if result contains Error, return entire message
            if (result.StartsWith("Error:"))
            {
                return result;
            }

            // add cell if _notebookPath is not null
            if (this._notebookPath != null)
            {
                await AddCellAsync(code, "csharp");
            }

            // if result is over 100 characters, only return the first 100 characters.
            if (result.Length > 100)
            {
                result = result.Substring(0, 100) + " (...too long to present)";

                return result;
            }

            return result;
        }

        // add cell if _notebookPath is not null
        if (this._notebookPath != null)
        {
            await AddCellAsync(code, "csharp");
        }

        return "Code run successfully. no output is available.";
    }

    /// <summary>
    /// Install nuget packages.
    /// </summary>
    /// <param name="nugetPackages">nuget package to install.</param>
    [Function]
    public async Task<string> InstallNugetPackages(string[] nugetPackages)
    {
        if (this._interactiveService == null)
        {
            throw new Exception("InteractiveService is not initialized.");
        }

        var codeSB = new StringBuilder();
        foreach (var nuget in nugetPackages ?? Array.Empty<string>())
        {
            var nugetInstallCommand = $"#r \"nuget:{nuget}\"";
            codeSB.AppendLine(nugetInstallCommand);
            await this._interactiveService.SubmitCSharpCodeAsync(nugetInstallCommand, default);
        }

        var code = codeSB.ToString();
        if (this._notebookPath != null)
        {
            await AddCellAsync(code, "csharp");
        }

        var sb = new StringBuilder();
        sb.AppendLine("Installed nuget packages:");
        foreach (var nuget in nugetPackages ?? Array.Empty<string>())
        {
            sb.AppendLine($"- {nuget}");
        }

        return sb.ToString();
    }

    private async Task AddCellAsync(string cellContent, string kernelName)
    {
        if (!File.Exists(this._notebookPath))
        {
            using var stream = File.OpenWrite(this._notebookPath);
            Notebook.Write(new InteractiveDocument(), stream, this._kernelInfoCollection);
            stream.Dispose();
        }

        using var readStream = File.OpenRead(this._notebookPath);
        var document = Notebook.Read(readStream, this._kernelInfoCollection);
        readStream.Dispose();

        var cell = new InteractiveDocumentElement(cellContent, kernelName);

        document.Add(cell);

        using var writeStream = File.OpenWrite(this._notebookPath);
        Notebook.Write(document, writeStream, this._kernelInfoCollection);
        // sleep 3 seconds
        await Task.Delay(3000);
        writeStream.Flush();
        writeStream.Dispose();
    }

    public void Dispose()
    {
        this._interactiveService?.Dispose();
    }
}
