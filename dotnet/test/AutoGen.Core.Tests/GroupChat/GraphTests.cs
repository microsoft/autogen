
namespace AutoGen.Core.Tests
{
    [TestClass()]
    public class GraphTests
    {
        [TestMethod()]
        public void GraphTest()
        {
            var graph1 = new Graph();
            Assert.IsNotNull(graph1);

            var graph2 = new Graph(null);
            Assert.IsNotNull(graph2);
        }
    }
}
