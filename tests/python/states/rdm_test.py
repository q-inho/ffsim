# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test reduced density matrices."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

import ffsim

RNG = np.random.default_rng(250368525468016360570772321326665989865)


def test_reduced_density_matrices_expectation():
    """Test ReducedDensityMatrix expectation method."""
    norb = 5
    nelec = (3, 2)

    vec = ffsim.random.random_state_vector(ffsim.dim(norb, nelec), seed=RNG)
    rdms = ffsim.ReducedDensityMatrix(
        *ffsim.rdms(vec, norb=norb, nelec=nelec, rank=2, spin_summed=True)
    )
    mol_ham = ffsim.random.random_molecular_hamiltonian(norb, seed=RNG)
    linop = ffsim.linear_operator(mol_ham, norb=norb, nelec=nelec)

    expected = np.vdot(vec, linop @ vec)
    actual = rdms.expectation(mol_ham)

    np.testing.assert_allclose(actual, expected)


def test_reduced_density_matrices_rotated():
    """Test ReducedDensityMatrix rotated method."""
    norb = 5
    nelec = (3, 2)

    vec = ffsim.random.random_state_vector(ffsim.dim(norb, nelec))
    rdms = ffsim.ReducedDensityMatrix(
        *ffsim.rdms(vec, norb=norb, nelec=nelec, rank=2, spin_summed=True)
    )
    mol_ham = ffsim.random.random_molecular_hamiltonian(norb, seed=RNG)
    energy = rdms.expectation(mol_ham)

    orbital_rotation = ffsim.random.random_unitary(norb, seed=RNG)
    energy_rotated = rdms.rotated(orbital_rotation).expectation(
        mol_ham.rotated(orbital_rotation)
    )

    np.testing.assert_allclose(energy_rotated, energy)


@pytest.mark.parametrize(
    "norb, nelec, spin_summed",
    [
        (4, (2, 2), True),
        (4, (2, 2), False),
        (3, (1, 2), True),
        (3, (1, 2), False),
        (2, (0, 1), True),
        (2, (0, 1), False),
        (1, (0, 0), True),
        (1, (0, 0), False),
    ],
)
def test_rdm1s(norb: int, nelec: tuple[int, int], spin_summed: bool):
    """Test computing spin-summed 1-RDM."""
    vec = ffsim.random.random_state_vector(ffsim.dim(norb, nelec), seed=RNG)
    rdm1_func = _rdm1_spin_summed if spin_summed else _rdm1s
    rdm = ffsim.rdms(vec, norb, nelec, spin_summed=spin_summed)
    expected = rdm1_func(vec, norb, nelec)
    np.testing.assert_allclose(rdm, expected, atol=1e-12)


@pytest.mark.parametrize(
    "norb, nelec, spin_summed, reorder",
    [
        (4, (2, 2), True, True),
        (4, (2, 2), True, False),
        (4, (2, 2), False, True),
        (4, (2, 2), False, False),
        (3, (1, 2), True, True),
        (3, (1, 2), True, False),
        (3, (1, 2), False, True),
        (3, (1, 2), False, False),
        (2, (0, 1), True, True),
        (2, (0, 1), True, False),
        (2, (0, 1), False, True),
        (2, (0, 1), False, False),
        (1, (0, 0), True, True),
        (1, (0, 0), True, False),
        (1, (0, 0), False, True),
        (1, (0, 0), False, False),
    ],
)
def test_rdm2s(norb: int, nelec: tuple[int, int], spin_summed: bool, reorder: bool):
    """Test computing 1- and 2-RDMs."""
    vec = ffsim.random.random_state_vector(ffsim.dim(norb, nelec), seed=RNG)

    rdm1, rdm2 = ffsim.rdms(
        vec,
        norb,
        nelec,
        rank=2,
        spin_summed=spin_summed,
        reorder=reorder,
    )

    func = {
        # (spin_summed, reorder): (rdm1_func, rdm2_func)
        (False, False): (_rdm1s, _rdm2s),
        (False, True): (_rdm1s, _rdm2s_reordered),
        (True, False): (_rdm1_spin_summed, _rdm2_spin_summed),
        (True, True): (_rdm1_spin_summed, _rdm2_spin_summed_reordered),
    }
    rdm1_func, rdm2_func = func[spin_summed, reorder]
    expected_rdm1 = rdm1_func(vec, norb, nelec)
    expected_rdm2 = rdm2_func(vec, norb, nelec)
    np.testing.assert_allclose(rdm1, expected_rdm1, atol=1e-12)
    np.testing.assert_allclose(rdm2, expected_rdm2, atol=1e-12)


def _rdm1s(vec: np.ndarray, norb: int, nelec: tuple[int, int]) -> np.ndarray:
    """Compute 1-RDM directly from its definition."""
    rdm_a = np.zeros((norb, norb), dtype=complex)
    rdm_b = np.zeros((norb, norb), dtype=complex)
    for i, j in itertools.combinations_with_replacement(range(norb), 2):
        op = ffsim.FermionOperator(
            {
                (ffsim.cre_a(i), ffsim.des_a(j)): 1,
            }
        )
        linop = ffsim.linear_operator(op, norb, nelec)
        val = np.vdot(vec, linop @ vec)
        rdm_a[i, j] = val
        rdm_a[j, i] = val.conjugate()
        op = ffsim.FermionOperator(
            {
                (ffsim.cre_b(i), ffsim.des_b(j)): 1,
            }
        )
        linop = ffsim.linear_operator(op, norb, nelec)
        val = np.vdot(vec, linop @ vec)
        rdm_b[i, j] = val
        rdm_b[j, i] = val.conjugate()
    return np.array([rdm_a, rdm_b])


def _rdm1_spin_summed(vec: np.ndarray, norb: int, nelec: tuple[int, int]) -> np.ndarray:
    """Compute spin-summed 1-RDM directly from its definition."""
    rdms = _rdm1s(vec, norb, nelec)
    return np.sum(rdms, axis=0)


def _rdm2s(vec: np.ndarray, norb: int, nelec: tuple[int, int]) -> np.ndarray:
    """Compute 2-RDM directly from its definition."""
    rdm_aa = np.zeros((norb, norb, norb, norb), dtype=complex)
    rdm_ab = np.zeros((norb, norb, norb, norb), dtype=complex)
    rdm_bb = np.zeros((norb, norb, norb, norb), dtype=complex)
    for p, q, r, s in itertools.product(range(norb), repeat=4):
        op = ffsim.FermionOperator(
            {
                (ffsim.cre_a(p), ffsim.des_a(q), ffsim.cre_a(r), ffsim.des_a(s)): 1,
            }
        )
        linop = ffsim.linear_operator(op, norb, nelec)
        val = np.vdot(vec, linop @ vec)
        rdm_aa[p, q, r, s] = val

        op = ffsim.FermionOperator(
            {
                (ffsim.cre_a(p), ffsim.des_a(q), ffsim.cre_b(r), ffsim.des_b(s)): 1,
            }
        )
        linop = ffsim.linear_operator(op, norb, nelec)
        val = np.vdot(vec, linop @ vec)
        rdm_ab[p, q, r, s] = val

        op = ffsim.FermionOperator(
            {
                (ffsim.cre_b(p), ffsim.des_b(q), ffsim.cre_b(r), ffsim.des_b(s)): 1,
            }
        )
        linop = ffsim.linear_operator(op, norb, nelec)
        val = np.vdot(vec, linop @ vec)
        rdm_bb[p, q, r, s] = val

    return np.array([rdm_aa, rdm_ab, rdm_bb])


def _rdm2s_reordered(vec: np.ndarray, norb: int, nelec: tuple[int, int]) -> np.ndarray:
    """Compute reordered 2-RDM directly from its definition."""
    rdm_aa = np.zeros((norb, norb, norb, norb), dtype=complex)
    rdm_ab = np.zeros((norb, norb, norb, norb), dtype=complex)
    rdm_bb = np.zeros((norb, norb, norb, norb), dtype=complex)
    for p, q, r, s in itertools.product(range(norb), repeat=4):
        op = ffsim.FermionOperator(
            {
                (ffsim.cre_a(p), ffsim.cre_a(r), ffsim.des_a(s), ffsim.des_a(q)): 1,
            }
        )
        linop = ffsim.linear_operator(op, norb, nelec)
        val = np.vdot(vec, linop @ vec)
        rdm_aa[p, q, r, s] = val

        op = ffsim.FermionOperator(
            {
                (ffsim.cre_a(p), ffsim.cre_b(r), ffsim.des_b(s), ffsim.des_a(q)): 1,
            }
        )
        linop = ffsim.linear_operator(op, norb, nelec)
        val = np.vdot(vec, linop @ vec)
        rdm_ab[p, q, r, s] = val

        op = ffsim.FermionOperator(
            {
                (ffsim.cre_b(p), ffsim.cre_b(r), ffsim.des_b(s), ffsim.des_b(q)): 1,
            }
        )
        linop = ffsim.linear_operator(op, norb, nelec)
        val = np.vdot(vec, linop @ vec)
        rdm_bb[p, q, r, s] = val
    return np.array([rdm_aa, rdm_ab, rdm_bb])


def _rdm2_spin_summed(vec: np.ndarray, norb: int, nelec: tuple[int, int]) -> np.ndarray:
    """Compute spin-summed 2-RDM directly from its definition."""
    rdm_aa, rdm_ab, rdm_bb = _rdm2s(vec, norb, nelec)
    return rdm_aa + rdm_ab + rdm_ab.transpose(2, 3, 0, 1) + rdm_bb


def _rdm2_spin_summed_reordered(
    vec: np.ndarray, norb: int, nelec: tuple[int, int]
) -> np.ndarray:
    """Compute spin-summed reordered 2-RDM directly from its definition."""
    rdm_aa, rdm_ab, rdm_bb = _rdm2s_reordered(vec, norb, nelec)
    return rdm_aa + rdm_ab + rdm_ab.transpose(2, 3, 0, 1) + rdm_bb
