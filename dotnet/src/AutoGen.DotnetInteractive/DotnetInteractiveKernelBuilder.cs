// Copyright (c) Microsoft Corporation. All rights reserved.
// DotnetInteractiveKernelBuilder.cs

namespace AutoGen.DotnetInteractive;

public static class DotnetInteractiveKernelBuilder
{

#if NET8_0_OR_GREATER
    public static InProccessDotnetInteractiveKernelBuilder CreateEmptyInProcessKernelBuilder()
    {
        return new InProccessDotnetInteractiveKernelBuilder();
    }

    public static InProccessDotnetInteractiveKernelBuilder CreateDefaultInProcessKernelBuilder()
    {
        return new InProccessDotnetInteractiveKernelBuilder()
            .AddCSharpKernel()
            .AddFSharpKernel();
    }
#endif

    public static DotnetInteractiveStdioKernelConnector CreateKernelBuilder(string workingDirectory, string kernelName = "root-proxy")
    {
        return new DotnetInteractiveStdioKernelConnector(workingDirectory, kernelName);
    }
}
