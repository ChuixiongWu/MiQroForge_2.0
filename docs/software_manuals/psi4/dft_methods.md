# DFT: Density Functional Theory

# DFT: Density Functional Theory

_Code author: Robert M. Parrish, Justin M. Turney, and Daniel G. A. Smith_

_Section author: Robert M. Parrish_

_Module:_ [Keywords](autodir_options_c/module__scf.html#apdx-scfdft), [PSI Variables](autodir_psivariables/module__scf.html#apdx-scf-psivar), [LIBFUNCTIONAL](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/libfunctional), [LIBFOCK](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/libfock), [LIBSCF_SOLVER](https://github.com/psi4/psi4/blob/master/psi4/src/psi4/libscf_solver)

Both density functional theory and Hartree–Fock theory are controlled through the SCF module, and the [SCF Introduction](scf.html#sec-scfintro) section is also relevant here.

Note

Starting version 1.5, the [WCOMBINE](autodoc_glossary_options_c.html#term-WCOMBINE-SCF) option is temporarily disabled.

Note

Starting version 1.4 (tag v1.4a1 in the development repository), PSI4 uses an updated and extended (to 104 elements) set of Bragg-Slater radii. This leads to minimal deviations in absolute energies (1E-06 au) and relative energies (below 0.002 kcal/mol for S22), depending also on the applied grid, compared to older versions. We advise not to mix absolute energies absolute energies from before and after this change for the calculation of relative energies.

Note

After May 2017 (anytime after the v1.1 release), PSI4 switched from hand- (+Matlab) coded functionals to Libxc. Thus many DFT results will be slightly different. Functionals more than slightly different are B97-D, wB97X (note, _not_ wB97X-D), SOGGA, DFDL, and M05.

## Theory

Generalized Kohn–Sham Density Functional Theory (KS-DFT) [[Kohn:1965:A1133]](bibliography.html#kohn-1965-a1133) [[Parr:1989]](bibliography.html#parr-1989) is one of the primary workhorses of modern computational chemistry due to its phenomenal accuracy/cost ratio.

Pure Kohn–Sham DFT is built on the Hohenberg–Kohn theorems [[Hohenberg:1964:136]](bibliography.html#hohenberg-1964-136) which states: A) the energy is a universal functional of the one-particle electronic density and B) there exists a set of noninteracting quasiparticles with the same density as the true set of electrons, with the quasiparticle states determined as eigenvectors of an effective one-body potential encapsulating the true \(N\)-body quantum effects. The former idea allows the electronic density to be dealt with instead of the much more complicated wavefunction, while the latter allows for the treatment of the troublesome kinetic energy term via the implicit one-body Kohn–Sham orbitals. KS-DFT borrows much of the machinery of Hartree–Fock, as is evident by looking at the energy expression,

[\begin{split}E_{\mathrm{KS}} &= \sum_{i} \langle i | \hat h | i \rangle \+ \frac 1 2 \sum_{i,j} [ii|jj] + E_{\mathrm{xc}} [\rho_\alpha, \rho_\beta] \\\ &= D_{\mu\nu}^{\mathrm{T}}\left(T_{\mu\nu} + V_{\mu\nu}\right) + \frac{1}{2} D_{\mu\nu}^{\mathrm{T}} D_{\lambda\sigma}^{\mathrm{T}} (\mu\nu|\lambda\sigma) + E_{\mathrm{xc}} [\rho_\alpha, \rho_\beta]\end{split}]

Here, \(T\) is the noninteracting quasiparticle kinetic energy operator, \(V\) is the nucleus-electron attraction potential, \(D^{\mathrm{T}}\) is the total electron density matrix, and \(E_{\mathrm{xc}} [\rho_\alpha, \rho_\beta]\) is the (potentially nonlocal) exchange, correlation, and residual kinetic energy functional. The residual kinetic energy term is usually quite small, and is often ignored, hence \(E_{\mathrm{xc}}\) is often referred to as simply the exchange-correlation functional (exchange _and_ correlation, not just exchange-type correlation).

In practice, the first few generations of KS-DFT functionals were chosen to be local, meaning that the form of the exchange correlation energy is an integral over all of space of a function depending only on local information in the density, such as the density value or derivatives. The simplest variants are Local Spin-Density Approximations (LSDA), which depend only on the spin density \(\rho_\alpha\) or \(\rho_\beta\),

[\rho_\sigma (\vec r_1) = D_{\mu\nu}^{\sigma} \phi_{\mu} (\vec r_1) \phi_\nu (\vec r_1)]

The most popular variants are Generalized Gradient Approximation (GGA) functionals which use the norm of the density gradient \(\gamma_{\alpha\alpha}\), \(\gamma_{\alpha\beta}\) or \(\gamma_{\beta\beta}\) to build an inhomogeneity parameter.

[\gamma_{\alpha\alpha} (\vec r_1) = \nabla \rho_{\alpha} (\vec r_1) \cdot \nabla \rho_{\alpha} (\vec r_1)]

[\gamma_{\alpha\beta} (\vec r_1) = \nabla \rho_{\alpha} (\vec r_1) \cdot \nabla \rho_{\beta} (\vec r_1)]

where,

[\nabla \rho_{\sigma} (\vec r_1) = 2 D_{\mu\nu}^{\sigma} \phi_{\mu} (\vec r_1) \nabla \phi_{\nu} (\vec r_1)]

GGA functionals are essentially the same cost as LSDA functionals and are often considerably more accurate.

Another local variant which has gained some popularity (though perhaps not as much as GGA functionals) is the meta approximation, in which information about the second derivative of the density is incorporated. The most canonical variant of these functionals rely on the spin kinetic energy density \(\tau_\alpha\) and \(\tau_\beta\),

[\tau_\sigma(\vec r_1) = \sum_{i} \left | \nabla \psi_i^{\sigma} (\vec r_1) \right | ^2 = \sum_{i} \left | C_{\mu i}^{\sigma} \nabla \phi_{\mu} (\vec r_1) \right | ^2 = D_{\mu\nu}^{\sigma} \nabla \phi_{\mu} (\vec r_1) \cdot \nabla \phi_{\nu} (\vec r_1)]

A generic local meta-GGA functional may then be written as,

[E_{\mathrm{xc}}^{\mathrm{DFA}} = \int_{\mathbb{R}^3} f_{\mathrm{xc}} \left( \rho_{\alpha} (\vec r_1), \rho_{\beta} (\vec r_1), \gamma_{\alpha\alpha} (\vec r_1), \gamma_{\alpha\beta} (\vec r_1), \gamma_{\beta\beta} (\vec r_1), \tau_{\alpha} (\vec r_1), \tau_{\beta} (\vec r_1) \right) \ \mathrm{d} ^3 r_1]

The potential corresponding to this energy functional is,

[ \begin{align}\begin{aligned}V_{\mu\nu}^{\mathrm{xc},\alpha} =\\\\\int_{\mathbb{R}^3} \left(\frac{\partial f}{\rho_\alpha}\right) \phi_{\mu} \phi_{\nu} \ \mathrm{d} ^3 r_1\end{aligned}\end{align} ]

[+ \int_{\mathbb{R}^3} \left(2 \frac{\partial f}{\gamma_{\alpha\alpha}} \nabla \rho_\alpha + \frac{\partial f}{\gamma_{\alpha\beta}}\nabla \rho_\beta \right) \nabla\left(\phi_{\mu} \phi_{\nu}\right) \ \mathrm{d} ^3 r_1]

[+ \int_{\mathbb{R}^3} \left(\frac{\partial f}{\tau_\alpha}\right) \nabla \phi_{\mu} \nabla \phi_{\nu} \ \mathrm{d} ^3 r_1]

This potential is used to build the Kohn–Sham matrix,

[F_{\mu\mu}^{\alpha} = H_{\mu\nu} + J_{\mu\nu} + V_{\mu\nu}^{\mathrm{xc},\alpha}]

which is diagonalized to form the Kohn–Sham orbitals in the same manner as in Hartree–Fock.

In practice the local functional kernel \(f_{\mathrm{xc}}\) and its required partial derivatives are exceedingly complex and are not analytically integrable. In this case, atom-centered numerical quadratures are used to evaluate the Kohn–Sham potentials and energies to a high degree of accuracy. The evaluation of these numerical integrals can be made to be linear scaling with a reasonable amount of cleverness (mostly related to the fact that the basis functions decay exponentially), meaning that the Coulomb and diagonalization steps become rate limiting. This enormous potential speed gain over Hartree–Fock with potentially exact treatment of electron correlation for “free” was one of the primary motivations for KS-DFT’s adoption by chemists in the late 1980s and early 1990s.

Unfortunately, local KS-DFT exhibits several spectacular failures, most of which stem from the exponential decay of the local Kohn–Sham potential, which cannot encapsulate long-range information in the exchange and correlation holes. In the exchange hole, this manifests as the problem of Many-Electron Self-Interaction Error (MSIE), which presents as spurious low-lying charge transfer states in excited-state calculations, eventual metallic breakdown in extended insulators, poor thermochemistry, and complete lack of a derivative discontinuity in the chemical potential as integer particle numbers are crossed. On the correlation side, this is primarily observed in the inability of KS-DFT to treat dispersion interactions.

Generalized Kohn–Sham (GKS) functionals incorporate long-range information into the functional through orbital-dependent contributions, and are designed to combat the failures of local KS-DFT, particularly the MSIE on the exchange side. Note that these functionals are often referred to as “implicit” density functionals, as the orbitals are themselves functionals of the Kohn–Sham potential.

The simplest form of an exchange-side GKS is the global hybrid ansatz, in which some fraction of the exact Hartree–Fock exchange of the noninteracting quasiparticles is added to the functional, with the local part of the exchange functional decreased by the corresponding amount. Note that the term “exact-exchange” refers to the Hartree–Fock being the exact exchange energy of the noninteracting quasiparticles, not the true electrons. Therefore, adding 100% exact exchange is not physically reasonable, and will often lead to extremely poor results. The fraction of exact-exchange, denoted \(\alpha\), is often determined by adiabatic or heuristic arguments and is typically around 25%. The addition of exact exchange borrows another piece from an existing Hartree–Fock code, with the caveat that Hartree–Fock exchange is often much more costly to obtain than the Coulomb matrix. The global hybrid ansatz has become exceedingly popular, with functionals such as the ubiquitous B3LYP often producing absurdly accurate results.

A more advanced GKS functional technology which has developed enormous popularity in recent years is the Long-Range Corrected (LRC) ansatz. LRC recognizes that the local DFA is potentially exact at short range in the exchange hole, and that the hybrid-exchange energy of the noninteracting quasiparticles is also exact for true electrons at long range in the exchange hole. Therefore LRC switches from DFA at short range to hybrid exchange at long range, typically using the function \(\mathrm{erf}(\omega r_{12})\) as a partition function.

Tying all these pieces together, a full LRC-hybrid GKS functional has the generic form,

[E_{\mathrm{xc}} = (1-\alpha) \int_{\mathrm{R}^3} f_{\mathrm{xc}} \left( \rho_{\alpha} (\vec r_1), \rho_{\beta} (\vec r_1), \gamma_{\alpha\alpha} (\vec r_1), \gamma_{\alpha\beta} (\vec r_1), \gamma_{\beta\beta} (\vec r_1), \tau_{\alpha} (\vec r_1), \tau_{\beta} (\vec r_1) ; \omega \right) \ \mathrm{d} ^3 r_1]

[-\frac{1}{2} \sum_{i,j} \delta_{\sigma_{i} \sigma_{j}} \alpha \iint_{\mathrm{R}^6} \phi_{i}^1 \phi_{j}^1 \frac{1}{r_{12}} \phi_{i}^2 \phi_{j}^2 \ \mathrm{d}^3 r_1 \ \mathrm{d}^3 r_2]

[-\frac{1}{2} \sum_{i,j} \delta_{\sigma_{i} \sigma_{j}} (1-\alpha)\iint_{\mathrm{R}^6} \phi_{i}^1 \phi_{j}^1 \frac{\mathrm{erf}(\omega r_{12})}{r_{12}} \phi_{i}^2 \phi_{j}^2 \ \mathrm{d}^3 r_1 \ \mathrm{d}^3 r_2]

For LRC functionals, the choice of range-separation parameter \(\omega\) has been the subject of considerable activity since the inception of LRC functionals. Some authors advocate a static range-separation parameter determined by optimization over a test set of chemical systems. However, a more physically-motivated and often more accurate approach is the idea of “gap fitting” or “optimal tuning” or simply “tuning.” The most popular tuned-LRC approach is IP-fitting, in which the \(\omega\) is varied until the Koopman’s IP (the opposite of the HOMO energy) matches the true IP (the difference between \(N-1\)-electron and \(N\)-electron total energies), within the LRC functional ansatz. This guarantees the asymptotics of the exchange potential,

[\lim_{r\rightarrow\infty} v_{\mathrm{x}}^{\mathrm{tuned-LRC}} (r) = - \frac{1}{r} + I_{\mathrm{IP}} + \epsilon_{\mathrm{HOMO}}]

Note that LRC functionals with default \(\omega\) only capture the \(-1/r\) dependence,

[\lim_{r\rightarrow\infty} v_{\mathrm{x}}^{\mathrm{LRC}} (r) = - \frac{1}{r},]

hybrid functionals only capture part of the \(-1/r\) dependence,

[\lim_{r\rightarrow\infty} v_{\mathrm{x}}^{\mathrm{Hybrid}} (r) = - \frac{\alpha}{r},]

and local functionals decay exponentially, resulting in completely incorrect asymptotics,

[\lim_{r\rightarrow\infty} v_{\mathrm{x}}^{\mathrm{Local}} (r) = 0]

IP-tuned LRC functionals effectively pin the chemical potential at \(N\) electrons to the correct value determined by the ionization potential. This often cleans up the MSIE problem for a surprisingly large number of high-lying occupied orbitals, as determined by fractional particle curves. Other gap fitting techniques involving the electron affinity or band gap are sometimes also used. IP-fitting is found to be particularly critical for the qualitative determination of excited state ordering in many low band-gap systems.

For dispersion-bound complexes, a very simple additive empirical dispersion potential, based on a damped Lennard-Jones potential can often produce remarkably accurate results with KS-DFT. This approach was championed by Grimme, whose “-D2” and more modern “-D3” approaches are a de facto industry standards.

## Minimal Input

Minimal input for a KS-DFT computation is a molecule block, basis set option, and a call to `energy('b3lyp')` (or other valid functional name):
 
    molecule {
    He
    }
    
    set basis sto-3g
    
    energy('b3lyp')
    

This will run a B3LYP Restricted Kohn–Sham (RKS) on neutral singlet Helium in \(D_{2h}\) spatial symmetry with a minimal `STO-3G` basis, 1.0E-6 energy and density convergence criteria, a DF ERI algorithm, symmetric orthogonalization, DIIS, and a core Hamiltonian guess (because single atom). For more information on any of these options, see the relevant section below, or in the preceding [Hartree–Fock section](scf.html#sec-scf).

## Spin/Symmetry Treatment

PSI4 implements the most popular spin specializations of KS-DFT, including:

Restricted Kohn–Sham (RKS) [Default]
    

Appropriate only for closed-shell singlet systems, but twice as efficient as the other flavors, as the alpha and beta densities are constrained to be identical.

Unrestricted Kohn–Sham (UKS)
    

Appropriate for most open-shell systems and fairly easy to converge. The spatial parts of the alpha and beta orbitals are fully independent of each other, which allows a considerable amount of flexibility in the wavefunction. However, this flexibility comes at the cost of spin symmetry; the resultant wavefunction may not be an eigenfunction of the \(\hat S^2\) operator. However, spin contamination is usually less of a problem with UKS than with UHF, as the spin contamination of the noninteracting quasiparticles (the \(S^2\) metric printed in the output) is usually a severe overestimation of the spin contamination of the true electrons.

These are set in the [REFERENCE](autodoc_glossary_options_c.html#term-REFERENCE-SCF) option.

Note that there are not equivalents to ROHF or CUHF, _e.g._ , no ROKS or CUKS. This is because ROHF is implicitly assumed to be followed by a correlated method which can break the positive definiteness of the spin polarization. KS-DFT with the true functional is expected to be the final step, thus restricting the solution to positive definite spin polarization is not physical. See the section in [[Szabo:1982]](bibliography.html#szabo-1982) on methyl radical for an example.

## Functional Selection

PSI4 features an extensive list of LSDA, GGA, Meta, Hybrid, LRC, and -D functionals. These can be specified by a variety of means. Perhaps the simplest is to use the functional name as the energy procedure call:
 
    energy('b3lyp')
    

Note that if you are running an unrestricted computation, you should set the [REFERENCE](autodoc_glossary_options_c.html#term-REFERENCE-SCF) option before the call to `energy`:
 
    set reference uks
    energy('b3lyp')
    

The functional may also be manually specified by calling `energy` (or any driver function) with a `dft_functional` argument:
 
    energy('scf', dft_functional = 'b3lyp')
    

Another alternative is providing a specially crafted dict-ionary to the `dft_functional` argument:
 
    custom_functional = { "name": "my_unique_name", ... }
    energy('scf', dft_functional = custom_functional)
    

For further details about this so called dict_func syntax, see Advanced Functional Use and Manipulation.

For hybrid functionals, the fraction of exact exchange is controlled by the [DFT_ALPHA](autodoc_glossary_options_c.html#term-DFT_ALPHA-SCF) option. For the LRC functionals, the fraction of long-range Hartree–Fock and short-range DFA is controlled by the [DFT_OMEGA](autodoc_glossary_options_c.html#term-DFT_OMEGA-SCF) option. Changing these will override the default behavior of the requested functional.

A brief summary of some of the more notable functionals in PSI4, and links to the complete listing of all functionals of each class are presented below:

[All Functionals](dft_byfunctional.html#table-dft-all)
    

All functionals, including LSDA-only functionals. Note that here and throughout, functionals which end in _X or _C are exchange or correlation only, and should not be used for most production-level computations. Examples include PBE_X and PBE_C, which contain the separate definitions of the PBE exchange and correlation holes. In most cases, the united PBE functional should be used instead.

[GGA Functionals](dft_byfunctional.html#table-dft-gga)
    

Many common GGA functionals. BLYP and PBE are probably among the best pure GGAs. Please do not use FT97 at the moment, as there are problems with the stability of the correlation hole. Don’t worry, it will definitely NaN on you if you try to use it.

[Meta Functionals](dft_byfunctional.html#table-dft-meta)
    

We have recently implemented the M05 classes of meta functionals in PSI4. Note that these functionals are not appropriate for modeling dispersion interactions, as they lack dispersion physics. A -D functional (Such as the much cheaper B97-D) should be used instead.

[Hybrid Functionals](dft_byfunctional.html#table-dft-hybrid)
    

Many common hybrid functionals, including the ubiquitous B3LYP. PBE0 and the B97 series are also quite good for many thermochemical problems.

[LRC Functionals](dft_byfunctional.html#table-dft-lrc)
    

LRC functionals are a particular area of interest of the PSI4 DFT team. LRC functionals are all denoted by a lower-case “w” in front of the standard DFA functional, such as wPBE. We offer a stable implementation of the Gill association function for wS and Head-Gordon’s wB97/wB97X functionals. Additionally, we are pleased to have recently completed a heavily conditioned implementation of the HJS exchange-hole model, which provides an analytical form for the short-range enhancement factor for wPBE, wPBEsol, and wB88. From a physics perspective, this implementation of wPBE is extremely useful for theoretical investigations, as it is parameter free, and properly integrated against the partition function in the exchange hole. We would like to thank Dr. Scuseria for providing helpful advice and a reference implementations of the older HSE exchange-hole model which led to the successful implementation of the HJS model.

[Double-Hybrid Functionals](dft_byfunctional.html#table-dft-dhybrid)
    

Double hybrids are percolating into PSI4. Note that these are only available with density-fitted, not conventional, MP2 algorithms.

[-D Functionals](dft_byfunctional.html#table-dft-disp)
    

We have several -D2 functionals implemented. -D3 functionls are available with the installation of Grimme’s [DFTD3 program](dftd3.html#sec-dftd3). For now, the pure-GGA B97-D functional of Grimme is remarkably accurate, and the hybrid B3LYP-D functional is also quite reliable.

Note: we have made a sincere effort to rigorously test all functionals implemented in PSI4 for correctness. If you find an error in a DFT functional or have a request for a new functional, please let us know on our forum or GitHub page.

## Grid Selection

PSI4 uses the standard Lebedev-Laikov spherical quadratures in concert with a number of radial quadratures and atomic partitioning schemes. The default grid in PSI4 is a Lebedev-Treutler (75,302) grid with a Treutler partition of the atomic weights.

Spherical grids are all of the extremely efficient Lebedev-Laikov type. Spherical grid resolution is controlled by the [DFT_SPHERICAL_POINTS](autodoc_glossary_options_c.html#term-DFT_SPHERICAL_POINTS-SCF) option, which may take one of the following values:

> [DFT_SPHERICAL_POINTS](autodoc_glossary_options_c.html#term-DFT_SPHERICAL_POINTS-SCF) | Order  
> ---|---  
> 6 | 3  
> 14 | 5  
> 26 | 7  
> 38 | 9  
> 50 | 11  
> 74 | 13  
> 86 | 15  
> 110 | 17  
> 146 | 19  
> 170 | 21  
> 194 | 23  
> 230 | 25  
> 266 | 27  
> 302 | 29  
> 350 | 31  
> 434 | 35  
> 590 | 41  
> 770 | 47  
> 974 | 53  
> 1202 | 59  
> 1454 | 65  
> 1730 | 71  
> 2030 | 77  
> 2354 | 83  
> 2702 | 89  
> 3074 | 95  
> 3470 | 101  
> 3890 | 107  
> 4334 | 113  
> 4802 | 119  
> 5294 | 125  
> 5810 | 131  
  
The spherical grids are rotated according to a common set of rules developed during the implementation of SG1. At the moment, the rules for tetrahedral, octohedral, and icosohedral systems are not complete, so there may be some ambiguity in the grid orientation for these systems.

Radial grid types are controlled by the [DFT_RADIAL_SCHEME](autodoc_glossary_options_c.html#term-DFT_RADIAL_SCHEME-SCF) option, which at the moment may be either `TREUTLER` or `BECKE`, while the number of radial points are controlled by the [DFT_RADIAL_POINTS](autodoc_glossary_options_c.html#term-DFT_RADIAL_POINTS-SCF) option, which is any positive integer (typically 50-100). The radial grids are “centered” on the Bragg-Slater radius of each atom, as described in Becke’s 1988 paper. If inaccurate integration is suspected in systems with anions or very diffuse basis functions, the [DFT_BS_RADIUS_ALPHA](autodoc_glossary_options_c.html#term-DFT_BS_RADIUS_ALPHA-SCF) option may be increased from 1.0 to a larger value to force the radial grid to span a larger extent in space.

The atomic weighting scheme is controlled by the [DFT_NUCLEAR_SCHEME](autodoc_glossary_options_c.html#term-DFT_NUCLEAR_SCHEME-SCF) option, which may be one of `TREUTLER`, `BECKE`, `STRATMANN`, `NAIVE`, or `SBECKE`. The last is a smoother variant of the BECKE scheme recently introduced by Laqua [[Laqua:2018:204111]](bibliography.html#laqua-2018-204111) that should behave better for weak interactions.

Pruning of the quadrature grid is controlled by the [DFT_PRUNING_SCHEME](autodoc_glossary_options_c.html#term-DFT_PRUNING_SCHEME-SCF) option. The options `ROBUST` and `TREUTLER` divide the grid into spherical regions based on the Bragg-Slater radius of each atom and apply different orders to them. The `ROBUST` scheme is a less aggressive variant of the `TREUTLER` approach and suitable for benchmark-level quality (MAD < 0.002 kcal/mol for the S22 with PBE/aug-cc-pVTZ for pruned versus unpruned grid). Our implementation of the `TREUTLER` scheme shows an error of 0.02 kcal/mol for the same benchmark. Both also reduce the grid order by 1 for H and He atoms and avoid any pruning of heavy atoms (Z >= 36) Other schemes mentioned in the keyword documentation (e.g. P_SLATER) are experimental and should be considered expert-only.

Once the molecular quadrature grid is built, the points are partitioned into blocks of points which are spatially close to each other. We use an octree algorithm for this procedure, which produces a good balance between spatial compactness of each block (which helps achieve linear scaling due to the exponential decay of the basis functions), and retaining a large number of points in each block (which helps keep the FLOP rate up by allowing for a reasonably large amount of BLAS3/BLAS2 work to form the densities and potentials in each block). For each block, a united set of significant basis functions is determined by the cutoff radius of each shell of basis functions. The size of this cutoff radius (and thereby the accuracy of the density/potential evaluation) can be varied by setting the [DFT_BASIS_TOLERANCE](autodoc_glossary_options_c.html#term-DFT_BASIS_TOLERANCE-SCF), which defaults to 1E-12. We are still exploring optimizations of the octree algorithm and the basis cutoffs, but it is likely that significant speed gains may be realized by relaxing the basis cutoff tolerance, with negligible decrease in accuracy.

Small density values can introduce numerical instabilities with some functionals that can result in trailing SCF convergence issues or even numerical failures (NaNs). If the default settings of the LibXC library are insufficient, a custom value can be request by setting [DFT_DENSITY_TOLERANCE](autodoc_glossary_options_c.html#term-DFT_DENSITY_TOLERANCE-SCF). For notorious cases a value of 1E-10 is sensible.

An example of a fully specified grid is as follows:
 
    molecule {
    H
    H 1 0.7
    }
    
    set {
    basis cc-pvdz
    scf_type df
    dft_spherical_points 590      # Often needed
    dft_radial_points 99          # Often needed
    dft_radial_scheme treutler    # Rarely needed
    dft_nuclear_scheme treutler   # Rarely needed
    dft_density_tolerance 1.0E-10 # Rarely needed
    dft_basis_tolerance 1.0E-11   # Can speed things up, but benchmark the error
    dft_pruning_scheme robust     # Generally safe and will speed things up
    }
    
    energy('b3lyp')
    

## ERI Algorithms

The ERI algorithms for the Coulomb and hybrid exchange are identical to [those for Hartree–Fock](scf.html#sec-scferi). However, for LRC functionals, the long-range exchange contributions to the Kohn–Sham matrix have only been implemented in the DF and DIRECT algorithms. The use of DF is highly recommended for KS-DFT, as the errors incurred by the density fitting approximation (in a proper -JKFIT auxiliary basis) are orders of magnitude smaller than the accuracy of any known functional.

Key representative methods supported by the SCF module in PSI4 are detailed in Table SCF Capabilities. Note from [SCF algorithm and convergence criteria defaults by calculation type 1](scf.html#table-conv-scf) that these SCF-level methods default to density-fitted reference; use [SCF_TYPE](autodoc_glossary_options_c.html#term-SCF_TYPE-GLOBALS) to select an alternate algorithm. SCF-level methods have no alternate implementations.

Detailed capabilities of the SCF module. “✓” runs analytically. Single underline “✓̲” is default module when [QC_MODULE](autodoc_glossary_options_c.html#term-QC_MODULE-GLOBALS) unspecified. Double underline “✓̳” is default algorithm type when type selector (e.g., [CC_TYPE](autodoc_glossary_options_c.html#term-CC_TYPE-GLOBALS)) unspecified. ◻ ◻ name ↓ → ◻ ◻ | ◻ [REFERENCE](autodoc_glossary_options_c.html#term-REFERENCE-SCF) → ◻ type[1] ↓ → [FREEZE_CORE](autodoc_glossary_options_c.html#term-FREEZE_CORE-GLOBALS)[2]→ | [QC_MODULE](autodoc_glossary_options_c.html#term-QC_MODULE-GLOBALS)=SCF Capabilities  
---|---|---  
Restricted (RHF) | Unrestricted (UHF) | Restricted Open (ROHF)  
[`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy") | [`gradient()`](api/psi4.driver.gradient.html#psi4.driver.gradient "psi4.driver.gradient")[3] | [`hessian()`](api/psi4.driver.hessian.html#psi4.driver.hessian "psi4.driver.hessian")[4] | [`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy") | [`gradient()`](api/psi4.driver.gradient.html#psi4.driver.gradient "psi4.driver.gradient")[3] | [`hessian()`](api/psi4.driver.hessian.html#psi4.driver.hessian "psi4.driver.hessian")[4] | [`energy()`](api/psi4.driver.energy.html#psi4.driver.energy "psi4.driver.energy") | [`gradient()`](api/psi4.driver.gradient.html#psi4.driver.gradient "psi4.driver.gradient")[3] | [`hessian()`](api/psi4.driver.hessian.html#psi4.driver.hessian "psi4.driver.hessian")[4]  
CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD | CV | DF | CD  
A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F | A | F  
hf | [SCF_TYPE](autodoc_glossary_options_c.html#term-SCF_TYPE-GLOBALS) | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  |  |  |  |  |  |   
svwn, LSDA DFT | [SCF_TYPE](autodoc_glossary_options_c.html#term-SCF_TYPE-GLOBALS) | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |   
pbe, GGA DFT | [SCF_TYPE](autodoc_glossary_options_c.html#term-SCF_TYPE-GLOBALS) | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  |  |  |  |  |  |  | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |   
b3lyp, Hybrid DFT | [SCF_TYPE](autodoc_glossary_options_c.html#term-SCF_TYPE-GLOBALS) | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  |  |  |  |  |  |  | ✓̲ |  | ✓̳ |  | ✓̲ |  | ✓̲ |  | ✓̳ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |   
wb97x, LRC DFT | [SCF_TYPE](autodoc_glossary_options_c.html#term-SCF_TYPE-GLOBALS) | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  |  |  |  |  |  |  |  |  | ✓̲ |  | ✓̳ |  |  |  | ✓̲ |  | ✓̳ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |   
b2plyp, DH DFT[5] | [SCF_TYPE](autodoc_glossary_options_c.html#term-SCF_TYPE-GLOBALS) | ✓̲ | ✓̲ | ✓̳ | ✓̳ | ✓̲ | ✓̲ |  |  |  |  |  |  |  |  |  |  |  |  | ✓̲ | ✓̲ | ✓̳ | ✓̳ | ✓̲ | ✓̲ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |   
  
## IP Fitting

In collaboration with the Bredas group, we have developed an automatic procedure for IP fitting of LRC functionals, based on a modified Regula-Falsi method. To perform IP fitting, one simply calls the [`ip_fitting()`](external_apis.html#psi4.driver.frac.ip_fitting "psi4.driver.frac.ip_fitting") Python macro, after setting up a standard LRC UKS computation. A representative example is:
 
    memory 512 MB
    
    molecule h2o {
    0 1  # must be neutral
    O
    H 1 1.0
    H 1 1.0 2 104.5
    # IP fitting runs in C1 symmetry
    }
    
    set {
    reference uks  # UKS, as we need to do neutral/cation
    basis cc-pvdz
    scf_type df
    }
    
    # Optional arguments are minimum omega, maximum omega, molecule object
    omega = ip_fitting('wb97', 0.4, 2.0, molecule=h2o)
    

This performs IP fitting on water for wB97/cc-pVDZ with density fitting. A number of neutral and cation single-point computations are run at various values of \(\omega\), though the later iterations are much faster due to reuse of the DF tensors, and starting from the neutral/cation orbitals of the previous \(\omega\). The procedure can also be assisted by providing a tighter guess for the bounds of \(\omega\). This small test case has a tuned \(\omega\) of 1.700, hence the bounds of 0.4 and 2.0. Larger systems, particularly conjugated systems, will typically have an optimized \(\omega\) between 0.1 and 0.5.

## Fractional Particle Curves

The behavior of the electronic energy and HOMO energy across fractional numbers of electrons is extremely useful for elucidating the MSIE behavior of various functional technologies. PSI4 features an efficient fractional-particle DFT code, written into the UKS spin specialization. Due to a combination of DIIS and reuse of integrals/guess orbitals across a range of fractional occupations, this code is able to perform fractional occupation curves for systems with up to 60 atoms, across a wide range of the particle number \(N\).

Two python macros exist for this code. The first is [`frac_traverse()`](external_apis.html#psi4.driver.frac.frac_traverse "psi4.driver.frac.frac_traverse"), which is used to investigate the fractional occupation behavior within one electron above and below the neutral. An example is:
 
    molecule h2o {
    0 1  # must be neutral
    O
    H 1 1.0
    H 1 1.0 2 104.5
    # FRAC jobs will be be run in C1 symmetry
    }
    
    set {
    reference uks  # UKS, as we need to do all kinds of weird stuff
    basis aug-cc-pvdz  # Augmented functions are very important on the anion side
    scf_type df
    }
    
    # Argument is functional.
    # Many optional arguments are available, see the python file
    frac_traverse('wb97', molecule=h2o)
    

The other macro is [`frac_nuke()`](external_apis.html#psi4.driver.frac.frac_nuke "psi4.driver.frac.frac_nuke"), which strips several electrons out of the system to gather information on the MSIE over a range of orbitals. The input is identical to the above, except that the [`frac_traverse()`](external_apis.html#psi4.driver.frac.frac_traverse "psi4.driver.frac.frac_traverse") call is substituted for something like:
 
    # Argument is the functional.
    # A useful optional argument is nmax, the total number of electrons to
    # strip out of the molecule, in this case, 2.
    # Many optional arguments are available, see the python file
    frac.frac_nuke('wb97', molecule=h2o, nmax = 2)
    

## Dispersion Corrections

[DFT-D dispersion corrections are discussed here.](dftd3.html#sec-dftd3)

[HF-3c and PBEh-3c dispersion and BSSE corrections are discussed here.](gcp.html#sec-gcp)

[DFT-NL dispersion corrections are discussed here.](dftnl.html#sec-dftnl)

## Recommendations

The KS-DFT code is quite new, but relatively complete. During code development, emphasis was placed on flexibility of functional technology, efficiency for medium to large systems in difficult electronic environments (_e.g._ , compact spatial extents, diffuse basis sets, low band-gaps, LRC and/or hybrid GKS functionals), and time to code completion. We are very interested in optimizing and extending the code, so expect performance gains and extensions to gradients/hessians and TDDFT in future releases.

Some rough guidelines for using the KS-DFT code are as follows,

  - Use DF for the ERI algorithm wherever possible.

  - PSI4 is a “tight” code, meaning we’ve set the default numerical cutoffs for integrals, grids, and convergence criteria in such a way that you will often get many more digits of precision than needed. You may be able to realize additional speed gains by loosening some of these thresholds. See [SCF Convergence](scf.html#table-conv-scf) for default convergence criteria.

  - Read the literature to determine which functional technology to use. The world contains far too many papers using B3LYP on noncovalent interactions without a -D.

The “best-practice” input file for KS-DFT is:
 
    memory 1 GB  # As much as you've got, the DF algorithm can use
    
    molecule {
    H
    H 1 0.7
    }
    
    set {
    basis cc-pvdz
    scf_type df
    guess sad
    }
    
    energy('b3lyp')
    

## Advanced Functional Use and Manipulation

New DFT functionals can be created from scratch from within the input file and accessed using the `dft_functional` keyword argument in the energy call:
 
    # DFT Custom Functional
    
    molecule h2o {
    0 1
    O
    H 1 1.0
    H 1 1.0 2 104.5
    }
    
    set {
    basis sto-3g
    dft_spherical_points 302
    dft_radial_points 99
    reference rks
    }
    
    pbe0 = {
        "name": "my_PBE0",
        "x_functionals": {"GGA_X_PBE": {"alpha": 0.75}},
        "x_hf": {"alpha": 0.25},
        "c_functionals": {"GGA_C_PBE": {}}
    }
    
    func_call = energy('SCF', dft_functional=pbe0)
    
    # as PBE0 is a pre-defined functional, the call above is equivalent to both below:
    func_call = energy('SCF', dft_functional="PBE0")
    func_call = energy('PBE0')
    

Supported keywords include:

>   - name: string, name of the functional. for custom defined functionals used for printing only.
> 
>   - xc_functionals: dict, definition of a complete (X + C) functional based in LibXC name
> 
>   - x_functionals: dict, definition of exchange functionals using LibXC names
> 
>   - c_functionals: dict, definition of correlation functionals using LibXC names
> 
>   - x_hf: dict, parameters dealing with exact (HF) exchange settings for hybrid DFT
> 
>   - c_mp2: dict, parameters dealing with MP2 correlation for double hybrid DFT
> 
>   - dispersion: dict, definition of dispersion corrections
> 
>   - citation: string, citation for the method, for printing purposes
> 
>   - description: string, description of the method, for printing purposes
> 
> 

The full interface is defined in [psi4/psi4/driver/procrouting/dft/dft_builder.py](https://github.com/psi4/psi4/blob/master/psi4/driver/procrouting/dft/dft_builder.py). All standard functionals provided in PSI4 are implemented in the `*_functionals.py` files in the same folder.
 
    """
    Superfunctional builder function & handlers.
    The new definition of functionals is based on a dictionary with the following structure
    dict = {
               "name":  "",       name of the functional - matched against name.lower() in method lookup
    
              "alias":  [""],     alternative names for the method in lookup functions, processed with .lower()
    
           "citation":  "",       citation of the method in the standard indented format, printed in output
    
        "description":  "",       description of the method, printed in output
    
     "xc_functionals":  {         definition of a full XC functional from LibXC
          "XC_METHOD_NAME": {}      must match a LibXC method, see libxc_functionals.py for examples
         },                         if present, the x/c_functionals and x_hf/c_mp2 parameters are not read!
    
      "x_functionals":  {          definition of X contributions
           "X_METHOD_NAME":  {       must match a LibXC method
                     "alpha": 1.0,   coefficient for (global) GGA exchange, by default 1.0
                     "omega": 0.0,   range-separation parameter
                 "use_libxc": False  whether "x_hf" parameters should be set from LibXC values for this method
                     "tweak": {},    tweak the underlying functional
         },
    
               "x_hf":  {          definition of HF exchange for hybrid functionals
                   "alpha": 0.0,             coefficient for (global) HF exchange, by default none
                    "beta": 0.0,             coefficient for long range HF exchange
                   "omega": 0.0,             range separation parameters
               "use_libxc": "X_METHOD_NAME"  reads the above 3 values from specified X functional
         },
    
      "c_functionals":  {          definition of C contributions
           "C_METHOD_NAME":  {       must match a LibXC method
                     "alpha": 1.0,   coefficient for (global) GGA correlation, by default 1.0
                     "tweak": {},    tweak the underlying functional
        },
    
              "c_mp2":  {          definition of MP2 correlation double hybrid functionals
                   "alpha": 0.0,     coefficient for MP2 correlation, by default none
                      "ss": 0.0,     coefficient for same spin correlation in SCS methods, forces alpha = 1.0
                      "os": 0.0,     coefficient for opposite spin correlation in SCS methods, forces alpha = 1.0
        },
    
         "dispersion":  {          definition of dispersion corrections
                   "type": "",       dispersion type - "d2", "d3zero", "d3bj" etc., see empirical_dispersion.py
                 "params": {},       parameters for the dispersion correction
                    "nlc": False     (optional) logical switch to turn off nlc (e.g. VV10) correction defined by LibXC
               "citation": "",       special reference for the dispersion correction parameters, appended to output
    

One can also use the `dft_functional` keyword argument to use the orbitals generated by DFT for correlated wavefunction methods:
 
    # MP2 with a PBE0 reference computation
    
    molecule h2o {
    0 1
    O
    H 1 1.0
    H 1 1.0 2 104.5
    }
    
    set {
    basis 6-31G
    dft_spherical_points 302
    dft_radial_points 99
    reference rks
    }
    
    mp2_dft = energy("MP2", dft_functional="PBE0")
    

Note that this would only update the generic Psi variables (e.g., “CURRENT ENERGY”) and not the MP2 or DFT variables. Psi4 also supports easy customization and manipulation of DFT functionals. The values of alpha and omega can be adjusted with the [DFT_ALPHA](autodoc_glossary_options_c.html#term-DFT_ALPHA-SCF) and [DFT_OMEGA](autodoc_glossary_options_c.html#term-DFT_OMEGA-SCF) keywords. For example, for LRC functionals, one can control the fraction of long-range Hartree-Fock and short-range DFA by changing [DFT_OMEGA](autodoc_glossary_options_c.html#term-DFT_OMEGA-SCF):
 
    molecule ch2 {
      0 3
      C
      H 1 R
      H 1 R 2 A
    
      R = 1.075
      A = 133.93
    }
    
    set reference uhf
    set guess gwh
    set basis cc-pvdz
    set e_convergence 8
    
    # Override the default value of omega
    set dft_omega 2.0
    
    E = energy('wb97x')
    
    # Revoke the change for later computations if needed
    revoke_global_option_changed('DFT_OMEGA')
    

This feature would be useful after finishing the IP fitting procedure, for example.

« hide menu menu sidebar » 

© Copyright 2007-2026, The Psi4 Project. Last updated on Friday, 01 May 2026 11:18PM. Created using [Sphinx](https://www.sphinx-doc.org/) 7.4.7.
