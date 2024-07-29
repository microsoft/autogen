from autogencap.actor_runtime import IRuntime
from autogencap.constants import ZMQ_Runtime
from autogencap.DebugLog import Error
from autogencap.zmq_runtime import ZMQRuntime


class RuntimeFactory:
    _supported_runtimes = {}

    """
    Factory class for creating a runtime instance.
    """

    @staticmethod
    def get_runtime(runtime_type: str = ZMQ_Runtime) -> IRuntime:
        """
        Creates a runtime instance based on the runtime type.

        :param runtime_type: The type of runtime to create.
        :return: The runtime instance.
        """
        if runtime_type in RuntimeFactory._supported_runtimes:
            return RuntimeFactory._supported_runtimes[runtime_type]
        else:
            not_found = f"Runtime type not found: {runtime_type}"
            Error("RuntimeFactory", not_found)
            raise ValueError(not_found)

    @staticmethod
    def register_runtime(runtime_type: str, runtime: IRuntime):
        """
        Registers a runtime instance.

        :param runtime: The runtime instance.
        """
        RuntimeFactory._supported_runtimes[runtime_type] = runtime

    @classmethod
    def _initialize(cls):
        """
        Static initialization method.
        """
        cls.register_runtime(ZMQ_Runtime, ZMQRuntime())


# Static initialization
RuntimeFactory._initialize()
