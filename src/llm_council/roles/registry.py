"""Role registry for managing and retrieving roles."""

from __future__ import annotations

from typing import Iterator

from llm_council.roles.role import Role


class RoleRegistry:
    """Registry for managing roles in a council.

    The registry maintains a collection of roles and provides methods for
    adding, retrieving, and organizing them.

    Example:
        ```python
        registry = RoleRegistry()

        # Add custom role
        registry.add(Role(
            name="domain_expert",
            prompt="You are an expert in...",
            model="gpt-4",
        ))

        # Get all roles
        for role in registry:
            print(role.name)
        ```
    """

    def __init__(self) -> None:
        """Initialize an empty role registry."""
        self._roles: dict[str, Role] = {}

    def add(self, role: Role) -> RoleRegistry:
        """Add a role to the registry.

        Args:
            role: The role to add

        Returns:
            Self for method chaining

        Raises:
            ValueError: If a role with the same name already exists
        """
        if role.name in self._roles:
            raise ValueError(f"Role '{role.name}' already exists in registry")
        self._roles[role.name] = role
        return self

    def get(self, name: str) -> Role:
        """Get a role by name.

        Args:
            name: Name of the role

        Returns:
            The role instance

        Raises:
            KeyError: If the role doesn't exist
        """
        if name not in self._roles:
            raise KeyError(f"Role '{name}' not found in registry")
        return self._roles[name]

    def has(self, name: str) -> bool:
        """Check if a role exists in the registry."""
        return name in self._roles

    def remove(self, name: str) -> RoleRegistry:
        """Remove a role from the registry.

        Args:
            name: Name of the role to remove

        Returns:
            Self for method chaining
        """
        if name in self._roles:
            del self._roles[name]
        return self

    def clear(self) -> RoleRegistry:
        """Remove all roles from the registry.

        Returns:
            Self for method chaining
        """
        self._roles.clear()
        return self

    def get_by_model(self, model: str) -> list[Role]:
        """Get all roles using a specific model.

        Args:
            model: Model identifier to filter by

        Returns:
            List of roles using that model
        """
        return [role for role in self._roles.values() if role.model == model]


    def list_names(self) -> list[str]:
        """Get a list of all role names."""
        return list(self._roles.keys())


    def __iter__(self) -> Iterator[Role]:
        """Iterate over all roles in the registry."""
        return iter(self._roles.values())

    def __len__(self) -> int:
        """Get the number of roles in the registry."""
        return len(self._roles)

    def __contains__(self, name: str) -> bool:
        """Check if a role name exists in the registry."""
        return name in self._roles

