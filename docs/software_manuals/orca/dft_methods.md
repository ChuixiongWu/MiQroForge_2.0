# DFT Methods

## Page 52

ORCA Manual, Release 6.0
4.2.2 Density Functional Methods
For density functional calculations a number of standard functionals can be selected via the “simple input” feature.
Since any of these keywords will select a DFT method, the keyword “DFT” is not needed in the input. Further func-
tionals are available via the %method block. References are given in Section [sec:model.dft.functionals.detailed]
Local and gradient corrected functionals
HFS
Hartree–Fock–Slater Exchange only functional
LDA or LSD
Local density approximation (defaults to VWN5)
VWN or VWN5
Vosko-Wilk-Nusair local density approx. parameter set “V”
VWN3
Vosko-Wilk-Nusair local density approx. parameter set “III”
PWLDA
Perdew-Wang parameterization of LDA
BP86 or BP
Becke ‘88 exchange and Perdew ‘86 correlation
BLYP
Becke ‘88 exchange and Lee-Yang-Parr correlation
OLYP
Handy’s “optimal” exchange and Lee-Yang-Parr correlation
GLYP
Gill’s ‘96 exchange and Lee-Yang-Parr correlation
XLYP
The Xu and Goddard exchange and Lee-Yang-Parr correlation
PW91
Perdew-Wang ‘91 GGA functional
mPWPW
Modified PW exchange and PW correlation
mPWLYP
Modified PW exchange and LYP correlation
PBE
Perdew-Burke-Erzerhoff GGA functional
RPBE
“Modified” PBE
REVPBE
“Revised” PBE
RPW86PBE
PBE correlation with refitted Perdew ‘86 exchange
PWP
Perdew-Wang ‘91 exchange and Perdew ‘86 correlation
Hybrid functionals
B1LYP
The one-parameter hybrid functional with Becke ‘88 exchange and Lee-Yang-Parr correlation
(25% HF exchange)
B3LYP
and
B3LYP/G
The popular B3LYP functional (20% HF exchange) as defined in the TurboMole program
system and the Gaussian program system, respectively
O3LYP
The Handy hybrid functional
X3LYP
The Xu and Goddard hybrid functional
B1P
The one-parameter hybrid version of BP86
B3P
The three-parameter hybrid version of BP86
B3PW
The three-parameter hybrid version of PW91
PW1PW
One-parameter hybrid version of PW91
mPW1PW
One-parameter hybrid version of mPWPW
mPW1LYP
One-parameter hybrid version of mPWLYP
PBE0
One-parameter hybrid version of PBE
REVPBE0
“Revised” PBE0
REVPBE38
“Revised” PBE0 with 37.5% HF exchange
BHANDHLYP
Half-and-half hybrid functional by Becke
32
Chapter 4. General Structure of the Input File

## Page 53

ORCA Manual, Release 6.0
Meta-GGA and hybrid meta-GGA functionals
TPSS
The TPSS meta-GGA functional
TPSSh
The hybrid version of TPSS (10% HF exchange)
TPSS0
A 25% exchange version of TPSSh that yields improved energetics
M06L
The Minnesota M06-L meta-GGA functional
M06
The M06 hybrid meta-GGA (27% HF exchange)
M062X
The M06-2X version with 54% HF exchange
PW6B95
Hybrid functional by Truhlar
B97M-V
Head-Gordon’s DF B97M-V with VV10 nonlocal correlation
B97M-D3BJ
Modified version of B97M-V with D3BJ correction by Najibi and Goerigk
B97M-D4
Modified version of B97M-V with DFT-D4 correction by Najibi and Goerigk
SCANfunc
Perdew’s SCAN functional
r2SCAN
Regularized and restored SCAN functional by Furness, Sun et. al.
r2SCANh
Global hybrid variant of 𝑟2 SCAN with 10% HF exchange
r2SCAN0
Global hybrid variant of 𝑟2 SCAN with 25% HF exchange
r2SCAN50
Global hybrid variant of 𝑟2 SCAN with 50% HF exchange
Range-separated hybrid functionals
wB97
Head-Gordon’s fully variable DF 𝜔B97
wB97X
Head-Gordon’s DF 𝜔B97X with minimal Fock exchange
wB97X-D3
Chai’s refit incl. D3 in its zero-damping version
wB97X-D4
Modified version of 𝜔B97X-V with DFT-D4 correction by Najibi and Goerigk
wB97X-D4rev
Modified version of 𝜔B97X-V with DFT-D4 correction by Grimme et al.
wB97X-V
Head-Gordon’s DF 𝜔B97X-V with VV10 nonlocal correlation
wB97X-D3BJ
Modified version of 𝜔B97X-V with D3BJ correction by Najibi and Goerigk
wB97M-V
Head-Gordon’s DF 𝜔B97M-V with VV10 nonlocal correlation
wB97M-D3BJ
Modified version of 𝜔B97M-V with D3BJ correction by Najibi and Goerigk
wB97M-D4
Modified version of 𝜔B97M-V with DFT-D4 correction by Najibi and Goerigk
wB97M-D4rev
Modified version of 𝜔B97M-V with DFT-D4 correction by Grimme et al.
CAM-B3LYP
Handy’s fit
LC-BLYP
Hirao’s original application
LC-PBE
range-separated PBE-based hybrid functional with 100% Fock exchange in the long-
range regime
wr2SCAN
Range-separated hybrid variant of 𝑟2 SCAN with 0-100% HF exchange
Perturbatively corrected double-hybrid functionals
Add the prefix RI- or DLPNO- to use the respective approximation for the MP2 part.
4.2. Keyword Lines
33

## Page 54

ORCA Manual, Release 6.0
B2PLYP
Grimme’s mixture of B88, LYP, and MP2
mPW2PLYP
mPW exchange instead of B88, which is supposed to improve on weak interac-
tions.
B2GP-PLYP
Gershom Martin’s “general purpose” reparameterization
B2K-PLYP
Gershom Martin’s “kinetic” reparameterization
B2T-PLYP
Gershom Martin’s “thermochemistry” reparameterization
PWPB95
Goerigk and Grimme’s mixture of modified PW91, modified B95, and SOS-
MP2
PBE-QIDH
Adamo and co-workers’ “quadratic integrand” double hybrid with PBE ex-
change and correlation
PBE0-DH
Adamo and co-workers’ PBE-based double hybrid
DSD-BLYP
Gershom Martin’s “general purpose” double-hybrid with B88 exchange, LYP
correlation and SCS-MP2 mixing, i.e. not incl. D3BJ correction
DSD-PBEP86
Gershom Martin’s “general purpose” double-hybrid with PBE exchange, P86
correlation and SCS-MP2 mixing, i.e. not incl. D3BJ correction
DSD-PBEB95
Gershom Martin’s “general purpose” double-hybrid with PBE exchange, B95
correlation and SCS-MP2 mixing, i.e. not incl. D3BJ correction
revDSD-PBEP86/2021,
revDSD-PBEP86-D4/2021
Double-Hybrid Functional with with PBE exchange, B95 correlation and SCS-
MP2 Mixing
revDOD-PBEP86/2021,
revDOD-PBEP86-D4/2021
Double-Hybrid Functional with with PBE exchange, B95 correlation and SOS-
MP2 Mixing
Pr2SCAN50
Global SOS-double-hybrid variant of 𝑟2 SCAN with 50% HF exchange
Pr2SCAN69
Global SOS-double-hybrid variant of 𝑟2 SCAN with 69% HF exchange
kPr2SCAN50
Global SOS-double-hybrid variant of 𝑟2 SCAN with 50% HF exchange and
kappa-regularized MP2
Range-separated double-hybrid functionals
Add the prefix RI- or DLPNO- to use the respective approximation for the MP2 part.
wB2PLYP
Goerigk and Casanova-Páez’s range-separated DHDF, with the correlation
contributions based on B2PLYP, optimized for excitation energies
wB2GP-PLYP
Goerigk and Casanova-Páez’s range-separated DHDF, with the correlation
contributions based on B2GP-PLYP, optimized for excitation energies
RSX-QIDH
range-separated version of the PBE-QIDH double-hybrid by Adamo and co-
workers
RSX-0DH
range-separated version of the PBE-0DH double-hybrid by Adamo and co-
workers
wB88PP86
Casanova-Páez and Goerigk’s range-separated DHDF based on Becke88 ex-
change and P86 correlation, optimized for excitation energies
wPBEPP86
Casanova-Páez and Goerigk’s range-separated DHDF based on PBE ex-
change and P86 correlation, optimized for excitation energies
wB97M(2)
Mardirossian and Head-Gordon’s 𝜔B97M(2) range-separated meta-GGA
DHDF including VV10 non-local correlation: must be used with 𝜔B97M-V
orbitals! See DFT Calculations with Second Order Perturbative Correction
(Double-Hybrid Functionals).
wPr2SCAN50
Range-separated SOS-double-hybrid variant of 𝑟2 SCAN with 50-100% HF
exchange
34
Chapter 4. General Structure of the Input File

## Page 55

ORCA Manual, Release 6.0
Global and range-separated double-hybrid functionals with spin-component and spin-opposite
scaling
Add the prefix RI- or DLPNO- to use the respective approximation for the MP2 part.
wB97X-2
Chai and Head-Gordon’s 𝜔B97X-2(TQZ) range-separated GGA-based
DHDF with spin-component scaling
SCS/SOS-B2PLYP21
spin-opposite scaled version of B2PLYP optimized for excited states by
Casanova-Páez and Goerigk (SCS fit gave SOS version; SOS only applies
to the CIS(D) component)
SCS-PBE-QIDH
spin-component scaled version of PBE-QIDH optimized for excited states by
Casanova-Páez and Goerigk (SCS only applies to the CIS(D) component)
SOS-PBE-QIDH
spin-opposite scaled version of PBE-QIDH optimized for excited states by
Casanova-Páez and Goerigk (SOS only applies to the CIS(D) component)
SCS-B2GP-PLYP21
spin-component scaled version of B2GP-PLYP optimized for excited states
by Casanova-Páez and Goerigk (SCS only applies to the CIS(D) component)
SOS-B2GP-PLYP21
spin-opposite scaled version of B2GP-PLYP optimized for excited states by
Casanova-Páez and Goerigk (SOS only applies to the CIS(D) component)
SCS/SOS-wB2PLYP
spin-opposite scaled version of 𝜔B2PLYP optimized for excited states by
Casanova-Páez and Goerigk (SCS fit gave SOS version; SOS only applies
to the CIS(D) component)
SCS-wB2GP-PLYP
spin-component scaled version of 𝜔B2GP-PLYP optimized for excited states
by Casanova-Páez and Goerigk (SCS only applies to the CIS(D) component)
SOS-wB2GP-PLYP
spin-opposite scaled version of 𝜔B2GP-PLYP optimized for excited states by
Casanova-Páez and Goerigk (SOS only applies to the CIS(D) component)
SCS-RSX-QIDH
spin-component scaled version of RSX-QIDH optimized for excited states by
Casanova-Páez and Goerigk (SCS only applies to the CIS(D) component)
SOS-RSX-QIDH
spin-opposite scaled version of RSX-QIDH optimized for excited states by
Casanova-Páez and Goerigk (SOS only applies to the CIS(D) component)
SCS-wB88PP86
spin-component scaled version of 𝜔B88PPBE86 optimized for excited states
by Casanova-Páez and Goerigk (SCS only applies to the CIS(D) component)
SOS-wB88PP86
spin-opposite scaled version of 𝜔B88PPBE86 optimized for excited states by
Casanova-Páez and Goerigk (SOS only applies to the CIS(D) component)
SCS-wPBEPP86
spin-component scaled version of 𝜔PBEPPBE86 optimized for excited states
by Casanova-Páez and Goerigk (SCS only applies to the CIS(D) component)
SOS-wPBEPP86
spin-opposite scaled version of 𝜔PBEPPBE86 optimized for excited states by
Casanova-Páez and Goerigk (SOS only applies to the CIS(D) component)
Composite Methods
HF-3c
HF-based composite method by Grimme et al. emplyoing the MINIX basis
set
B97-3c
GGA composite method by Grimme et al.
employing a modified def2-
mTZVP basis set
R2SCAN-3c
meta-GGA composite method by Grimme et al. employing a modified def2-
mTZVPP basis set
PBEh-3c
Hybrid (42% HF exchange) composite method by Grimme et al. employing
a modified def2-mSVP basis set
wB97X-3c
Range-separated hybrid composite DFT method by Grimme et al. employing
a polarized valence double-𝜁basis set
4.2. Keyword Lines
35

## Page 56

ORCA Manual, Release 6.0
Dispersion corrections
See DFT Calculations with Atom-pairwise Dispersion Correction and Treatment of Dispersion Interactions with
DFT-D3 for details.
D4
density dependent atom-pairwise dispersion correction with Becke-Johnson damping and ATM
D3BJ
Atom-pairwise dispersion correction to the DFT energy with Becke-Johnson damping
D3ZERO
Atom-pairwise dispersion correction with zero damping
D2
Empirical dispersion correction from 2006 (not recommended)
Non-local correlation
See DFT Calculations with the Non-Local, Density Dependent Dispersion Correction (VV10): DFT-NL for details.
NL
Does a post-SCF correction on the energy only
SCNL
Fully self-consistent approach, adding the VV10 correlation to the KS Hamiltonian
4.3 Basis Sets
4.3.1 Standard basis set library
There are standard basis sets that can be specified via the “simple input” feature in the keyword line. However, any
basis set that is not already included in the ORCA library can be provided either directly in the input or through an
external file. See the BASIS input block for a full list of internal basis sets and various advanced aspects (section
Choice of Basis Set). Effective core potentials and their use are described in section Effective Core Potentials.
Pople-style basis sets
STO-3G
Minimal basis set(H–I)
3-21G
Pople 3-21G (H–Cs)
3-21GSP
Buenker 3-21GSP (H–Ar)
4-22GSP
Buenker 4-22GSP (H–Ar)
6-31G
Pople 6-31G and its modifications (H–Zn)
m6-31G
Modified 6-31G for 3d transition metals (Sc–Cu)
6-311G
Pople 6-311G and its modifications (H–Br)
Polarization functions for the 6-31G basis set:
* or (d)
One set of first polarization functions on all atoms except H
** or (d,p)
One set of first polarization functions on all atoms
Further combinations:
(2d), (2df), (2d,p), (2d,2p), (2df,2p), (2df,2pd)
Polarization functions for the 6-311G basis set: All of the above plus (3df) and (3df,3pd)
Diffuse functions for the 6-31G and 6-311G basis sets:
+
before
“G”
Include diffuse functions on all atoms except H (e.g. 6-31+G)
++
before
“G”
Include diffuse functions on all atoms. Works only when H polarization is already included,
e.g. 6-31++G(d,p)
36
Chapter 4. General Structure of the Input File