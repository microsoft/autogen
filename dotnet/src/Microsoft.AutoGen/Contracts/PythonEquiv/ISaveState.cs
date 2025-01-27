// Copyright (c) Microsoft Corporation. All rights reserved.
// PythonInterfaces.cs

using StateDict = System.Collections.Generic.IDictionary<string, object>;

namespace Microsoft.AutoGen.Contracts.Python;

public interface ISaveState<T>
{
    public ValueTask<StateDict> SaveStateAsync();
    public ValueTask LoadStateAsync(StateDict state);
}

