#pragma warning disable IDE0073
// Copyright 2019 The gRPC Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using System.Threading.Channels;
using Grpc.Core;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests.Helpers.Grpc;

public class TestAsyncStreamReader<T> : IDisposable, IAsyncStreamReader<T>
                                           where T : class
{
    private readonly Channel<T> _channel;
    private readonly ServerCallContext _serverCallContext;

    public T Current { get; private set; } = null!;

    public TestAsyncStreamReader(ServerCallContext serverCallContext)
    {
        _channel = Channel.CreateUnbounded<T>();
        _serverCallContext = serverCallContext;
    }

    public void AddMessage(T message)
    {
        if (!_channel.Writer.TryWrite(message))
        {
            throw new InvalidOperationException("Unable to write message.");
        }
    }

    public void Complete()
    {
        _channel.Writer.Complete();
    }

    public async Task<bool> MoveNext(CancellationToken cancellationToken)
    {
        _serverCallContext.CancellationToken.ThrowIfCancellationRequested();

        if (await _channel.Reader.WaitToReadAsync(cancellationToken) &&
            _channel.Reader.TryRead(out var message))
        {
            Current = message;
            return true;
        }
        else
        {
            Current = null!;
            return false;
        }
    }

    public void Dispose()
    {
        Complete();
    }
}
