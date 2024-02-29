// Copyright (c) Microsoft Corporation. All rights reserved.
// RegisterReplyAgentTest.cs

using System.Threading.Tasks;
using FluentAssertions;
using Xunit;

namespace AutoGen.Tests
{
    public class RegisterReplyAgentTest
    {
        [Fact]
        public async Task RegisterReplyTestAsync()
        {
            IAgent echoAgent = new EchoAgent("echo");
            echoAgent = echoAgent
                .RegisterReply(async (conversations, ct) => new TextMessage(Role.Assistant, "I'm your father", from: echoAgent.Name));

            var msg = new Message(Role.User, "hey");
            var reply = await echoAgent.SendAsync(msg);
            reply.Should().BeOfType<TextMessage>();
            reply.GetContent().Should().Be("I'm your father");
            reply.GetRole().Should().Be(Role.Assistant);
            reply.From.Should().Be("echo");
        }
    }
}
