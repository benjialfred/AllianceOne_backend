class KernelException(Exception):
    """
    Base exception for all Kernel-level errors in Alliance OS.
    Ensures that any infrastructural error can be caught uniformly.
    """
    def __init__(self, message: str, code: str = "KERNEL_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

class ConfigurationError(KernelException):
    """Raised when an environment or config variable is missing or invalid."""
    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR")

class DependencyInjectionError(KernelException):
    """Raised when a dependency cannot be resolved or registered."""
    def __init__(self, message: str):
        super().__init__(message, code="DI_ERROR")

class PluginLoadError(KernelException):
    """Raised when a plugin/module fails to load."""
    def __init__(self, message: str):
        super().__init__(message, code="PLUGIN_ERROR")

class TaskDispatchError(KernelException):
    """Raised when a background task fails to be dispatched or scheduled."""
    def __init__(self, message: str):
        super().__init__(message, code="TASK_DISPATCH_ERROR")

class SecurityError(KernelException):
    """Raised for cryptographic or security validation failures."""
    def __init__(self, message: str):
        super().__init__(message, code="SECURITY_ERROR")
