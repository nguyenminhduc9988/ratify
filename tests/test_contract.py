"""Tests for Contract: construction, params/binding, composition."""

from __future__ import annotations

import pytest

from ratify import Contract, Lifecycle, Scope, checks
from ratify.exceptions import BindingError, ContractDefinitionError


def base() -> Contract:
    return (
        Contract("c", version="1.0")
        .hard("len", "bounded", scope=Scope.OUTPUT, check=checks.max_length(100))
        .judge("nice", "be nice", scope=Scope.BEHAVIORAL)
    )


def test_fluent_build() -> None:
    c = base()
    assert len(c) == 2
    assert [cl.id for cl in c] == ["len", "nice"]
    assert c.version == "1.0"


def test_duplicate_clause_id_rejected() -> None:
    c = Contract("c").hard("x", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    with pytest.raises(ContractDefinitionError, match="duplicate clause id"):
        c.hard("x", "d2", scope=Scope.OUTPUT, check=checks.always_pass())


def test_proof_flag_sets_enforcement() -> None:
    from ratify import Enforcement

    c = Contract("c").hard("p", "d", scope=Scope.POLICY, check=checks.always_pass(), proof=True)
    assert c.clauses[0].enforcement is Enforcement.PROOF


def test_param_and_bind() -> None:
    c = (
        Contract("c")
        .param("brand", type=str)
        .judge("b", "mentions {brand}", scope=Scope.BEHAVIORAL)
    )
    bound = c.bind(brand="Acme")
    assert bound.bound_params() == {"brand": "Acme"}
    # original untouched (immutability of bind)
    assert c.bound_params() == {}


def test_bind_unknown_param() -> None:
    c = Contract("c").param("brand", type=str)
    with pytest.raises(BindingError, match="unknown param"):
        c.bind(nonsense="x")


def test_bind_missing_required() -> None:
    c = Contract("c").param("brand", type=str).judge("b", "d", scope=Scope.OUTPUT)
    with pytest.raises(BindingError, match="missing required param"):
        c.bind()


def test_bind_type_mismatch() -> None:
    c = Contract("c").param("n", type=int)
    with pytest.raises(BindingError, match="expected int"):
        c.bind(n="not an int")


def test_bind_uses_default() -> None:
    c = (
        Contract("c")
        .param("tone", type=str, default="formal")
        .judge("t", "tone is {tone}", scope=Scope.BEHAVIORAL)
    )
    assert c.bind().bound_params() == {"tone": "formal"}


def test_duplicate_param_rejected() -> None:
    c = Contract("c").param("x", type=str)
    with pytest.raises(ContractDefinitionError, match="duplicate param"):
        c.param("x", type=int)


def test_clauses_for_phase() -> None:
    c = (
        Contract("c")
        .hard("pre", "d", scope=Scope.INPUT, check=checks.always_pass(), when=Lifecycle.PRE)
        .hard("post", "d", scope=Scope.OUTPUT, check=checks.always_pass(), when=Lifecycle.POST)
    )
    assert [cl.id for cl in c.clauses_for(Lifecycle.PRE)] == ["pre"]
    assert [cl.id for cl in c.clauses_for(Lifecycle.POST)] == ["post"]


def test_include_merges_clauses_and_params() -> None:
    a = (
        Contract("a")
        .param("brand", type=str)
        .hard("a1", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    )
    b = Contract("b").hard("b1", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    merged = a.include(b)
    assert [cl.id for cl in merged] == ["a1", "b1"]
    assert "brand" in [p.name for p in merged.params]


def test_include_collision_raises() -> None:
    a = Contract("a").hard("dup", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    b = Contract("b").hard("dup", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    with pytest.raises(ContractDefinitionError, match="duplicate clause id"):
        a.include(b)


def test_include_with_prefix_avoids_collision() -> None:
    a = Contract("a").hard("dup", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    b = Contract("b").hard("dup", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    merged = a.include(b, prefix="b.")
    assert [cl.id for cl in merged] == ["dup", "b.dup"]


def test_add_operator() -> None:
    a = Contract("a").hard("a1", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    b = Contract("b").hard("b1", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    merged = a + b
    assert len(merged) == 2


def test_repr() -> None:
    assert "Contract('c'" in repr(base())
