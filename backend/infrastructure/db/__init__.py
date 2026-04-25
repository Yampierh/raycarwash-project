# Intentionally empty — avoids circular import with domain model files.
# Domain models import infrastructure.db.base; if __init__.py imported domains,
# Python would hit a circular initialization loop.
# Use infrastructure.db.registry to force-register all models before queries.
