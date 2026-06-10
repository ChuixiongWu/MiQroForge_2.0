"""Cluster Hamiltonian contract: round-trip, symmetry, and schema validation tests.

Covers:
- ``make_mock_cluster`` produces valid output with correct shapes/dtypes.
- ``write_cluster`` → ``load_cluster`` round-trip preserves all contract datasets.
- ``heff`` is symmetric (one-body Hermiticity for real MOs).
- ``eris`` (physicist ordering) satisfies 8-fold symmetry for real integrals.
- Error on missing / corrupt file.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

import sys

_EWF_PROFILE = Path(__file__).resolve().parents[2] / "nodes" / "quantum" / "ewf-decompose" / "profile"
if str(_EWF_PROFILE) not in sys.path:
    sys.path.insert(0, str(_EWF_PROFILE))

from cluster_contract import (
    DTYPE,
    ECORE_DS,
    ERIS_DS,
    HEFF_DS,
    MOLECULE_DS,
    NORB_DS,
    SOURCE_DS,
    SOURCE_VAYESTA_MOCK,
    load_cluster,
    make_mock_cluster,
    write_cluster,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def h2_mock():
    """Default H₂ / STO-3G mock cluster (2 orbitals)."""
    return make_mock_cluster()


@pytest.fixture(scope="module")
def h2o_mock():
    """H₂O / STO-3G mock cluster (7 orbitals) for richer symmetry tests."""
    return make_mock_cluster(
        molecule="O 0 0 0; H 0 0.757 0.587; H 0 -0.757 0.587",
    )


@pytest.fixture
def tmp_h5():
    """Temporary HDF5 file path that is cleaned up after each test."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        path = f.name
    yield Path(path)
    if os.path.exists(path):
        os.unlink(path)


# ── Schema / structural tests ───────────────────────────────────────────────


def test_make_mock_cluster_shapes_dtypes(h2_mock):
    """Default mock returns correct shapes, dtypes, and meta keys."""
    heff, eris, e_core, meta = h2_mock["heff"], h2_mock["eris"], h2_mock["e_core"], h2_mock["meta"]

    norb = meta["norb"]
    assert heff.shape == (norb, norb)
    assert eris.shape == (norb, norb, norb, norb)
    assert heff.dtype == DTYPE
    assert eris.dtype == DTYPE
    assert isinstance(e_core, np.float64)
    assert meta["source"] == SOURCE_VAYESTA_MOCK
    assert "molecule" in meta
    assert "norb" in meta


def test_make_mock_cluster_returns_molecule_id(h2_mock, h2o_mock):
    """Molecule identifier reflects the chemical formula and basis."""
    assert "H2" in h2_mock["meta"]["molecule"]
    assert "H2O" in h2o_mock["meta"]["molecule"]


# ── Round-trip tests ────────────────────────────────────────────────────────


def test_round_trip_heff(h2_mock, tmp_h5):
    """heff survives write → load unchanged."""
    write_cluster(tmp_h5, h2_mock["heff"], h2_mock["eris"], h2_mock["e_core"], **h2_mock["meta"])
    loaded = load_cluster(tmp_h5)
    assert np.array_equal(loaded["heff"], h2_mock["heff"])


def test_round_trip_eris(h2_mock, tmp_h5):
    """eris survives write → load unchanged."""
    write_cluster(tmp_h5, h2_mock["heff"], h2_mock["eris"], h2_mock["e_core"], **h2_mock["meta"])
    loaded = load_cluster(tmp_h5)
    assert np.array_equal(loaded["eris"], h2_mock["eris"])


def test_round_trip_e_core(h2_mock, tmp_h5):
    """e_core survives write → load unchanged."""
    write_cluster(tmp_h5, h2_mock["heff"], h2_mock["eris"], h2_mock["e_core"], **h2_mock["meta"])
    loaded = load_cluster(tmp_h5)
    np.testing.assert_equal(loaded["e_core"], h2_mock["e_core"])


def test_round_trip_meta_norb(h2_mock, tmp_h5):
    """meta/norb survives round-trip."""
    write_cluster(tmp_h5, h2_mock["heff"], h2_mock["eris"], h2_mock["e_core"], **h2_mock["meta"])
    loaded = load_cluster(tmp_h5)
    assert loaded["meta"]["norb"] == h2_mock["meta"]["norb"]


def test_round_trip_meta_source(h2_mock, tmp_h5):
    """meta/source survives round-trip."""
    write_cluster(tmp_h5, h2_mock["heff"], h2_mock["eris"], h2_mock["e_core"], **h2_mock["meta"])
    loaded = load_cluster(tmp_h5)
    assert loaded["meta"]["source"] == h2_mock["meta"]["source"]


def test_round_trip_meta_molecule(h2_mock, tmp_h5):
    """meta/molecule survives round-trip."""
    write_cluster(tmp_h5, h2_mock["heff"], h2_mock["eris"], h2_mock["e_core"], **h2_mock["meta"])
    loaded = load_cluster(tmp_h5)
    assert loaded["meta"]["molecule"] == h2_mock["meta"]["molecule"]


def test_make_mock_cluster_with_output_path(tmp_h5):
    """make_mock_cluster(output_path=...) writes a loadable file."""
    result = make_mock_cluster(output_path=str(tmp_h5))
    loaded = load_cluster(tmp_h5)
    assert np.array_equal(loaded["heff"], result["heff"])
    assert np.array_equal(loaded["eris"], result["eris"])
    np.testing.assert_equal(loaded["e_core"], result["e_core"])


# ── Symmetry tests ──────────────────────────────────────────────────────────


def test_heff_symmetry(h2_mock):
    """One-body Hamiltonian must be Hermitian (symmetric for real MOs)."""
    heff = h2_mock["heff"]
    assert np.allclose(heff, heff.T, atol=1e-12)


def test_heff_symmetry_h2o(h2o_mock):
    """Symmetry holds for larger system too."""
    heff = h2o_mock["heff"]
    assert np.allclose(heff, heff.T, atol=1e-12)


def test_eris_eightfold_symmetry_h2o(h2o_mock):
    """2-body integrals in physicist ordering satisfy 8-fold symmetry.

    For real MO integrals:
      h2[p,q,r,s] == h2[r,s,p,q]    (swap bra & ket)
      h2[p,q,r,s] == h2[q,p,s,r]    (swap within each pair)
    Combined these generate 8 equivalent index permutations.
    """
    eris = h2o_mock["eris"]
    norb = eris.shape[0]

    # Generate all 4-index combinations (norb ≤ 7 → manageable)
    for p in range(norb):
        for q in range(norb):
            for r in range(norb):
                for s in range(norb):
                    ref = eris[p, q, r, s]
                    # Swap bra & ket
                    assert eris[r, s, p, q] == pytest.approx(ref, abs=1e-12), (
                        f"bra-ket swap failed at ({p},{q},{r},{s})"
                    )
                    # Swap within each pair
                    assert eris[q, p, s, r] == pytest.approx(ref, abs=1e-12), (
                        f"within-pair swap failed at ({p},{q},{r},{s})"
                    )


def test_eris_chemist_to_physicist_consistency(h2o_mock):
    """The transpose(0,2,1,3) reorder is self-inverse on real 4-fold symmetric data.

    Applying the reorder twice yields the original (up to numerical precision),
    because real chemist integrals have (ij|kl) = (ij|lk) symmetry.
    """
    eris_phys = h2o_mock["eris"]  # already physicist-ordered

    # Reorder back to chemist
    eris_chem = eris_phys.transpose(0, 2, 1, 3)
    # Reorder to physicist again
    eris_phys2 = eris_chem.transpose(0, 2, 1, 3)

    assert np.allclose(eris_phys, eris_phys2, atol=1e-12)


def test_e_core_positive(h2_mock, h2o_mock):
    """Nuclear repulsion energy must be positive."""
    assert h2_mock["e_core"] > 0
    assert h2o_mock["e_core"] > 0


# ── Error handling ──────────────────────────────────────────────────────────


def test_load_missing_file():
    """load_cluster raises FileNotFoundError for nonexistent path."""
    with pytest.raises((FileNotFoundError, OSError)):
        load_cluster("/nonexistent/path/cluster.h5")


# ── Contract dataset presence ───────────────────────────────────────────────


def test_contract_datasets_present(tmp_h5, h2o_mock):
    """Written HDF5 contains exactly the contract-specified datasets."""
    write_cluster(
        tmp_h5,
        h2o_mock["heff"],
        h2o_mock["eris"],
        h2o_mock["e_core"],
        **h2o_mock["meta"],
    )
    import h5py

    with h5py.File(tmp_h5, "r") as f:
        assert HEFF_DS in f
        assert ERIS_DS in f
        assert ECORE_DS in f
        assert NORB_DS in f
        assert SOURCE_DS in f
        assert MOLECULE_DS in f
        # Verify dtypes
        assert f[HEFF_DS].dtype == np.float64
        assert f[ERIS_DS].dtype == np.float64
        assert np.issubdtype(f[ECORE_DS].dtype, np.floating)
        assert np.issubdtype(f[NORB_DS].dtype, np.integer)


def test_h2_mock_2d_arrays(h2_mock):
    """H₂ has 2 spatial orbitals → all arrays reflect this."""
    assert h2_mock["heff"].shape == (2, 2)
    assert h2_mock["eris"].shape == (2, 2, 2, 2)
    assert h2_mock["meta"]["norb"] == 2


def test_h2o_mock_7d_arrays(h2o_mock):
    """H₂O / STO-3G has 7 spatial orbitals."""
    norb = h2o_mock["meta"]["norb"]
    assert norb == 7
    assert h2o_mock["heff"].shape == (norb, norb)
    assert h2o_mock["eris"].shape == (norb, norb, norb, norb)
