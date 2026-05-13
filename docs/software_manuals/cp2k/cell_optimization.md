# CELL_OPT

# CELL_OPT

This section sets the environment for the optimization of the simulation cell. As is noted in FORCE_EVAL/SUBSYS/CELL, the program convention is that the first cell vector A lies along the X-axis and the second cell vector B is in the XY plane, such that the cell vector matrix is a lower triangle. The algorithm support for updating the three upper triangular components during a cell optimization is not complete or tested, so the input structure has to be prepared accordingly with these three components precisely 0 even for cases like the primitive rhombohedral cell of the FCC lattice. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L1015)]

Subsections

  - [BFGS](CELL_OPT/BFGS.html)
  - [CG](CELL_OPT/CG.html)
  - [LBFGS](CELL_OPT/LBFGS.html)
  - [PRINT](CELL_OPT/PRINT.html)

## Keywords

  - CONSTRAINT

  - EPS_SYMMETRY

  - EXTERNAL_PRESSURE

  - KEEP_ANGLES

  - KEEP_SPACE_GROUP

  - KEEP_SYMMETRY

  - KEEP_VOLUME

  - MAX_DR

  - MAX_FORCE

  - MAX_ITER

  - OPTIMIZER

  - PRESSURE_TOLERANCE

  - RMS_DR

  - RMS_FORCE

  - SHOW_SPACE_GROUP

  - SPGR_PRINT_ATOMS

  - STEP_START_VAL

  - SYMM_EXCLUDE_RANGE

  - SYMM_REDUCTION

  - TYPE

## Keyword descriptions

CONSTRAINT _: enum_ _ = NONE _
    

**Usage:** _CONSTRAINT (none|x|y|z|xy|xz|yz)_

**Valid values:**

  - `NONE` Fix nothing

  - `X` Fix only x component

  - `Y` Fix only y component

  - `Z` Fix only z component

  - `XY` Fix x and y component

  - `XZ` Fix x and z component

  - `YZ` Fix y and z component

Imposes a constraint on the pressure tensor by fixing the specified cell components. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L1089)]

EPS_SYMMETRY _: real_ _ = 1.00000000E-004 _
    

**Usage:** _EPS_SYMMETRY {REAL}_

Accuracy for space group determination. EPS_SYMMETRY is dimensionless. Roughly speaking, two scaled (fractional) atomic positions v1, v2 are considered identical if |v1 - v2| < EPS_SYMMETRY. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L894)]

EXTERNAL_PRESSURE _: real[ ]__ = 1.00000000E+002 0.00000000E+000 0.00000000E+000 0.00000000E+000 1.00000000E+002 0.00000000E+000 0.00000000E+000 0.00000000E+000 1.00000000E+002 [bar]_
    

**Usage:** _EXTERNAL_PRESSURE {REAL} .. {REAL}_

Specifies the external pressure (1 value or the full 9 components of the pressure tensor) applied during the cell optimization. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L1047)]

KEEP_ANGLES _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _KEEP_ANGLES TRUE_

Keep angles between the cell vectors constant, but allow the lengths of the cell vectors to change independently during cell optimization. This is implemented by projecting out the components of angles in the cell gradient before the cell is updated. Albeit general, this is most useful for triclinic cells; to enforce higher symmetry, see KEEP_SYMMETRY. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L1066)]

KEEP_SPACE_GROUP _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _KEEP_SPACE_GROUP .TRUE._

Detect space group of the system and preserve it during optimization. The space group symmetry is applied to coordinates, forces, and the stress tensor. It works for supercell. It does not affect/reduce computational cost. Use EPS_SYMMETRY to adjust the detection threshold. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L871)]

KEEP_SYMMETRY _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _KEEP_SYMMETRY TRUE_

Keep the requested initial cell symmetry as specified in the FORCE_EVAL/SUBSYS/CELL section during cell optimization. This is implemented by removing symmetry-breaking components and taking averages of components if necessary in the cell gradient before the cell is updated. To enforce the space group (which requires spglib package), see KEEP_SPACE_GROUP. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L1077)]

KEEP_VOLUME _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _KEEP_VOLUME TRUE_

Keep the volume of the cell constant during cell optimization. This is implemented by comparing the cell volumes and scaling the new cell vectors just before updating the cell information, and can be used together with KEEP_ANGLES or KEEP_SYMMETRY. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L1057)]

MAX_DR _: real_ _ = 3.00000000E-003 [bohr]_
    

**Usage:** _MAX_DR {real}_

Convergence criterion for the maximum geometry change between the current and the last optimizer iteration. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L833)]

MAX_FORCE _: real_ _ = 4.50000000E-004 [bohr^-1*hartree]_
    

**Usage:** _MAX_FORCE {real}_

Convergence criterion for the maximum force component of the current configuration. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L841)]

MAX_ITER _: integer_ _ = 200 _
    

**Usage:** _MAX_ITER {integer}_

Specifies the maximum number of geometry optimization steps. One step might imply several force evaluations for the CG and LBFGS optimizers. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L825)]

OPTIMIZER _: enum_ _ = BFGS _
    

**Aliases:** MINIMIZER

**Usage:** _OPTIMIZER {BFGS|LBFGS|CG}_

**Valid values:**

  - `BFGS` Most efficient minimizer, but only for ""'small""' systems, as it relies on diagonalization of a full Hessian matrix

  - `LBFGS` Limited-memory variant of BFGS suitable for large systems. Not as well fine-tuned but can be more robust.

  - `CG` conjugate gradients, robust minimizer (depending on the line search) also OK for large systems

**References:** [Byrd1995](../../bibliography.html#byrd1995)

Specify which method to use to perform a geometry optimization. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L809)]

PRESSURE_TOLERANCE _: real_ _ = 1.00000000E+002 [bar]_
    

**Usage:** _PRESSURE_TOLERANCE {REAL}_

Specifies the Pressure tolerance (compared to the external pressure) to achieve during the cell optimization. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L1105)]

RMS_DR _: real_ _ = 1.50000000E-003 [bohr]_
    

**Usage:** _RMS_DR {real}_

Convergence criterion for the root mean square (RMS) geometry change between the current and the last optimizer iteration. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L848)]

RMS_FORCE _: real_ _ = 3.00000000E-004 [bohr^-1*hartree]_
    

**Usage:** _RMS_FORCE {real}_

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

The starting step value for the CELL_OPT module. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L863)]

SYMM_EXCLUDE_RANGE _: integer[2]_
    

**Keyword can be repeated.**

**Usage:** _SYMM_EXCLUDE_RANGE {Int} {Int}_

Range of atoms to exclude from space group symmetry. These atoms are excluded from both identification and enforcement. This keyword can be repeated. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L916)]

SYMM_REDUCTION _: real[3]__ = 0.00000000E+000 0.00000000E+000 0.00000000E+000 _
    

**Usage:** _SYMM_REDUCTION 0.0 0.0 0.0_

Direction of the external static electric field. Some symmetry operations are not compatible with the direction of an electric field. These operations are used when enforcing the space group. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L904)]

TYPE _: enum_ _ = DIRECT_CELL_OPT _
    

**Usage:** _TYPE (DIRECT_CELL_OPT|GEO_OPT|MD)_

**Valid values:**

  - `DIRECT_CELL_OPT` Performs a geometry and cell optimization at the same time. The stress tensor is computed at every step

  - `GEO_OPT` Performs a geometry optimization between cell optimization steps. The MOTION/GEO_OPT section must be defined. The stress tensor is computed at the optimized geometry.

  - `MD` Performs a molecular dynamics run for computing the stress tensor used for the cell optimization. The MOTION/MD section must be defined.

Specify which kind of method to use for the optimization of the simulation cell [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/start/input_cp2k_motion.F#L1029)]
