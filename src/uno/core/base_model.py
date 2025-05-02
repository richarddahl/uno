from pydantic import BaseModel


class FrameworkBaseModel(BaseModel):
    model_config = {
        "frozen": True,
        "populate_by_name": True,
    }

    def to_canonical_dict(self, **kwargs) -> dict:
        """
        Return a JSON-serializable dict using Uno's canonical contract.
        """
        return self.model_dump(
            mode="json", exclude_none=True, exclude_unset=True, by_alias=True, **kwargs
        )
