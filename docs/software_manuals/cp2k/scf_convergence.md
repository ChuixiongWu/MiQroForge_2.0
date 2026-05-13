# SCF

# SCF

Parameters needed to perform an SCF run. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L94)]

Subsections

  - [DIAGONALIZATION](SCF/DIAGONALIZATION.html)
  - [MIXING](SCF/MIXING.html)
  - [MOM](SCF/MOM.html)
  - [OT](SCF/OT.html)
  - [OUTER_SCF](SCF/OUTER_SCF.html)
  - [PRINT](SCF/PRINT.html)
  - [SMEAR](SCF/SMEAR.html)

## Keywords

  - ADDED_MOS

  - CHOLESKY

  - EPS_DIIS

  - EPS_EIGVAL

  - EPS_LUMO

  - **EPS_SCF**

  - EPS_SCF_HISTORY

  - FORCE_SCF_CALCULATION

  - IGNORE_CONVERGENCE_FAILURE

  - LEVEL_SHIFT

  - MAX_DIIS

  - MAX_ITER_LUMO

  - **MAX_SCF**

  - MAX_SCF_HISTORY

  - NCOL_BLOCK

  - NROW_BLOCK

  - ROKS_F

  - ROKS_PARAMETERS

  - ROKS_SCHEME

  - **SCF_GUESS**

## Keyword descriptions

ADDED_MOS _: integer[ ]__ = 0 _
    

**Usage:** _ADDED_MOS_

Number of additional molecular orbitals added for each spin channel. This is commonly needed for smearing, excited-state, or post-Hartree-Fock calculations. Use -1 to add all available orbitals. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L239)]

CHOLESKY _: enum_ _ = RESTORE _
    

**Usage:** _CHOLESKY REDUCE_

**Valid values:**

  - `OFF` The cholesky algorithm is not used

  - `REDUCE` Reduce is called

  - `RESTORE` Reduce is replaced by two restore

  - `INVERSE` Restore uses operator multiply by inverse of the triangular matrix

  - `INVERSE_DBCSR` Like inverse, but matrix stored as dbcsr, sparce matrix algebra used when possible

If the cholesky method should be used for computing the inverse of S, and in this case calling which Lapack routines [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L181)]

EPS_DIIS _: real_ _ = 1.00000000E-001 _
    

**Usage:** _EPS_DIIS 5.0e-2_

Threshold on the convergence to start using DIAG/DIIS or OT/DIIS. Default for OT/DIIS is never to switch. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L200)]

EPS_EIGVAL _: real_ _ = 1.00000000E-005 _
    

**Usage:** _EPS_EIGVAL 1.0_

Throw away linear combinations of basis functions with a small eigenvalue in S [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L194)]

EPS_LUMO _: real_ _ = 1.00000000E-005 _
    

**Aliases:** EPS_LUMOS

**Usage:** _EPS_LUMO 1.0E-6_

Target accuracy for the calculation of the LUMO energies with the OT eigensolver. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L134)]

EPS_SCF _: real_ _ = 1.00000000E-005 _
    

**Usage:** _EPS_SCF 1.e-6_

**Mentions:** "­[Molecular Dynamics](../../../methods/sampling/molecular_dynamics.html), "­[Monte Carlo](../../../methods/sampling/monte_carlo.html)

Target convergence threshold for the inner SCF cycle. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L169)]

EPS_SCF_HISTORY _: real_ _ = 0.00000000E+000 _
    

**Aliases:** EPS_SCF_HIST

**Lone keyword:** `1.00000000E-005`

**Usage:** _EPS_SCF_HISTORY 1.e-5_

Target accuracy for the SCF convergence after the history pipeline is filled. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L175)]

FORCE_SCF_CALCULATION _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _FORCE_SCF_CALCULATION logical_value_

Request a SCF type solution even for nonSCF methods. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L297)]

IGNORE_CONVERGENCE_FAILURE _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _IGNORE_CONVERGENCE_FAILURE logical_value_

If true, only a warning is issued if an SCF iteration has not converged. By default, a run is aborted if the required convergence criteria have not been achieved. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L287)]

LEVEL_SHIFT _: real_ _ = 0.00000000E+000 [hartree]_
    

**Aliases:** LSHIFT

**Usage:** _LEVEL_SHIFT 0.1_

Use level shifting to improve convergence [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L160)]

MAX_DIIS _: integer_ _ = 4 _
    

**Aliases:** MAX_DIIS_BUFFER_SIZE

**Usage:** _MAX_DIIS 3_

Maximum number of DIIS vectors to be used [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L153)]

MAX_ITER_LUMO _: integer_ _ = 299 _
    

**Aliases:** MAX_ITER_LUMOS

**Usage:** _MAX_ITER_LUMO 100_

Maximum number of iterations for the calculation of the LUMO energies with the OT eigensolver. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L126)]

MAX_SCF _: integer_ _ = 50 _
    

**Usage:** _MAX_SCF 200_

**Mentions:** "­[Monte Carlo](../../../methods/sampling/monte_carlo.html)

Maximum number of inner SCF iterations for one electronic optimization. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L141)]

MAX_SCF_HISTORY _: integer_ _ = 0 _
    

**Aliases:** MAX_SCF_HIST

**Lone keyword:** `1`

**Usage:** _MAX_SCF_HISTORY 1_

Maximum number of SCF iterations after the history pipeline is filled [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L147)]

NCOL_BLOCK _: integer_ _ = 32 _
    

**Usage:** _NCOL_BLOCK 31_

Sets the number of columns in a scalapack block [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L233)]

NROW_BLOCK _: integer_ _ = 32 _
    

**Usage:** _NROW_BLOCK 31_

sets the number of rows in a scalapack block [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L227)]

ROKS_F _: real_ _ = 5.00000000E-001 _
    

**Aliases:** F_ROKS

**Usage:** _ROKS_F 1/2_

Allows to define the parameter f for the general ROKS scheme. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L259)]

ROKS_PARAMETERS _: real[6]__ = -5.00000000E-001 1.50000000E+000 5.00000000E-001 5.00000000E-001 1.50000000E+000 -5.00000000E-001 _
    

**Aliases:** ROKS_PARAMETER

**Usage:** _ROKS_PARAMETERS 1/2 1/2 1/2 1/2 1/2 1/2_

Allows to define all parameters for the high-spin ROKS scheme explicitly. The full set of 6 parameters has to be specified in the order acc, bcc, aoo, boo, avv, bvv [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L272)]

ROKS_SCHEME _: enum_ _ = HIGH-SPIN _
    

**Usage:** _ROKS_SCHEME HIGH-SPIN_

**Valid values:**

  - `GENERAL`

  - `HIGH-SPIN`

Selects the ROKS scheme when ROKS is applied. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L247)]

SCF_GUESS _: enum_ _ = ATOMIC _
    

**Usage:** _SCF_GUESS RESTART_

**Valid values:**

  - `ATOMIC` Generate an atomic density using the atomic code and internal default values

  - `RESTART` Use the RESTART file as an initial guess (and ATOMIC if not present).

  - `RANDOM` Use random wavefunction coefficients.

  - `CORE` Diagonalize the core hamiltonian for an initial guess.

  - `HISTORY_RESTART` Extrapolated from previous RESTART files.

  - `MOPAC` Use same guess as MOPAC for semi-empirical methods or a simple diagonal density matrix for other methods

  - `EHT` Use the EHT (gfn0-xTB) code to generate an initial wavefunction.

  - `SPARSE` Generate a sparse wavefunction using the atomic code (for OT based methods)

  - `NONE` Skip initial guess (only for non-self consistent methods).

**Mentions:** "­[Molecular Dynamics](../../../methods/sampling/molecular_dynamics.html)

Selects how the initial wavefunction or density matrix is generated. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_scf.F#L208)]
