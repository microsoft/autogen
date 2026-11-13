"""DNS-AID tool classes for AutoGen."""

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from dns_aid.integrations import DiscoverInput, PublishInput, UnpublishInput


class DnsAidDiscoverTool(BaseTool[DiscoverInput, str]):
    """Discover AI agents at a domain via DNS-AID SVCB records."""

    def __init__(self, backend_name: str | None = None, backend=None):
        super().__init__(
            args_type=DiscoverInput,
            return_type=str,
            name="dns_aid_discover",
            description="Discover AI agents at a domain via DNS-AID SVCB records.",
        )
        self._backend_name = backend_name
        self._backend = backend

    async def run(self, args: DiscoverInput, cancellation_token: CancellationToken) -> str:
        from dns_aid.integrations import DnsAidOperations

        ops = DnsAidOperations(
            backend_name=self._backend_name, backend=self._backend
        )
        return await ops.discover_async(
            domain=args.domain,
            protocol=args.protocol,
            name=args.name,
            require_dnssec=args.require_dnssec,
        )


class DnsAidPublishTool(BaseTool[PublishInput, str]):
    """Publish an AI agent to DNS via DNS-AID SVCB records."""

    def __init__(self, backend_name: str | None = None, backend=None):
        super().__init__(
            args_type=PublishInput,
            return_type=str,
            name="dns_aid_publish",
            description="Publish an AI agent to DNS via DNS-AID SVCB records.",
        )
        self._backend_name = backend_name
        self._backend = backend

    async def run(self, args: PublishInput, cancellation_token: CancellationToken) -> str:
        from dns_aid.integrations import DnsAidOperations

        ops = DnsAidOperations(
            backend_name=self._backend_name, backend=self._backend
        )
        return await ops.publish_async(
            name=args.name,
            domain=args.domain,
            protocol=args.protocol,
            endpoint=args.endpoint,
            port=args.port,
            capabilities=args.capabilities,
            version=args.version,
            description=args.description,
            ttl=args.ttl,
        )


class DnsAidUnpublishTool(BaseTool[UnpublishInput, str]):
    """Remove an AI agent from DNS via DNS-AID SVCB records."""

    def __init__(self, backend_name: str | None = None, backend=None):
        super().__init__(
            args_type=UnpublishInput,
            return_type=str,
            name="dns_aid_unpublish",
            description="Remove an AI agent from DNS via DNS-AID SVCB records.",
        )
        self._backend_name = backend_name
        self._backend = backend

    async def run(self, args: UnpublishInput, cancellation_token: CancellationToken) -> str:
        from dns_aid.integrations import DnsAidOperations

        ops = DnsAidOperations(
            backend_name=self._backend_name, backend=self._backend
        )
        return await ops.unpublish_async(
            name=args.name,
            domain=args.domain,
            protocol=args.protocol,
        )
