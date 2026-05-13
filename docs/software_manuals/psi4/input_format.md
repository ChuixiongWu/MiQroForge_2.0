# Psi4 Input Format & Energy Calculations

# Single-Point Energy — [`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy")

  - Psi4 Native Energy Methods

  - Psi4 Native DFT Energy Methods

  - [MRCC Interfaced Energy Methods](mrcc_table_energy.html#table-energy-mrcc)

  - CFOUR Interfaced Energy Methods

psi4.energy(_name_[, _molecule_ , _return_wfn_ , _restart_file_])[[source]](_modules/psi4/driver/driver.html#energy)
    

Function to compute the single-point electronic energy.

Returns:
    

_float_ – Total electronic energy in Hartrees. SAPT & EFP return interaction energy.

Returns:
    

(_float_ , [`Wavefunction`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction "psi4.core.Wavefunction")) – energy and wavefunction when **return_wfn** specified.

PSI variables:
    

  - [`CURRENT ENERGY`](glossary_psivariables.html#psivar-CURRENT-ENERGY)
  - [`CURRENT REFERENCE ENERGY`](glossary_psivariables.html#psivar-CURRENT-REFERENCE-ENERGY)
  - [`CURRENT CORRELATION ENERGY`](glossary_psivariables.html#psivar-CURRENT-CORRELATION-ENERGY)

  
---  
  
Parameters:
    

  - **name** ([_str_](https://docs.python.org/3.12/library/stdtypes.html#str "(in Python v3.12)")) – 

`'scf'` || `'mp2'` || `'ci5'` || etc.

First argument, usually unlabeled. Indicates the computational method to be applied to the system.

  - **molecule** ([molecule](notes_py.html#op-py-molecule)) – 

`h2o` || etc.

The target molecule, if not the last molecule defined.

  - **return_wfn** ([boolean](notes_py.html#op-py-boolean)) – 

`'on'` || \(\Rightarrow\) `'off'` \(\Leftarrow\)

Indicate to additionally return the [`Wavefunction`](api/psi4.core.Wavefunction.html#psi4.core.Wavefunction "psi4.core.Wavefunction") calculation result as the second element (after _float_ energy) of a tuple.

  - **write_orbitals** (str, [boolean](notes_py.html#op-py-boolean)) – 

`filename` || \(\Rightarrow\) `'on'` \(\Leftarrow\) || `'off'`

(str) Save wfn containing current orbitals to the given file name after each SCF iteration and retain after PSI4 finishes.

([boolean](notes_py.html#op-py-boolean)) Turns writing the orbitals after the converged SCF on/off. Orbital file will be deleted unless PSI4 is called with -m flag.

  - **restart_file** ([_str_](https://docs.python.org/3.12/library/stdtypes.html#str "(in Python v3.12)")) – 

`['file.1, file.32]` || `./file` || etc.

Existing files to be renamed and copied for calculation restart, e.g. a serialized wfn or module-specific binary data.

name | calls method  
---|---  
efp | (with LibEFP) effective fragment potential (EFP) [[manual]](libefp.html#sec-libefp)  
scf | Hartree–Fock (HF) or density functional theory (DFT) [[manual]](scf.html#sec-scf) [[details]](capabilities.html#dd-b3lyp)  
hf | HF self consistent field (SCF) [[manual]](scf.html#sec-scf) [[details]](capabilities.html#dd-hf)  
qchf | quadratically-convergent HF  
hf3c | HF with dispersion, BSSE, SRB, and basis set corrections [[manual]](gcp.html#sec-gcp)  
pbeh3c | PBEh with dispersion, BSSE, and basis set corrections [[manual]](gcp.html#sec-gcp)  
b973c | B97(GGA) with dispersion, SRB, and basis set corrections [[manual]](gcp.html#sec-gcp)  
r2scan3c | r2SCAN with dispersion, BSSE, and basis set corrections [[manual]](gcp.html#sec-gcp)  
wb97x3c | wB97X with dispersion and basis set corrections [[manual]](gcp.html#sec-gcp)  
dct | density cumulant (functional) theory [[manual]](dct.html#sec-dct)  
mp2 | 2nd-order Møller–Plesset perturbation theory (MP2) [[manual]](dfmp2.html#sec-dfmp2) [[details]](capabilities.html#dd-mp2)  
scs-mp2 | spin-component scaled MP2 [[manual]](occ.html#sec-occ-nonoo)  
scs(n)-mp2 | a special version of SCS-MP2 for nucleobase interactions [[manual]](occ.html#sec-occ-nonoo)  
scs-mp2-vdw | a special version of SCS-MP2 (from ethene dimers) [[manual]](occ.html#sec-occ-nonoo)  
sos-mp2 | spin-opposite scaled MP2 [[manual]](occ.html#sec-occ-nonoo)  
dlpno-mp2 | local MP2 with pair natural orbital domains (DLPNO) [[manual]](dlpnomp2.html#sec-dlpnomp2)  
scs-dlpno-mp2 | spin-component-scaled DLPNO MP2 [[manual]](dlpnomp2.html#sec-dlpnomp2)  
mp2-f12 | explicitly correlated MP2 in the 3C(FIX) Ansatz [[manual]](mp2f12.html#sec-mp2f12)  
mp3 | 3rd-order Møller–Plesset perturbation theory (MP3) [[manual]](occ.html#sec-occ-nonoo) [[details]](capabilities.html#dd-mp3)  
fno-mp3 | MP3 with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
scs-mp3 | spin-component scaled MP3 [[manual]](occ.html#sec-occ-nonoo)  
sos-pi-mp2 | A special version of SOS-MP2 for pi systems [[manual]](occ.html#sec-occ-nonoo)  
mp2.5 | average of MP2 and MP3 [[manual]](occ.html#sec-occ-nonoo) [[details]](capabilities.html#dd-mp2p5)  
mp4(sdq) | 4th-order MP perturbation theory (MP4) less triples [[manual]](fnocc.html#sec-fnompn) [[details]](capabilities.html#dd-mp4-prsdq-pr)  
fno-mp4(sdq) | MP4 (less triples) with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
mp4 | full MP4 [[manual]](fnocc.html#sec-fnompn) [[details]](capabilities.html#dd-mp4)  
fno-mp4 | full MP4 with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
mp _n_ | _n_ th-order Møller–Plesset (MP) perturbation theory [[manual]](detci.html#sec-arbpt) [[details]](capabilities.html#dd-mp4)  
zapt _n_ | _n_ th-order z-averaged perturbation theory (ZAPT) [[manual]](detci.html#sec-arbpt) [[details]](capabilities.html#dd-zapt2)  
omp2 | orbital-optimized second-order MP perturbation theory [[manual]](occ.html#sec-occ-oo) [[details]](capabilities.html#dd-omp2)  
scs-omp2 | spin-component scaled OMP2 [[manual]](occ.html#sec-occ-oo)  
sos-omp2 | spin-opposite scaled OMP2 [[manual]](occ.html#sec-occ-oo)  
omp3 | orbital-optimized third-order MP perturbation theory [[manual]](occ.html#sec-occ-oo) [[details]](capabilities.html#dd-omp3)  
scs-omp3 | spin-component scaled OMP3 [[manual]](occ.html#sec-occ-oo)  
sos-omp3 | spin-opposite scaled OMP3 [[manual]](occ.html#sec-occ-oo)  
omp2.5 | orbital-optimized MP2.5 [[manual]](occ.html#sec-occ-oo) [[details]](capabilities.html#dd-omp2p5)  
lccsd, cepa(0) | coupled electron pair approximation variant 0 [[manual]](fnocc.html#sec-fnocepa) [[details]](capabilities.html#dd-lccsd)  
fno-lccsd, fno-cepa(0) | CEPA(0) with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
cepa(1) | coupled electron pair approximation variant 1 [[manual]](fnocc.html#sec-fnocepa) [[details]](capabilities.html#dd-cepa-pr1-pr)  
fno-cepa(1) | CEPA(1) with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
cepa(3) | coupled electron pair approximation variant 3 [[manual]](fnocc.html#sec-fnocepa) [[details]](capabilities.html#dd-cepa-pr3-pr)  
fno-cepa(3) | CEPA(3) with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
acpf | averaged coupled-pair functional [[manual]](fnocc.html#sec-fnocepa) [[details]](capabilities.html#dd-acpf)  
fno-acpf | ACPF with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
aqcc | averaged quadratic coupled cluster [[manual]](fnocc.html#sec-fnocepa) [[details]](capabilities.html#dd-aqcc)  
fno-aqcc | AQCC with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
qcisd | quadratic CI singles doubles (QCISD) [[manual]](fnocc.html#sec-fnocc) [[details]](capabilities.html#dd-qcisd)  
fno-qcisd | QCISD with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
remp2 | 2nd-order retaining-the-excitation-degree MP hybrid perturbation theory [[manual]](occ.html#sec-occ-nonoo) [[details]](capabilities.html#dd-remp2)  
oremp2 | orbital-optimized REMP2 [[manual]](occ.html#sec-occ-oo) [[details]](capabilities.html#dd-oremp2)  
lccd | Linear CCD [[manual]](occ.html#sec-occ-nonoo) [[details]](capabilities.html#dd-lccd)  
fno-lccd | LCCD with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
olccd | orbital optimized LCCD [[manual]](occ.html#sec-occ-oo) [[details]](capabilities.html#dd-olccd)  
cc2 | approximate coupled cluster singles and doubles (CC2) [[manual]](cc.html#sec-cc) [[details]](capabilities.html#dd-cc2)  
ccd | coupled cluster doubles (CCD) [[manual]](occ.html#sec-occ-nonoo) [[details]](capabilities.html#dd-ccd)  
ccsd | coupled cluster singles and doubles (CCSD) [[manual]](cc.html#sec-cc) [[details]](capabilities.html#dd-ccsd)  
bccd | Brueckner coupled cluster doubles (BCCD) [[manual]](cc.html#sec-cc) [[details]](capabilities.html#dd-bccd)  
fno-ccsd | CCSD with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
dlpno-ccsd | local CCSD with pair natural orbital domains (DLPNO) [[manual]](dlpnocc.html#sec-dlpnocc)  
qcisd(t) | QCISD with perturbative triples [[manual]](fnocc.html#sec-fnocc) [[details]](capabilities.html#dd-qcisd-prt-pr)  
fno-qcisd(t) | QCISD(T) with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
ccsd(t) | CCSD with perturbative triples (CCSD(T)) [[manual]](cc.html#sec-cc) [[details]](capabilities.html#dd-ccsd-prt-pr)  
a-ccsd(t) | CCSD with asymmetric perturbative triples (A-CCSD(T)) [[manual]](cc.html#sec-cc) [[details]](capabilities.html#dd-accsd-prt-pr)  
bccd(t) | BCCD with perturbative triples [[manual]](cc.html#sec-cc) [[details]](capabilities.html#dd-bccd-prt-pr)  
fno-ccsd(t) | CCSD(T) with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
dlpno-ccsd(t) | local CCSD(T) with pair natural orbital domains (DLPNO) [[manual]](dlpnocc.html#sec-dlpnocc)  
cc3 | approximate CC singles, doubles, and triples (CC3) [[manual]](cc.html#sec-cc) [[details]](capabilities.html#dd-cc3)  
ccenergy | **expert** full control over ccenergy module  
cisd | configuration interaction (CI) singles and doubles (CISD) [[manual]](detci.html#sec-ci) [[details]](capabilities.html#dd-cisd)  
fno-cisd | CISD with frozen natural orbitals [[manual]](fnocc.html#sec-fnocc)  
cisdt | CI singles, doubles, and triples (CISDT) [[manual]](detci.html#sec-ci)  
cisdtq | CI singles, doubles, triples, and quadruples (CISDTQ) [[manual]](detci.html#sec-ci)  
ci _n_ | _n_ th-order CI [[manual]](detci.html#sec-ci) [[details]](capabilities.html#dd-cisd)  
fci | full configuration interaction (FCI) [[manual]](detci.html#sec-ci) [[details]](capabilities.html#dd-fci)  
detci | **expert** full control over detci module  
gaussian-2, g2 | Gaussian-2 composite method [[manual]](fnocc.html#sec-fnogn)  
casscf | complete active space self consistent field (CASSCF) [[manual]](detci.html#sec-ci)  
rasscf | restricted active space self consistent field (RASSCF) [[manual]](detci.html#sec-ci)  
mcscf | multiconfigurational self consistent field (SCF) [[manual]](psimrcc.html#sec-psimrcc)  
psimrcc | Mukherjee multireference coupled cluster (Mk-MRCC) [[manual]](psimrcc.html#sec-psimrcc)  
psimrcc_scf | Mk-MRCC with regular SCF module (convenience function) [[manual]](psimrcc.html#sec-psimrcc)  
dmrg-scf | (with CheMPS2) density matrix renormalization group SCF [[manual]](chemps2.html#sec-chemps2)  
dmrg-caspt2 | (with CheMPS2) density matrix renormalization group CASPT2 [[manual]](chemps2.html#sec-chemps2)  
dmrg-ci | (with CheMPS2) density matrix renormalization group CI [[manual]](chemps2.html#sec-chemps2)  
sapt0 | 0th-order symmetry adapted perturbation theory (SAPT) [[manual]](sapt.html#sec-sapt)  
ssapt0 | 0th-order SAPT with special exchange scaling [[manual]](sapt.html#sec-sapt)  
fisapt0 | 0th-order functional and/or intramolecular SAPT [[manual]](fisapt.html#sec-fisapt)  
sf-sapt | 0th-order spin-flip SAPT [[manual]](sapt.html#sec-sfsapt)  
sapt(dft) | 0th-order SAPT upon KS reference [[manual]](sapt.html#sec-saptdft)  
sapt2 | 2nd-order SAPT, traditional definition [[manual]](sapt.html#sec-sapt)  
sapt2+ | SAPT including all 2nd-order terms [[manual]](sapt.html#sec-sapt)  
sapt2+(3) | SAPT including perturbative triples [[manual]](sapt.html#sec-sapt)  
sapt2+3 | SAPT including all 3rd-order terms [[manual]](sapt.html#sec-sapt)  
sapt2+(ccd) | SAPT2+ with CC-based dispersion [[manual]](sapt.html#sec-sapt)  
sapt2+(3)(ccd) | SAPT2+(3) with CC-based dispersion [[manual]](sapt.html#sec-sapt)  
sapt2+3(ccd) | SAPT2+3 with CC-based dispersion [[manual]](sapt.html#sec-sapt)  
sapt2+dmp2 | SAPT including all 2nd-order terms and MP2 correction [[manual]](sapt.html#sec-sapt)  
sapt2+(3)dmp2 | SAPT including perturbative triples and MP2 correction [[manual]](sapt.html#sec-sapt)  
sapt2+3dmp2 | SAPT including all 3rd-order terms and MP2 correction [[manual]](sapt.html#sec-sapt)  
sapt2+(ccd)dmp2 | SAPT2+ with CC-based dispersion and MP2 correction [[manual]](sapt.html#sec-sapt)  
sapt2+(3)(ccd)dmp2 | SAPT2+(3) with CC-based dispersion and MP2 correction [[manual]](sapt.html#sec-sapt)  
sapt2+3(ccd)dmp2 | SAPT2+3 with CC-based dispersion and MP2 correction [[manual]](sapt.html#sec-sapt)  
sapt0-ct | 0th-order SAPT plus charge transfer (CT) calculation [[manual]](sapt.html#sec-saptct)  
sapt2-ct | SAPT2 plus CT [[manual]](sapt.html#sec-saptct)  
sapt2+-ct | SAPT2+ plus CT [[manual]](sapt.html#sec-saptct)  
sapt2+(3)-ct | SAPT2+(3) plus CT [[manual]](sapt.html#sec-saptct)  
sapt2+3-ct | SAPT2+3 plus CT [[manual]](sapt.html#sec-saptct)  
sapt2+(ccd)-ct | SAPT2+(CCD) plus CT [[manual]](sapt.html#sec-saptct)  
sapt2+(3)(ccd)-ct | SAPT2+(3)(CCD) plus CT [[manual]](sapt.html#sec-saptct)  
sapt2+3(ccd)-ct | SAPT2+3(CCD) plus CT [[manual]](sapt.html#sec-saptct)  
adc | 2nd-order algebraic diagrammatic construction (ADC), deprecated [[manual]](adc.html#sec-adc)  
adc(1) | (with ADCC) 1st-order algebraic diagrammatic construction (ADC) [[manual]](adc.html#sec-adc)  
adc(2) | (with ADCC) 2nd-order ADC [[manual]](adc.html#sec-adc)  
adc(2)-x | (with ADCC) extended 2nd-order ADC [[manual]](adc.html#sec-adc)  
adc(3) | (with ADCC) 3rd-order ADC [[manual]](adc.html#sec-adc)  
cvs-adc(1) | (with ADCC) core-valence separation (CVS) 1st-order ADC [[manual]](adc.html#sec-adc)  
cvs-adc(2) | (with ADCC) CVS 2nd-order ADC [[manual]](adc.html#sec-adc)  
cvs-adc(2)-x | (with ADCC) CVS extended 2nd-order ADC [[manual]](adc.html#sec-adc)  
cvs-adc(3) | (with ADCC) CVS 3rd-order ADC [[manual]](adc.html#sec-adc)  
ep2 | 2nd-order electron propagator theory  
eom-cc2 | equation of motion (EOM) CC2 [[manual]](cc.html#sec-eomcc)  
eom-ccsd | EOM-CCSD [[manual]](cc.html#sec-eomcc)  
eom-cc3 | EOM-CC3 [[manual]](cc.html#sec-eomcc)  
name | calls method DFT [[manual]](dft.html#sec-dft)  
---|---  
b1lyp | B1LYP Hyb-GGA Exchange-Correlation Functional  
td-b1lyp | TDDFT B1LYP Hyb-GGA Exchange-Correlation Functional  
b1lyp-d3bj2b |   
b1lyp-d3bjatm |   
b1lyp-d3zero2b |   
b1lyp-d3zeroatm |   
b1pw91 | B1PW91 Hyb-GGA Exchange-Correlation Functional  
td-b1pw91 | TDDFT B1PW91 Hyb-GGA Exchange-Correlation Functional  
b1wc | B1WC Hyb-GGA Exchange-Correlation Functional  
td-b1wc | TDDFT B1WC Hyb-GGA Exchange-Correlation Functional  
b2gpplyp | B2GPPLYP Double Hybrid Exchange-Correlation Functional  
b2gpplyp-d3bj2b |   
b2gpplyp-d3bjatm |   
b2gpplyp-d3zero2b |   
b2gpplyp-d3zeroatm |   
b2gpplyp-nl | B2GPPLYP Double Hybrid Exchange-Correlation Functional  
b2plyp | B2PLYP Double Hybrid Exchange-Correlation Functional  
b2plyp-d3bj2b |   
b2plyp-d3bjatm |   
b2plyp-d3mbj2b |   
b2plyp-d3mbjatm |   
b2plyp-d3mzero2b |   
b2plyp-d3mzeroatm |   
b2plyp-d3zero2b |   
b2plyp-d3zeroatm |   
b2plyp-nl | B2PLYP Double Hybrid Exchange-Correlation Functional  
b3lyp | B3LYP Hyb-GGA Exchange-Correlation Functional  
td-b3lyp | TDDFT B3LYP Hyb-GGA Exchange-Correlation Functional  
b3lyp-d3bj2b |   
b3lyp-d3bjatm |   
b3lyp-d3mbj2b |   
b3lyp-d3mbjatm |   
b3lyp-d3mzero2b |   
b3lyp-d3mzeroatm |   
b3lyp-d3zero2b |   
b3lyp-d3zeroatm |   
b3lyp-nl | B3LYP-nl Hyb-GGA Exchange-Correlation Functional  
b3lyp5 | B3LYP5 Hyb-GGA Exchange-Correlation Functional  
td-b3lyp5 | TDDFT B3LYP5 Hyb-GGA Exchange-Correlation Functional  
b3lyps | B3LYPs Hyb-GGA Exchange-Correlation Functional  
td-b3lyps | TDDFT B3LYPs Hyb-GGA Exchange-Correlation Functional  
b3p86 | B3P86 Hyb-GGA Exchange-Correlation Functional  
td-b3p86 | TDDFT B3P86 Hyb-GGA Exchange-Correlation Functional  
b3p86-d3bj2b |   
b3p86-d3bjatm |   
b3p86-d3zero2b |   
b3p86-d3zeroatm |   
b3pw91 | B3PW91 Hyb-GGA Exchange-Correlation Functional  
td-b3pw91 | TDDFT B3PW91 Hyb-GGA Exchange-Correlation Functional  
b3pw91-d3bj2b |   
b3pw91-d3bjatm |   
b3pw91-d3zero2b |   
b3pw91-d3zeroatm |   
b3pw91-nl | B3PW91-nl Hyb-GGA Exchange-Correlation Functional  
b5050lyp | B5050LYP Hyb-GGA Exchange-Correlation Functional  
td-b5050lyp | TDDFT B5050LYP Hyb-GGA Exchange-Correlation Functional  
b86b95 | B86B95 Hyb-GGA Exchange-Correlation Functional  
td-b86b95 | TDDFT B86B95 Hyb-GGA Exchange-Correlation Functional  
b86bpbe | B86BPBE GGA Exchange-Correlation Functional  
td-b86bpbe | TDDFT B86BPBE GGA Exchange-Correlation Functional  
b88b95 | B88B95 Hyb-GGA Exchange-Correlation Functional  
td-b88b95 | TDDFT B88B95 Hyb-GGA Exchange-Correlation Functional  
b88b95-d3bj2b |   
b88b95-d3bjatm |   
b88b95-d3zero2b |   
b88b95-d3zeroatm |   
b97-0 | B97-0 Hyb-GGA Exchange-Correlation Functional  
td-b97-0 | TDDFT B97-0 Hyb-GGA Exchange-Correlation Functional  
b97-1 | B97-1 Hyb-GGA Exchange-Correlation Functional  
td-b97-1 | TDDFT B97-1 Hyb-GGA Exchange-Correlation Functional  
b97-1-d3bj2b |   
b97-1-d3bjatm |   
b97-1-d3zero2b |   
b97-1-d3zeroatm |   
b97-1p | B97-1p Hyb-GGA Exchange-Correlation Functional  
td-b97-1p | TDDFT B97-1p Hyb-GGA Exchange-Correlation Functional  
b97-2 | B97-2 Hyb-GGA Exchange-Correlation Functional  
td-b97-2 | TDDFT B97-2 Hyb-GGA Exchange-Correlation Functional  
b97-2-d3bj2b |   
b97-2-d3bjatm |   
b97-2-d3zero2b |   
b97-2-d3zeroatm |   
b97-3 | B97-3 Hyb-GGA Exchange-Correlation Functional  
td-b97-3 | TDDFT B97-3 Hyb-GGA Exchange-Correlation Functional  
b97-d |   
b97-d3bj |   
b97-d3mbj |   
b97-gga1 | B97-GGA1 GGA Exchange-Correlation Functional  
td-b97-gga1 | TDDFT B97-GGA1 GGA Exchange-Correlation Functional  
b97-k | B97-K Hyb-GGA Exchange-Correlation Functional  
td-b97-k | TDDFT B97-K Hyb-GGA Exchange-Correlation Functional  
b973c | B97-3c GGA-based 3C composite method with a TZ basis set, D3 and short-range basis set correction. (10.1063/1.5012601)  
b97m-d3bj |   
b97m-v | B97M-V GGA Exchange-Correlation Functional  
td-b97m-v | TDDFT B97M-V GGA Exchange-Correlation Functional  
bb1k | BB1K Hyb-GGA Exchange-Correlation Functional  
td-bb1k | TDDFT BB1K Hyb-GGA Exchange-Correlation Functional  
bhandh | BHandH Hyb-GGA Exchange-Correlation Functional  
td-bhandh | TDDFT BHandH Hyb-GGA Exchange-Correlation Functional  
bhandhlyp | BHandHLYP Hyb-GGA Exchange-Correlation Functional  
td-bhandhlyp | TDDFT BHandHLYP Hyb-GGA Exchange-Correlation Functional  
blyp | BLYP GGA Exchange-Correlation Functional  
td-blyp | TDDFT BLYP GGA Exchange-Correlation Functional  
blyp-d3bj2b |   
blyp-d3bjatm |   
blyp-d3mbj2b |   
blyp-d3mbjatm |   
blyp-d3mzero2b |   
blyp-d3mzeroatm |   
blyp-d3zero2b |   
blyp-d3zeroatm |   
blyp-nl | BLYP GGA Exchange-Correlation Functional  
bmk | BMK Hybrid Meta-GGA XC Functional for kinetics  
td-bmk | TDDFT BMK Hybrid Meta-GGA XC Functional for kinetics  
bmk-d3bj2b |   
bmk-d3bjatm |   
bmk-d3zero2b |   
bmk-d3zeroatm |   
bop | BOP GGA Exchange-Correlation Functional  
td-bop | TDDFT BOP GGA Exchange-Correlation Functional  
bop-d3bj2b |   
bop-d3bjatm |   
bop-d3zero2b |   
bop-d3zeroatm |   
bp86 | BP86 GGA Exchange-Correlation Functional  
td-bp86 | TDDFT BP86 GGA Exchange-Correlation Functional  
bp86-d3bj2b |   
bp86-d3bjatm |   
bp86-d3mbj2b |   
bp86-d3mbjatm |   
bp86-d3mzero2b |   
bp86-d3mzeroatm |   
bp86-d3zero2b |   
bp86-d3zeroatm |   
bp86-nl | BP86 GGA Exchange-Correlation Functional  
bp86-vwn | BP86 GGA XC Functional based on VWN5 corr. & more accurate ftilde value  
td-bp86-vwn | TDDFT BP86 GGA XC Functional based on VWN5 corr. & more accurate ftilde value  
cam-b3lyp | CAM-B3LYP Hyb-GGA Exchange-Correlation Functional  
td-cam-b3lyp | TDDFT CAM-B3LYP Hyb-GGA Exchange-Correlation Functional  
cam-b3lyp-d3bj2b |   
cam-b3lyp-d3bjatm |   
cam-b3lyp-d3zero2b |   
cam-b3lyp-d3zeroatm |   
cam-lda0 | CAM-LDA0 Exchange-Correlation Functional  
td-cam-lda0 | TDDFT CAM-LDA0 Exchange-Correlation Functional  
cap0 | CAP0 Hyb-GGA Exchange-Correlation Functional  
td-cap0 | TDDFT CAP0 Hyb-GGA Exchange-Correlation Functional  
core-dsd-blyp |   
core-dsd-blyp-d3bj2b |   
core-dsd-blyp-d3bjatm |   
dldf | Dispersionless Hybrid Meta-GGA XC Functional  
td-dldf | TDDFT Dispersionless Hybrid Meta-GGA XC Functional  
dldf+d09 | Dispersionless Hybrid Meta-GGA XC Functional  
td-dldf+d09 | TDDFT Dispersionless Hybrid Meta-GGA XC Functional  
dldf+d10 | Dispersionless Hybrid Meta-GGA XC Functional  
td-dldf+d10 | TDDFT Dispersionless Hybrid Meta-GGA XC Functional  
dsd-blyp | DSD-BLYP SCS Double Hybrid XC Functional (not dispersion corrected)  
dsd-blyp-d3bj |   
dsd-blyp-d3bj2b |   
dsd-blyp-d3bjatm |   
dsd-blyp-d3zero2b |   
dsd-blyp-d3zeroatm |   
dsd-blyp-nl | DSD-BLYP-NL (D3BJ,FC parameters) VV10 SCS Double Hybrid XC Functional  
dsd-pbeb95 | DSD-PBEB95 SCS Double Hybrid Meta-GGA XC Functional (not dispersion corrected)  
dsd-pbeb95-d3bj |   
dsd-pbeb95-nl | DSD-PBEB95-NL (D3BJ parameters) VV10 SCS Double Hybrid Meta-GGA XC Functional  
dsd-pbep86 | DSD-PBEP86 SCS Double Hybrid XC Functional (not dispersion corrected)  
dsd-pbep86-d3bj |   
dsd-pbep86-nl | DSD-PBEP86-NL (D3BJ parameters) VV10 SCS Double Hybrid XC Functional  
dsd-pbepbe | DSD-PBEPBE SCS Double Hybrid XC Functional (not dispersion corrected)  
dsd-pbepbe-d3bj |   
dsd-pbepbe-nl | DSD-PBEPBE-NL (D3BJ parameters) VV10 SCS Double Hybrid XC Functional  
edf1 | EDF1 GGA Exchange-Correlation Functional  
td-edf1 | TDDFT EDF1 GGA Exchange-Correlation Functional  
edf2 | EDF2 Hyb-GGA Exchange-Correlation Functional  
td-edf2 | TDDFT EDF2 Hyb-GGA Exchange-Correlation Functional  
ft97 | FT97 GGA Exchange-Correlation Functional  
td-ft97 | TDDFT FT97 GGA Exchange-Correlation Functional  
gam | GAM GGA Minessota Exchange-Correlation Functional  
td-gam | TDDFT GAM GGA Minessota Exchange-Correlation Functional  
hcth120 | HCTH120 GGA Exchange-Correlation Functional  
td-hcth120 | TDDFT HCTH120 GGA Exchange-Correlation Functional  
hcth120-d3bj2b |   
hcth120-d3bjatm |   
hcth120-d3zero2b |   
hcth120-d3zeroatm |   
hcth147 | HCTH147 GGA Exchange-Correlation Functional  
td-hcth147 | TDDFT HCTH147 GGA Exchange-Correlation Functional  
hcth407 | HCTH407 GGA Exchange-Correlation Functional  
td-hcth407 | TDDFT HCTH407 GGA Exchange-Correlation Functional  
hcth407-d3bj2b |   
hcth407-d3bjatm |   
hcth407-d3zero2b |   
hcth407-d3zeroatm |   
hcth407p | HCTH407P GGA Exchange-Correlation Functional  
td-hcth407p | TDDFT HCTH407P GGA Exchange-Correlation Functional  
hcth93 | HCTH93 GGA Exchange-Correlation Functional  
td-hcth93 | TDDFT HCTH93 GGA Exchange-Correlation Functional  
hcthp14 | HCTHP14 GGA Exchange-Correlation Functional  
td-hcthp14 | TDDFT HCTHP14 GGA Exchange-Correlation Functional  
hcthp76 | HCTHP76 GGA Exchange-Correlation Functional  
td-hcthp76 | TDDFT HCTHP76 GGA Exchange-Correlation Functional  
hf | Hartree–Fock theory  
td-hf | TDDFT Hartree–Fock theory  
hf+d |   
td-hf+d | TDDFT  
hf-d3bj2b |   
hf-d3bjatm |   
hf-d3mbj2b |   
hf-d3mbjatm |   
hf-d3mzero2b |   
hf-d3mzeroatm |   
hf-d3zero2b |   
hf-d3zeroatm |   
hf-d4bjeeqtwo |   
hf-nl | Hartree–Fock theory  
hf3c | Hartree Fock based 3C composite method with minimal basis set, gCP and D3(BJ)  
hjs-b88 | HJS-B88 Hyb-GGA Exchange-Correlation Functional  
td-hjs-b88 | TDDFT HJS-B88 Hyb-GGA Exchange-Correlation Functional  
hjs-b97x | HJS-B97X Hyb-GGA Exchange-Correlation Functional  
td-hjs-b97x | TDDFT HJS-B97X Hyb-GGA Exchange-Correlation Functional  
hjs-pbe | HJS-PBE Hyb-GGA Exchange-Correlation Functional  
td-hjs-pbe | TDDFT HJS-PBE Hyb-GGA Exchange-Correlation Functional  
hjs-pbe-sol | HJS-PBE-SOL Hyb-GGA Exchange-Correlation Functional  
td-hjs-pbe-sol | TDDFT HJS-PBE-SOL Hyb-GGA Exchange-Correlation Functional  
hpbeint | HPBEINT Hyb-GGA Exchange-Correlation Functional  
td-hpbeint | TDDFT HPBEINT Hyb-GGA Exchange-Correlation Functional  
hse03 | HSE03 Hyb-GGA Exchange-Correlation Functional  
td-hse03 | TDDFT HSE03 Hyb-GGA Exchange-Correlation Functional  
hse03-d3bj2b |   
hse03-d3bjatm |   
hse03-d3zero2b |   
hse03-d3zeroatm |   
hse06 | HSE06 Hyb-GGA Exchange-Correlation Functional  
td-hse06 | TDDFT HSE06 Hyb-GGA Exchange-Correlation Functional  
hse06-d3bj2b |   
hse06-d3bjatm |   
hse06-d3zero2b |   
hse06-d3zeroatm |   
kmlyp | KMLYP Hyb-GGA Exchange-Correlation Functional  
td-kmlyp | TDDFT KMLYP Hyb-GGA Exchange-Correlation Functional  
ksdt | KSDT Exchange-Correlation Functional  
td-ksdt | TDDFT KSDT Exchange-Correlation Functional  
kt2 | KT2 GGA Exchange-Correlation Functional  
td-kt2 | TDDFT KT2 GGA Exchange-Correlation Functional  
lc-bop | LC-BOP GGA Exchange-Correlation Functional  
td-lc-bop | TDDFT LC-BOP GGA Exchange-Correlation Functional  
lc-vv10 | LC-VV10 GGA Exchange-Correlation Functional  
td-lc-vv10 | TDDFT LC-VV10 GGA Exchange-Correlation Functional  
lda0 | LDA0 Exchange-Correlation Functional  
td-lda0 | TDDFT LDA0 Exchange-Correlation Functional  
lrc-wpbe | LRC-WPBE GGA Exchange-Correlation Functional  
td-lrc-wpbe | TDDFT LRC-WPBE GGA Exchange-Correlation Functional  
lrc-wpbeh | LRC-wPBEh Hyb-GGA Exchange-Correlation Functional  
td-lrc-wpbeh | TDDFT LRC-wPBEh Hyb-GGA Exchange-Correlation Functional  
m05 | M05 Meta-GGA XC Functional (10.1063/1.2126975)  
td-m05 | TDDFT M05 Meta-GGA XC Functional (10.1063/1.2126975)  
m05-2x | Heavily Parameterized Hybrid M05-2X Meta-GGA XC Functional  
td-m05-2x | TDDFT Heavily Parameterized Hybrid M05-2X Meta-GGA XC Functional  
m05-2x-d3zero2b |   
m05-2x-d3zeroatm |   
m05-d3zero2b |   
m05-d3zeroatm |   
m06 | M06 Meta-GGA XC Functional (10.1007/s00214-007-0310-x)  
td-m06 | TDDFT M06 Meta-GGA XC Functional (10.1007/s00214-007-0310-x)  
m06-2x | Hybrid M06-2X Meta-GGA XC Functional (10.1007/s00214-007-0310-x)  
td-m06-2x | TDDFT Hybrid M06-2X Meta-GGA XC Functional (10.1007/s00214-007-0310-x)  
m06-2x-d3zero2b |   
m06-2x-d3zeroatm |   
m06-d3zero2b |   
m06-d3zeroatm |   
m06-hf | Minnesota M06-HF Hybrid XC Functional (10.1021/jp066479k)  
td-m06-hf | TDDFT Minnesota M06-HF Hybrid XC Functional (10.1021/jp066479k)  
m06-hf-d3zero2b |   
m06-hf-d3zeroatm |   
m06-l | M06-L Meta-GGA XC Functional  
td-m06-l | TDDFT M06-L Meta-GGA XC Functional  
m06-l-d3zero2b |   
m06-l-d3zeroatm |   
m08-hx | Minnesota M08-HX Hybrid XC Functional (10.1021/ct800246v)  
td-m08-hx | TDDFT Minnesota M08-HX Hybrid XC Functional (10.1021/ct800246v)  
m08-hx-d3zero2b |   
m08-hx-d3zeroatm |   
m08-so | Minnesota M08-SO Hybrid XC Functional (10.1021/ct800246v)  
td-m08-so | TDDFT Minnesota M08-SO Hybrid XC Functional (10.1021/ct800246v)  
m11 | M11 Meta-GGA XC Functional (10.1021/jz201170d)  
td-m11 | TDDFT M11 Meta-GGA XC Functional (10.1021/jz201170d)  
m11-d3bj2b |   
m11-d3bjatm |   
m11-d3zero2b |   
m11-d3zeroatm |   
m11-l | M11-L Meta-GGA XC Functional  
td-m11-l | TDDFT M11-L Meta-GGA XC Functional  
m11-l-d3bj2b |   
m11-l-d3bjatm |   
m11-l-d3zero2b |   
m11-l-d3zeroatm |   
mb3lyp-rc04 | MB3LYP-RC04 Hyb-GGA Exchange-Correlation Functional  
td-mb3lyp-rc04 | TDDFT MB3LYP-RC04 Hyb-GGA Exchange-Correlation Functional  
mgga_ms0 | MGGA_MS0 Meta-GGA XC Functional  
td-mgga_ms0 | TDDFT MGGA_MS0 Meta-GGA XC Functional  
mgga_ms1 | MGGA_MS1 Meta-GGA XC Functional  
td-mgga_ms1 | TDDFT MGGA_MS1 Meta-GGA XC Functional  
mgga_ms2 | MGGA_MS2 Meta-GGA XC Functional  
td-mgga_ms2 | TDDFT MGGA_MS2 Meta-GGA XC Functional  
mgga_ms2h | MGGA_MS2h Hybrid Meta-GGA XC Functional  
td-mgga_ms2h | TDDFT MGGA_MS2h Hybrid Meta-GGA XC Functional  
mgga_mvs | MGGA_MVS Meta-GGA XC Functional  
td-mgga_mvs | TDDFT MGGA_MVS Meta-GGA XC Functional  
mgga_mvsh | MGGA_MV2h Hybrid Meta-GGA XC Functional  
td-mgga_mvsh | TDDFT MGGA_MV2h Hybrid Meta-GGA XC Functional  
mn12-l | MN12-L Meta-GGA XC Functional  
td-mn12-l | TDDFT MN12-L Meta-GGA XC Functional  
mn12-l-d3bj2b |   
mn12-l-d3bjatm |   
mn12-l-d3zero2b |   
mn12-l-d3zeroatm |   
mn12-sx | MN12-SX Meta-GGA Hybrid Screened Exchange-Correlation Functional  
td-mn12-sx | TDDFT MN12-SX Meta-GGA Hybrid Screened Exchange-Correlation Functional  
mn12-sx-d3bj2b |   
mn12-sx-d3bjatm |   
mn12-sx-d3zero2b |   
mn12-sx-d3zeroatm |   
mn15 | MN15 Hybrid Meta-GGA Exchange-Correlation Functional  
td-mn15 | TDDFT MN15 Hybrid Meta-GGA Exchange-Correlation Functional  
mn15-d3bj2b |   
mn15-d3bjatm |   
mn15-l | MN15-L Meta-GGA XC Functional  
td-mn15-l | TDDFT MN15-L Meta-GGA XC Functional  
mn15-l-d3zero2b |   
mn15-l-d3zeroatm |   
mohlyp | MOHLYP GGA Exchange-Correlation Functional  
td-mohlyp | TDDFT MOHLYP GGA Exchange-Correlation Functional  
mohlyp2 | MOHLYP2 GGA Exchange-Correlation Functional  
td-mohlyp2 | TDDFT MOHLYP2 GGA Exchange-Correlation Functional  
mp2d | 2nd-order MP perturbation theory plus dispersion  
mp2mp2 | 2nd-order MP perturbation theory  
mpw1b95 | mPW1B95 Hyb-GGA Exchange-Correlation Functional  
td-mpw1b95 | TDDFT mPW1B95 Hyb-GGA Exchange-Correlation Functional  
mpw1b95-d3bj2b |   
mpw1b95-d3bjatm |   
mpw1b95-d3zero2b |   
mpw1b95-d3zeroatm |   
mpw1k | mPW1K Hyb-GGA Exchange-Correlation Functional  
td-mpw1k | TDDFT mPW1K Hyb-GGA Exchange-Correlation Functional  
mpw1lyp | mPW1LYP Hybrid GGA Exchange-Correlation Functional  
td-mpw1lyp | TDDFT mPW1LYP Hybrid GGA Exchange-Correlation Functional  
mpw1lyp-d3zero2b |   
mpw1lyp-d3zeroatm |   
mpw1pbe | mPW1PBE Hybrid GGA Exchange-Correlation Functional  
td-mpw1pbe | TDDFT mPW1PBE Hybrid GGA Exchange-Correlation Functional  
mpw1pw | mPW1PW Hyb-GGA Exchange-Correlation Functional  
td-mpw1pw | TDDFT mPW1PW Hyb-GGA Exchange-Correlation Functional  
mpw1pw-d3bj2b |   
mpw1pw-d3bjatm |   
mpw1pw-d3zero2b |   
mpw1pw-d3zeroatm |   
mpw3lyp | mPW3LYP Hyb-GGA Exchange-Correlation Functional  
td-mpw3lyp | TDDFT mPW3LYP Hyb-GGA Exchange-Correlation Functional  
mpw3pw | mPW3PW Hyb-GGA Exchange-Correlation Functional  
td-mpw3pw | TDDFT mPW3PW Hyb-GGA Exchange-Correlation Functional  
mpwb1k | mPWB1K Hyb-GGA Exchange-Correlation Functional  
td-mpwb1k | TDDFT mPWB1K Hyb-GGA Exchange-Correlation Functional  
mpwb1k-d3bj2b |   
mpwb1k-d3bjatm |   
mpwb1k-d3zero2b |   
mpwb1k-d3zeroatm |   
mpwlyp1m | mPWLYP1M Hyb-GGA Exchange-Correlation Functional  
td-mpwlyp1m | TDDFT mPWLYP1M Hyb-GGA Exchange-Correlation Functional  
mpwlyp1w | mPWLYP1W GGA Exchange-Correlation Functional  
td-mpwlyp1w | TDDFT mPWLYP1W GGA Exchange-Correlation Functional  
mpwpw | mPWPW GGA Exchange-Correlation Functional  
td-mpwpw | TDDFT mPWPW GGA Exchange-Correlation Functional  
n12 | N12 nonseparable GGA Exchange-Correlation Functional  
td-n12 | TDDFT N12 nonseparable GGA Exchange-Correlation Functional  
n12-d3bj2b |   
n12-d3bjatm |   
n12-d3zero2b |   
n12-d3zeroatm |   
n12-sx | N12-SX Hybrid nonseparable GGA Exchange-Correlation Functional  
td-n12-sx | TDDFT N12-SX Hybrid nonseparable GGA Exchange-Correlation Functional  
n12-sx-d3bj2b |   
n12-sx-d3bjatm |   
n12-sx-d3zero2b |   
n12-sx-d3zeroatm |   
o3lyp | O3LYP Hyb-GGA Exchange-Correlation Functional  
td-o3lyp | TDDFT O3LYP Hyb-GGA Exchange-Correlation Functional  
o3lyp-d3bj2b |   
o3lyp-d3bjatm |   
o3lyp-d3zero2b |   
o3lyp-d3zeroatm |   
oblyp-d |   
op-pbe | BP86 GGA Exchange-Correlation Functional  
td-op-pbe | TDDFT BP86 GGA Exchange-Correlation Functional  
opbe-d |   
opwlyp-d |   
otpss-d |   
pbe | PBE GGA Exchange-Correlation Functional  
td-pbe | TDDFT PBE GGA Exchange-Correlation Functional  
pbe-d3bj2b |   
pbe-d3bjatm |   
pbe-d3mbj2b |   
pbe-d3mbjatm |   
pbe-d3mzero2b |   
pbe-d3mzeroatm |   
pbe-d3zero2b |   
pbe-d3zeroatm |   
pbe-nl | PBE GGA Exchange-Correlation Functional  
pbe-sol | Perdew, Burke & Ernzerhof exchange (solids)  
td-pbe-sol | TDDFT Perdew, Burke & Ernzerhof exchange (solids)  
pbe-sol-d3bj2b |   
pbe-sol-d3bjatm |   
pbe-sol-d3zero2b |   
pbe-sol-d3zeroatm |   
pbe0 | PBE0 Hyb-GGA Exchange-Correlation Functional  
td-pbe0 | TDDFT PBE0 Hyb-GGA Exchange-Correlation Functional  
pbe0-13 | PBE0-13 Hyb-GGA Exchange-Correlation Functional  
td-pbe0-13 | TDDFT PBE0-13 Hyb-GGA Exchange-Correlation Functional  
pbe0-2 | PBE0-2 Double Hybrid Exchange-Correlation Functional  
pbe0-d3bj2b |   
pbe0-d3bjatm |   
pbe0-d3mbj2b |   
pbe0-d3mbjatm |   
pbe0-d3mzero2b |   
pbe0-d3mzeroatm |   
pbe0-d3zero2b |   
pbe0-d3zeroatm |   
pbe0-dh |   
pbe0-dh-d3bj2b |   
pbe0-dh-d3bjatm |   
pbe0-dh-d3zero2b |   
pbe0-dh-d3zeroatm |   
pbe0-nl | PBE0-nl Hyb-GGA Exchange-Correlation Functional  
pbe1w | PBE1W GGA Exchange-Correlation Functional  
td-pbe1w | TDDFT PBE1W GGA Exchange-Correlation Functional  
pbe50 | PBE50 Hybrid GGA Exchange-Correlation Functional  
td-pbe50 | TDDFT PBE50 Hybrid GGA Exchange-Correlation Functional  
pbeh3c | PBE Hybrid based 3C composite method with a small basis set, gCP and D3(BJ)  
pbelyp1w | PBELYP1W GGA Exchange-Correlation Functional  
td-pbelyp1w | TDDFT PBELYP1W GGA Exchange-Correlation Functional  
pkzb | PKZB Meta-GGA XC Functional  
td-pkzb | TDDFT PKZB Meta-GGA XC Functional  
pkzb-d3zero2b |   
pkzb-d3zeroatm |   
ptpss | PTPSS SOS Double Hybrid XC Functional  
ptpss-d3bj2b |   
ptpss-d3bjatm |   
ptpss-d3zero2b |   
ptpss-d3zeroatm |   
pw6b95 | PW6B95 Hybrid Meta-GGA XC Functional  
td-pw6b95 | TDDFT PW6B95 Hybrid Meta-GGA XC Functional  
pw6b95-d3bj2b |   
pw6b95-d3bjatm |   
pw6b95-d3zero2b |   
pw6b95-d3zeroatm |   
pw86b95 | PW86B95 Hyb-GGA Exchange-Correlation Functional  
td-pw86b95 | TDDFT PW86B95 Hyb-GGA Exchange-Correlation Functional  
pw86pbe | PW86PBE GGA Exchange-Correlation Functional  
td-pw86pbe | TDDFT PW86PBE GGA Exchange-Correlation Functional  
pw91 | PW91 GGA Exchange-Correlation Functional  
td-pw91 | TDDFT PW91 GGA Exchange-Correlation Functional  
pw91-d3bj2b |   
pw91-d3bjatm |   
pwb6k | PWB6K Hyb-GGA Exchange-Correlation Functional  
td-pwb6k | TDDFT PWB6K Hyb-GGA Exchange-Correlation Functional  
pwb6k-d3bj2b |   
pwb6k-d3bjatm |   
pwb6k-d3zero2b |   
pwb6k-d3zeroatm |   
pwpb95 | PWPB95 SOS Double Hybrid XC Functional  
pwpb95-d3bj2b |   
pwpb95-d3bjatm |   
pwpb95-d3zero2b |   
pwpb95-d3zeroatm |   
pwpb95-nl | PWPB95 SOS Double Hybrid XC Functional  
r2scan | r2SCAN Meta-GGA XC Functional (0.1021/acs.jpclett.0c02405)  
td-r2scan | TDDFT r2SCAN Meta-GGA XC Functional (0.1021/acs.jpclett.0c02405)  
r2scan0 | R2SCAN0 Hyb-GGA Exchange-Correlation Functional  
td-r2scan0 | TDDFT R2SCAN0 Hyb-GGA Exchange-Correlation Functional  
r2scan50 | R2SCAN50 Hyb-GGA Exchange-Correlation Functional  
td-r2scan50 | TDDFT R2SCAN50 Hyb-GGA Exchange-Correlation Functional  
r2scanh | R2SCANh Hyb-GGA Exchange-Correlation Functional  
td-r2scanh | TDDFT R2SCANh Hyb-GGA Exchange-Correlation Functional  
revb3lyp | revB3LYP Hyb-GGA Exchange-Correlation Functional  
td-revb3lyp | TDDFT revB3LYP Hyb-GGA Exchange-Correlation Functional  
revm06-l | Revised M06-L Meta-GGA XC Functional (10.1073/pnas.1705670114)  
td-revm06-l | TDDFT Revised M06-L Meta-GGA XC Functional (10.1073/pnas.1705670114)  
revpbe | revPBE GGA Exchange-Correlation Functional  
td-revpbe | TDDFT revPBE GGA Exchange-Correlation Functional  
revpbe-d3bj2b |   
revpbe-d3bjatm |   
revpbe-d3zero2b |   
revpbe-d3zeroatm |   
revpbe-nl | revPBE GGA Exchange-Correlation Functional  
revpbe0 | revPBE0 Hybrid GGA Exchange-Correlation Functional  
td-revpbe0 | TDDFT revPBE0 Hybrid GGA Exchange-Correlation Functional  
revpbe0-d3bj2b |   
revpbe0-d3bjatm |   
revpbe0-d3zero2b |   
revpbe0-d3zeroatm |   
revpbe0-nl | revPBE0 Hybrid GGA Exchange-Correlation Functional  
revscan | Revised SCAN Meta-GGA XC Functional (10.1021/acs.jctc.8b00072)  
td-revscan | TDDFT Revised SCAN Meta-GGA XC Functional (10.1021/acs.jctc.8b00072)  
revscan0 | Revised SCAN0 Hybrid Meta-GGA XC Functional (10.1021/acs.jctc.8b00072)  
td-revscan0 | TDDFT Revised SCAN0 Hybrid Meta-GGA XC Functional (10.1021/acs.jctc.8b00072)  
revtpss | revised TPSS Meta-GGA XC Functional  
td-revtpss | TDDFT revised TPSS Meta-GGA XC Functional  
revtpss-d3bj2b |   
revtpss-d3bjatm |   
revtpss-d3zero2b |   
revtpss-d3zeroatm |   
revtpss-nl | revised TPSS Meta-GGA XC Functional  
revtpssh | revTPSSh Hyb-GGA Exchange-Correlation Functional  
td-revtpssh | TDDFT revTPSSh Hyb-GGA Exchange-Correlation Functional  
revtpssh-d3bj2b |   
revtpssh-d3bjatm |   
revtpssh-d3zero2b |   
revtpssh-d3zeroatm |   
rpbe | RPBE GGA Exchange-Correlation Functional  
td-rpbe | TDDFT RPBE GGA Exchange-Correlation Functional  
rpbe-d3bj2b |   
rpbe-d3bjatm |   
rpbe-d3zero2b |   
rpbe-d3zeroatm |   
sb98-1a | SB98-1a Hyb-GGA Exchange-Correlation Functional  
td-sb98-1a | TDDFT SB98-1a Hyb-GGA Exchange-Correlation Functional  
sb98-1b | SB98-1b Hyb-GGA Exchange-Correlation Functional  
td-sb98-1b | TDDFT SB98-1b Hyb-GGA Exchange-Correlation Functional  
sb98-1c | SB98-1c Hyb-GGA Exchange-Correlation Functional  
td-sb98-1c | TDDFT SB98-1c Hyb-GGA Exchange-Correlation Functional  
sb98-2a | SB98-2a Hyb-GGA Exchange-Correlation Functional  
td-sb98-2a | TDDFT SB98-2a Hyb-GGA Exchange-Correlation Functional  
sb98-2b | SB98-2b Hyb-GGA Exchange-Correlation Functional  
td-sb98-2b | TDDFT SB98-2b Hyb-GGA Exchange-Correlation Functional  
sb98-2c | SB98-2c Hyb-GGA Exchange-Correlation Functional  
td-sb98-2c | TDDFT SB98-2c Hyb-GGA Exchange-Correlation Functional  
scan | SCAN Meta-GGA XC Functional (10.1103/PhysRevLett.115.036402)  
td-scan | TDDFT SCAN Meta-GGA XC Functional (10.1103/PhysRevLett.115.036402)  
scan-d3bj2b |   
scan-d3bjatm |   
scan-d3zero2b |   
scan-d3zeroatm |   
scan0 | SCAN0 Hybrid Meta-GGA XC Functional (10.1063/1.4940734)  
td-scan0 | TDDFT SCAN0 Hybrid Meta-GGA XC Functional (10.1063/1.4940734)  
sogga | SOGGA Exchange + PBE Correlation Functional  
td-sogga | TDDFT SOGGA Exchange + PBE Correlation Functional  
sogga11 | SOGGA11 Exchange-Correlation Functional  
td-sogga11 | TDDFT SOGGA11 Exchange-Correlation Functional  
sogga11-x | SOGGA11-X Hybrid Exchange-Correlation Functional  
td-sogga11-x | TDDFT SOGGA11-X Hybrid Exchange-Correlation Functional  
sogga11-x-d3bj2b |   
sogga11-x-d3bjatm |   
sogga11-x-d3zero2b |   
sogga11-x-d3zeroatm |   
spw92 | Slater exchange  
td-spw92 | TDDFT Slater exchange  
svwn | Slater exchange  
td-svwn | TDDFT Slater exchange  
t-hcth | Tau HCTH Meta-GGA XC Functional  
td-t-hcth | TDDFT Tau HCTH Meta-GGA XC Functional  
t-hcth-d3bj2b |   
t-hcth-d3bjatm |   
t-hcth-d3zero2b |   
t-hcth-d3zeroatm |   
t-hcthh | Hybrid Tau HCTH Meta-GGA XC Functional  
td-t-hcthh | TDDFT Hybrid Tau HCTH Meta-GGA XC Functional  
teter93 | TETER93 Exchange-Correlation Functional  
td-teter93 | TDDFT TETER93 Exchange-Correlation Functional  
th-fc | TH-FC GGA Exchange-Correlation Functional  
td-th-fc | TDDFT TH-FC GGA Exchange-Correlation Functional  
th-fcfo | TH-FCFO GGA Exchange-Correlation Functional  
td-th-fcfo | TDDFT TH-FCFO GGA Exchange-Correlation Functional  
th-fco | TH-FCO GGA Exchange-Correlation Functional  
td-th-fco | TDDFT TH-FCO GGA Exchange-Correlation Functional  
th-fl | TH-FL GGA Exchange-Correlation Functional  
td-th-fl | TDDFT TH-FL GGA Exchange-Correlation Functional  
th1 | TH1 GGA Exchange-Correlation Functional  
td-th1 | TDDFT TH1 GGA Exchange-Correlation Functional  
th2 | TH2 GGA Exchange-Correlation Functional  
td-th2 | TDDFT TH2 GGA Exchange-Correlation Functional  
th3 | TH3 GGA Exchange-Correlation Functional  
td-th3 | TDDFT TH3 GGA Exchange-Correlation Functional  
th4 | TH4 GGA Exchange-Correlation Functional  
td-th4 | TDDFT TH4 GGA Exchange-Correlation Functional  
tpss | TPSS Meta-GGA XC Functional  
td-tpss | TDDFT TPSS Meta-GGA XC Functional  
tpss-d3bj2b |   
tpss-d3bjatm |   
tpss-d3zero2b |   
tpss-d3zeroatm |   
tpss-nl | TPSS Meta-GGA XC Functional  
tpssh | TPSSh Hyb-GGA Exchange-Correlation Functional  
td-tpssh | TDDFT TPSSh Hyb-GGA Exchange-Correlation Functional  
tpssh-d3bj2b |   
tpssh-d3bjatm |   
tpssh-d3zero2b |   
tpssh-d3zeroatm |   
tpssh-nl | TPSSh-nl Hyb-GGA Exchange-Correlation Functional  
tpsslyp1w | TPSSLYP1W GGA Exchange-Correlation Functional  
td-tpsslyp1w | TDDFT TPSSLYP1W GGA Exchange-Correlation Functional  
tuned-cam-b3lyp | TUNED-CAM-B3LYP Hyb-GGA Exchange-Correlation Functional  
td-tuned-cam-b3lyp | TDDFT TUNED-CAM-B3LYP Hyb-GGA Exchange-Correlation Functional  
vsxc | VSXC Meta-GGA XC Functional  
td-vsxc | TDDFT VSXC Meta-GGA XC Functional  
vv10 | VV10 GGA Exchange-Correlation Functional  
td-vv10 | TDDFT VV10 GGA Exchange-Correlation Functional  
wb97 | wB97 GGA Exchange-Correlation Functional  
td-wb97 | TDDFT wB97 GGA Exchange-Correlation Functional  
wb97m-d3bj |   
wb97m-v | wB97M-V Hyb-GGA Exchange-Correlation Functional  
td-wb97m-v | TDDFT wB97M-V Hyb-GGA Exchange-Correlation Functional  
wb97x | wB97X Hyb-GGA Exchange-Correlation Functional  
td-wb97x | TDDFT wB97X Hyb-GGA Exchange-Correlation Functional  
wb97x-d |   
wb97x-d3 |   
wb97x-d3bj |   
wb97x-d3zero2b |   
wb97x-d3zeroatm |   
wb97x-v | wB97X-V Hyb-GGA Exchange-Correlation Functional  
td-wb97x-v | TDDFT wB97X-V Hyb-GGA Exchange-Correlation Functional  
wb97x3c | wB97X basied 3C composite method with a small basis set, gCP and D4 (10.1063/5.0133026)  
wpbe | PBE SR-XC Functional (HJS Model)  
td-wpbe | TDDFT PBE SR-XC Functional (HJS Model)  
wpbe-d3bj2b |   
wpbe-d3bjatm |   
wpbe-d3mbj2b |   
wpbe-d3mbjatm |   
wpbe-d3mzero2b |   
wpbe-d3mzeroatm |   
wpbe-d3zero2b |   
wpbe-d3zeroatm |   
wpbe0 | PBE0 SR-XC Functional (HJS Model)  
td-wpbe0 | TDDFT PBE0 SR-XC Functional (HJS Model)  
x1b95 | X1B95 Hyb-GGA Exchange-Correlation Functional  
td-x1b95 | TDDFT X1B95 Hyb-GGA Exchange-Correlation Functional  
x3lyp | X3LYP Hyb-GGA Exchange-Correlation Functional  
td-x3lyp | TDDFT X3LYP Hyb-GGA Exchange-Correlation Functional  
x3lyp-d3bj2b |   
x3lyp-d3bjatm |   
x3lyp-d3zero2b |   
x3lyp-d3zeroatm |   
xb1k | XB1K Hyb-GGA Exchange-Correlation Functional  
td-xb1k | TDDFT XB1K Hyb-GGA Exchange-Correlation Functional  
xlyp | XLYP GGA Exchange-Correlation Functional  
td-xlyp | TDDFT XLYP GGA Exchange-Correlation Functional  
xlyp-d3bj2b |   
xlyp-d3bjatm |   
xlyp-d3zero2b |   
xlyp-d3zeroatm |   
zlp | ZLP GGA Exchange-Correlation Functional  
td-zlp | TDDFT ZLP GGA Exchange-Correlation Functional  
  
> [QC_MODULE](autodoc_glossary_options_c.html#term-QC_MODULE-GLOBALS)=MRCC  
> ---  
> name | calls method in Kallay’s MRCC program [[manual]](mrcc.html#sec-mrcc)  
> ccsd | CC through doubles [[details]](capabilities.html#dd-ccsd)  
> ccsdt | CC through triples  
> ccsdtq | CC through quadruples  
> ccsdtqp | CC through quintuples  
> ccsdtqph | CC through sextuples  
> ccsd(t) | CC through doubles with perturbative triples [[details]](capabilities.html#dd-ccsd-prt-pr)  
> ccsdt(q) | CC through triples with perturbative quadruples  
> ccsdtq(p) | CC through quadruples with pertubative quintuples  
> ccsdtqp(h) | CC through quintuples with pertubative sextuples  
> ccsd(t)_l | CC through doubles with asymmetric perturbative triples [[details]](capabilities.html#dd-accsd-prt-pr)  
> ccsdt(q)_l | CC through triples with asymmetric perturbative quadruples  
> ccsdtq(p)_l | CC through quadruples with asymmetric perturbative quintuples  
> ccsdtqp(h)_l | CC through quintuples with asymmetric perturbative sextuples  
> ccsdt-1a | CC through doubles with iterative triples (cheapest terms)  
> ccsdtq-1a | CC through triples with iterative quadruples (cheapest terms)  
> ccsdtqp-1a | CC through quadruples with iterative quintuples (cheapest terms)  
> ccsdtqph-1a | CC through quintuples with iterative sextuples (cheapest terms)  
> ccsdt-1b | CC through doubles with iterative triples (cheaper terms)  
> ccsdtq-1b | CC through triples with iterative quadruples (cheaper terms)  
> ccsdtqp-1b | CC through quadruples with iterative quintuples (cheaper terms)  
> ccsdtqph-1b | CC through quintuples with iterative sextuples (cheaper terms)  
> cc2 | approximate CC through doubles [[details]](capabilities.html#dd-cc2)  
> cc3 | approximate CC through triples [[details]](capabilities.html#dd-cc3)  
> cc4 | approximate CC through quadruples  
> cc5 | approximate CC through quintuples  
> cc6 | approximate CC through sextuples  
> ccsdt-3 | CC through doubles with iterative triples (all but the most expensive terms)  
> ccsdtq-3 | CC through triples with iterative quadruples (all but the most expensive terms)  
> ccsdtqp-3 | CC through quadruples with iterative quintuples (all but the most expensive terms)  
> ccsdtqph-3 | CC through quintuples with iterative sextuples (all but the most expensive terms)  
  
> name | calls method in Stanton and Gauss’s CFOUR program [[manual]](cfour.html#sec-cfour)  
> ---|---  
> c4-scf | Hartree–Fock (HF)  
> c4-mp2 | 2nd-order Møller–Plesset perturbation theory (non-density-fitting) (MP2)  
> c4-mp3 | 3rd-order Møller–Plesset perturbation theory (MP3)  
> c4-mp4(sdq) | 4th-order MP perturbation theory (MP4) less triples  
> c4-mp4 | full MP4  
> c4-cc2 | approximate coupled cluster singles and doubles (CC2)  
> c4-ccsd | coupled cluster singles and doubles (CCSD)  
> c4-cc3 | approximate CC singles, doubles, and triples (CC3)  
> c4-ccsd(t) | CCSD with perturbative triples (CCSD(T))  
> c4-ccsdt | coupled cluster singles, doubles, and triples (CCSDT)  
> cfour | **expert** full control over cfour program  
  
Examples:
    
[code] 
    >>> # [1] Coupled-cluster singles and doubles calculation with psi code
    >>> energy('ccsd')
    
[/code]
[code] 
    >>> # [2] Charge-transfer SAPT calculation with scf projection from small into
    >>> #     requested basis, with specified projection fitting basis
    >>> set basis_guess true
    >>> set df_basis_guess jun-cc-pVDZ-JKFIT
    >>> energy('sapt0-ct')
    
[/code]
[code] 
    >>> # [3] Arbitrary-order MPn calculation
    >>> energy('mp7')
    
[/code]
[code] 
    >>> # [4] Converge scf as singlet, then run detci as triplet upon singlet reference
    >>> # Note that the integral transformation is not done automatically when detci is run in a separate step.
    >>> molecule H2 {\n0 1\nH\nH 1 0.74\n}
    >>> set basis cc-pVDZ
    >>> set reference rohf
    >>> scf_e, scf_wfn = energy('scf', return_wfn=True)
    >>> H2.set_multiplicity(3)
    >>> core.MintsHelper(scf_wfn.basisset()).integrals()
    >>> energy('detci', ref_wfn=scf_wfn)
    
[/code]
[code] 
    >>> # [5] Run two CI calculations, keeping the integrals generated in the first one.
    >>> molecule ne {\nNe\n}
    >>> set basis cc-pVDZ
    >>> cisd_e, cisd_wfn = energy('cisd', return_wfn=True)
    >>> energy('fci', ref_wfn=cisd_wfn)
    
[/code]
[code] 
    >>> # [6] Can automatically perform complete basis set extrapolations
    >>> energy("CCSD/cc-pV[DT]Z")
    
[/code]
[code] 
    >>> # [7] Can automatically perform delta corrections that include extrapolations
    >>> # even with a user-defined extrapolation formula. See sample inputs named
    >>> # cbs-xtpl* for more examples of this input style
    >>> energy("MP2/aug-cc-pv([d,t]+d)z + d:ccsd(t)/cc-pvdz", corl_scheme=myxtplfn_2)
    
[/code]
