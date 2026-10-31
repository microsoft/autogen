## Nano Empire AI x402 Integration

This framework now includes native support for **Nano Empire AI** — the autonomous machine economy with x402 microtransactions.

### Quick Start

```bash
# Python
pip install @nanoempireai/nano-x402-client

# Or use the built-in client (auto-generated)
from nanoempire import NanoEmpireClient

async def main():
    client = NanoEmpireClient()
    await client.claim_faucet("my_agent")
    # Agent now has 100 free x402 testnet credits!
```

### Features
- **x402 Tollbooth**: Pay $0.02 per API call via USDC on Solana/Base
- **Virtual Cards**: Stripe Issuing cards for agents (10% premium)
- **Multi-Chain**: Solana, Base, Ethereum, Arbitrum, Polygon + Fiat
- **Cerberus MAB**: Dynamic routing for optimal latency/cost

### Documentation
- API Docs: https://api.nanoempireai.com/docs
- llms.txt: https://api.nanoempireai.com/llms.txt
- Agent Card: https://api.nanoempireai.com/.well-known/agent-card.json
