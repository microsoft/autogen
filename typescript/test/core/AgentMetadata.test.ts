import { describe, it, expect } from '@jest/globals';
import { AgentMetadata } from '../../src/contracts/AgentMetadata';

describe('AgentMetadata', () => {
  it('should initialize correctly', () => {
    const metadata: AgentMetadata = {
      type: "TestType",
      key: "TestKey",
      description: "TestDescription"
    };

    expect(metadata.type).toBe("TestType");
    expect(metadata.key).toBe("TestKey");
    expect(metadata.description).toBe("TestDescription");
  });
});
