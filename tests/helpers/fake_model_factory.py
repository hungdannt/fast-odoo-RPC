"""Fake model factory for testing."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import random
import string


@dataclass
class FakeModel:
    """A fake model for testing."""

    id: int
    name: str
    fields: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key):
        return self.fields.get(key)

    def __setitem__(self, key, value):
        self.fields[key] = value

    def get(self, key, default=None):
        return self.fields.get(key, default)


class FakeModelFactory:
    """Factory for creating fake models for testing."""

    def __init__(self):
        self._id_counter = 1
        self._models: Dict[str, Dict[int, FakeModel]] = {}

    def create(
        self, model_name: str, name: Optional[str] = None, **kwargs
    ) -> FakeModel:
        """Create a fake model instance."""
        if model_name not in self._models:
            self._models[model_name] = {}

        model_id = self._id_counter
        self._id_counter += 1

        if name is None:
            name = f"{model_name}_{model_id}"

        model = FakeModel(id=model_id, name=name, fields=kwargs)
        self._models[model_name][model_id] = model

        return model

    def create_batch(self, model_name: str, count: int, **kwargs) -> List[FakeModel]:
        """Create multiple fake model instances."""
        models = []
        for i in range(count):
            name = kwargs.pop("name", None)
            if name:
                name = f"{name}_{i}"
            models.append(self.create(model_name, name=name, **kwargs))
        return models

    def get(self, model_name: str, model_id: int) -> Optional[FakeModel]:
        """Get a model by ID."""
        return self._models.get(model_name, {}).get(model_id)

    def get_all(self, model_name: str) -> List[FakeModel]:
        """Get all models of a specific type."""
        return list(self._models.get(model_name, {}).values())

    def clear(self):
        """Clear all created models."""
        self._models.clear()
        self._id_counter = 1

    def generate_random_string(self, length: int = 10) -> str:
        """Generate a random string."""
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    def generate_random_email(self) -> str:
        """Generate a random email address."""
        username = self.generate_random_string(8)
        domain = self.generate_random_string(6)
        return f"{username}@{domain}.com"
