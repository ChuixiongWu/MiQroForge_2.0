# Harmonic Vibrational Analysis and Visualization of Normal Modes —frequency()andhessian()

# Harmonic Vibrational Analysis and Visualization of Normal Modes — [`frequency()`](api/psi4.driver.frequency.html#psi4.driver.frequency "psi4.driver.frequency") and [`hessian()`](api/psi4.driver.hessian.html#psi4.driver.hessian "psi4.driver.hessian")

  - Psi4 Native Hessian Methods

For further discussion of vibrational and thermochemical analysis, see Sec. [Vibrational and Thermochemical Analysis](thermo.html#sec-thermo).

[`frequency()`](api/psi4.driver.frequency.html#psi4.driver.frequency "psi4.driver.frequency") is the only command most users will ever need to access directly to perform frequency calculations. Behind the scenes, [`frequency()`](api/psi4.driver.frequency.html#psi4.driver.frequency "psi4.driver.frequency") is a light wrapper over [`hessian()`](api/psi4.driver.hessian.html#psi4.driver.hessian "psi4.driver.hessian") that computes the Hessian then adds a thermochemical analysis.

psi4.frequency(_name_[, _molecule_ , _return_wfn_ , _func_ , _mode_ , _dertype_ , _irrep_])[[source]](_modules/psi4/driver/driver.html#frequency)
    

Function to compute harmonic vibrational frequencies.

Aliases:
    

frequencies(), freq()

Returns:
    

_float_ – Total electronic energy in Hartrees.

Returns:
    

(_float_ , [`Wavefunction`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction "psi4.core.Wavefunction")) – energy and wavefunction when **return_wfn** specified.

Parameters:
    

  - **name** ([_str_](https://docs.python.org/3.12/library/stdtypes.html#str "(in Python v3.12)")) – 

`'scf'` || `'mp2'` || `'ci5'` || etc.

First argument, usually unlabeled. Indicates the computational method to be applied to the system.

  - **molecule** ([molecule](notes_py.html#op-py-molecule)) – 

`h2o` || etc.

The target molecule, if not the last molecule defined.

  - **return_wfn** ([boolean](notes_py.html#op-py-boolean)) – 

`'on'` || \(\Rightarrow\) `'off'` \(\Leftarrow\)

Indicate to additionally return the [`Wavefunction`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction "psi4.core.Wavefunction") calculation result as the second element (after _float_ energy) of a tuple. Arrays of frequencies and the Hessian can be accessed through the wavefunction.

  - **func** ([function](notes_py.html#op-py-function)) – 

\(\Rightarrow\) `gradient` \(\Leftarrow\) || `energy` || `cbs`

Indicates the type of calculation to be performed on the molecule. The default dertype accesses `'gradient'` or `'energy'`, while `'cbs'` performs a multistage finite difference calculation. If a nested series of python functions is intended (see [Function Intercalls](intercalls.html#sec-intercalls)), use keyword `freq_func` instead of `func`.

  - **dertype** ([dertype](notes_py.html#op-py-dertype)) – 

\(\Rightarrow\) `'hessian'` \(\Leftarrow\) || `'gradient'` || `'energy'`

Indicates whether analytic (if available- they’re not), finite difference of gradients (if available) or finite difference of energies is to be performed.

  - **irrep** ([_int_](https://docs.python.org/3.12/library/functions.html#int "(in Python v3.12)") _or_[ _str_](https://docs.python.org/3.12/library/stdtypes.html#str "(in Python v3.12)")) – 

\(\Rightarrow\) `-1` \(\Leftarrow\) || `1` || `'b2'` || `'App'` || etc.

Indicates which symmetry block ([Cotton](psithonmol.html#table-irrepordering) ordering) of vibrational frequencies to be computed. `1`, `'1'`, or `'a1'` represents \(a_1\), requesting only the totally symmetric modes. `-1` indicates a full frequency calculation.

Note

Analytic hessians are only available for RHF and UHF. For all other methods, Frequencies will proceed through finite differences according to availability of gradients or energies.

name | calls method  
---|---  
scf | Hartree–Fock (HF) or LSDA density functional theory (DFT) [[manual]](scf.html#sec-scf) [[details]](capabilities.html#dd-svwn)  
  
Examples:
    
 
    >>> # [1] Frequency calculation for all modes through highest available derivatives
    >>> frequency('ccsd')
    

 
    >>> # [2] Frequency calculation for b2 modes through finite difference of gradients
    >>> #     printing lowest mode frequency to screen and Hessian to output
    >>> E, wfn = frequencies('scf', dertype=1, irrep=4, return_wfn=True)
    >>> print wfn.frequencies().get(0, 0)
    >>> wfn.hessian().print_out()
    

 
    >>> # [3] Frequency calculation at default conditions and Hessian reuse at STP
    >>> E, wfn = freq('mp2', return_wfn=True)
    >>> set t 273.15
    >>> set p 100000
    >>> thermo(wfn, wfn.frequencies())
    

 
    >>> # [4] Opt+Freq, skipping the gradient recalc at the start of the Hessian
    >>> e, wfn = optimize('hf', return_wfn=True)
    >>> frequencies('hf', ref_gradient=wfn.gradient())
    

psi4.hessian(_name_[, _molecule_ , _return_wfn_ , _func_ , _dertype_ , _irrep_])[[source]](_modules/psi4/driver/driver.html#hessian)
    

Function complementary to [`frequency()`](api/psi4.driver.frequency.html#psi4.driver.frequency "psi4.driver.frequency"). Computes force constants, deciding analytic, finite difference of gradients, or finite difference of energies.

Returns:
    

[`Matrix`](api/psi4.core.Matrix.html#psi4.core.Matrix "psi4.core.Matrix") – Total non-mass-weighted electronic Hessian in Hartrees/Bohr/Bohr.

Returns:
    

([`Matrix`](api/psi4.core.Matrix.html#psi4.core.Matrix "psi4.core.Matrix"), [`Wavefunction`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction "psi4.core.Wavefunction")) – Hessian and wavefunction when **return_wfn** specified.

Examples:
    
 
    >>> # [1] Frequency calculation without thermochemical analysis
    >>> hessian('mp3')
    

 
    >>> # [2] Frequency calc w/o thermo analysis getting the Hessian
    >>> #     in file, core.Matrix, and np.array forms
    >>> set hessian_write on
    >>> H, wfn = hessian('ccsd', return_wfn=True)
    >>> wfn.hessian().print_out()
    >>> np.array(H)
    

It’s handy to collect the wavefunction after a frequency calculation through `e, wfn = psi4.frequency(..., return_wfn=True)` as the frequencies can be accessed through [`psi4.core.Wavefunction.frequencies()`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction.frequencies "psi4.core.Wavefunction.frequencies"), the Hessian through [`psi4.core.Wavefunction.hessian()`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction.hessian "psi4.core.Wavefunction.hessian"), and much other computation info through `psi4.core.Wavefunction.frequency_analysis` (note no parentheses). Examples of using this data structure can be found [fd-freq-gradient](https://github.com/psi4/psi4/blob/master/samples/fd-freq-gradient/input.dat) and [psi4/tests/pytests/test_vibanalysis.py](https://github.com/psi4/psi4/blob/master/tests/pytests/test_vibanalysis.py). Formatted printing of vibrational results is available through [`psi4.driver.qcdb.vib.print_vibs()`](api/psi4.driver.qcdb.vib.print_vibs.html#psi4.driver.qcdb.vib.print_vibs "psi4.driver.qcdb.vib.print_vibs").

Results accessible through `psi4.core.Wavefunction.frequency_analysis` key | description (lbl & comment) | units | data (real/imaginary modes)  
---|---|---|---  
omega | frequency | cm^-1 | ndarray(ndof) complex (real/imag)  
q | normal mode, normalized mass-weighted | a0 u^1/2 | ndarray(ndof, ndof) float  
w | normal mode, un-mass-weighted | a0 | ndarray(ndof, ndof) float  
x | normal mode, normalized un-mass-weighted | a0 | ndarray(ndof, ndof) float  
degeneracy | degree of degeneracy |  | ndarray(ndof) int  
TRV | translation/rotation/vibration |  | ndarray(ndof) str ‘TR’ or ‘V’ or ‘-’ for partial  
gamma | irreducible representation |  | ndarray(ndof) str irrep or None if unclassifiable  
mu | reduced mass | u | ndarray(ndof) float (+/+)  
k | force constant | mDyne/A | ndarray(ndof) float (+/-)  
DQ0 | RMS deviation v=0 | a0 u^1/2 | ndarray(ndof) float (+/0)  
Qtp0 | Turning point v=0 | a0 u^1/2 | ndarray(ndof) float (+/0)  
Xtp0 | Turning point v=0 | a0 | ndarray(ndof) float (+/0)  
theta_vib | char temp | K | ndarray(ndof) float (+/0)  
  
## Visualization of Normal Modes

PSI4 has the ability to export a Molden file that stores information about the harmonic frequencies and normal modes computed via [`frequency()`](api/psi4.driver.frequency.html#psi4.driver.frequency "psi4.driver.frequency"). This feature can be enabled by setting the option [NORMAL_MODES_WRITE](autodoc_glossary_options_c.html#term-NORMAL_MODES_WRITE-FINDIF) to true. The filename of the Molden file ends in `.molden_normal_modes`, and the prefix is determined by [WRITER_FILE_LABEL](autodoc_glossary_options_c.html#term-WRITER_FILE_LABEL-GLOBALS) (if set), or else by the name of the output file plus the name of the current molecule. The normal coordinates saved in the Molden file are normalized and are not mass weighted.

### Molden Interface Keywords

#### [NORMAL_MODES_WRITE](autodoc_glossary_options_c.html#term-NORMAL_MODES_WRITE-FINDIF)

> Do write a file containing the normal modes in Molden format? If so, the filename will end in .molden_normal_modes, and the prefix is determined by [WRITER_FILE_LABEL](autodoc_glossary_options_c.html#term-WRITER_FILE_LABEL-GLOBALS) (if set), or else by the name of the output file plus the name of the current molecule.
> 
>   - **Type** : [boolean](notes_c.html#op-c-boolean)
> 
>   - **Default** : false
> 
> 

#### [WRITER_FILE_LABEL](autodoc_glossary_options_c.html#term-WRITER_FILE_LABEL-GLOBALS)

> Base filename for text files written by PSI, such as the MOLDEN output file, the Hessian file, the internal coordinate file, etc. Use the add_str_i function to make this string case sensitive.
> 
>   - **Type** : string
> 
>   - **Default** : No Default
> 
> 

## psi4.driver.qcdb.vib Module

### Functions

[`compare_vibinfos`](api/psi4.driver.qcdb.vib.compare_vibinfos.html#psi4.driver.qcdb.vib.compare_vibinfos "psi4.driver.qcdb.vib.compare_vibinfos")(expected, computed, tol, label) | Returns True if two dictionaries of vibration Datum objects are equivalent within a tolerance.  
---|---  
[`filter_nonvib`](api/psi4.driver.qcdb.vib.filter_nonvib.html#psi4.driver.qcdb.vib.filter_nonvib "psi4.driver.qcdb.vib.filter_nonvib")(vibinfo[, remove]) | From a dictionary of vibration Datum, remove normal coordinates.  
[`filter_omega_to_real`](api/psi4.driver.qcdb.vib.filter_omega_to_real.html#psi4.driver.qcdb.vib.filter_omega_to_real "psi4.driver.qcdb.vib.filter_omega_to_real")(omega) | Returns ndarray (float) of omega (complex) where imaginary entries are converted to negative reals.  
[`harmonic_analysis`](api/psi4.driver.qcdb.vib.harmonic_analysis.html#psi4.driver.qcdb.vib.harmonic_analysis "psi4.driver.qcdb.vib.harmonic_analysis")(hess, geom, mass, ...[, ...]) | Extract frequencies, normal modes and other properties from electronic Hessian.  
[`hessian_symmetrize`](api/psi4.driver.qcdb.vib.hessian_symmetrize.html#psi4.driver.qcdb.vib.hessian_symmetrize "psi4.driver.qcdb.vib.hessian_symmetrize")(hess, mol) | Apply Abelian symmetry of mol to Hessian hess.  
[`print_molden_vibs`](api/psi4.driver.qcdb.vib.print_molden_vibs.html#psi4.driver.qcdb.vib.print_molden_vibs "psi4.driver.qcdb.vib.print_molden_vibs")(vibinfo, atom_symbol, geom) | Format vibrational analysis for Molden.  
[`print_vibs`](api/psi4.driver.qcdb.vib.print_vibs.html#psi4.driver.qcdb.vib.print_vibs "psi4.driver.qcdb.vib.print_vibs")(vibinfo[, atom_lbl, normco, ...]) | Pretty printer for vibrational analysis.  
[`thermo`](api/psi4.driver.qcdb.vib.thermo.html#psi4.driver.qcdb.vib.thermo "psi4.driver.qcdb.vib.thermo")(vibinfo, T, P, multiplicity, ...[, ...]) | Perform thermochemical analysis from vibrational output.  
  
## API

_pydantic model _psi4.driver.driver_findif.FiniteDifferenceComputer[[source]](_modules/psi4/driver/driver_findif.html#FiniteDifferenceComputer)
    

Show JSON schema

    {
       "title": "FiniteDifferenceComputer",
       "description": "Base class for \"computers\" that plan, run, and process QC tasks.",
       "type": "object",
       "properties": {
          "molecule": {
             "title": "Molecule"
          },
          "driver": {
             "$ref": "#/definitions/DriverEnum"
          },
          "metameta": {
             "title": "Metameta",
             "default": {},
             "type": "object"
          },
          "task_list": {
             "title": "Task List",
             "default": {},
             "type": "object",
             "additionalProperties": {
                "$ref": "#/definitions/BaseComputer"
             }
          },
          "findifrec": {
             "title": "Findifrec",
             "default": {},
             "type": "object"
          },
          "method": {
             "title": "Method",
             "type": "string"
          }
       },
       "required": [
          "driver",
          "method"
       ],
       "definitions": {
          "DriverEnum": {
             "title": "DriverEnum",
             "description": "Allowed computation driver values.",
             "enum": [
                "energy",
                "gradient",
                "hessian",
                "properties"
             ],
             "type": "string"
          },
          "BaseComputer": {
             "title": "BaseComputer",
             "description": "Base class for \"computers\" that plan, run, and process QC tasks.",
             "type": "object",
             "properties": {}
          }
       }
    }
    

Fields:
    

  - `driver (qcelemental.models.common_models.DriverEnum)`

  - `findifrec (Dict[str, Any])`

  - `metameta (Dict[str, Any])`

  - `method (str)`

  - `molecule (Any)`

  - `task_list (Dict[str, psi4.driver.task_base.BaseComputer])`

Validators:
    

  - `set_driver` » `driver`

  - `set_molecule` » `molecule`

_field _driver _: [`DriverEnum`](https://molssi.github.io/QCElemental/dev/api/qcelemental.models.DriverEnum.html#qcelemental.models.DriverEnum "(in QCElemental v0.30.2)")_ _[Required]_
    

Validated by:
    

  - `set_driver`

_field _findifrec _: [`Dict`](https://docs.python.org/3.12/library/typing.html#typing.Dict "(in Python v3.12)")[[`str`](https://docs.python.org/3.12/library/stdtypes.html#str "(in Python v3.12)"), [`Any`](https://docs.python.org/3.12/library/typing.html#typing.Any "(in Python v3.12)")]__ = {}_
    

_field _metameta _: [`Dict`](https://docs.python.org/3.12/library/typing.html#typing.Dict "(in Python v3.12)")[[`str`](https://docs.python.org/3.12/library/stdtypes.html#str "(in Python v3.12)"), [`Any`](https://docs.python.org/3.12/library/typing.html#typing.Any "(in Python v3.12)")]__ = {}_
    

_field _method _: [`str`](https://docs.python.org/3.12/library/stdtypes.html#str "(in Python v3.12)")_ _[Required]_
    

_field _molecule _: [`Any`](https://docs.python.org/3.12/library/typing.html#typing.Any "(in Python v3.12)")_ _ = None_
    

Validated by:
    

  - `set_molecule`

_field _task_list _: [`Dict`](https://docs.python.org/3.12/library/typing.html#typing.Dict "(in Python v3.12)")[[`str`](https://docs.python.org/3.12/library/stdtypes.html#str "(in Python v3.12)"), [`BaseComputer`](external_apis.html#psi4.driver.task_base.BaseComputer "psi4.driver.task_base.BaseComputer")]__ = {}_
    

computer
    

alias of [`AtomicComputer`](api/psi4.driver.AtomicComputer.html#psi4.driver.AtomicComputer "psi4.driver.task_base.AtomicComputer")

build_tasks(_obj_ , _** kwargs_)[[source]](_modules/psi4/driver/driver_findif.html#FiniteDifferenceComputer.build_tasks)
    

compute(_client =None_)[[source]](_modules/psi4/driver/driver_findif.html#FiniteDifferenceComputer.compute)
    

Run each job in task list.

Parameters:
    

**client** ([_PortalClient_](https://docs.qcarchive.molssi.org/user_guide/qcportal_reference/clients.html#qcportal.client.PortalClient "(in QCArchive v0.64.post11+g63a1c0666)") _|__None_)

get_psi_results(_client =None_, _*_ , _return_wfn =False_)[[source]](_modules/psi4/driver/driver_findif.html#FiniteDifferenceComputer.get_psi_results)
    

Called by driver to assemble results into FiniteDifference-flavored QCSchema, then reshape and return them in the customary Psi4 driver interface: `(e/g/h, wfn)`.

Parameters:
    

  - **return_wfn** ([`bool`](https://docs.python.org/3.12/library/functions.html#bool "(in Python v3.12)")) – 

Whether to additionally return the dummy [`Wavefunction`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction "psi4.core.Wavefunction") calculation result as the second element of a tuple. Contents are:

    - undisplaced molecule

    - compute basis if simple, else dummy basis def2-svp

    - e/g/h member data

    - QCVariables

    - module

  - **client** ([_PortalClient_](https://docs.qcarchive.molssi.org/user_guide/qcportal_reference/clients.html#qcportal.client.PortalClient "(in QCArchive v0.64.post11+g63a1c0666)") _|__None_)

Return type:
    

[`Union`](https://docs.python.org/3.12/library/typing.html#typing.Union "(in Python v3.12)")[[`float`](https://docs.python.org/3.12/library/functions.html#float "(in Python v3.12)"), [`Matrix`](api/psi4.core.Matrix.html#psi4.core.Matrix "psi4.core.Matrix"), [`Tuple`](https://docs.python.org/3.12/library/typing.html#typing.Tuple "(in Python v3.12)")[[`Union`](https://docs.python.org/3.12/library/typing.html#typing.Union "(in Python v3.12)")[[`float`](https://docs.python.org/3.12/library/functions.html#float "(in Python v3.12)"), [`Matrix`](api/psi4.core.Matrix.html#psi4.core.Matrix "psi4.core.Matrix")], [`Wavefunction`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction "psi4.core.Wavefunction")]]

Returns:
    

  - _ret_ – Gradient or Hessian according to self.driver.

  - _wfn_ – Wavefunction described above when _return_wfn_ specified.

get_results(_client =None_)[[source]](_modules/psi4/driver/driver_findif.html#FiniteDifferenceComputer.get_results)
    

Return results as FiniteDifference-flavored QCSchema.

Return type:
    

[`AtomicResult`](https://molssi.github.io/QCElemental/dev/api/qcelemental.models.AtomicResult.html#qcelemental.models.AtomicResult "(in QCElemental v0.30.2)")

Parameters:
    

**client** ([_PortalClient_](https://docs.qcarchive.molssi.org/user_guide/qcportal_reference/clients.html#qcportal.client.PortalClient "(in QCArchive v0.64.post11+g63a1c0666)") _|__None_)

plan()[[source]](_modules/psi4/driver/driver_findif.html#FiniteDifferenceComputer.plan)
    

_validator _set_driver _ » __driver_[[source]](_modules/psi4/driver/driver_findif.html#FiniteDifferenceComputer.set_driver)
    

_validator _set_molecule _ » __molecule_[[source]](_modules/psi4/driver/driver_findif.html#FiniteDifferenceComputer.set_molecule)
    

« hide menu menu sidebar » 

© Copyright 2007-2026, The Psi4 Project. Last updated on Friday, 01 May 2026 11:18PM. Created using [Sphinx](https://www.sphinx-doc.org/) 7.4.7.
