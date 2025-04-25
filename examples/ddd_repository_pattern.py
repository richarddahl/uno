import datetime
from typing import TypeVar

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from uno.core.di.interfaces import DomainRepositoryProtocol, RepositoryProtocol

# SQLAlchemy Base
Base = declarative_base()

# Type variables
EntityT = TypeVar("EntityT")
ModelT = TypeVar("ModelT")


# Domain Entity
class OrderEntity:
    def __init__(self, order_id: str, customer_id: str, total_amount: float):
        self.order_id = order_id
        self.customer_id = customer_id
        self.total_amount = total_amount
        self.status = "PENDING"
        self.created_at = datetime.datetime.now(datetime.UTC)
        self._events = []

    def approve(self):
        """Domain method to approve an order"""
        if self.status != "PENDING":
            raise ValueError("Order must be in PENDING state to approve")
        self.status = "APPROVED"
        self._events.append(OrderApproved(self.order_id))

    def cancel(self, reason: str):
        """Domain method to cancel an order"""
        if self.status == "CANCELLED":
            raise ValueError("Order is already cancelled")
        self.status = "CANCELLED"
        self.cancellation_reason = reason
        self._events.append(OrderCancelled(self.order_id, reason))

    def get_events(self) -> list["DomainEvent"]:
        return self._events


class DomainEvent:
    def __init__(self, order_id: str):
        self.order_id = order_id
        self.occurred_at = datetime.datetime.now(datetime.UTC)


class OrderApproved(DomainEvent):
    pass


class OrderCancelled(DomainEvent):
    def __init__(self, order_id: str, reason: str):
        super().__init__(order_id)
        self.reason = reason


# Infrastructure Model
class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False)
    total_amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    cancellation_reason = Column(String)


# Infrastructure Repository
class OrderRepository(RepositoryProtocol[OrderModel]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, order_id: str) -> OrderModel | None:
        return await self.session.get(OrderModel, order_id)

    async def list(self, customer_id: str | None = None) -> list[OrderModel]:
        query = self.session.query(OrderModel)
        if customer_id:
            query = query.filter(OrderModel.customer_id == customer_id)
        return await query.all()

    async def add(self, order: OrderModel) -> OrderModel:
        self.session.add(order)
        await self.session.flush()
        return order

    async def update(self, order: OrderModel) -> OrderModel:
        await self.session.merge(order)
        await self.session.flush()
        return order

    async def remove(self, order: OrderModel) -> None:
        await self.session.delete(order)
        await self.session.flush()


# Domain Repository
class DomainOrderRepository(DomainRepositoryProtocol[OrderEntity]):
    def __init__(self, infrastructure_repo: OrderRepository):
        self._infra_repo = infrastructure_repo

    async def get(self, order_id: str) -> OrderEntity | None:
        """Get an order entity by ID"""
        model = await self._infra_repo.get(order_id)
        if model:
            return OrderEntity(
                order_id=model.id,
                customer_id=model.customer_id,
                total_amount=model.total_amount,
            )
        return None

    async def list(self, customer_id: str | None = None) -> list[OrderEntity]:
        """List order entities with optional customer filter"""
        models = await self._infra_repo.list(customer_id)
        return [
            OrderEntity(
                order_id=model.id,
                customer_id=model.customer_id,
                total_amount=model.total_amount,
            )
            for model in models
        ]

    async def add(self, entity: OrderEntity) -> OrderEntity:
        """Add a new order entity"""
        model = OrderModel(
            id=entity.order_id,
            customer_id=entity.customer_id,
            total_amount=entity.total_amount,
            status=entity.status,
            created_at=entity.created_at.isoformat(),
        )
        await self._infra_repo.add(model)
        return entity

    async def update(self, entity: OrderEntity) -> OrderEntity:
        """Update an existing order entity"""
        model = await self._infra_repo.get(entity.order_id)
        if not model:
            raise ValueError(f"Order {entity.order_id} not found")

        # Update model properties
        model.status = entity.status
        if hasattr(entity, "cancellation_reason"):
            model.cancellation_reason = entity.cancellation_reason

        await self._infra_repo.update(model)
        return entity

    async def remove(self, entity: OrderEntity) -> None:
        """Remove an order entity"""
        model = await self._infra_repo.get(entity.order_id)
        if model:
            await self._infra_repo.remove(model)


# Usage example
async def example_usage():
    # Assume we have a session factory
    async with AsyncSession() as session:
        # Create infrastructure repository
        infra_repo = OrderRepository(session)

        # Create domain repository
        domain_repo = DomainOrderRepository(infra_repo)

        # Create a new order
        new_order = OrderEntity(
            order_id="ORD123", customer_id="CUST456", total_amount=100.0
        )

        # Save the order through domain repository
        await domain_repo.add(new_order)

        # Get the order back
        order = await domain_repo.get("ORD123")
        if order:
            # Use domain methods
            order.approve()

            # Save changes
            await domain_repo.update(order)

            # Get events
            events = order.get_events()
            for event in events:
                print(f"Event: {type(event).__name__} for order {event.order_id}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
