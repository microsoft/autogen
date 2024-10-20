// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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
