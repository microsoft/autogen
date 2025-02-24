import { describe, it, expect } from '@jest/globals';
import { AgentId } from '../../src/contracts/IAgentRuntime';
import { KVStringParseHelper } from '../../src/utils/KVStringParseHelper';

describe('AgentId', () => {
  it('should initialize correctly', () => {
    const agentId: AgentId = {
      type: "TestType",
      key: "TestKey"
    };

    expect(agentId.type).toBe("TestType");
    expect(agentId.key).toBe("TestKey");
  });

  it('should parse from string correctly', () => {
    const agentIdStr = "ParsedType/ParsedKey";
    const [type, key] = KVStringParseHelper.toKVPair(agentIdStr, "type", "key");
    const agentId: AgentId = { type, key };

    expect(agentId.type).toBe("ParsedType");
    expect(agentId.key).toBe("ParsedKey");
  });

  it('should compare equality correctly', () => {
    const agentId1: AgentId = { type: "SameType", key: "SameKey" };
    const agentId2: AgentId = { type: "SameType", key: "SameKey" };
    const agentId3: AgentId = { type: "DifferentType", key: "DifferentKey" };

    expect(agentId1).toEqual(agentId2);
    expect(agentId1).not.toEqual(agentId3);
  });

  it('should reject invalid names', () => {
    // Invalid type tests
    expect(() => validateAgentId({ type: "123InvalidType", key: "ValidKey" }))
      .toThrow("Agent type cannot start with a number");

    expect(() => validateAgentId({ type: "Invalid Type", key: "ValidKey" }))
      .toThrow("Agent type cannot contain spaces");

    expect(() => validateAgentId({ type: "Invalid@Type", key: "ValidKey" }))
      .toThrow("Agent type cannot contain special characters");

    // Invalid key test
    expect(() => validateAgentId({ type: "ValidType", key: "Invalid💀Key" }))
      .toThrow("Agent key must only contain ASCII characters");

    // Valid case
    expect(() => validateAgentId({ type: "Valid_Type", key: "Valid_Key_123" }))
      .not.toThrow();
  });
});

// Helper function to validate AgentId
function validateAgentId(agentId: AgentId): void {
  const typeRegex = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
  const keyRegex = /^[\x20-\x7E]+$/;

  if (!typeRegex.test(agentId.type)) {
    if (/^\d/.test(agentId.type)) {
      throw new Error("Agent type cannot start with a number");
    } else if (agentId.type.includes(" ")) {
      throw new Error("Agent type cannot contain spaces");
    } else {
      throw new Error("Agent type cannot contain special characters");
    }
  }

  if (!keyRegex.test(agentId.key)) {
    throw new Error("Agent key must only contain ASCII characters between 32 (space) and 126 (~)");
  }
}
