# XC

# XC

Parameters needed for the calculation of the eXchange and Correlation potential [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1298)]

Subsections

  - [ADIABATIC_RESCALING](XC/ADIABATIC_RESCALING.html)
  - [GCP_POTENTIAL](XC/GCP_POTENTIAL.html)
  - [HF](XC/HF.html)
  - [HFX_KERNEL](XC/HFX_KERNEL.html)
  - [VDW_POTENTIAL](XC/VDW_POTENTIAL.html)
  - [WF_CORRELATION](XC/WF_CORRELATION.html)
  - [XC_FUNCTIONAL](XC/XC_FUNCTIONAL.html)
  - [XC_GRID](XC/XC_GRID.html)
  - [XC_KERNEL](XC/XC_KERNEL.html)
  - [XC_POTENTIAL](XC/XC_POTENTIAL.html)

## Keywords

  - 2ND_DERIV_ANALYTICAL

  - 3RD_DERIV_ANALYTICAL

  - DENSITY_CUTOFF

  - DENSITY_SMOOTH_CUTOFF_RANGE

  - GRADIENT_CUTOFF

  - NSTEPS

  - STEP_SIZE

  - TAU_CUTOFF

## Keyword descriptions

2ND_DERIV_ANALYTICAL _: logical_ _ = T _
    

**Lone keyword:** `T`

**Usage:** _2ND_DERIV_ANALYTICAL logical_

Use analytical formulas or finite differences for 2nd derivatives of XC [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1371)]

3RD_DERIV_ANALYTICAL _: logical_ _ = T _
    

**Lone keyword:** `T`

**Usage:** _3RD_DERIV_ANALYTICAL logical_

Use analytical formulas or finite differences for 3rd derivatives of XC [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1378)]

DENSITY_CUTOFF _: real_ _ = 1.00000000E-010 _
    

**Usage:** _density_cutoff 1.e-11_

The cutoff on the density used by the xc calculation [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1304)]

DENSITY_SMOOTH_CUTOFF_RANGE _: real_ _ = 0.00000000E+000 _
    

**Usage:** _DENSITY_SMOOTH_CUTOFF_RANGE {real}_

Parameter for the smoothing procedure in xc calculation [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1317)]

GRADIENT_CUTOFF _: real_ _ = 1.00000000E-010 _
    

**Usage:** _gradient_cutoff 1.e-11_

The cutoff on the gradient of the density used by the xc calculation [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1310)]

NSTEPS _: integer_ _ = 3 _
    

**Usage:** _NSTEPS 4_

Number of steps to consider in each direction for the numerical evaluation of XC derivatives. Must be a value from 1 to 4 (Default: 3). [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1392)]

STEP_SIZE _: real_ _ = 1.00000000E-003 _
    

**Usage:** _STEP_SIZE 1.0E-3_

Step size in terms of the first order potential for the numerical evaluation of XC derivatives [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1385)]

TAU_CUTOFF _: real_ _ = 1.00000000E-010 _
    

**Usage:** _tau_cutoff 1.e-11_

The cutoff on tau used by the xc calculation [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_xc.F#L1323)]
