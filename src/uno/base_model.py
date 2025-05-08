from pydantic import BaseModel, ConfigDict


class FrameworkBaseModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
    )

    # Note: to_dict() is always canonical and contract-compliant (see Uno DDD base classes).
