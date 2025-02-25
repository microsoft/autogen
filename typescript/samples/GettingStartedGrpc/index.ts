import { AgentsAppBuilder } from "../../src/core/AgentsApp";
import { GrpcAgentRuntime } from "../../src/core.grpc/GrpcAgentRuntime";
import { createDefaultOptions } from "../../src/core.grpc/GrpcAgentRuntimeClientOptions";
import { Checker } from "./Checker";
import { Modifier } from "./Modifier";

async function main() {
    const builder = new AgentsAppBuilder()
        .useGrpcRuntime(); // Use gRPC runtime instead of InProcessRuntime

    const app = await builder.build();
    
    // Register agents
    const checker = new Checker();
    const modifier = new Modifier();

    // Start the app
    await app.start();
    try {
        // Run same scenario as basic sample but using gRPC
        await checker.startCount();
    } finally {
        await app.shutdown();
    }
}

main().catch(console.error);
