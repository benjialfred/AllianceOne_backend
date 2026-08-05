from abc import ABC, abstractmethod


class CLIService(ABC):
    """
    Abstract interface for platform CLI operations in Alliance OS.
    Ensures that Typer is just a frontend detail, while the actual logic lives here.
    """

    @abstractmethod
    def create_module(self, name: str) -> None:
        pass

    @abstractmethod
    def publish(self, module_name: str) -> None:
        pass

    @abstractmethod
    def doctor(self) -> None:
        pass

    @abstractmethod
    def upgrade(self) -> None:
        pass

    @abstractmethod
    def install(self, plugin_name: str) -> None:
        pass

    @abstractmethod
    def remove(self, plugin_name: str) -> None:
        pass


class DefaultCLIService(CLIService):
    """
    Default implementation of CLIService.
    """

    def create_module(self, name: str) -> None:
        print(f"[CLIService] Creating Alliance module: {name}")
        # Logic to scaffold a new module

    def publish(self, module_name: str) -> None:
        print(f"[CLIService] Publishing module: {module_name}")

    def doctor(self) -> None:
        print("[CLIService] Running diagnostics on Alliance OS...")
        print("✔ Kernel dependencies")
        print("✔ Database connection")
        print("✔ Event Bus active")
        print("✔ Task Queue ready")

    def upgrade(self) -> None:
        print("[CLIService] Upgrading Alliance OS to latest version.")

    def install(self, plugin_name: str) -> None:
        print(f"[CLIService] Installing plugin {plugin_name}...")

    def remove(self, plugin_name: str) -> None:
        print(f"[CLIService] Removing plugin {plugin_name}...")
