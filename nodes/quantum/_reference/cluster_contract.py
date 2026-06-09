"""Cluster Hamiltonian contract: HDF5 schema, I/O helpers, and mock generator.

Defines the ``vayesta/cluster-hamiltonian-h5`` data contract for the
quantum-ewf-qsci pipeline.  The contract specifies exact HDF5 paths, shapes,
dtypes, and index ordering conventions.

HDF5 Layout
-----------
::

    /
    ├── cluster/
    │   ├── heff       float64 (norb, norb)     1-body effective Hamiltonian
    │   ├── eris       float64 (norb, norb,      2-body integrals (physicist)
    │   │                        norb, norb)     ordering: <pq|rs>
    │   ├── e_core     float64 scalar            Core energy constant
    │   ├── t2_amps    float64 (no, no, nv, nv)  MP2 t2 ansatz seed (optional)
    │   ├── eps_mo     float64 (norb,)           Canonical MO energies (optional)
    │   └── C_mo       float64 (norb, norb)      Cluster→canonical MOs (optional)
    └── meta/
        ├── norb        int64 scalar             Number of spatial orbitals
        ├── n_elec      int64 scalar             Cluster electron count (optional)
        ├── source      string                   "vayesta_mock" or "vayesta"
        └── molecule    string                   Molecule identifier

The ``t2_amps`` / ``eps_mo`` / ``C_mo`` datasets and ``meta/n_elec`` are written
by the real Vayesta node (ewf-decompose >= 1.2.0) in the canonical cluster MO
basis and consumed by qsci-prep as the ansatz seed; ``make_mock_cluster`` omits
them.

Index Conventions
-----------------
- **heff[p,q]** : one-body effective Hamiltonian in MO basis, h_{pq}.
  Symmetric: heff[p,q] == heff[q,p].
- **eris[p,q,r,s]** : two-body integrals in **physicist** ordering
  (〈pq|rs〉 convention, matching OpenFermion ``InteractionOperator``).
  Chemist→physicist reorder (applied by ``make_mock_cluster`` before writing):
  ``eris_phys[p,q,r,s] = eris_chem[p,r,q,s]``.
  For real MO integrals, 8-fold symmetry holds.
- **e_core** : scalar constant term (nuclear repulsion + core corrections).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import numpy as np


# ── Schema constants ─────────────────────────────────────────────────────────

CLUSTER_GROUP = "cluster"
META_GROUP = "meta"

HEFF_DS = "cluster/heff"
ERIS_DS = "cluster/eris"
ECORE_DS = "cluster/e_core"
T2_DS = "cluster/t2_amps"
EPS_MO_DS = "cluster/eps_mo"
C_MO_DS = "cluster/C_mo"
NORB_DS = "meta/norb"
NELEC_DS = "meta/n_elec"
SOURCE_DS = "meta/source"
MOLECULE_DS = "meta/molecule"

DTYPE = np.float64

# Valid source values
SOURCE_VAYESTA_MOCK = "vayesta_mock"
SOURCE_VAYESTA = "vayesta"


# ── I/O helpers ──────────────────────────────────────────────────────────────


def load_cluster(path: str | Path) -> dict[str, Any]:
    """Load a cluster Hamiltonian HDF5 file into memory.

    Parameters
    ----------
    path : str or Path
        Path to an HDF5 file conforming to the cluster Hamiltonian contract.

    Returns
    -------
    dict
        Keys:
        - ``heff`` : (norb, norb) float64 ndarray
        - ``eris`` : (norb, norb, norb, norb) float64 ndarray
        - ``e_core`` : float64 scalar
        - ``meta`` : dict with ``norb`` (int), ``source`` (str), ``molecule`` (str)

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    KeyError
        If a required dataset is missing from the file.
    """
    with h5py.File(path, "r") as f:
        heff = f[HEFF_DS][:]
        eris = f[ERIS_DS][:]
        e_core = f[ECORE_DS][()]
        norb = int(f[NORB_DS][()])
        source = f[SOURCE_DS][()].decode("utf-8")
        molecule = f[MOLECULE_DS][()].decode("utf-8")
        # Optional MP2 ansatz seed + electron count (real Vayesta output >= 1.2.0)
        t2_amps = f[T2_DS][:] if T2_DS in f else None
        eps_mo = f[EPS_MO_DS][:] if EPS_MO_DS in f else None
        c_mo = f[C_MO_DS][:] if C_MO_DS in f else None
        n_elec = int(f[NELEC_DS][()]) if NELEC_DS in f else None

    out: dict[str, Any] = {
        "heff": np.asarray(heff, dtype=DTYPE),
        "eris": np.asarray(eris, dtype=DTYPE),
        "e_core": np.float64(e_core),
        "meta": {
            "norb": norb,
            "source": source,
            "molecule": molecule,
        },
    }
    if n_elec is not None:
        out["meta"]["n_elec"] = n_elec
    if t2_amps is not None:
        out["t2_amps"] = np.asarray(t2_amps, dtype=DTYPE)
    if eps_mo is not None:
        out["eps_mo"] = np.asarray(eps_mo, dtype=DTYPE)
    if c_mo is not None:
        out["C_mo"] = np.asarray(c_mo, dtype=DTYPE)
    return out


def write_cluster(
    path: str | Path,
    heff: np.ndarray,
    eris: np.ndarray,
    e_core: float,
    t2_amps: np.ndarray | None = None,
    eps_mo: np.ndarray | None = None,
    c_mo: np.ndarray | None = None,
    **meta,
) -> None:
    """Write a cluster Hamiltonian to HDF5 following the contract schema.

    Parameters
    ----------
    path : str or Path
        Output HDF5 file path.
    heff : (norb, norb) ndarray
        One-body effective Hamiltonian, must be float64 and symmetric.
    eris : (norb, norb, norb, norb) ndarray
        Two-body integrals in physicist ordering, float64.
    e_core : float
        Core energy constant.
    **meta
        Keyword metadata persisted under ``/meta/``.
        Required keys: ``norb`` (int), ``source`` (str), ``molecule`` (str).
    """
    heff = np.asarray(heff, dtype=DTYPE)
    eris = np.asarray(eris, dtype=DTYPE)
    e_core = np.float64(e_core)

    norb = heff.shape[0]
    if meta.get("norb") is None:
        meta["norb"] = norb

    with h5py.File(path, "w") as f:
        f.create_dataset(HEFF_DS, data=heff)
        f.create_dataset(ERIS_DS, data=eris)
        f.create_dataset(ECORE_DS, data=e_core)
        f.create_dataset(NORB_DS, data=np.int64(meta.get("norb", norb)))
        f.create_dataset(SOURCE_DS, data=np.bytes_(meta.get("source", SOURCE_VAYESTA_MOCK)))
        f.create_dataset(MOLECULE_DS, data=np.bytes_(meta.get("molecule", "unknown")))
        if meta.get("n_elec") is not None:
            f.create_dataset(NELEC_DS, data=np.int64(meta["n_elec"]))
        if t2_amps is not None:
            f.create_dataset(T2_DS, data=np.asarray(t2_amps, dtype=DTYPE))
        if eps_mo is not None:
            f.create_dataset(EPS_MO_DS, data=np.asarray(eps_mo, dtype=DTYPE))
        if c_mo is not None:
            f.create_dataset(C_MO_DS, data=np.asarray(c_mo, dtype=DTYPE))


# ── Mock generator ───────────────────────────────────────────────────────────


def make_mock_cluster(
    molecule: str = "H 0 0 0; H 0 0 0.7414",
    basis: str = "sto-3g",
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Generate a valid cluster Hamiltonian HDF5 from a small PySCF computation.

    No Vayesta dependency required.  A restricted Hartree-Fock (RHF) calculation
    is run on *molecule* in *basis*, the AO integrals are transformed to the MO
    basis, and the result is written to *output_path* (if provided) and returned
    as a dict.

    The mock treats the **full molecule as a single cluster**, so ``heff`` is
    the bare one-body MO Hamiltonian (``h1_mo``).

    Parameters
    ----------
    molecule : str
        PySCF atom string, e.g. ``"H 0 0 0; H 0 0 0.7414"``.
    basis : str
        Basis set name recognised by PySCF, e.g. ``"sto-3g"``.
    output_path : str or Path or None
        If given, write the HDF5 file to this path.

    Returns
    -------
    dict
        Same structure as ``load_cluster`` (heff, eris, e_core, meta).
    """
    from pyscf import gto, scf

    # --- Build molecule & run RHF ---
    mol = gto.M(atom=molecule, basis=basis, verbose=0)
    mf = scf.RHF(mol)
    mf.kernel()

    # --- AO integrals ---
    h1_ao = mol.intor("int1e_kin") + mol.intor("int1e_nuc")  # T + V_nuc
    eri_ao = mol.intor("int2e")                               # (ij|kl) chemist
    e_nuc = mol.energy_nuc()                                   # nuclear repulsion

    # --- MO coefficients ---
    C = mf.mo_coeff                    # (nao, norb)

    # --- Transform 1-body to MO ---
    heff_mo = np.asarray(C.T @ h1_ao @ C, dtype=DTYPE)

    # --- Transform 2-body to MO (still chemist notation) ---
    # pyscf.ao2mo is unusable in this image (lib.einsum/numpy version
    # incompatibility), so use the equivalent BLAS-backed numpy contraction.
    eri_mo_chem = np.asarray(
        np.einsum("pi,qj,rk,sl,pqrs->ijkl", C, C, C, C, eri_ao, optimize=True),
        dtype=DTYPE,
    )

    # --- Chemist → physicist reorder ---
    #   h2[p,q,r,s] = eris[p,r,q,s]   (transpose axes 1↔2)
    #   See OpenFermion ``get_chemist_two_body_coefficients`` for the inverse.
    eri_mo_phys = eri_mo_chem.transpose(0, 2, 1, 3).copy()

    # --- Core energy ---
    e_core = np.float64(e_nuc)

    # --- Metadata ---
    norb = mol.nao
    n_elec = mol.nelectron
    mol_id = _mol_identifier(mol)

    meta = {
        "norb": norb,
        "source": SOURCE_VAYESTA_MOCK,
        "molecule": mol_id,
        "basis": basis,
        "nelectron": n_elec,
    }

    # --- Write if path given ---
    if output_path is not None:
        write_cluster(
            output_path,
            heff=heff_mo,
            eris=eri_mo_phys,
            e_core=e_core,
            **meta,
        )

    return {
        "heff": heff_mo,
        "eris": eri_mo_phys,
        "e_core": e_core,
        "meta": meta,
    }


# ── Internal helpers ─────────────────────────────────────────────────────────


def _mol_identifier(mol) -> str:
    """Build a compact molecule identifier string, e.g. ``"H2_sto3g"``."""
    atoms = [mol.atom_symbol(i) for i in range(mol.natm)]
    counts: dict[str, int] = {}
    for a in atoms:
        counts[a] = counts.get(a, 0) + 1
    formula = "".join(f"{el}{counts[el] if counts[el] > 1 else ''}" for el in sorted(counts))
    return f"{formula}_{mol.basis}"
