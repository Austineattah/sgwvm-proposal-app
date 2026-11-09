"""Tenant-scoped, retrieval-only AI support for NexusVault.

The PostgreSQL schema expected by this module is:

* ``nv_knowledge_base(id, tenant_id, title, content)``
* ``nv_support_tickets(ticket_id, tenant_id, user_id, email, query_text,
  priority, status, created_at)``

Both tables must have RLS policies that consult
``current_setting('app.current_tenant', true)``. Public onboarding documents
and tickets use the reserved tenant ID ``public``. This module sets the RLS
context for every transaction; database roles and policies must still enforce
RLS independently. The application must build ``INTERNAL_ADMIN`` contexts only
after authenticating the user and authorizing their tenant membership.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

import psycopg2
from psycopg2.extensions import connection as PostgresConnection
from psycopg2.extensions import cursor as PostgresCursor


CONFIDENCE_THRESHOLD = 0.90
PUBLIC_TENANT_ID = "public"
LEGAL_DISCLAIMER = (
    "[OFFICIAL NOTICE]: This automated response is provided for guidance and "
    "technical navigation only. It does not constitute a legally binding "
    "administrative decision or procurement commitment under BPP/ICRC frameworks."
)
_STOP_WORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for",
        "from", "how", "i", "in", "is", "it", "of", "on", "or", "the", "to",
        "we", "what", "when", "where", "which", "who", "why", "with", "you",
    }
)


class SupportTier(str, Enum):
    """Access tier for the support engine."""

    PUBLIC_ONBOARDING = "PUBLIC_ONBOARDING"
    INTERNAL_ADMIN = "INTERNAL_ADMIN"


@dataclass(frozen=True)
class UserContext:
    """Identity and tenant scope supplied by the authenticated application."""

    user_id: str | None
    tenant_id: str | None
    role: str
    tier: SupportTier
    email: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.tier, SupportTier):
            try:
                object.__setattr__(self, "tier", SupportTier(self.tier))
            except ValueError as exc:
                raise ValueError(f"Unsupported support tier: {self.tier!r}.") from exc


@dataclass(frozen=True)
class AgentResponse:
    """A grounded answer or a human-support escalation."""

    query_id: str
    response_text: str
    confidence_score: float
    grounded_in_kb: bool
    escalated_to_human: bool
    ticket_id: str | None


@dataclass(frozen=True)
class KnowledgeEntry:
    """A knowledge-base result and its query coverage score."""

    entry_id: str
    title: str
    content: str
    confidence_score: float


class _RLSPostgresStore:
    """Owns short transactions whose first statement establishes tenant scope."""

    def __init__(
        self,
        connection_string: str | None = None,
        connection_factory: Callable[[], PostgresConnection] | None = None,
    ) -> None:
        if connection_factory is not None:
            self._connection_factory = connection_factory
        else:
            dsn = connection_string or os.environ.get("DATABASE_URL")
            if not dsn:
                raise ValueError(
                    "Provide a PostgreSQL connection string or set DATABASE_URL."
                )
            self._connection_factory = lambda: psycopg2.connect(dsn)

    @contextmanager
    def tenant_cursor(self, tenant_id: str) -> Iterator[PostgresCursor]:
        """Yield a cursor after setting transaction-local RLS context."""
        conn = self._connection_factory()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SET LOCAL app.current_tenant = %s",
                        (tenant_id,),
                    )
                    yield cursor
        finally:
            conn.close()


class SovereignKnowledgeBase:
    """Retrieves tenant-scoped passages from ``nv_knowledge_base``.

    Confidence is a conservative lexical coverage measure: the proportion of
    meaningful query terms present in the retrieved passage, blended with
    whole-query phrase similarity. It is not a calibrated probability.
    """

    def __init__(
        self,
        connection_string: str | None = None,
        *,
        connection_factory: Callable[[], PostgresConnection] | None = None,
    ) -> None:
        self._store = _RLSPostgresStore(connection_string, connection_factory)

    def retrieve(
        self,
        query_text: str,
        context: UserContext,
        *,
        limit: int = 5,
    ) -> list[KnowledgeEntry]:
        """Return full-text-ranked entries visible in the caller's tenant."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        tenant_id = _validate_context(context)
        if not query_text or not query_text.strip():
            raise ValueError("query_text must not be empty")

        statement = """
            SELECT id, title, content,
                   ts_rank_cd(
                       to_tsvector('english', coalesce(title, '') || ' ' || content),
                       plainto_tsquery('english', %s)
                   ) AS rank
            FROM nv_knowledge_base
            WHERE tenant_id = %s
              AND to_tsvector(
                      'english', coalesce(title, '') || ' ' || content
                  ) @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC, id
            LIMIT %s
        """
        with self._store.tenant_cursor(tenant_id) as cursor:
            cursor.execute(statement, (query_text, tenant_id, query_text, limit))
            rows: Sequence[Sequence[Any]] = cursor.fetchall()

        return [
            KnowledgeEntry(
                entry_id=str(row[0]),
                title=str(row[1] or ""),
                content=str(row[2] or ""),
                confidence_score=_query_coverage(
                    query_text, f"{row[1] or ''} {row[2] or ''}"
                ),
            )
            for row in rows
        ]


class NexusAgenticSupportEngine:
    """Answers from the tenant's knowledge base or creates a priority ticket."""

    def __init__(
        self,
        knowledge_base: SovereignKnowledgeBase,
        *,
        connection_string: str | None = None,
        connection_factory: Callable[[], PostgresConnection] | None = None,
    ) -> None:
        self._knowledge_base = knowledge_base
        if connection_string is None and connection_factory is None:
            self._store = knowledge_base._store
        else:
            self._store = _RLSPostgresStore(connection_string, connection_factory)

    def process_query(
        self,
        query_text: str,
        context: UserContext,
    ) -> AgentResponse:
        """Return a grounded answer only when confidence meets the threshold."""
        tenant_id = _validate_context(context)
        if not query_text or not query_text.strip():
            raise ValueError("query_text must not be empty")

        query_id = str(uuid.uuid4())
        entries = self._knowledge_base.retrieve(query_text, context)
        best_entry = entries[0] if entries else None
        confidence = best_entry.confidence_score if best_entry else 0.0
        grounded = best_entry is not None

        if confidence < CONFIDENCE_THRESHOLD:
            ticket_id = self._create_priority_ticket(
                tenant_id=tenant_id,
                context=context,
                query_text=query_text.strip(),
            )
            message = (
                "I could not verify a sufficiently reliable answer from the "
                "authorized knowledge base. A priority support ticket has "
                "been created for human assistance."
            )
            return AgentResponse(
                query_id=query_id,
                response_text=_with_disclaimer(message),
                confidence_score=confidence,
                grounded_in_kb=grounded,
                escalated_to_human=True,
                ticket_id=ticket_id,
            )

        assert best_entry is not None
        answer = best_entry.content.strip()
        if best_entry.title.strip():
            answer = f"{best_entry.title.strip()}\n\n{answer}"
        return AgentResponse(
            query_id=query_id,
            response_text=_with_disclaimer(answer),
            confidence_score=confidence,
            grounded_in_kb=True,
            escalated_to_human=False,
            ticket_id=None,
        )

    def _create_priority_ticket(
        self,
        *,
        tenant_id: str,
        context: UserContext,
        query_text: str,
    ) -> str:
        ticket_id = str(uuid.uuid4())
        statement = """
            INSERT INTO nv_support_tickets
                (ticket_id, tenant_id, user_id, email, query_text,
                 priority, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING ticket_id
        """
        with self._store.tenant_cursor(tenant_id) as cursor:
            cursor.execute(
                statement,
                (
                    ticket_id,
                    tenant_id,
                    context.user_id,
                    context.email,
                    query_text,
                    "HIGH",
                    "OPEN",
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Priority support ticket insert returned no ID.")
        return str(row[0])


def _validate_context(context: UserContext) -> str:
    """Validate tier-specific identity and return the RLS tenant scope."""
    if not isinstance(context.tier, SupportTier):
        raise ValueError("context.tier must be a SupportTier value.")
    if context.tier is SupportTier.PUBLIC_ONBOARDING:
        if context.tenant_id not in (None, "", PUBLIC_TENANT_ID):
            raise ValueError("Public onboarding cannot select an internal tenant.")
        return PUBLIC_TENANT_ID

    if not context.user_id or not context.user_id.strip():
        raise ValueError("Internal support requires an authenticated user_id.")
    if not context.tenant_id or not context.tenant_id.strip():
        raise ValueError("Internal support requires an authenticated tenant_id.")
    if not context.role or not context.role.strip():
        raise ValueError("Internal support requires an authenticated role.")
    return context.tenant_id.strip()


def _query_coverage(query_text: str, passage: str) -> float:
    """Score lexical support without treating database rank as probability."""
    query_terms = {
        token
        for token in re.findall(r"[a-z0-9]+", query_text.casefold())
        if token not in _STOP_WORDS
    }
    if not query_terms:
        query_terms = set(re.findall(r"[a-z0-9]+", query_text.casefold()))
    passage_terms = set(re.findall(r"[a-z0-9]+", passage.casefold()))
    if not query_terms:
        return 0.0

    coverage = len(query_terms & passage_terms) / len(query_terms)
    normalized_query = " ".join(sorted(query_terms))
    normalized_passage = " ".join(sorted(passage_terms))
    phrase_similarity = SequenceMatcher(
        None, normalized_query, normalized_passage
    ).ratio()
    return min(1.0, max(0.0, coverage * (0.9 + 0.1 * phrase_similarity)))


def _with_disclaimer(response_text: str) -> str:
    return f"{response_text.rstrip()}\n\n{LEGAL_DISCLAIMER}"
