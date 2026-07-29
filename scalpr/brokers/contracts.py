"""Canonical contract models — re-exported from :mod:`scalpr.domain.contracts`.

This module exists for backward compatibility during the migration from
``scalpr.brokers.*`` to ``scalpr.domain.*``. All contract types are defined in
:mod:`scalpr.domain.contracts`. Importing from here still works but new code
should import from ``scalpr.domain.contracts`` directly.
"""
from __future__ import annotations

# ruff: noqa: F401 — re-export all contract types for backward compat
from scalpr.domain.contracts import (
    DepthLevel,
    Funds,
    Holding,
    HttpClientProtocol,
    MarketDepth,
    Quote,
    ResolverProtocol,
    Trade,
)
