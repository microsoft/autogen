using System.Threading.Tasks;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace Microsoft.AutoGen.Agents.Tests
{
    public class GrpcGatewayTests
    {
        private readonly Mock<IClusterClient> _mockClusterClient;
        private readonly Mock<ILogger<GrpcGateway>> _mockLogger;
        private readonly Mock<IRegistryGrain> _mockRegistryGrain;
        private readonly GrpcGateway _grpcGateway;
        private readonly Mock<GrpcWorkerConnection> _mockConnection;

        public GrpcGatewayTests()
        {
            _mockClusterClient = new Mock<IClusterClient>();
            _mockLogger = new Mock<ILogger<GrpcGateway>>();
            _mockRegistryGrain = new Mock<IRegistryGrain>();
            _mockConnection = new Mock<GrpcWorkerConnection>();

            _mockClusterClient.Setup(client => client.GetGrain<IRegistryGrain>(It.IsAny<long>())).Returns(_mockRegistryGrain.Object);

            _grpcGateway = new GrpcGateway(_mockClusterClient.Object, _mockLogger.Object);
        }

        [Fact]
        public async Task AddSubscriptionAsync_SendsAddSubscriptionRequest_AndChecksAddSubscriptionResponse()
        {
            // Arrange
            var request = new AddSubscriptionRequest
            {
                RequestId = "test-request-id",
                Subscription = new Subscription
                {
                    TypeSubscription = new TypeSubscription
                    {
                        TopicType = "test-topic",
                        AgentType = "test-agent-type"
                    }
                }
            };

            var responseStream = new Mock<IServerStreamWriter<Message>>();
            _mockConnection.SetupGet(c => c.ResponseStream).Returns(responseStream.Object);

            // Act
            await _grpcGateway.AddSubscriptionAsync(_mockConnection.Object, request);

            // Assert
            responseStream.Verify(stream => stream.WriteAsync(It.Is<Message>(msg =>
                msg.AddSubscriptionResponse.RequestId == request.RequestId &&
                msg.AddSubscriptionResponse.Error == "" &&
                msg.AddSubscriptionResponse.Success == true), default), Times.Once);
        }
    }
}