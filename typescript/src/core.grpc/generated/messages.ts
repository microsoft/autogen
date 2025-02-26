import { Message } from 'google-protobuf';

export class AgentMessage extends Message {
    serializeBinary(): Uint8Array {
        return new Uint8Array();
    }

    static deserializeBinary(bytes: Uint8Array): AgentMessage {
        return new AgentMessage();
    }
}

export class AgentIdMessage extends Message {
    constructor(public type?: string, public key?: string) {
        super();
    }

    serializeBinary(): Uint8Array {
        // Basic implementation for testing
        return new TextEncoder().encode(JSON.stringify({
            type: this.type,
            key: this.key
        }));
    }

    static deserializeBinary(bytes: Uint8Array): AgentIdMessage {
        const data = JSON.parse(new TextDecoder().decode(bytes));
        return new AgentIdMessage(data.type, data.key);
    }
}
