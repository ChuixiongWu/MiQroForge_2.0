# CC: Coupled Cluster Theory

# CC: Coupled Cluster Theory

_Code author: T. Daniel Crawford_

_Section author: T. Daniel Crawford_

_Module:_ [PSI Variables](autodir_psivariables/module__ccenergy.html#apdx-ccenergy-psivar)

_Module:_ [Keywords](autodir_options_c/module__ccenergy.html#apdx-ccenergy), [CCENERGY](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/cc/ccenergy)

_Module:_ [Keywords](autodir_options_c/module__cceom.html#apdx-cceom), [CCEOM](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/cc/cceom)

_Module:_ [Keywords](autodir_options_c/module__ccresponse.html#apdx-ccresponse), [CCRESPONSE](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/cc/ccresponse)

_Module:_ [Keywords](autodir_options_c/module__cctriples.html#apdx-cctriples), [CCTRIPLES](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/cc/cctriples)

_Module:_ [Keywords](autodir_options_c/module__ccdensity.html#apdx-ccdensity), [CCDENSITY](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/cc/ccdensity)

_Module:_ [Keywords](autodir_options_c/module__cchbar.html#apdx-cchbar), [CCHBAR](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/cc/cchbar)

_Module:_ [Keywords](autodir_options_c/module__cclambda.html#apdx-cclambda), [CCLAMBDA](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/cc/cclambda)

The coupled cluster approach is one of the most accurate and reliable quantum chemical techniques for including the effects of electron correlation. Instead of the linear expansion of the wavefunction used by configuration interaction, coupled cluster uses an exponential expansion,

(1)[\begin{split}| \Psi \rangle &= e^{\hat{T}} | \Phi_0 \rangle \\\ &= \left( 1 + {\hat{T}} + \frac{1}{2} {\hat{T}}^2 + \frac{1}{3!}{\hat{T}}^3 + \cdots \right) | \Phi_0 \rangle,\end{split}]

where the cluster operator \({\hat{T}}\) is written as a sum of operators that generate singly-excited, doubly-excited, _etc._ , determinants:

[{\hat{T}} = {\hat{T}_1} + {\hat{T}_2} + {\hat{T}_3} + \cdots + {\hat{T}_N},]

with

[\begin{split}{\hat T}_1 | \Phi_0 \rangle &= \sum_{i}^{\rm occ} \sum_a^{\rm vir} t_i^a | \Phi_i^a \rangle \\\ {\hat T}_2 | \Phi_0 \rangle &= \sum_{i<j}^{\rm occ} \sum_{a<b}^{\rm vir} t_{ij}^{ab} | \Phi_{ij}^{ab} \rangle,\end{split}]

_etc._ The popular coupled cluster singles and doubles (CCSD) model [[Purvis:1982]](bibliography.html#purvis-1982) truncates the expansion at \({\hat{T}} = {\hat{T}_1} \+ {\hat{T}_2}\). This model has the same number of parameters as configuration interaction singles and doubles (CISD) but improves upon it by approximately accounting for higher-order terms using products of lower-order terms (_e.g._ , the term \({\hat{T}_2}^2\) approximately accounts for quadruple excitations). The inclusion of such products makes coupled-cluster methods _size extensive_ , meaning that the quality of the computation should not degrade for larger molecules. The computational cost for CCSD scales as \({\cal{O}}(o^2 v^4)\), where \(o\) is the number of occupied orbitals and \(v\) is the number of virtual orbitals.

Improving upon CCSD, the CCSD(T) method [[Raghavachari:1989]](bibliography.html#raghavachari-1989) includes a perturbative estimate of the energy contributed by the \({\hat{T}_3}\) operator. The computational cost of this additional term scales as \({\cal{O}}(o^3 v^4)\), making it rather expensive for molecules with more than a dozen heavy atoms or so. However, when this method is affordable, it provides very high quality results in most cases.

PSI4 is capable of computing energies and analytic gradients for a number of coupled cluster models. It can also compute linear response properties (such as static or frequency-dependent polarizability, or optical rotation angles) for some models. Excited states can also be computed by the CC2 and CC3 models, or by EOM-CCSD. Table CC Methods summarizes these capabilities. This section describes how to carry out coupled cluster calculations within PSI4. For higher-order coupled-cluster methods like CCSDT and CCSDTQ, PSI4 can interface to Kállay’s MRCC code (see [MRCC](mrcc.html#sec-mrcc)).

Solvent effects on energies can be taken into account using the polarizable continuum model (PCM) in the PTE approximation [[Cammi:2009:164104]](bibliography.html#cammi-2009-164104), see [PCM](pcmsolver.html#sec-pcmsolver)

The following wavefunctions are currently recognized by PSI4 as arguments to functions like [`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy"): `'ccsd'`, `'ccsd(t)'`, `'a-ccsd(t)'`, `'cc2'`, `'cc3'`, `'bccd'` (CCD with Brueckner orbitals), `'bccd(t)'` (CCD(T) with Brueckner orbitals), `'eom-ccsd'`, `'eom-cc2'` (CC2 for excited states), `'eom-cc3'` (CC3 for excited states). Response properties can be obtained by calling the function [`properties()`](api/psi4.driver.properties.html#psi4.driver.properties "psi4.driver.properties") (instead of, for example, [`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy"), _e.g._ , `properties('ccsd')`. There are many sample coupled cluster inputs provided in [psi4/samples](https://github.com/psi4/psi4/blob/master/samples).

The various methods supported by the CCENERGY modules in PSI4 are summarized in Table CC Methods and detailed (except excited state methods) in Table CCENERGY Capabilities. Even without `set qc_module ccenergy`, methods will default to this module, but alternate implementations can be seen at [other modules](capabilities.html#table-managedmethods).

Current coupled cluster capabilities of PSI4 Method | Reference | Energy | Gradient | Exc. Energies | LR Props  
---|---|---|---|---|---  
CC2 | RHF | Y | Y | Y | Y  
UHF | Y | — | — | —  
ROHF | Y | — | — | —  
CCSD | RHF | Y | Y | Y | Y  
UHF | Y | Y | Y | —  
ROHF | Y | Y | Y | —  
CCSD(T) | RHF | Y | Y [4] | n/a | n/a  
UHF | Y | Y [4] | n/a | n/a  
ROHF | Y | — | n/a | n/a  
A-CCSD(T) [5] | RHF | Y | — | n/a | n/a  
CC3 | RHF | Y | — | Y | —  
UHF | Y | — | Y | —  
ROHF | Y | — | Y | —  
CCD | Brueckner | Y | — | — | —  
CCD(T) | Brueckner | Y | — | n/a | n/a  
Detailed capabilities of CCENERGY and related modules. “✓” runs analytically. Single underline “✓̲” is default module when [QC_MODULE](autodoc_glossary_options_c.html#term-QC_MODULE-GLOBALS) unspecified. Double underline “✓̳” is default algorithm type when type selector (e.g., [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS)) unspecified. ◻ ◻ name ↓ → ◻ ◻ | ◻ [REFERENCE](autodoc_glossary_options_c.html#term-REFERENCE-SCF) → ◻ type[1] ↓ → [FREEZE_CORE](autodoc_glossary_options_c.html#term-FREEZE_CORE-GLOBALS)[2]→ | [QC_MODULE](autodoc_glossary_options_c.html#term-QC_MODULE-GLOBALS)=CCENERGY Capabilities  
---|---|---  
Restricted (RHF) | Unrestricted (UHF) | Restricted Open (ROHF)  
[`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy") | [`gradient()`](api/psi4.driver.gradient.html#psi4.driver.gradient "psi4.driver.gradient")[3] | [`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy") | [`gradient()`](api/psi4.driver.gradient.html#psi4.driver.gradient "psi4.driver.gradient")[3] | [`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy") | [`gradient()`](api/psi4.driver.gradient.html#psi4.driver.gradient "psi4.driver.gradient")[3]  
CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD  
A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F  
bccd | [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS) | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |   
cc2 | [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS) | ✓̳ | ✓̳ |  |  |  |  | ✓̳ |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |   
ccsd | [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS) | ✓̳ | ✓̳ |  |  |  |  | ✓̳ |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  | ✓̳ |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  | ✓̳ |  |  |  |  |   
ccsd(t)[4] | [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS) | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |   
a-ccsd(t)[5] | [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS) | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |   
bccd(t) | [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS) | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |   
cc3 | [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS) | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |  | ✓̳ | ✓̳ |  |  |  |  |  |  |  |  |  |   
  
## Basic Keywords

A complete list of keywords related to coupled-cluster computations is provided in the appendices, with the majority of the relevant keywords appearing in Appendix [CCENERGY](autodir_options_c/module__ccenergy.html#apdx-ccenergy). For a standard ground-state CCSD or CCSD(T) computation, the following keywords are common:

### [REFERENCE](autodoc_glossary_options_c.html#term-REFERENCE-CCENERGY)

> Reference wavefunction type
> 
>   - **Type** : string
> 
>   - **Possible Values** : RHF, ROHF, UHF
> 
>   - **Default** : RHF
> 
> 

### [R_CONVERGENCE](autodoc_glossary_options_c.html#term-R_CONVERGENCE-CCENERGY)

> Convergence criterion for wavefunction (change) in CC amplitude equations.
> 
>   - **Type** : [conv double](notes_c.html#op-c-conv)
> 
>   - **Default** : 1e-7
> 
> 

### [MAXITER](autodoc_glossary_options_c.html#term-MAXITER-CCENERGY)

> Maximum number of iterations to solve the CC equations
> 
>   - **Type** : integer
> 
>   - **Default** : 50
> 
> 

### [BRUECKNER_ORBS_R_CONVERGENCE](autodoc_glossary_options_c.html#term-BRUECKNER_ORBS_R_CONVERGENCE-CCENERGY)

> Convergence criterion for Brueckner orbitals. The convergence is determined based on the largest \(T_1\) amplitude. Default adjusts depending on [E_CONVERGENCE](autodoc_glossary_options_c.html#term-E_CONVERGENCE-CCENERGY)
> 
>   - **Type** : [conv double](notes_c.html#op-c-conv)
> 
>   - **Default** : 1e-5
> 
> 

### [RESTART](autodoc_glossary_options_c.html#term-RESTART-CCENERGY)

> Do restart the coupled-cluster iterations from old \(t_1\) and \(t_2\) amplitudes? For geometry optimizations, Brueckner calculations, etc. the iterative solution of the CC amplitude equations may benefit considerably by reusing old vectors as initial guesses. Assuming that the MO phases remain the same between updates, the CC codes will, by default, re-use old vectors, unless the user sets RESTART = false.
> 
>   - **Type** : [boolean](notes_c.html#op-c-boolean)
> 
>   - **Default** : true
> 
> 

### [CACHELEVEL](autodoc_glossary_options_c.html#term-CACHELEVEL-CCENERGY)

> Caching level for libdpd governing the storage of amplitudes, integrals, and intermediates in the CC procedure. A value of 0 retains no quantities in cache, while a level of 6 attempts to store all quantities in cache. For particularly large calculations, a value of 0 may help with certain types of memory problems. The default is 2, which means that all four-index quantities with up to two virtual-orbital indices (e.g., \(\langle ij | ab \rangle\) integrals) may be held in the cache.
> 
>   - **Type** : integer
> 
>   - **Default** : 2
> 
> 

### [CACHETYPE](autodoc_glossary_options_c.html#term-CACHETYPE-CCENERGY)

> Selects the priority type for maintaining the automatic memory cache used by the libdpd codes. A value of `LOW` selects a “low priority” scheme in which the deletion of items from the cache is based on pre-programmed priorities. A value of LRU selects a “least recently used” scheme in which the oldest item in the cache will be the first one deleted.
> 
>   - **Type** : string
> 
>   - **Possible Values** : LOW, LRU
> 
>   - **Default** : LOW
> 
> 

### [NUM_AMPS_PRINT](autodoc_glossary_options_c.html#term-NUM_AMPS_PRINT-CCENERGY)

> Number of important \(t_1\) and \(t_2\) amplitudes to print
> 
>   - **Type** : integer
> 
>   - **Default** : 10
> 
> 

### [MP2_AMPS_PRINT](autodoc_glossary_options_c.html#term-MP2_AMPS_PRINT-CCENERGY)

> Do print the MP2 amplitudes which are the starting guesses for RHF and UHF reference functions?
> 
>   - **Type** : [boolean](notes_c.html#op-c-boolean)
> 
>   - **Default** : false
> 
> 

## Larger Calculations

Here are a few recommendations for carrying out large-basis-set coupled cluster calculations with PSI4:

  - In most cases it is reasonable to set the `memory` keyword to 90% of the available physical memory, at most. There is a small amount of overhead associated with the coupled cluster modules that is not accounted for by the internal CC memory handling routines. Thus, the user should _not_ specify the entire physical memory of the system, or swapping is likely. However, for especially large calculations, it is better to set the `memory` keyword to a value less than 16 GB.

  - Set the [CACHELEVEL](autodoc_glossary_options_c.html#term-CACHELEVEL-CCENERGY) keyword to `0`. This will turn off cacheing, which, for very large calculations, can lead to heap fragmentation and memory faults, even when sufficient physical memory exists.

  - Set the [PRINT](autodoc_glossary_options_c.html#term-PRINT-GLOBALS) keyword to `2`. This will help narrow where memory bottlenecks or other errors exist in the event of a crash.

## Excited State Coupled Cluster Calculations

A complete list of keywords related to coupled cluster linear response is provided in Appendix [CCEOM](autodir_options_c/module__cceom.html#apdx-cceom). The most important keywords associated with EOM-CC calculations are:

### [ROOTS_PER_IRREP](autodoc_glossary_options_c.html#term-ROOTS_PER_IRREP-CCEOM)

> Number of excited states per irreducible representation for EOM-CC and CC-LR calculations. Irreps denote the final state symmetry, not the symmetry of the transition.
> 
>   - **Type** : array
> 
>   - **Default** : No Default
> 
> 

### [E_CONVERGENCE](autodoc_glossary_options_c.html#term-E_CONVERGENCE-CCEOM)

> Convergence criterion for excitation energy (change) in the Davidson algorithm for CC-EOM. See Table [Post-SCF Convergence](scf.html#table-conv-corl) for default convergence criteria for different calculation types.
> 
>   - **Type** : [conv double](notes_c.html#op-c-conv)
> 
>   - **Default** : 1e-6
> 
> 

### [SINGLES_PRINT](autodoc_glossary_options_c.html#term-SINGLES_PRINT-CCEOM)

> Do print information on the iterative solution to the single-excitation EOM-CC problem used as a guess to full EOM-CC?
> 
>   - **Type** : [boolean](notes_c.html#op-c-boolean)
> 
>   - **Default** : false
> 
> 

### [SCHMIDT_ADD_RESIDUAL_TOLERANCE](autodoc_glossary_options_c.html#term-SCHMIDT_ADD_RESIDUAL_TOLERANCE-CCEOM)

> Minimum absolute value above which a guess vector to a root is added to the Davidson algorithm in the EOM-CC iterative procedure.
> 
>   - **Type** : [conv double](notes_c.html#op-c-conv)
> 
>   - **Default** : 1e-3
> 
> 

### [EOM_GUESS](autodoc_glossary_options_c.html#term-EOM_GUESS-CCEOM)

> Specifies a set of single-excitation guess vectors for the EOM-CC procedure. If EOM_GUESS = `SINGLES`, the guess will be taken from the singles-singles block of the similarity-transformed Hamiltonian, Hbar. If EOM_GUESS = `DISK`, guess vectors from a previous computation will be read from disk. If EOM_GUESS = `INPUT`, guess vectors will be specified in user input. The latter method is not currently available.
> 
>   - **Type** : string
> 
>   - **Possible Values** : SINGLES, DISK, INPUT
> 
>   - **Default** : SINGLES
> 
> 

## Linear Response (CCLR) Calculations

Linear response computations are invoked like `properties('ccsd')` or `properties('cc2')`, along with a list of requested properties. A complete list of keywords related to coupled cluster linear response is provided in Appendix [CCRESPONSE](autodir_options_c/module__ccresponse.html#apdx-ccresponse).

The most important keywords associated with CC-LR calculations are as follows.

### [PROPERTY](autodoc_glossary_options_c.html#term-PROPERTY-CCRESPONSE)

> The response property desired. Acceptable values are `POLARIZABILITY` (default) for dipole polarizabilities, `ROTATION` for specific rotations, `ROA` for Raman Optical Activity (`ROA_TENSOR` for each displacement), and `ALL` for all of the above.
> 
>   - **Type** : string
> 
>   - **Possible Values** : POLARIZABILITY, ROTATION, ROA, ROA_TENSOR, ALL
> 
>   - **Default** : POLARIZABILITY
> 
> 

### [OMEGA](autodoc_glossary_options_c.html#term-OMEGA-CCRESPONSE)

> Array that specifies the desired frequencies of the incident radiation field in CCLR calculations. If only one element is given, the units will be assumed to be atomic units. If more than one element is given, then the units must be specified as the final element of the array. Acceptable units are `HZ`, `NM`, `EV`, and `AU`.
> 
>   - **Type** : array
> 
>   - **Default** : No Default
> 
> 

### [GAUGE](autodoc_glossary_options_c.html#term-GAUGE-CCRESPONSE)

> Specifies the choice of representation of the electric dipole operator. For polarizability, this keyword is ignored and `LENGTH` gauge is computed. For optical rotation and raman optical activity, this keyword is active, and acceptable values are `LENGTH` for the usual length-gauge representation, `VELOCITY``(default) for the modified velocity-gauge representation in which the static-limit optical rotation tensor is subtracted from the frequency- dependent tensor, or ``BOTH`. Note that, for optical rotation and raman optical activity calculations, only the choices of `VELOCITY` or `BOTH` will yield origin-independent results.
> 
>   - **Type** : string
> 
>   - **Possible Values** : LENGTH, VELOCITY, BOTH
> 
>   - **Default** : VELOCITY
> 
> 

« hide menu menu sidebar » 

© Copyright 2007-2026, The Psi4 Project. Last updated on Friday, 01 May 2026 11:18PM. Created using [Sphinx](https://www.sphinx-doc.org/) 7.4.7.
