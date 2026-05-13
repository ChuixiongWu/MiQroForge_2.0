# Gaussian 16 DFT Methods

Density Functional (DFT) Methods
     * Description
     * Background
     * Keywords: Hybrid Functionals
     * Keyword: Pure Functionals
     * Empirical Dispersion
     * Availability
     * Related Keywords
     * Examples
   Description
   Gaussian 16 offers a wide variety of Density Functional Theory (DFT)
   [Hohenberg64, Kohn65, Parr89, Salahub89] models (see also
   [Labanowski91, Andzelm92, Becke92, Gill92, Perdew92, Scuseria92,
   Becke92a, Perdew92a, Perdew93a, Sosa93a, Stephens94, Stephens94a,
   Ricca95] for discussions of DFT methods and applications). Energies
   [Pople92], analytic gradients, and true analytic frequencies
   [Johnson93a, Johnson94, Stratmann97] are available for all DFT models.
   The self-consistent reaction field (SCRF) can be used with DFT
   energies, optimizations, and frequency calculations to model systems in
   solution.
   Pure DFT calculations will often want to take advantage of density
   fitting. See the discussion in Basis Sets for details.
   The same optimum memory sizes given by freqmem are recommended for DFT
   frequency calculations.
   Polarizability derivatives (Raman intensities) and
   hyperpolarizabilities are not computed by default during DFT frequency
   calculations. Use Freq=Raman to request them. Polar calculations do
   compute them.
   Note: The double hybrid functionals are discussed with the MP2 keyword
   since they have similar computational cost.
Accuracy Considerations
   A DFT calculation adds an additional step to each major phase of a
   Hartree-Fock calculation. This step is a numerical integration of the
   functional (or various derivatives of the functional). Thus in addition
   to the sources of numerical error in Hartree-Fock calculations
   (integral accuracy, SCF convergence, CPHF convergence), the accuracy of
   DFT calculations also depends on the number of points used in the
   numerical integration.
   The UltraFine integration grid (corresponding to Integral=UltraFine) is
   the default in Gaussian 16. This grid greatly enhances calculation
   accuracy at reasonable additional cost. We do not recommend using any
   smaller grid in production DFT calculations. Note also that it is
   important to use the same grid for all calculations where you intend to
   compare energies (e.g., computing energy differences, heats of
   formation, and so on).
   Larger grids are available when needed (e.g. tight geometry
   optimizations of certain kinds of systems). An alternate grid may be
   selected with the Integral=Grid option in the route section.
   Background
   In Hartree-Fock theory, the energy has the form:
   E[HF] = V + 〈hP〉 + 1/2〈PJ(P)〉 – 1/2〈PK(P)〉
   where the terms have the following meanings:
   V The nuclear repulsion energy.
   P The density matrix.
   〈hP〉 The one-electron (kinetic plus potential) energy.
   1/2〈PJ(P)〉 The classical coulomb repulsion of the electrons.
   -1/2〈PK(P)〉 The exchange energy resulting from the quantum (fermion)
   nature of electrons.
   In the Kohn-Sham formulation of density functional theory [Kohn65], the
   exact exchange (HF) for a single determinant is replaced by a more
   general expression, the exchange-correlation functional, which can
   include terms accounting for both the exchange and the electron
   correlation energies, the latter not being present in Hartree-Fock
   theory:
   E[KS] = V + 〈hP〉 + 1/2〈PJ(P)〉 + E[X][P] + E[C][P]
   where E[X][P] is the exchange functional, and E[C][P] is the
   correlation functional.
   Within the Kohn-Sham formulation, Hartree-Fock theory can be regarded
   as a special case of density functional theory, with E[X][P] given by
   the exchange integral -1/2<PK(P)> and E[C]=0. The functionals normally
   used in density functional theory are integrals of some function of the
   density and possibly the density gradient:
   E[X][P] = ∫f(ρ[α](r),ρ[β](r),∇ρ[α](r),∇ρ[β](r))dr
   where the methods differ in which function f is used for E[X] and which
   (if any) f is used for E[C]. In addition to pure DFT methods, Gaussian
   supports hybrid methods in which the exchange functional is a linear
   combination of the Hartree-Fock exchange and a functional integral of
   the above form. Proposed functionals lead to integrals which cannot be
   evaluated in closed form and are solved by numerical quadrature.
   Keywords: Hybrid Functionals
   A number of hybrid functionals, which include a mixture of Hartree-Fock
   exchange with DFT exchange-correlation, are available via keywords:
Becke Three-Parameter Hybrid Functionals
   These functionals have the form devised by Becke in 1993 [Becke93a]:
   A*E[X]^Slater+(1-A)*E[X]^HF+B*ΔE[X]^Becke+E[C]^VWN+C*ΔE[C]^non-local
   where A, B, and C are the constants determined by Becke via fitting to
   the G1 molecule set.
   There are several variations of this hybrid functional.
   B3LYP uses the non-local correlation provided by the LYP expression,
   and VWN functional III for local correlation (not functional V). Note
   that since LYP includes both local and non-local terms, the correlation
   functional used is actually:

\##    C*E[C]^LYP+(1-C)*E[C]^VWN

   In other words, VWN is used to provide the excess local correlation
   required, since LYP contains a local term essentially equivalent to

\##    VWN.

   B3P86 specifies the same functional with the non-local correlation
   provided by Perdew 86, and B3PW91 specifies this functional with the
   non-local correlation provided by Perdew/Wang 91.
   O3LYP is a three-parameter functional similar to B3LYP:

\##    A*E[X]^LSD+(1-A)*E[X]^HF+B*ΔE[X]^OPTX+C*ΔE[C]^LYP+(1-C)E[C]^VWN

   where A, B and C are as defined by Cohen and Handy in reference
   [Cohen01].
Functionals Including Dispersion
     * APFD requests the Austin-Frisch-Petersson functional with
       dispersion [Austin12], and APF requests the same functional without
       dispersion.
     * The wB97XD functional uses a version of Grimme’s D2 dispersion
       model.
   The standalone keyword EmpiricalDispersion also allows you to specify a
   dispersion scheme with various functionals.
Long-Range-Corrected Functionals
   The non-Coulomb part of exchange functionals typically dies off too
   rapidly and becomes very inaccurate at large distances, making them
   unsuitable for modeling processes such as electron excitations to high
   orbitals. Various schemes have been devised to handle such cases.
   Gaussian 16 offers the following functionals which include long-range
   corrections:
     * LC-wHPBE: Recommended version [Henderson09] of the
       long-range-corrected ωPBE functional [Vydrov06, Vydrov06a,
       Vydrov07]. LC-wPBE requests the original version.
     * CAM-B3LYP: Handy and coworkers’ long-range-corrected version of
       B3LYP using the Coulomb-attenuating method [Yanai04].
     * wB97XD: The latest functional from Head-Gordon and coworkers, which
       includes empirical dispersion [Chai08a]. The wB97 and wB97X
       [Chai08] variations are also available. These functionals also
       include long-range corrections.
   In addition, the prefix LC- may be added to most pure functionals to
   apply the long correction of Hirao and coworkers [Iikura01]: e.g.,

\##    LC-BLYP.

Other Hybrid Functionals
Functionals from the Truhlar Group
     * MN15 requests the MN15 [Yu16] functional.
     * M11 [Peverati11a], SOGGA11X [Peverati11b], N12SX [Peverati12a], and
       MN12SX [Peverati12a] request these hybrid functionals from the
       Truhlar group.
     * PW6B95 and PW6B95D3 [Zhao05a].
     * M08HX: The M08-HX functional [Zhao08a].
     * M06 hybrid functional of Truhlar and Zhao [Zhao08]. The M06HF
       [Zhao06b, Zhao06c] and M062X [Zhao08] variations are also
       available.
     * M05 [Zhao05] and M052X [Zhao06].
Functionals Employing PBE Correlation
     * The 1996 pure functional of Perdew, Burke and Ernzerhof [Perdew96a,
       Perdew97] as made into a hybrid functional by Adamo [Adamo99a]. The
       keyword is PBE1PBE. This functional uses 25% exact exchange and 75%
       DFT exchange. It is known in the literature as PBE0 [Adamo99a] and
       as the PBE hybrid [Ernzerhof99].
     * HSEH1PBE: The recommended version of the full
       Heyd-Scuseria-Ernzerhof functional, referred to as HSE06 in the
       literature [Heyd04, Heyd04a, Heyd05, Heyd06, Henderson09,
       Izmaylov06, Krukau06].
     * OHSE2PBE: The initial form of the HS06 functional, referred to as
       HSE03 in the literature.
     * OHSE1PBE: The version of the HS06 functional prior to modification
       to support third derivatives.
     * PBEh1PBE: Hybrid using the 1998 revised form of PBE pure functional
       (exchange and correlation) [Ernzerhof98].
Becke One-Parameter Hybrid Functionals
   The B1B95 keyword is used to specify Becke’s one-parameter hybrid
   functional as defined in the original paper [Becke96].
   The program also provides other, similar one parameter hybrid
   functionals implemented by Adamo and Barone [Adamo97]. In one
   variation, B1LYP, the LYP correlation functional is used (as described
   for B3LYP above). Another version, mPW1PW91, uses Perdew-Wang exchange
   as modified by Adamo and Barone combined with PW91 correlation
   [Adamo98]; the mPW1LYP, mPW1PBE and mPW3PBE variations are available.
Revisions to B97
     * Becke’s 1998 revisions to B97 [Becke97, Schmider98]. The keyword is
       B98, and it implements fit 2c in reference [Schmider98].
     * Handy, Tozer and coworkers modification to B97: B971 [Hamprecht98].
     * Wilson, Bradley and Tozer’s modification to B97: B972 [Wilson01a].
Functionals with τ-Dependent Gradient-Corrected Correlation
     * TPSSh: Hybrid functional using the TPSS functionals [Tao03,
       Staroverov03].
     * tHCTHhyb: Hybrid functional using the tHCTH functional [Boese02].
     * BMK: Boese and Martin’s τ-dependent 2004 hybrid functional
       [Boese04].
Older Functionals
     * HISSbPBE requests the HISS functional [Henderson08].
     * X3LYP: Functional of Xu and Goddard [Xu04].
Half-and-Half Functionals
   The following functionals, which are included for
   backward-compatibility only. Note that these are not the same as the
   “half-and-half” functionals proposed by Becke [Becke93].
     * BHandH: 0.5*E[X]^HF + 0.5*E[X]^LSDA + E[C]^LYP
     * BHandHLYP: 0.5*E[X]^HF + 0.5*E[X]^LSDA + 0.5*ΔE[X]^Becke88 +

\##        E[C]^LYP

User-Defined Hybrid Models
   Gaussian 16 can use any model of the general form:
   P[2]E[X]^HF + P[1](P[4]E[X]^Slater + P[3]ΔE[x]^non-local) +
   P[6]E[C]^local + P[5]ΔE[C]^non-local
   The only available local exchange method is Slater (S), which should be
   used when only local exchange is desired. Any combinable non-local
   exchange functional and combinable correlation functional may be used
   (as listed previously).
   The values of the six parameters are specified with various
   non-standard options to the program:
     * IOp(3/76=mmmmmnnnnn) sets P[1] to mmmmm/10000 and P[2] to
       nnnnn/10000. P[1] is usually set to either 1.0 or 0.0, depending on
       whether an exchange functional is desired or not, and any scaling
       is accomplished using P[3] and P[4].
     * IOp(3/77=mmmmmnnnnn) sets P[3] to mmmmm/10000 and P[4] to
       nnnnn/10000.
     * IOp(3/78=mmmmmnnnnn) sets P[5] to mmmmm/10000 and P[6] to
       nnnnn/10000.
   For example, IOp(3/76=1000005000) sets P[1] to 1.0 and P[2] to 0.5.
   Note that all values must be expressed using five digits, adding any
   necessary leading zeros.
   Here is a route section specifying the functional corresponding to the
   B3LYP keyword:
#P BLYP IOp(3/76=1000002000) IOp(3/77=0720008000) IOp(3/78=0810010000)
   The output file displays the values that are in use:
 IExCor=  402 DFT=T Ex=B+HF Corr=LYP ExCW=0 ScaHFX=  0.200000
 ScaDFX=  0.800000  0.720000  1.000000  0.810000
   where the value of ScaHFX is P[2], and the sequence of values given for
   ScaDFX are P[4], P[3], P[6], and P[5].
   Keywords: Pure Functionals
   Names for the various pure DFT models are given by combining the names
   for the exchange and correlation functionals. In some cases, standard
   synonyms used in the field are also available as keywords. In order to
   specify a pure functional, combine an exchange functional component
   keyword with the one for desired correlation functional. For example,
   the combination of the Becke exchange functional (B) and the LYP
   correlation functional is requested by the BLYP keyword. Similarly,
   SVWN requests the Slater exchange functional (S) and the VWN
   correlation functional, and is known in the literature by its synonym
   LSDA (Local Spin Density Approximation). LSDA is a synonym for SVWN.
   Some other software packages with DFT facilities use the equivalent of
   SVWN5 when “LSDA” is requested. Check the documentation carefully for
   all packages when making comparisons.
Exchange Functionals
   The following exchange functionals are available in Gaussian 16. Unless
   otherwise indicated, these exchange functionals must be combined with a
   correlation functional in order to produce a usable method.
     * S: The Slater exchange, ρ^4/3 with theoretical coefficient of 2/3,
       also referred to as Local Spin Density exchange [Hohenberg64,
       Kohn65, Slater74]. Keyword if used alone: HFS.
     * XA: The XAlpha exchange, ρ^4/3 with the empirical coefficient of
       0.7, usually employed as a standalone exchange functional, without
       a correlation functional [Hohenberg64, Kohn65, Slater74]. Keyword
       if used alone: XAlpha.
     * B: Becke’s 1988 functional, which includes the Slater exchange
       along with corrections involving the gradient of the density
       [Becke88b]. Keyword if used alone: HFB.
     * PW91: The exchange component of Perdew and Wang’s 1991 functional
       [Perdew91, Perdew92, Perdew93a, Perdew96, Burke98].
     * mPW: The Perdew-Wang 1991 exchange functional as modified by Adamo
       and Barone [Adamo98].
     * G96: The 1996 exchange functional of Gill [Gill96, Adamo98a].
     * PBE: The 1996 functional of Perdew, Burke and Ernzerhof [Perdew96a,
       Perdew97].
     * O: Handy’s OPTX modification of Becke’s exchange functional
       [Handy01, Hoe01].
     * TPSS: The exchange functional of Tao, Perdew, Staroverov, and
       Scuseria [Tao03].
     * RevTPSS: The revised TPSS exchange functional of Perdew et. al.
       [Perdew09, Perdew11].
     * BRx: The 1989 exchange functional of Becke [Becke89a].
     * PKZB: The exchange part of the Perdew, Kurth, Zupan and Blaha
       functional [Perdew99].
     * wPBEh: The exchange part of screened Coulomb potential-based final
       of Heyd, Scuseria and Ernzerhof (also known as HSE) [Heyd03,
       Izmaylov06, Henderson09].
     * PBEh: 1998 revision of PBE [Ernzerhof98].
Correlation Functionals
   The following correlation functionals are available, listed by their
   corresponding keyword component, all of which must be combined with the
   keyword for the desired exchange functional:
     * VWN: Vosko, Wilk, and Nusair 1980 correlation functional(III)
       fitting the RPA solution to the uniform electron gas, often
       referred to as Local Spin Density (LSD) correlation [Vosko80]
       (functional III in this article).
     * VWN5: Functional V from reference [Vosko80] which fits the
       Ceperly-Alder solution to the uniform electron gas (this is the
       functional recommended in [Vosko80]).
     * LYP: The correlation functional of Lee, Yang, and Parr, which
       includes both local and non-local terms [Lee88, Miehlich89].
     * PL (Perdew Local): The local (non-gradient corrected) functional of
       Perdew (1981) [Perdew81].
     * P86 (Perdew 86): The gradient corrections of Perdew, along with his
       1981 local correlation functional [Perdew86].
     * PW91 (Perdew/Wang 91): Perdew and Wang’s 1991 gradient-corrected
       correlation functional [Perdew91, Perdew92, Perdew93a, Perdew96,
       Burke98].
     * B95 (Becke 95): Becke’s τ-dependent gradient-corrected correlation
       functional (defined as part of his one parameter hybrid functional
       [Becke96]).
     * PBE: The 1996 gradient-corrected correlation functional of Perdew,
       Burke and Ernzerhof [Perdew96a, Perdew97].
     * TPSS: The τ-dependent gradient-corrected functional of Tao, Perdew,
       Staroverov, and Scuseria [Tao03].
     * RevTPSS: The revised TPSS correlation functional of Perdew et. al.
       [Perdew09, Perdew11].
     * KCIS: The Krieger-Chen-Iafrate-Savin correlation functional [Rey98,
       Krieger99, Krieger01, Toulouse02].
     * BRC: Becke-Roussel correlation functional [Becke89a].
     * PKZB: The correlation part of the Perdew, Kurth, Zupan and Blaha
       functional [Perdew99].
   Correlation Functional Variations. The following correlation
   functionals combine local and non-local terms from different
   correlation functionals:
     * VP86: VWN5 local and P86 non-local correlation functional.
     * V5LYP: VWN5 local and LYP non-local correlation functional.
Standalone Pure Functionals
   The following pure functionals are self-contained and are not combined
   with any other functional keyword components:
     * VSXC: van Voorhis and Scuseria’s τ-dependent gradient-corrected
       correlation functional [VanVoorhis98].
     * HCTH/*: Handy’s family of functionals including gradient-corrected
       correlation [Hamprecht98, Boese00, Boese01]. HCTH refers to
       HCTH/407, HCTH93 to HCTH/93, HCTH147 to HCTH/147, and HCTH407 to
       HCTH/407. Note that the related HCTH/120 functional is not
       implemented.
     * tHCTH: The τ-dependent member of the HCTH family [Boese02]. See
       also tHCTHhyb.
     * B97D: Grimme’s functional including dispersion [Grimme06]. B97D3
       requests the same but with Grimme’s D3BJ dispersion [Grimme11].
     * M06L [Zhao06a], SOGGA11 [Peverati11], M11L [Peverati12], MN12L
       [Peverati12c] N12 [Peverati12b] and MN15L [Yu16a] request these
       pure functionals from the Truhlar group.
   Dispersion
   The EmpiricalDispersion keyword enables empirical dispersion. It takes
   the following options:
PFD
   Add the Petersson-Frisch dispersion model from the APFD functional
   [Austin12].
GD2
   Add the D2 version of Grimme’s dispersion [Grimme06]. The table below
   gives the list of functionals in Gaussian 16 for which GD2 parameters
   are defined. The functionals highlighted in bold include this
   dispersion model by default when the indicated keyword is specified
   (e.g., B2PLYPD). For the rest of the functionals, dispersion is
   requested with EmpiricalDispersion=GD2.
   Functional S6     SR6

\##    B97D       1.2500 1.1000


\##    B2PLYPD    0.5500 1.1000

   mPW2PLYPD  0.4000 1.1000

\##    PBEPBE     0.7500 1.1000


\##    BLYP       1.2000 1.1000


\##    B3LYP      1.0500 1.1000


\##    BP86       1.0500 1.1000


\##    TPSSTPSS   1.0000 1.1000

   The damping function used by this model also contains a D6 parameter
   with a fixed value of 6.0.
   You can use this empirical dispersion method with other functionals via
   the IOps(3/174,176) (SR6 should be 1.1).
   The wB97XD functional specified as an independent keyword uses a
   version of this dispersion model with values of S6 and SR6 of 1.0 and
   1.1, respectively. This functional uses a similar damping function to
   that used by the GD3 model, with D6 and IA6 having fixed values of 6.0
   and 12, respectively.
GD3
   Add the D3 version of Grimme’s dispersion with the original D3 damping
   function [Grimme10]. The table below gives the list of functionals in
   Gaussian 16 for which GD3 parameters are defined. For these
   functionals, dispersion is requested with EmpiricalDispersion=GD3.
   Functional           S6     SR6    S8
   B2PLYPD3 [Goerigk11] 0.6400 1.4270 1.0220

\##    B97D3                1.0000 0.8920 0.9090


\##    B3LYP                1.0000 1.2610 1.7030


\##    BLYP                 1.0000 1.0940 1.6820


\##    PBE1PBE              1.0000 1.2870 0.9280


\##    TPSSTPSS             1.0000 1.1660 1.1050


\##    PBEPBE               1.0000 1.2170 0.7220


\##    BP86                 1.0000 1.1390 1.6830


\##    BPBE                 1.0000 1.0870 2.0330


\##    B3PW91               1.0000 1.1760 1.7750


\##    BMK                  1.0000 1.9310 2.1680


\##    CAM–B3LYP            1.0000 1.3780 1.2170

   LC-wPBE              1.0000 1.3550 1.2790

\##    M05                  1.0000 1.3730 0.5950


\##    M052X                1.0000 1.4170 0.0000


\##    M06L                 1.0000 1.5810 0.0000


\##    M06                  1.0000 1.3250 0.0000


\##    M062X                1.0000 1.6190 0.0000


\##    M06HF                1.0000 1.4460 0.0000


\##    PW6B95D3             1.0000 1.532  0.862

   This model also uses an SR8 parameter with a fixed value of 1.0. The
   damping function used by this model also contains D6, IA6, D8, and IA8
   parameters with fixed values of 6.0, 14, 6.0, and 16, respectively.
   You can use this empirical dispersion method with other functionals via
   the IOps(3/174-176) (S6 should be 1.0).
GD3BJ
   Add the D3 version of Grimme’s dispersion with Becke-Johnson damping
   [Grimme11]. The table below gives the list of functionals in Gaussian
   16 for which GD3BJ parameters are defined. The functionals highlighted
   in bold include this dispersion model by default when the indicated
   keyword is specified (e.g., B2PLYPD3). For the rest of the functionals,
   dispersion is requested with EmpiricalDispersion=GD3BJ.
   Functional           S6     S8     ABJ1   ABJ2
   B2PLYPD3 [Goerigk11] 0.6400 0.9147 0.3065 5.0570

\##    B97D3                1.0000 2.2609 0.5545 3.2297


\##    PW6B95D3             1.0000 0.7257 0.2076 6.3750


\##    B3LYP                1.0000 1.9889 0.3981 4.4211


\##    BLYP                 1.0000 2.6996 0.4298 4.2359


\##    PBE1PBE              1.0000 1.2177 0.4145 4.8593


\##    TPSSTPSS             1.0000 1.9435 0.4535 4.4752


\##    PBEPBE               1.0000 0.7875 0.4289 4.4407


\##    BP86                 1.0000 3.2822 0.3946 4.8516


\##    BPBE                 1.0000 4.0728 0.4567 4.3908


\##    B3PW91               1.0000 2.8524 0.4312 4.4693


\##    BMK                  1.0000 2.0860 0.1940 5.9197


\##    CAM–B3LYP            1.0000 2.0674 0.3708 5.4743

   LC-wPBE              1.0000 1.8541 0.3919 5.0897
   You can use this empirical dispersion method with other functionals via
   the IOps(3/174-178) (S6 should be 1.0).
   Availability
   Energies, analytic gradients, and analytic frequencies; ADMP
   calculations.
   Third order properties such as hyperpolarizabilities and Raman
   intensities are not available for functionals for which third
   derivatives are not implemented: the exchange functionals G96, P86,
   PKZB, wPBEh and PBEh; the correlation functional PKZB; the hybrid
   functionals OHSE1PBE and OHSE2PBE.
   Related Keywords
   IOp, Int=Grid, Stable, TD, DenFit, B2PLYP, mPW2LYP
   Examples
   The energy is reported in DFT calculations in a form similar to that of
   Hartree-Fock calculations. Here is the energy output from a B3LYP
   calculation:
 SCF Done:  E(RB3LYP) =  -75.3197099428     A.U. after    5 cycles
     * Description
     * Background
     * Keywords: Hybrid Functionals
     * Keyword: Pure Functionals
     * Empirical Dispersion
     * Availability
     * Related Keywords
     * Examples
   Description - Mobile
   Gaussian 16 offers a wide variety of Density Functional Theory (DFT)
   [Hohenberg64, Kohn65, Parr89, Salahub89] models (see also
   [Labanowski91, Andzelm92, Becke92, Gill92, Perdew92, Scuseria92,
   Becke92a, Perdew92a, Perdew93a, Sosa93a, Stephens94, Stephens94a,
   Ricca95] for discussions of DFT methods and applications). Energies
   [Pople92], analytic gradients, and true analytic frequencies
   [Johnson93a, Johnson94, Stratmann97] are available for all DFT models.
   The self-consistent reaction field (SCRF) can be used with DFT
   energies, optimizations, and frequency calculations to model systems in
   solution.
   Pure DFT calculations will often want to take advantage of density
   fitting. See the discussion in Basis Sets for details.
   The same optimum memory sizes given by freqmem are recommended for DFT
   frequency calculations.
   Polarizability derivatives (Raman intensities) and
   hyperpolarizabilities are not computed by default during DFT frequency
   calculations. Use Freq=Raman to request them. Polar calculations do
   compute them.
   Note: The double hybrid functionals are discussed with the MP2 keyword
   since they have similar computational cost.
Accuracy Considerations
   A DFT calculation adds an additional step to each major phase of a
   Hartree-Fock calculation. This step is a numerical integration of the
   functional (or various derivatives of the functional). Thus in addition
   to the sources of numerical error in Hartree-Fock calculations
   (integral accuracy, SCF convergence, CPHF convergence), the accuracy of
   DFT calculations also depends on the number of points used in the
   numerical integration.
   The UltraFine integration grid (corresponding to Integral=UltraFine) is
   the default in Gaussian 16. This grid greatly enhances calculation
   accuracy at reasonable additional cost. We do not recommend using any
   smaller grid in production DFT calculations. Note also that it is
   important to use the same grid for all calculations where you intend to
   compare energies (e.g., computing energy differences, heats of
   formation, and so on).
   Larger grids are available when needed (e.g. tight geometry
   optimizations of certain kinds of systems). An alternate grid may be
   selected with the Integral=Grid option in the route section.
   In Hartree-Fock theory, the energy has the form:
   E[HF] = V + 〈hP〉 + 1/2〈PJ(P)〉 - 1/2〈PK(P)〉
   where the terms have the following meanings:
   V The nuclear repulsion energy.
   P The density matrix.
   〈hP〉 The one-electron (kinetic plus potential) energy.
   1/2〈PJ(P)〉 The classical coulomb repulsion of the electrons.
   -1/2〈PK(P)〉 The exchange energy resulting from the quantum (fermion)
   nature of electrons.
   In the Kohn-Sham formulation of density functional theory [Kohn65], the
   exact exchange (HF) for a single determinant is replaced by a more
   general expression, the exchange-correlation functional, which can
   include terms accounting for both the exchange and the electron
   correlation energies, the latter not being present in Hartree-Fock
   theory:
   E[KS] = V + 〈hP〉 + 1/2〈PJ(P)〉 + E[X][P] + E[C][P]
   where E[X][P] is the exchange functional, and E[C][P] is the
   correlation functional.
   Within the Kohn-Sham formulation, Hartree-Fock theory can be regarded
   as a special case of density functional theory, with E[X][P] given by
   the exchange integral -1/2 and E[C]=0. The functionals normally used in
   density functional theory are integrals of some function of the density
   and possibly the density gradient:
   E[X][P] = ∫f(ρ[α](r),ρ[β](r),∇ρ[α](r),∇ρ[β](r))dr
   where the methods differ in which function f is used for E[X] and which
   (if any) f is used for E[C]. In addition to pure DFT methods, Gaussian
   supports hybrid methods in which the exchange functional is a linear
   combination of the Hartree-Fock exchange and a functional integral of
   the above form. Proposed functionals lead to integrals which cannot be
   evaluated in closed form and are solved by numerical quadrature.
   A number of hybrid functionals, which include a mixture of Hartree-Fock
   exchange with DFT exchange-correlation, are available via keywords:
Becke Three-Parameter Hybrid Functionals
   These functionals have the form devised by Becke in 1993 [Becke93a]:
   A*E[X]^Slater+(1-A)*E[X]^HF+B*ΔE[X]^Becke+E[C]^VWN+C*ΔE[C]^non-local
   where A, B, and C are the constants determined by Becke via fitting to
   the G1 molecule set.
   There are several variations of this hybrid functional.
   B3LYP uses the non-local correlation provided by the LYP expression,
   and VWN functional III for local correlation (not functional V). Note
   that since LYP includes both local and non-local terms, the correlation
   functional used is actually:

\##    C*E[C]^LYP+(1-C)*E[C]^VWN

   In other words, VWN is used to provide the excess local correlation
   required, since LYP contains a local term essentially equivalent to

\##    VWN.

   B3P86 specifies the same functional with the non-local correlation
   provided by Perdew 86, and B3PW91 specifies this functional with the
   non-local correlation provided by Perdew/Wang 91.
   O3LYP is a three-parameter functional similar to B3LYP:

\##    A*E[X]^LSD+(1-A)*E[X]^HF+B*ΔE[X]^OPTX+C*ΔE[C]^LYP+(1-C)E[C]^VWN

   where A, B and C are as defined by Cohen and Handy in reference
   [Cohen01].
Functionals Including Dispersion
     * APFD requests the Austin-Frisch-Petersson functional with
       dispersion [Austin12], and APF requests the same functional without
       dispersion.
     * The wB97XD functional uses a version of Grimme’s D2 dispersion
       model.
   The standalone keyword EmpiricalDispersion also allows you to specify a
   dispersion scheme with various functionals.
Long-Range-Corrected Functionals
   The non-Coulomb part of exchange functionals typically dies off too
   rapidly and becomes very inaccurate at large distances, making them
   unsuitable for modeling processes such as electron excitations to high
   orbitals. Various schemes have been devised to handle such cases.
   Gaussian 16 offers the following functionals which include long-range
   corrections:
     * LC-wHPBE: Recommended version [Henderson09] of the
       long-range-corrected ωPBE functional [Vydrov06, Vydrov06a,
       Vydrov07]. LC-wPBE requests the original version.
     * CAM-B3LYP: Handy and coworkers’ long-range-corrected version of
       B3LYP using the Coulomb-attenuating method [Yanai04].
     * wB97XD: The latest functional from Head-Gordon and coworkers, which
       includes empirical dispersion [Chai08a]. The wB97 and wB97X
       [Chai08] variations are also available. These functionals also
       include long-range corrections.
   In addition, the prefix LC- may be added to most pure functionals to
   apply the long correction of Hirao and coworkers [Iikura01]: e.g.,

\##    LC-BLYP.

Other Hybrid Functionals
Functionals from the Truhlar Group
     * MN15 requests the MN15 [Yu16] functional.
     * M11 [Peverati11a], SOGGA11X [Peverati11b], N12SX [Peverati12a], and
       MN12SX [Peverati12a] request these hybrid functionals from the
       Truhlar group.
     * PW6B95 and PW6B95D3 [Zhao05a].
     * M08HX: The M08-HX functional [Zhao08a].
     * M06 hybrid functional of Truhlar and Zhao [Zhao08]. The M06HF
       [Zhao06b, Zhao06c] and M062X [Zhao08] variations are also
       available.
     * M05 [Zhao05] and M052X [Zhao06].
Functionals Employing PBE Correlation
     * The 1996 pure functional of Perdew, Burke and Ernzerhof [Perdew96a,
       Perdew97] as made into a hybrid functional by Adamo [Adamo99a]. The
       keyword is PBE1PBE. This functional uses 25% exact exchange and 75%
       DFT exchange. It is known in the literature as PBE0 [Adamo99a] and
       as the PBE hybrid [Ernzerhof99].
     * HSEH1PBE: The recommended version of the full
       Heyd-Scuseria-Ernzerhof functional, referred to as HSE06 in the
       literature [Heyd04, Heyd04a, Heyd05, Heyd06, Henderson09,
       Izmaylov06, Krukau06].
     * OHSE2PBE: The initial form of the HS06 functional, referred to as
       HSE03 in the literature.
     * OHSE1PBE: The version of the HS06 functional prior to modification
       to support third derivatives.
     * PBEh1PBE: Hybrid using the 1998 revised form of PBE pure functional
       (exchange and correlation) [Ernzerhof98].
Becke One-Parameter Hybrid Functionals
   The B1B95 keyword is used to specify Becke’s one-parameter hybrid
   functional as defined in the original paper [Becke96].
   The program also provides other, similar one parameter hybrid
   functionals implemented by Adamo and Barone [Adamo97]. In one
   variation, B1LYP, the LYP correlation functional is used (as described
   for B3LYP above). Another version, mPW1PW91, uses Perdew-Wang exchange
   as modified by Adamo and Barone combined with PW91 correlation
   [Adamo98]; the mPW1LYP, mPW1PBE and mPW3PBE variations are available.
Revisions to B97
     * Becke’s 1998 revisions to B97 [Becke97, Schmider98]. The keyword is
       B98, and it implements fit 2c in reference [Schmider98].
     * Handy, Tozer and coworkers modification to B97: B971 [Hamprecht98].
     * Wilson, Bradley and Tozer’s modification to B97: B972 [Wilson01a].
Functionals with τ-Dependent Gradient-Corrected Correlation
     * TPSSh: Hybrid functional using the TPSS functionals [Tao03,
       Staroverov03].
     * tHCTHhyb: Hybrid functional using the tHCTH functional [Boese02].
     * BMK: Boese and Martin’s τ-dependent 2004 hybrid functional
       [Boese04].
Older Functionals
     * HISSbPBE requests the HISS functional [Henderson08].
     * X3LYP: Functional of Xu and Goddard [Xu04].
Half-and-Half Functionals
   The following functionals, which are included for
   backward-compatibility only. Note that these are not the same as the
   “half-and-half” functionals proposed by Becke [Becke93].
     * BHandH: 0.5*E[X]^HF + 0.5*E[X]^LSDA + E[C]^LYP
     * BHandHLYP: 0.5*E[X]^HF + 0.5*E[X]^LSDA + 0.5*ΔE[X]^Becke88 +

\##        E[C]^LYP

User-Defined Hybrid Models
   Gaussian 16 can use any model of the general form:
   P[2]E[X]^HF + P[1](P[4]E[X]^Slater + P[3]ΔE[x]^non-local) +
   P[6]E[C]^local + P[5]ΔE[C]^non-local
   The only available local exchange method is Slater (S), which should be
   used when only local exchange is desired. Any combinable non-local
   exchange functional and combinable correlation functional may be used
   (as listed previously).
   The values of the six parameters are specified with various
   non-standard options to the program:
     * IOp(3/76=mmmmmnnnnn) sets P[1] to mmmmm/10000 and P[2] to
       nnnnn/10000. P[1] is usually set to either 1.0 or 0.0, depending on
       whether an exchange functional is desired or not, and any scaling
       is accomplished using P[3] and P[4].
     * IOp(3/77=mmmmmnnnnn) sets P[3] to mmmmm/10000 and P[4] to
       nnnnn/10000.
     * IOp(3/78=mmmmmnnnnn) sets P[5] to mmmmm/10000 and P[6] to
       nnnnn/10000.
   For example, IOp(3/76=1000005000) sets P[1] to 1.0 and P[2] to 0.5.
   Note that all values must be expressed using five digits, adding any
   necessary leading zeros.
   Here is a route section specifying the functional corresponding to the
   B3LYP keyword:
#P BLYP IOp(3/76=1000002000) IOp(3/77=0720008000) IOp(3/78=0810010000)
   The output file displays the values that are in use:
 IExCor=  402 DFT=T Ex=B+HF Corr=LYP ExCW=0 ScaHFX=  0.200000
 ScaDFX=  0.800000  0.720000  1.000000  0.810000
   where the value of ScaHFX is P[2], and the sequence of values given for
   ScaDFX are P[4], P[3], P[6], and P[5].
   Names for the various pure DFT models are given by combining the names
   for the exchange and correlation functionals. In some cases, standard
   synonyms used in the field are also available as keywords. In order to
   specify a pure functional, combine an exchange functional component
   keyword with the one for desired correlation functional. For example,
   the combination of the Becke exchange functional (B) and the LYP
   correlation functional is requested by the BLYP keyword. Similarly,
   SVWN requests the Slater exchange functional (S) and the VWN
   correlation functional, and is known in the literature by its synonym
   LSDA (Local Spin Density Approximation). LSDA is a synonym for SVWN.
   Some other software packages with DFT facilities use the equivalent of
   SVWN5 when “LSDA” is requested. Check the documentation carefully for
   all packages when making comparisons.
Exchange Functionals
   The following exchange functionals are available in Gaussian 16. Unless
   otherwise indicated, these exchange functionals must be combined with a
   correlation functional in order to produce a usable method.
     * S: The Slater exchange, ρ^4/3 with theoretical coefficient of 2/3,
       also referred to as Local Spin Density exchange [Hohenberg64,
       Kohn65, Slater74]. Keyword if used alone: HFS.
     * XA: The XAlpha exchange, ρ^4/3 with the empirical coefficient of
       0.7, usually employed as a standalone exchange functional, without
       a correlation functional [Hohenberg64, Kohn65, Slater74]. Keyword
       if used alone: XAlpha.
     * B: Becke’s 1988 functional, which includes the Slater exchange
       along with corrections involving the gradient of the density
       [Becke88b]. Keyword if used alone: HFB.
     * PW91: The exchange component of Perdew and Wang’s 1991 functional
       [Perdew91, Perdew92, Perdew93a, Perdew96, Burke98].
     * mPW: The Perdew-Wang 1991 exchange functional as modified by Adamo
       and Barone [Adamo98].
     * G96: The 1996 exchange functional of Gill [Gill96, Adamo98a].
     * PBE: The 1996 functional of Perdew, Burke and Ernzerhof [Perdew96a,
       Perdew97].
     * O: Handy’s OPTX modification of Becke’s exchange functional
       [Handy01, Hoe01].
     * TPSS: The exchange functional of Tao, Perdew, Staroverov, and
       Scuseria [Tao03].
     * RevTPSS: The revised TPSS exchange functional of Perdew et. al.
       [Perdew09, Perdew11].
     * BRx: The 1989 exchange functional of Becke [Becke89a].
     * PKZB: The exchange part of the Perdew, Kurth, Zupan and Blaha
       functional [Perdew99].
     * wPBEh: The exchange part of screened Coulomb potential-based final
       of Heyd, Scuseria and Ernzerhof (also known as HSE) [Heyd03,
       Izmaylov06, Henderson09].
     * PBEh: 1998 revision of PBE [Ernzerhof98].
Correlation Functionals
   The following correlation functionals are available, listed by their
   corresponding keyword component, all of which must be combined with the
   keyword for the desired exchange functional:
     * VWN: Vosko, Wilk, and Nusair 1980 correlation functional(III)
       fitting the RPA solution to the uniform electron gas, often
       referred to as Local Spin Density (LSD) correlation [Vosko80]
       (functional III in this article).
     * VWN5: Functional V from reference [Vosko80] which fits the
       Ceperly-Alder solution to the uniform electron gas (this is the
       functional recommended in [Vosko80]).
     * LYP: The correlation functional of Lee, Yang, and Parr, which
       includes both local and non-local terms [Lee88, Miehlich89].
     * PL (Perdew Local): The local (non-gradient corrected) functional of
       Perdew (1981) [Perdew81].
     * P86 (Perdew 86): The gradient corrections of Perdew, along with his
       1981 local correlation functional [Perdew86].
     * PW91 (Perdew/Wang 91): Perdew and Wang’s 1991 gradient-corrected
       correlation functional [Perdew91, Perdew92, Perdew93a, Perdew96,
       Burke98].
     * B95 (Becke 95): Becke’s τ-dependent gradient-corrected correlation
       functional (defined as part of his one parameter hybrid functional
       [Becke96]).
     * PBE: The 1996 gradient-corrected correlation functional of Perdew,
       Burke and Ernzerhof [Perdew96a, Perdew97].
     * TPSS: The τ-dependent gradient-corrected functional of Tao, Perdew,
       Staroverov, and Scuseria [Tao03].
     * RevTPSS: The revised TPSS correlation functional of Perdew et. al.
       [Perdew09, Perdew11].
     * KCIS: The Krieger-Chen-Iafrate-Savin correlation functional [Rey98,
       Krieger99, Krieger01, Toulouse02].
     * BRC: Becke-Roussel correlation functional [Becke89a].
     * PKZB: The correlation part of the Perdew, Kurth, Zupan and Blaha
       functional [Perdew99].
   Correlation Functional Variations. The following correlation
   functionals combine local and non-local terms from different
   correlation functionals:
     * VP86: VWN5 local and P86 non-local correlation functional.
     * V5LYP: VWN5 local and LYP non-local correlation functional.
Standalone Pure Functionals
   The following pure functionals are self-contained and are not combined
   with any other functional keyword components:
     * VSXC: van Voorhis and Scuseria’s τ-dependent gradient-corrected
       correlation functional [VanVoorhis98].
     * HCTH/*: Handy’s family of functionals including gradient-corrected
       correlation [Hamprecht98, Boese00, Boese01]. HCTH refers to
       HCTH/407, HCTH93 to HCTH/93, HCTH147 to HCTH/147, and HCTH407 to
       HCTH/407. Note that the related HCTH/120 functional is not
       implemented.
     * tHCTH: The τ-dependent member of the HCTH family [Boese02]. See
       also tHCTHhyb.
     * B97D: Grimme’s functional including dispersion [Grimme06]. B97D3
       requests the same but with Grimme’s D3BJ dispersion [Grimme11].
     * M06L [Zhao06a], SOGGA11 [Peverati11], M11L [Peverati12], MN12L
       [Peverati12c] N12 [Peverati12b] and MN15L [Yu16a] request these
       pure functionals from the Truhlar group.
   The EmpiricalDispersion keyword enables empirical dispersion. It takes
   the following options:
PFD
   Add the Petersson-Frisch dispersion model from the APFD functional
   [Austin12].
GD2
   Add the D2 version of Grimme’s dispersion [Grimme06]. The table below
   gives the list of functionals in Gaussian 16 for which GD2 parameters
   are defined. The functionals highlighted in bold include this
   dispersion model by default when the indicated keyword is specified
   (e.g., B2PLYPD). For the rest of the functionals, dispersion is
   requested with EmpiricalDispersion=GD2.
   Functional S6     SR6

\##    B97D       1.2500 1.1000


\##    B2PLYPD    0.5500 1.1000

   mPW2PLYPD  0.4000 1.1000

\##    PBEPBE     0.7500 1.1000


\##    BLYP       1.2000 1.1000


\##    B3LYP      1.0500 1.1000


\##    BP86       1.0500 1.1000


\##    TPSSTPSS   1.0000 1.1000

   The damping function used by this model also contains a D6 parameter
   with a fixed value of 6.0.
   You can use this empirical dispersion method with other functionals via
   the IOps(3/174,176) (SR6 should be 1.1).
   The wB97XD functional specified as an independent keyword uses a
   version of this dispersion model with values of S6 and SR6 of 1.0 and
   1.1, respectively. This functional uses a similar damping function to
   that used by the GD3 model, with D6 and IA6 having fixed values of 6.0
   and 12, respectively.
GD3
   Add the D3 version of Grimme’s dispersion with the original D3 damping
   function [Grimme10]. The table below gives the list of functionals in
   Gaussian 16 for which GD3 parameters are defined. For these
   functionals, dispersion is requested with EmpiricalDispersion=GD3.
   Functional           S6     SR6    S8
   B2PLYPD3 [Goerigk11] 0.6400 1.4270 1.0220

\##    B97D3                1.0000 0.8920 0.9090


\##    B3LYP                1.0000 1.2610 1.7030


\##    BLYP                 1.0000 1.0940 1.6820


\##    PBE1PBE              1.0000 1.2870 0.9280


\##    TPSSTPSS             1.0000 1.1660 1.1050


\##    PBEPBE               1.0000 1.2170 0.7220


\##    BP86                 1.0000 1.1390 1.6830


\##    BPBE                 1.0000 1.0870 2.0330


\##    B3PW91               1.0000 1.1760 1.7750


\##    BMK                  1.0000 1.9310 2.1680


\##    CAM–B3LYP            1.0000 1.3780 1.2170

   LC-wPBE              1.0000 1.3550 1.2790

\##    M05                  1.0000 1.3730 0.5950


\##    M052X                1.0000 1.4170 0.0000


\##    M06L                 1.0000 1.5810 0.0000


\##    M06                  1.0000 1.3250 0.0000


\##    M062X                1.0000 1.6190 0.0000


\##    M06HF                1.0000 1.4460 0.0000


\##    PW6B95D3             1.0000 1.532  0.862

   This model also uses an SR8 parameter with a fixed value of 1.0. The
   damping function used by this model also contains D6, IA6, D8, and IA8
   parameters with fixed values of 6.0, 14, 6.0, and 16, respectively.
   You can use this empirical dispersion method with other functionals via
   the IOps(3/174-176) (S6 should be 1.0).
GD3BJ
   Add the D3 version of Grimme’s dispersion with Becke-Johnson damping
   [Grimme11]. The table below gives the list of functionals in Gaussian
   16 for which GD3BJ parameters are defined. The functionals highlighted
   in bold include this dispersion model by default when the indicated
   keyword is specified (e.g., B2PLYPD3). For the rest of the functionals,
   dispersion is requested with EmpiricalDispersion=GD3BJ.
   Functional           S6     S8     ABJ1   ABJ2
   B2PLYPD3 [Goerigk11] 0.6400 0.9147 0.3065 5.0570

\##    B97D3                1.0000 2.2609 0.5545 3.2297


\##    PW6B95D3             1.0000 0.7257 0.2076 6.3750


\##    B3LYP                1.0000 1.9889 0.3981 4.4211


\##    BLYP                 1.0000 2.6996 0.4298 4.2359


\##    PBE1PBE              1.0000 1.2177 0.4145 4.8593


\##    TPSSTPSS             1.0000 1.9435 0.4535 4.4752


\##    PBEPBE               1.0000 0.7875 0.4289 4.4407


\##    BP86                 1.0000 3.2822 0.3946 4.8516


\##    BPBE                 1.0000 4.0728 0.4567 4.3908


\##    B3PW91               1.0000 2.8524 0.4312 4.4693


\##    BMK                  1.0000 2.0860 0.1940 5.9197


\##    CAM–B3LYP            1.0000 2.0674 0.3708 5.4743

   LC-wPBE              1.0000 1.8541 0.3919 5.0897
   You can use this empirical dispersion method with other functionals via
   the IOps(3/174-178) (S6 should be 1.0).
   Energies, analytic gradients, and analytic frequencies; ADMP
   calculations.
   Third order properties such as hyperpolarizabilities and Raman
   intensities are not available for functionals for which third
   derivatives are not implemented: the exchange functionals G96, P86,
   PKZB, wPBEh and PBEh; the correlation functional PKZB; the hybrid
   functionals OHSE1PBE and OHSE2PBE.
   IOp, Int=Grid, Stable, TD, DenFit, B2PLYP, mPW2LYP
   The energy is reported in DFT calculations in a form similar to that of
   Hartree-Fock calculations. Here is the energy output from a B3LYP
   calculation:
 SCF Done:  E(RB3LYP) =  -75.3197099428     A.U. after    5 cycles
   Last updated on: 30 August 2022. [G16 Rev. C.01]