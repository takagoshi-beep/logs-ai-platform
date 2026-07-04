"""Shared CapabilityRegistry instance for the backend API surface.

`backend/api/capability_router.py` previously constructed its own
`CapabilityRegistry()` (see the `# TODO: Inject from app context` note that
used to sit next to it). That meant any capability executions recorded by
business logic (e.g. `ProjectService`) would live in a *different* registry
instance than the one the `/capabilities` REST API reads from — so nothing
business logic recorded would ever actually show up over HTTP.

Any code that wants its work tracked as a Blueprint Capability (Principle 2:
Capability Driven) must import `registry` from here, not construct its own
`CapabilityRegistry()`.

Note: like `capability.registry.CapabilityRegistry` itself, this is an
in-memory singleton — it resets on every process restart. Capability
definitions are re-registered lazily (idempotently) by whoever uses them,
so this doesn't require a startup hook or import-order guarantee.
"""
from __future__ import annotations

from capability.domain import Capability, CapabilityStatus, GovernanceLevel
from capability.registry import CapabilityRegistry

registry = CapabilityRegistry()


def ensure_registered(capability: Capability) -> None:
    """Register (or re-register) a capability definition, idempotently.

    Registering an already-known capability_id simply overwrites the
    existing entry, so calling this on every request is cheap and safe —
    it's how we survive registry resets without needing a startup hook.
    """
    registry.register_capability(capability)


PROJECT_AGGREGATE_CAPABILITY = Capability(
    capability_id="project_aggregate_analysis",
    name="Project Aggregate Analysis",
    category="business",
    description=(
        "Builds a complete project understanding (events, state, goal "
        "evaluations, decisions, actions, health/risk/opportunity scoring) "
        "from a purchase order in Supabase."
    ),
    owner_team="AI OS",
    owner_user_id="system",
    team_id="ai-os",
    status=CapabilityStatus.DEPLOYED,
    version="1.0.0",
    supported_inputs=["project_id"],
    supported_outputs=["project_aggregate"],
    required_context=["purchase_orders"],
    governance_level=GovernanceLevel.LOW,
)