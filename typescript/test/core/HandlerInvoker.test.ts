import { describe, it, expect } from '@jest/globals';
import { HandlerInvoker } from '../../src/core/HandlerInvoker';
import { MessageContext } from '../../src/contracts/MessageContext';

class HandlerInvokerTest {
  public publishlikeInvocations: Array<[string, MessageContext]> = [];
  public sendlikeInvocations: Array<[string, MessageContext]> = [];

  async publishlikeAsync(message: string, messageContext: MessageContext): Promise<void> {
    this.publishlikeInvocations.push([message, messageContext]);
  }

  async sendlikeAsync(message: string, messageContext: MessageContext): Promise<number> {
    this.sendlikeInvocations.push([message, messageContext]);
    return this.sendlikeInvocations.length;
  }
}

describe('HandlerInvoker', () => {
  it('should successfully invoke publishlike method', async () => {
    const messageContext = new MessageContext(crypto.randomUUID());
    const testInstance = new HandlerInvokerTest();
    
    const handler = {
      handleAsync: testInstance.publishlikeAsync.bind(testInstance)
    };
    
    const invoker = new HandlerInvoker(handler);
    const result = await invoker.invoke("Hello, world!", messageContext);

    expect(testInstance.publishlikeInvocations).toHaveLength(1);
    expect(testInstance.publishlikeInvocations[0][0]).toBe("Hello, world!");
    expect(result).toBeUndefined();
  });

  it('should successfully invoke sendlike method', async () => {
    const messageContext = new MessageContext(crypto.randomUUID());
    const testInstance = new HandlerInvokerTest();
    
    const handler = {
      handleAsync: testInstance.sendlikeAsync.bind(testInstance)
    };
    
    const invoker = new HandlerInvoker(handler);
    const result = await invoker.invoke("Hello, world!", messageContext);

    expect(testInstance.sendlikeInvocations).toHaveLength(1);
    expect(testInstance.sendlikeInvocations[0][0]).toBe("Hello, world!");
    expect(result).toBe(1);
  });
});
