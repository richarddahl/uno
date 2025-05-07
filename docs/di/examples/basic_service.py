"""
Basic service example for the Uno DI system.

This example demonstrates:
1. Service interface definition
2. Service implementation
3. Service registration
4. Service resolution
5. Basic dependency injection
"""

from typing import Protocol, List
from dataclasses import dataclass
from uno.infrastructure.di.decorators import service, singleton
from uno.infrastructure.di.service_scope import ServiceScope
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.infrastructure.di.errors import ServiceConfigurationError

# Define interfaces
class IMessageService(Protocol):
    """Interface for message services."""
    async def send_message(self, message: str) -> None:
        """Send a message."""
        ...

class IEmailService(Protocol):
    """Interface for email services."""
    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Send an email."""
        ...

# Define service options
@dataclass
class EmailOptions:
    """Options for email service."""
    smtp_server: str
    port: int
    use_ssl: bool = True
    timeout: int = 30

    def validate(self) -> None:
        """Validate email options."""
        if not self.smtp_server:
            raise ServiceConfigurationError("SMTP server is required")
        if self.port < 1 or self.port > 65535:
            raise ServiceConfigurationError("Invalid port number")

# Implement services
@service(interface=IMessageService, scope=ServiceScope.SINGLETON)
class MessageService:
    """Message service implementation."""
    def __init__(self, email_service: IEmailService):
        self.email_service = email_service

    async def send_message(self, message: str) -> None:
        """Send a message via email."""
        await self.email_service.send_email(
            to="user@example.com",
            subject="New Message",
            body=message
        )

@service(
    interface=IEmailService,
    scope=ServiceScope.SINGLETON,
    options_type=EmailOptions
)
class EmailService:
    """Email service implementation."""
    def __init__(self, options: EmailOptions):
        self.options = options

    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Send an email."""
        print(f"Sending email to {to}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        print(f"Using SMTP server: {self.options.smtp_server}:{self.options.port}")

# Or use convenience decorators
@singleton(interface=IMessageService)
class AnotherMessageService:
    """Another message service implementation."""
    def __init__(self, email_service: IEmailService):
        self.email_service = email_service

    async def send_message(self, message: str) -> None:
        """Send a message via email."""
        await self.email_service.send_email(
            to="user@example.com",
            subject="New Message",
            body=message
        )

def main() -> None:
    """Run the example."""
    # Create service collection
    services = ServiceCollection()

    # Register services
    services.add_singleton(IEmailService, EmailService)
    services.add_singleton(IMessageService, MessageService)

    # Configure services
    services.configure[EmailOptions](lambda options: {
        "smtp_server": "smtp.example.com",
        "port": 587,
        "use_ssl": True,
        "timeout": 30
    })

    # Create service provider
    provider = ServiceProvider(services)

    # Resolve services
    message_service = provider.get_service(IMessageService)
    email_service = provider.get_service(IEmailService)

    # Use services
    import asyncio
    asyncio.run(message_service.send_message("Hello, World!"))

if __name__ == "__main__":
    main() 