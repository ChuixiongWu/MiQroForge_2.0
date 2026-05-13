# VIBRATIONAL_ANALYSIS

# VIBRATIONAL_ANALYSIS

Section to setup parameters to perform a Normal Modes, vibrational, or phonon analysis. Vibrations are computed using finite differences, which implies a very tight (e.g. 1E-8) threshold is needed for EPS_SCF to get accurate low frequencies. The analysis assumes a stationary state (minimum or TS), i.e. tight geometry optimization (MAX_FORCE) is needed as well. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L66)]

Subsections

  - [MODE_SELECTIVE](VIBRATIONAL_ANALYSIS/MODE_SELECTIVE.html)
  - [PRINT](VIBRATIONAL_ANALYSIS/PRINT.html)

## Keywords

  - DX

  - FULLY_PERIODIC

  - INTENSITIES

  - **NPROC_REP**

  - PROC_DIST_TYPE

  - TC_PRESSURE

  - TC_TEMPERATURE

  - THERMOCHEMISTRY

## Keyword descriptions

DX _: real_ _ = 1.00000000E-002 [bohr]_
    

Specify the increment to be used to construct the HESSIAN with finite difference method [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L75)]

FULLY_PERIODIC _: logical_ _ = F _
    

**Lone keyword:** `T`

Avoids to clean rotations from the Hessian matrix. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L103)]

INTENSITIES _: logical_ _ = F _
    

**Lone keyword:** `T`

Calculation of the IR/Raman-Intensities. Calculation of dipoles and/or polarizabilities have to be specified explicitly in DFT/PRINT/MOMENTS and/or PROPERTIES/LINRES/POLAR [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L109)]

NPROC_REP _: integer_ _ = 1 _
    

**Mentions:** "­[Simulating Vibronic Effects in Optical Spectra](../methods/properties/optical/vibronicspec.html)

Specify the number of processors to be used per replica environment (for parallel runs). In case of mode selective calculations more than one replica will start a block Davidson algorithm to track more than only one frequency [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L82)]

PROC_DIST_TYPE _: enum_ _ = BLOCKED _
    

**Usage:** _PROC_DIST_TYPE (INTERLEAVED|BLOCKED)_

**Valid values:**

  - `INTERLEAVED` Interleaved distribution

  - `BLOCKED` Blocked distribution

Specify the topology of the mapping of processors into replicas. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L91)]

TC_PRESSURE _: real_ _ = 1.01325000E+005 [Pa]_
    

Pressure for the calculation of the thermochemical data [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L131)]

TC_TEMPERATURE _: real_ _ = 2.73150000E+002 [K]_
    

**Usage:** _tc_temperature 325.0_

Temperature for the calculation of the thermochemical data [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L124)]

THERMOCHEMISTRY _: logical_ _ = F _
    

**Lone keyword:** `T`

Calculation of the thermochemical data. Valid for molecules in the gas phase. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/motion/input_cp2k_vib.F#L118)]
