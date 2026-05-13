# DFT

# DFT

Controls electronic-structure settings for Quickstep and related Gaussian-basis DFT methods. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L128)]

## Keywords

  - **AUTO_BASIS**

  - **BASIS_SET_FILE_NAME**

  - **CHARGE**

  - CORE_CORR_DIP

  - MULTIPLICITY

  - PLUS_U_METHOD

  - **POTENTIAL_FILE_NAME**

  - RELAX_MULTIPLICITY

  - ROKS

  - **SORT_BASIS**

  - SUBCELLS

  - SURFACE_DIPOLE_CORRECTION

  - SURF_DIP_DIR

  - SURF_DIP_POS

  - SURF_DIP_SWITCH

  - UKS

  - **WFN_RESTART_FILE_NAME**

## Keyword descriptions

AUTO_BASIS _: string[ ]__ = X X _
    

**Keyword can be repeated.**

**Usage:** _AUTO_BASIS {basis_type} {basis_size}_

**Mentions:** â­[Preliminaries](../../methods/post_hartree_fock/preliminaries.html), â­[X-Ray Absorption from TDDFT](../../methods/properties/x-ray/tddft.html)

Specify size of automatically generated auxiliary (RI) basis sets: Options={small,medium,large,huge} [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L252)]

BASIS_SET_FILE_NAME _: string_ _ = BASIS_SET _
    

**Keyword can be repeated.**

**Usage:** _BASIS_SET_FILE_NAME_

**Mentions:** â­[Basis Sets](../../methods/dft/basis_sets.html)

Name of a basis-set library file, optionally including a path. This keyword can be repeated to search several basis-set files. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L134)]

CHARGE _: integer_ _ = 0 _
    

**Usage:** _CHARGE -1_

**Mentions:** â­[RESP Charges](../../methods/properties/resp_charges.html)

The total charge of the system [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L193)]

CORE_CORR_DIP _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _CORE_CORR_DIP .TRUE._

If the total CORE_CORRECTION is non-zero and surface dipole correction is switched on, presence of this keyword will adjust electron density via MO occupation to reflect the total CORE_CORRECTION. The default value is .FALSE. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L311)]

MULTIPLICITY _: integer_ _ = 0 _
    

**Aliases:** MULTIP

**Usage:** _MULTIPLICITY 3_

Two times the total spin plus one. Specify 3 for a triplet, 4 for a quartet, and so on. Default is 1 (singlet) for an even number and 2 (doublet) for an odd number of electrons. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L181)]

PLUS_U_METHOD _: enum_ _ = MULLIKEN _
    

**Usage:** _PLUS_U_METHOD Lowdin_

**Valid values:**

  - `LOWDIN` Method based on Lowdin population analysis (computationally expensive, since the diagonalization of the overlap matrix is required, but possibly more robust than Mulliken)

  - `MULLIKEN` Method based on Mulliken population analysis using the net AO and overlap populations (computationally cheap method)

  - `MULLIKEN_CHARGES` Method based on Mulliken gross orbital populations (GOP)

Method employed for the calculation of the DFT+U contribution [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L200)]

POTENTIAL_FILE_NAME _: string_ _ = POTENTIAL _
    

**Usage:** _POTENTIAL_FILE_NAME_

**Mentions:** â­[Pseudopotentials](../../methods/dft/pseudopotentials.html)

Name of the pseudopotential library file, optionally including a path. The potential selected for each kind is set with KIND%POTENTIAL. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L143)]

RELAX_MULTIPLICITY _: real_ _ = 0.00000000E+000 _
    

**Aliases:** RELAX_MULTIP

**Usage:** _RELAX_MULTIPLICITY 0.00001_

Tolerance in Hartrees. Do not enforce the occupation of alpha and beta MOs due to the initially defined multiplicity, but rather follow the Aufbau principle. A value greater than zero activates this option. If alpha/beta MOs differ in energy less than this tolerance, then alpha-MO occupation is preferred even if it is higher in energy (within the tolerance). Such spin-symmetry broken (spin-polarized) occupation is used as SCF input, which (is assumed to) bias the SCF towards a spin-polarized solution. Thus, larger tolerance increases chances of ending up with spin-polarization. This option is only valid for unrestricted (i.e. spin polarised) Kohn-Sham (UKS) calculations. It also needs non-zero [ADDED_MOS](DFT/SCF.html#CP2K_INPUT.FORCE_EVAL.DFT.SCF.ADDED_MOS "CP2K_INPUT.FORCE_EVAL.DFT.SCF.ADDED_MOS") to actually affect the calculations, which is why it is not expected to work with [OT](DFT/SCF/OT.html#cp2k-input-force-eval-dft-scf-ot) and may raise errors when used with OT. For more details see [this discussion](https://github.com/cp2k/cp2k/issues/4389). [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L218)]

ROKS _: logical_ _ = F _
    

**Aliases:** RESTRICTED_OPEN_KOHN_SHAM

**Lone keyword:** `T`

**Usage:** _ROKS_

Requests a restricted open Kohn-Sham calculation [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L172)]

SORT_BASIS _: enum_ _ = DEFAULT _
    

**Usage:** _SORT_BASIS EXP_

**Valid values:**

  - `DEFAULT` don't sort

  - `EXP` sort w.r.t. exponent

**Mentions:** â­[HFX-RI for Î-Point (non-periodic)](../../methods/dft/hartree-fock/ri_gamma.html)

Sorts basis functions according to a selected criterion. Sorting by exponent can improve data locality for selected exact-exchange and RI workflows. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L323)]

SUBCELLS _: real_ _ = 2.00000000E+000 _
    

**Usage:** _SUBCELLS 1.5_

Read the grid size for subcell generation in the construction of neighbor lists. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L245)]

SURFACE_DIPOLE_CORRECTION _: logical_ _ = F _
    

**Aliases:** SURFACE_DIPOLE ,SURF_DIP

**Lone keyword:** `T`

**Usage:** _SURF_DIP_

**References:** [Bengtsson1999](../../bibliography.html#bengtsson1999)

For slab calculations with asymmetric geometries, activate the correction of the electrostatic potential with by compensating for the surface dipole. Implemented only for slabs with normal parallel to one Cartesian axis. The normal direction is given by the keyword SURF_DIP_DIR [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L260)]

SURF_DIP_DIR _: enum_ _ = Z _
    

**Usage:** _SURF_DIP_DIR Z_

**Valid values:**

  - `X` Along x

  - `Y` Along y

  - `Z` Along z

Cartesian axis parallel to surface normal. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L275)]

SURF_DIP_POS _: real_ _ = -1.00000000E+000 _
    

**Usage:** _SURF_DIP_POS -1.0_dp_

This keyword assigns an user defined position in Angstroms in the direction normal to the surface (given by SURF_DIP_DIR). The default value is -1.0_dp which appplies the correction at a position that has minimum electron density on the grid. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L287)]

SURF_DIP_SWITCH _: logical_ _ = F _
    

**Lone keyword:** `T`

**Usage:** _SURF_DIP_SWITCH .TRUE._

WARNING: Experimental feature under development that will help the user to switch parameters to facilitate SCF convergence. In its current form the surface dipole correction is switched off if the calculation does not converge in (0.5*MAX_SCF + 1) outer_scf steps. The default value is .FALSE. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L298)]

UKS _: logical_ _ = F _
    

**Aliases:** UNRESTRICTED_KOHN_SHAM ,LSD ,SPIN_POLARIZED

**Lone keyword:** `T`

**Usage:** _LSD_

Requests a spin-polarized calculation using alpha and beta orbitals, i.e. no spin restriction is applied [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L160)]

WFN_RESTART_FILE_NAME _: string_
    

**Aliases:** RESTART_FILE_NAME

**Usage:** _WFN_RESTART_FILE_NAME_

**Mentions:** â­[Real-Time Propagation and Ehrenfest MD](../../methods/sampling/ehrenfest.html)

Name of the wavefunction restart file, may include a path. If no file is specified, the default is to open the file as generated by the wfn restart print key. [[Edit on GitHub](https://github.com/cp2k/cp2k/blob/master/src/input_cp2k_dft.F#L151)]
