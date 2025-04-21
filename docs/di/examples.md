
# Dependency Injection Examples

This document provides concrete examples of how to use the Uno framework's dependency injection system in various scenarios.

## Basic Application Setup

This example shows a complete setup for a small application:

```python
import asyncio
import logging
from uno.core.di import ServiceCollection
from uno.core.di.provider import ServiceProvider

# Define some services
class ConfigService:
    def __init__(self):
        self.settings = {"db_url": "postgres://localhost/mydb", "api_key": "secret"}
        
    def get_value(self, key, default=None):
        return self.settings.get(key, default)
        
class DatabaseService:
    def __init__(self, config: ConfigService):
        self.config = config
        self.connection = None
        self.logger = logging.getLogger("database")
        
    async def initialize(self):
        db_url = self.config.get_value("db_url")
        self.logger.info(f"Connecting to database: {db_url}")
        # In a real app, actually connect to the database
        self.connection = {"url": db_url, "connected": True}
        
    async def dispose(self):
        if self.connection:
            self.logger.info("Closing database connection")
            # In a real app, actually close the connection
            self.connection = None
            
    async def execute_query(self, query):
        return [{"id": 1, "name": "Test User"}]
        
class UserService:
    def __init__(self, db: DatabaseService):
        self.db = db
        
    async def get_user(self, user_id):
        results = await self.db.execute_query(f"SELECT * FROM users WHERE id = {user_id}")
        return results[0] if results else None
        
# Main application class
class Application:
    def __init__(self):
        self.provider = ServiceProvider()
        self.logger = logging.getLogger("app")
        
    async def setup(self):
        # Configure DI
        def configure_services(services):
            services.add_singleton(ConfigService)
            services.add_singleton(DatabaseService)
            services.add_scoped(UserService)
            
        self.provider.configure_services(configure_services)
        
        # Initialize all services
        await self.provider.initialize()
        self.logger.info("Application initialized")
        
    async def run(self):
        try:
            # Create a scope for the operation
            async with self.provider.create_async_scope() as scope:
                user_service = scope.resolve(UserService)
                user = await user_service.get_user(1)
                print(f"Found user: {user}")
        finally:
            # Clean up all services
            await self.provider.dispose()
            self.logger.info("Application shut down")
            
# Run the application
async def main():
    logging.basicConfig(level=logging.INFO)
    app = Application()
    await app.setup()
    await app.run()
    
if __name__ == "__main__":
    asyncio.run(main())
```

## Web Application Example with FastAPI

This example demonstrates how to integrate the DI system with FastAPI:

```python
from fastapi import FastAPI, Request, Depends, HTTPException
from uno.core.di import ServiceCollection, initialize_container, create_async_scope
from pydantic import BaseModel

# Define models
class UserCreate(BaseModel):
    name: str
    email: str
    
class User(BaseModel):
    id: int
    name: str
    email: str
    
# Define services
class UserRepository:
    async def get_by_id(self, user_id: int) -> dict:
        # Simulate database lookup
        if user_id == 1:
            return {"id": 1, "name": "John Doe", "email": "john@example.com"}
        return None
        
    async def create(self, user_data: dict) -> dict:
        # Simulate user creation
        return {"id": 2, **user_data}
        
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
        
    async def get_user(self, user_id: int) -> User:
        data = await self.repo.get_by_id(user_id)
        if not data:
            return None
        return User(**data)
        
    async def create_user(self, user: UserCreate) -> User:
        data = await self.repo.create(user.dict())
        return User(**data)
        
# Set up DI container
services = ServiceCollection()
services.add_singleton(UserRepository)
services.add_scoped(UserService)
container = initialize_container(services)

# Create FastAPI app
app = FastAPI()

# DI middleware to create scopes per request
@app.middleware("http")
async def di_middleware(request: Request, call_next):
    async with create_async_scope() as scope:
        request.state.di_scope = scope
        response = await call_next(request)
        return response
        
# Helper to get services from the request scope
def get_service(service_type):
    async def _get_service(request: Request):
        scope = request.state.di_scope
        return scope.resolve(service_type)
    return Depends(_get_service)
    
# API endpoints
@app.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    user_service: UserService = get_service(UserService)
):
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
    
@app.post("/users/", response_model=User)
async def create_user(
    user: UserCreate,
    user_service: UserService = get_service(UserService)
):
    return await user_service.create_user(user)
    
# Run with: uvicorn app:app
```

## Testing Example

This example shows how to set up tests with mocked dependencies:

```python
import pytest
from uno.core.di import ServiceCollection, initialize_container, get_service

# Service to test
class PaymentProcessor:
    def __init__(self, payment_gateway, notification_service):
        self.payment_gateway = payment_gateway
        self.notification_service = notification_service
        
    async def process_payment(self, user_id, amount):
        success = await self.payment_gateway.charge(user_id, amount)
        if success:
            await self.notification_service.send_notification(
                user_id, f"Payment of ${amount} processed"
            )
        return success
        
# Mock dependencies
class MockPaymentGateway:
    def __init__(self):
        self.charges = []
        
    async def charge(self, user_id, amount):
        self.charges.append({"user_id": user_id, "amount": amount})
        return True
        
class MockNotificationService:
    def __init__(self):
        self.notifications = []
        
    async def send_notification(self, user_id, message):
        self.notifications.append({"user_id": user_id, "message": message})
        
# Tests
@pytest.fixture
def container():
    # Create a test container with mock services
    services = ServiceCollection()
    
    # Create and register mock instances
    mock_gateway = MockPaymentGateway()
    mock_notifications = MockNotificationService()
    
    services.add_instance(MockPaymentGateway, mock_gateway)
    services.add_instance(MockNotificationService, mock_notifications)
    
    # Register the service to test, with dependencies injected
    services.add_singleton(PaymentProcessor)
    
    # Initialize container and return it along with mocks for verification
    initialize_container(services)
    return {
        "gateway": mock_gateway,
        "notifications": mock_notifications
    }
    
@pytest.mark.asyncio
async def test_process_payment(container):
    # Get the service with injected mocks
    processor = get_service(PaymentProcessor)
    
    # Test the service
    result = await processor.process_payment("user123", 99.99)
    
    # Verify the result
    assert result is True
    
    # Verify interactions with mocks
    assert len(container["gateway"].charges) == 1
    assert container["gateway"].charges[0]["user_id"] == "user123"
    assert container["gateway"].charges[0]["amount"] == 99.99
    
    assert len(container["notifications"].notifications) == 1
    assert container["notifications"].notifications[0]["user_id"] == "user123"
    assert "Payment of $99.99 processed" in container["notifications"].notifications[0]["message"]
```

## Advanced Example: Factory Services and Custom Scopes

This example demonstrates more advanced features like factory services and custom-named scopes:

```python
from enum import Enum, auto
from typing import Protocol
from uno.core.di import (
    ServiceCollection, ServiceScope, initialize_container, 
    create_scope, get_service
)
from uno.core.di.provider import ServiceLifecycle

# Define different storage strategies
class StorageType(Enum):
    LOCAL = auto()
    S3 = auto()
    AZURE = auto()

# Storage interface
class StorageProtocol(Protocol):
    def save(self, data: bytes, path: str) -> str: ...
    def load(self, path: str) -> bytes: ...

# Implementations
class LocalStorage:
    def __init__(self, base_path: str = "/tmp"):
        self.base_path = base_path
        
    def save(self, data: bytes, path: str) -> str:
        full_path = f"{self.base_path}/{path}"
        print(f"[LOCAL] Saving {len(data)} bytes to {full_path}")
        return full_path
        
    def load(self, path: str) -> bytes:
        full_path = f"{self.base_path}/{path}"
        print(f"[LOCAL] Loading from {full_path}")
        return b"test data"

class S3Storage:
    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region
        
    def save(self, data: bytes, path: str) -> str:
        s3_path = f"s3://{self.bucket}/{path}"
        print(f"[S3] Saving {len(data)} bytes to {s3_path}")
        return s3_path
        
    def load(self, path: str) -> bytes:
        s3_path = f"s3://{self.bucket}/{path}"
        print(f"[S3] Loading from {s3_path}")
        return b"test data from s3"
        
class AzureStorage:
    def __init__(self, container: str, account: str):
        self.container = container
        self.account = account
        
    def save(self, data: bytes, path: str) -> str:
        azure_path = f"azure://{self.account}/{self.container}/{path}"
        print(f"[AZURE] Saving {len(data)} bytes to {azure_path}")
        return azure_path
        
    def load(self, path: str) -> bytes:
        azure_path = f"azure://{self.account}/{self.container}/{path}"
        print(f"[AZURE] Loading from {azure_path}")
        return b"test data from azure"

# Factory class to create appropriate storage
class StorageFactory(ServiceLifecycle):
    def __init__(self, config: dict):
        self.config = config
        self.instances = {}
        
    async def initialize(self) -> None:
        # Pre-initialize some common storage providers
        print("Initializing storage factory...")
        
    async def dispose(self) -> None:
        # Clean up any resources
        print("Disposing storage factory...")
        
    def get_storage(self, storage_type: StorageType) -> StorageProtocol:
        """Get or create a storage instance of the requested type"""
        if storage_type in self.instances:
            return self.instances[storage_type]
            
        if storage_type == StorageType.LOCAL:
            storage = LocalStorage(self.config.get("local_path", "/tmp"))
        elif storage_type == StorageType.S3:
            storage = S3Storage(
                self.config.get("s3_bucket", "default-bucket"),
                self.config.get("s3_region", "us-east-1")
            )
        elif storage_type == StorageType.AZURE:
            storage = AzureStorage(
                self.config.get("azure_container", "default-container"),
                self.config.get("azure_account", "myaccount")
            )
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
            
        self.instances[storage_type] = storage
        return storage

# File processor that uses storage
class FileProcessor:
    def __init__(self, storage_factory: StorageFactory):
        self.storage_factory = storage_factory
        
    def process_file(self, data: bytes, path: str, storage_type: StorageType = StorageType.LOCAL) -> str:
        # Get appropriate storage
        storage = self.storage_factory.get_storage(storage_type)
        
        # Process the data (just an example)
        processed_data = data.upper()
        
        # Save the processed data
        return storage.save(processed_data, path)

# Set up the container
def setup_container():
    services = ServiceCollection()
    
    # Register the config with an instance
    config = {
        "local_path": "/app/data",
        "s3_bucket": "my-app-bucket",
        "s3_region": "eu-west-1",
        "azure_container": "files",
        "azure_account": "myapp"
    }
    services.add_instance(dict, config)
    
    # Register the factory as a singleton
    services.add_singleton(StorageFactory)
    
    # Register file processor as transient - new one each time
    services.add_transient(FileProcessor)
    
    return initialize_container(services)

# Usage example
def main():
    # Set up the container
    setup_container()
    
    # Create different named scopes for different operations
    with create_scope("upload-operation") as upload_scope:
        processor1 = upload_scope.resolve(FileProcessor)
        result1 = processor1.process_file(b"hello world", "file1.txt", StorageType.LOCAL)
        
        # Same scope = same storage factory instance
        processor2 = upload_scope.resolve(FileProcessor)
        result2 = processor2.process_file(b"test data", "file2.txt", StorageType.S3)
        
    # Different scope = different processor instance but same factory
    with create_scope("download-operation") as download_scope:
        processor3 = download_scope.resolve(FileProcessor)
        
        # Get a storage instance and use it directly
        storage_factory = download_scope.resolve(StorageFactory)
        s3_storage = storage_factory.get_storage(StorageType.S3)
        
        data = s3_storage.load("file2.txt")
        print(f"Downloaded data: {data}")
        
if __name__ == "__main__":
    main()
```

## Domain-Driven Design Example

This example demonstrates using the DI system with a domain-driven design approach:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Protocol
from uuid import UUID, uuid4

from uno.core.di import ServiceCollection, initialize_container, get_service
from uno.core.di.provider import ServiceLifecycle

# Domain entities and value objects
@dataclass
class OrderItem:
    product_id: UUID
    name: str
    price: float
    quantity: int
    
    @property
    def total_price(self) -> float:
        return self.price * self.quantity

@dataclass
class Order:
    id: UUID
    customer_id: UUID
    items: List[OrderItem]
    created_at: datetime
    status: str = "pending"
    
    @property
    def total(self) -> float:
        return sum(item.total_price for item in self.items)
    
    def add_item(self, item: OrderItem) -> None:
        self.items.append(item)
        
    def mark_as_paid(self) -> None:
        self.status = "paid"
        
    def mark_as_shipped(self) -> None:
        self.status = "shipped"

# Repository interfaces
class OrderRepositoryProtocol(Protocol):
    async def get_by_id(self, order_id: UUID) -> Order: ...
    async def save(self, order: Order) -> None: ...
    async def list_by_customer(self, customer_id: UUID) -> List[Order]: ...

# Implementation
class InMemoryOrderRepository:
    def __init__(self):
        self.orders = {}
        
    async def get_by_id(self, order_id: UUID) -> Order:
        return self.orders.get(order_id)
        
    async def save(self, order: Order) -> None:
        self.orders[order.id] = order
        
    async def list_by_customer(self, customer_id: UUID) -> List[Order]:
        return [order for order in self.orders.values() 
                if order.customer_id == customer_id]

# Domain services
class PricingService:
    def calculate_discount(self, order: Order) -> float:
        # Example logic - 10% discount for orders over $100
        if order.total > 100:
            return order.total * 0.1
        return 0

class PaymentServiceProtocol(Protocol):
    async def process_payment(self, order_id: UUID, amount: float) -> bool: ...

class StripePaymentService(ServiceLifecycle):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        
    async def initialize(self) -> None:
        # In a real app, initialize the Stripe client
        print(f"Initializing Stripe client with API key: {self.api_key}")
        self.client = {"initialized": True}
        
    async def dispose(self) -> None:
        # Clean up resources
        print("Disposing Stripe client")
        self.client = None
        
    async def process_payment(self, order_id: UUID, amount: float) -> bool:
        # Simulate payment processing
        print(f"Processing payment of ${amount} for order {order_id}")
        return True

# Application services
class OrderService:
    def __init__(
        self, 
        order_repository: OrderRepositoryProtocol,
        pricing_service: PricingService,
        payment_service: PaymentServiceProtocol
    ):
        self.repository = order_repository
        self.pricing_service = pricing_service
        self.payment_service = payment_service
        
    async def create_order(
        self, 
        customer_id: UUID, 
        items: List[OrderItem]
    ) -> Order:
        order = Order(
            id=uuid4(),
            customer_id=customer_id,
            items=items,
            created_at=datetime.now()
        )
        await self.repository.save(order)
        return order
        
    async def add_item_to_order(
        self, 
        order_id: UUID, 
        item: OrderItem
    ) -> Order:
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
            
        order.add_item(item)
        await self.repository.save(order)
        return order
        
    async def checkout_order(self, order_id: UUID) -> bool:
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
            
        if order.status != "pending":
            raise ValueError(f"Order {order_id} is already processed")
            
        # Calculate final amount with discounts
        discount = self.pricing_service.calculate_discount(order)
        final_amount = order.total - discount
        
        # Process payment
        payment_success = await self.payment_service.process_payment(
            order.id, final_amount
        )
        
        if payment_success:
            order.mark_as_paid()
            await self.repository.save(order)
            
        return payment_success

# Set up dependency injection
def setup_container():
    services = ServiceCollection()
    
    # Register repositories
    services.add_singleton(OrderRepositoryProtocol, InMemoryOrderRepository)
    
    # Register domain services
    services.add_singleton(PricingService)
    services.add_singleton(
        PaymentServiceProtocol, 
        StripePaymentService, 
        api_key="sk_test_example"
    )
    
    # Register application services
    services.add_scoped(OrderService)
    
    return initialize_container(services)

# Usage example
async def main():
    # Set up DI
    setup_container()
    
    # Create a customer ID
    customer_id = uuid4()
    
    # Create some order items
    items = [
        OrderItem(
            product_id=uuid4(),
            name="Widget A",
            price=29.99,
            quantity=2
        ),
        OrderItem(
            product_id=uuid4(),
            name="Gadget B",
            price=49.99,
            quantity=1
        )
    ]
    
    # Use the order service
    order_service = get_service(OrderService)
    
    # Create a new order
    order = await order_service.create_order(customer_id, items)
    print(f"Created order: {order.id} with total: ${order.total}")
    
    # Add another item
    new_item = OrderItem(
        product_id=uuid4(),
        name="Doohickey C",
        price=19.99,
        quantity=3
    )
    
    order = await order_service.add_item_to_order(order.id, new_item)
    print(f"Updated order total: ${order.total}")
    
    # Process checkout
    success = await order_service.checkout_order(order.id)
    print(f"Checkout {'successful' if success else 'failed'}")
    
    # Verify order status
    repository = get_service(OrderRepositoryProtocol)
    updated_order = await repository.get_by_id(order.id)
    print(f"Order status: {updated_order.status}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Service Discovery and Plugin Architecture Example

This example demonstrates using the DI system to implement a plugin architecture:

```python
import importlib
import inspect
import pkgutil
from typing import Dict, List, Protocol, Type

from uno.core.di import ServiceCollection, ServiceScope, initialize_container, get_service

# Plugin interface
class PluginProtocol(Protocol):
    @property
    def name(self) -> str: ...
    
    def initialize(self) -> None: ...
    def execute(self, *args, **kwargs) -> Dict: ...

# Plugin manager
class PluginManager:
    def __init__(self):
        self.plugins: Dict[str, Type[PluginProtocol]] = {}
        
    def register_plugin(self, plugin_class: Type[PluginProtocol]) -> None:
        """Register a plugin by its class"""
        # Create a temporary instance to get the name
        temp_instance = plugin_class()
        self.plugins[temp_instance.name] = plugin_class
        print(f"Registered plugin: {temp_instance.name}")
        
    def discover_plugins(self, package_name: str) -> None:
        """Discover plugins in a package"""
        package = importlib.import_module(package_name)
        
        for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
            if not is_pkg:
                module = importlib.import_module(name)
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if this class implements the plugin protocol
                    if hasattr(obj, 'name') and callable(getattr(obj, 'execute', None)):
                        self.register_plugin(obj)
                        
    def get_plugin_classes(self) -> Dict[str, Type[PluginProtocol]]:
        """Get all registered plugin classes"""
        return self.plugins

# Plugin factory
class PluginFactory:
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self.instances: Dict[str, PluginProtocol] = {}
        
    def get_plugin(self, name: str) -> PluginProtocol:
        """Get or create a plugin instance by name"""
        if name in self.instances:
            return self.instances[name]
            
        plugin_classes = self.plugin_manager.get_plugin_classes()
        if name not in plugin_classes:
            raise ValueError(f"Plugin '{name}' not found")
            
        plugin = plugin_classes[name]()
        plugin.initialize()
        self.instances[name] = plugin
        return plugin
        
    def get_all_plugins(self) -> List[PluginProtocol]:
        """Get instances of all registered plugins"""
        result = []
        for name in self.plugin_manager.get_plugin_classes().keys():
            result.append(self.get_plugin(name))
        return result

# Sample plugins
class TextProcessorPlugin:
    @property
    def name(self) -> str:
        return "text_processor"
        
    def initialize(self) -> None:
        print("Initializing text processor plugin")
        
    def execute(self, text: str) -> Dict:
        word_count = len(text.split())
        char_count = len(text)
        return {
            "word_count": word_count,
            "char_count": char_count
        }

class SentimentAnalyzerPlugin:
    @property
    def name(self) -> str:
        return "sentiment_analyzer"
        
    def initialize(self) -> None:
        print("Initializing sentiment analyzer plugin")
        
    def execute(self, text: str) -> Dict:
        # Very simple "analyzer" for demonstration
        positive_words = ["good", "great", "excellent", "happy", "love"]
        negative_words = ["bad", "terrible", "awful", "sad", "hate"]
        
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        return {
            "sentiment": sentiment,
            "positive_score": positive_count,
            "negative_score": negative_count
        }

# Application using plugins
class TextAnalysisService:
    def __init__(self, plugin_factory: PluginFactory):
        self.plugin_factory = plugin_factory
        
    def analyze_text(self, text: str) -> Dict:
        """Analyze text using all available plugins"""
        results = {}
        
        # Get all plugins and execute them
        plugins = self.plugin_factory.get_all_plugins()
        for plugin in plugins:
            results[plugin.name] = plugin.execute(text)
            
        return results
        
    def analyze_with_plugin(self, text: str, plugin_name: str) -> Dict:
        """Analyze text with a specific plugin"""
        plugin = self.plugin_factory.get_plugin(plugin_name)
        return plugin.execute(text)

# Set up DI
def setup_container():
    services = ServiceCollection()
    
    # Register the plugin manager and discovery
    services.add_singleton(PluginManager)
    
    # Register plugin factory
    services.add_singleton(PluginFactory)
    
    # Register the application service
    services.add_scoped(TextAnalysisService)
    
    container = initialize_container(services)
    
    # Discover and register plugins
    plugin_manager = get_service(PluginManager)
    
    # Manually register plugins (in a real app, these might be discovered from packages)
    plugin_manager.register_plugin(TextProcessorPlugin)
    plugin_manager.register_plugin(SentimentAnalyzerPlugin)
    
    return container

# Usage example
def main():
    # Set up DI
    setup_container()
    
    # Get the text analysis service
    analysis_service = get_service(TextAnalysisService)
    
    # Sample text
    text = "I love this great product! It works really well and makes me happy."
    
    # Analyze with all plugins
    results = analysis_service.analyze_text(text)
    
    # Print results
    print("\nAnalysis Results:")
    print("================")
    for plugin_name, result in results.items():
        print(f"\n{plugin_name}:")
        for key, value in result.items():
            print(f"  {key}: {value}")
            
    # Analyze with specific plugin
    sentiment_result = analysis_service.analyze_with_plugin(text, "sentiment_analyzer")
    print("\nSentiment only:")
    print(f"Sentiment: {sentiment_result['sentiment']}")

if __name__ == "__main__":
    main()
```

## Dependency Resolution Visualization Example

This example shows how to visualize the dependency graph in your DI container:

```python
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Set, Type

from uno.core.di import ServiceCollection, initialize_container, get_service
from uno.core.di.scoped_container import ServiceResolver

# Sample services with dependencies
class ConfigService:
    def __init__(self):
        self.settings = {"app_name": "DI Demo", "debug": True}
        
class LoggerService:
    def __init__(self, config: ConfigService):
        self.config = config
        self.debug = config.settings.get("debug", False)
        
class DatabaseService:
    def __init__(self, config: ConfigService, logger: LoggerService):
        self.config = config
        self.logger = logger
        
class UserRepository:
    def __init__(self, db: DatabaseService):
        self.db = db
        
class AuthService:
    def __init__(self, user_repo: UserRepository, logger: LoggerService):
        self.user_repo = user_repo
        self.logger = logger
        
class UserService:
    def __init__(self, user_repo: UserRepository, auth: AuthService):
        self.user_repo = user_repo
        self.auth = auth

# DI visualization service
class DIVisualizer:
    def __init__(self, container: ServiceResolver):
        self.container = container
        
    def get_dependencies(self, service_type: Type) -> List[Type]:
        """Extract constructor dependencies for a service type"""
        try:
            import inspect
            
            # Handle factory functions
            registration = self.container._registrations.get(service_type)
            if not registration:
                return []
                
            impl = registration.implementation
            if not inspect.isclass(impl):
                return []  # Can't inspect factory functions easily
                
            # Get constructor signature
            sig = inspect.signature(impl.__init__)
            
            # Extract parameter types, excluding self
            dependencies = []
            for param_name, param in