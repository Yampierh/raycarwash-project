# Re-exports the canonical body-class → VehicleSize mapping from infrastructure.
from infrastructure.nhtsa.client import map_body_to_size as get_size_from_body_class  # noqa: F401

__all__ = ["get_size_from_body_class"]
