from uno.core.domain.core import AggregateRoot, DomainEvent


class UserCreated(DomainEvent):
    event_type: str = "user_created"
    user_id: str
    username: str
    email: str


class User(AggregateRoot[str]):
    username: str
    email: str

    def __init__(self, username: str, email: str, **data):
        super().__init__(**data)
        self.username = username
        self.email = email
        event = UserCreated(
            user_id=self.id,
            username=username,
            email=email,
        )
        self.add_event(event)
