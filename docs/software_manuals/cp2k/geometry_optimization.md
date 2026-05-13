# GEO_OPT

# GEO_OPT

This section sets the environment of the geometry optimizer. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L97)]

Subsections

  - [BFGS](GEO_OPT/BFGS.html)
  - [CG](GEO_OPT/CG.html)
  - [LBFGS](GEO_OPT/LBFGS.html)
  - [PRINT](GEO_OPT/PRINT.html)
  - [TRANSITION_STATE](GEO_OPT/TRANSITION_STATE.html)

## Keywords

  - EPS_SYMMETRY

  - KEEP_SPACE_GROUP

  - **MAX_DR**

  - **MAX_FORCE**

  - **MAX_ITER**

  - **OPTIMIZER**

  - RMS_DR

  - **RMS_FORCE**

  - SHOW_SPACE_GROUP

  - SPGR_PRINT_ATOMS

  - STEP_START_VAL

  - SYMM_EXCLUDE_RANGE

  - SYMM_REDUCTION

  - **TYPE**

## Keyword descriptions

EPS_SYMMETRY _: real_ _ = 1.00000000E-004 _
    

**Usage:** _EPS_SYMMETRY {REAL}_

Accuracy for space group determination. EPS_SYMMETRY is dimensionless. Roughly speaking, two scaled (fractional) atomic positions v1, v2 are considered identical if |v1 - v2| < EPS_SYMMETRY. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L894)]

KEEP_SPACE_GROUP _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _KEEP_SPACE_GROUP .TRUE._

Detect space group of the system and preserve it during optimization. The space group symmetry is applied to coordinates, forces, and the stress tensor. It works for supercell. It does not affect/reduce computational cost. Use EPS_SYMMETRY to adjust the detection threshold. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L871)]

MAX_DR _: real_ _ = 3.00000000E-003 [bohr]_
    

**Usage:** _MAX_DR {real}_

**Mentions:** "­[Geometry Optimisation](../../methods/optimization/geometry.html)

Convergence criterion for the maximum geometry change between the current and the last optimizer iteration. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L833)]

MAX_FORCE _: real_ _ = 4.50000000E-004 [bohr^-1*hartree]_
    

**Usage:** _MAX_FORCE {real}_

**Mentions:** "­[Geometry Optimisation](../../methods/optimization/geometry.html), "­[Simulating Vibronic Effects in Optical Spectra](../../methods/properties/optical/vibronicspec.html)

Convergence criterion for the maximum force component of the current configuration. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L841)]

MAX_ITER _: integer_ _ = 200 _
    

**Usage:** _MAX_ITER {integer}_

**Mentions:** "­[Geometry Optimisation](../../methods/optimization/geometry.html)

Specifies the maximum number of geometry optimization steps. One step might imply several force evaluations for the CG and LBFGS optimizers. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L825)]

OPTIMIZER _: enum_ _ = BFGS _
    

**Aliases:** MINIMIZER

**Usage:** _OPTIMIZER {BFGS|LBFGS|CG}_

**Valid values:**

  - `BFGS` Most efficient minimizer, but only for ""'small""' systems, as it relies on diagonalization of a full Hessian matrix

  - `LBFGS` Limited-memory variant of BFGS suitable for large systems. Not as well fine-tuned but can be more robust.

  - `CG` conjugate gradients, robust minimizer (depending on the line search) also OK for large systems

**References:** [Byrd1995](../../bibliography.html#byrd1995)

**Mentions:** "­[Geometry Optimisation](../../methods/optimization/geometry.html)

Specify which method to use to perform a geometry optimization. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L809)]

RMS_DR _: real_ _ = 1.50000000E-003 [bohr]_
    

**Usage:** _RMS_DR {real}_

Convergence criterion for the root mean square (RMS) geometry change between the current and the last optimizer iteration. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L848)]

RMS_FORCE _: real_ _ = 3.00000000E-004 [bohr^-1*hartree]_
    

**Usage:** _RMS_FORCE {real}_

**Mentions:** "­[Geometry Optimisation](../../methods/optimization/geometry.html)

Convergence criterion for the root mean square (RMS) force of the current configuration. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L856)]

SHOW_SPACE_GROUP _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _SHOW_SPACE_GROUP .TRUE._

Detect and show space group of the system after optimization. It works for supercell. It does not affect/reduce computational cost. Use EPS_SYMMETRY to adjust the detection threshold. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L883)]

SPGR_PRINT_ATOMS _: logical_ _ = F _
    

**Lone keyword:** `T`

Print equivalent atoms list for each space group symmetry operation. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L925)]

STEP_START_VAL _: integer_ _ = 0 _
    

**Usage:** _step_start_val_

The starting step value for the GEO_OPT module. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L863)]

SYMM_EXCLUDE_RANGE _: integer[2]_
    

**Keyword can be repeated.**

**Usage:** _SYMM_EXCLUDE_RANGE {Int} {Int}_

Range of atoms to exclude from space group symmetry. These atoms are excluded from both identification and enforcement. This keyword can be repeated. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L916)]

SYMM_REDUCTION _: real[3]__ = 0.00000000E+000 0.00000000E+000 0.00000000E+000 _
    

**Usage:** _SYMM_REDUCTION 0.0 0.0 0.0_

Direction of the external static electric field. Some symmetry operations are not compatible with the direction of an electric field. These operations are used when enforcing the space group. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L904)]

TYPE _: enum_ _ = MINIMIZATION _
    

**Usage:** _TYPE (MINIMIZATION|TRANSITION_STATE)_

**Valid values:**

  - `MINIMIZATION` Performs a geometry minimization.

  - `TRANSITION_STATE` Performs a transition state optimization.

**Mentions:** "­[Geometry Optimisation](../../methods/optimization/geometry.html)

Specify which kind of geometry optimization to perform [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L796)]
