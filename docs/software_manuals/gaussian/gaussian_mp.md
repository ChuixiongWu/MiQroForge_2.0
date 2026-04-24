# Gaussian 16 Møller-Plesset Perturbation Theory

   The MPn method keywords request a Hartree-Fock calculation (by default,
   RHF for singlets, UHF for higher multiplicities) followed by a
   Møller-Plesset correlation energy correction [Moller34]:
     * MP2: The Møller-Plesset expansion is truncated at second-order
       [Frisch90b, Frisch90c, Head-Gordon88a, Saebo89, Head-Gordon94].
     * MP3: Third-order MP theory correction [Pople76, Pople77].
     * MP4: Fourth-order MP theory correction [Raghavachari78], which
       defaults to full MP4 with single, double, triple and quadruple
       substitutions [Raghavachari78, Raghavachari80] (MP4(SDTQ)).
     * MP4(DQ): Include only the space of double and quadruple
       substitutions in the MP expansion.
     * MP4(SDQ): Include only single, double and quadruple substitutions.
     * MP5: Fifth-order MP theory correction [Raghavachari90]. The MP5
       code has been written for the open-shell case only, and so
       specifying MP5 defaults to a UMP5 calculation. This method requires
       O^3V^3 disk storage and scales as O^4V^4 in cpu time.
   Analytic gradients are available for MP2 [Frisch90b, Frisch90c,
   Pople79, Handy84], MP3 and MP4(SDQ) [Trucks88, Trucks88a], and analytic
   frequencies are available for MP2 [Head-Gordon94]. ROMP2, ROMP3 and
   ROMP4 energies are also available [Knowles91, Lauderdale91,
   Lauderdale92].
Double-Hybrid Methods
   Gaussian 16 also includes some double hybrid methods that combine exact
   HF exchange with an MP2-like correlation to a DFT calculation. These
   methods have the same computational cost as MP2 (rather than that of
   DFT). Gaussian 16 includes:
     * Grimme’s B2PLYP [Grimme06a] and mPW2PLYP [Schwabe06] methods; the
       empirical dispersion corrected variations are specified by
       appending a D to the keyword name: e.g., B2PLYPD for B2PLYP with
       empirical dispersion [Schwabe07].
     * B2PLYPD3 requests the B2PLYP method combined with Grimme’s D3BJ
       dispersion [Grimme11, Goerigk11].
     * DSDPBEP86[Kozuch11,Kozuch13], a dispersion-corrected double hybrid
       functional with Grimme’s D3BJ dispersion.
     * The PBE0DH [Bremond11] and PBEQIDH [Bremond14] double-hybrid
       functionals.
   Options
Frozen Core Options
FC
   All frozen core options are available with this keyword; a frozen core
   calculation is the default. See the discussion of the FC options for
   full information.
Algorithm Selection Options for MP2 and Double Hybrid Methods
   The appropriate algorithm for MP2 will be selected automatically based
   on the settings of %Mem and MaxDisk. Thus, the following options are
   almost never needed.
FullDirect
   Forces the fully direct algorithm, which requires no external storage
   beyond that for the SCF. Requires a minimum of 2OVN words of main
   memory (O=number of occupied orbitals, V=number of virtual orbitals,
   N=number of basis functions). This is seldom a good choice, except for
   machines with very large main memory and limited disk.
TWInCore
   Whether to store amplitudes and products in memory during higher-order
   post-SCF calculations. The default is to store these if possible, but
   to run off disk if memory is insufficient. TWInCore causes the program
   to terminate if these can not be held in memory, while NoTWInCore
   prohibits in-memory storage.
SemiDirect
   Forces the semi-direct algorithm.
Direct
   Requests some sort of direct algorithm. The choice between in-core,
   fully direct and semidirect is made by the program based on memory and
   disk limits and the dimensions of the problem.
InCore
   Forces the in-memory algorithm. This is very fast when it can be used,
   but requires N^4/4 words of memory. It is normally used in conjunction
   with SCF=InCore. NoInCore prevents the use of the in-core algorithm.
   Availability
   MP2, B2PLYP methods, mPW2PLYP methods: Energies, analytic gradients,
   and analytic frequencies.
   MP3, MP4(DQ) and MP4(SDQ): Energies, analytic gradients, and numerical
   frequencies.
   MP4(SDTQ) and MP5: Analytic energies, numerical gradients, and
   numerical frequencies.
   RO may be combined with MP2, MP3 and MP4 for energies only.
   Related Keywords
   HF, SCF, Transformation, MaxDisk
   Examples
   The MP2 energy appears in the output as follows, labeled as EUMP2:

## E2=        -.3906492545D-01 EUMP2=        -.75003727493390D+02

   Here is the output from an MP4(SDTQ) calculation:
Time for triples=         .04 seconds.

## MP4(T)=    -.55601167D-04


## E3=        -.10847902D-01        EUMP3=       -.75014575395D+02


## E4(DQ)=    -.32068082D-02        UMP4(DQ)=    -.75017782203D+02


## E4(SDQ)=   -.33238377D-02        UMP4(SDQ)=   -.75017899233D+02


## E4(SDTQ)=  -.33794389D-02        UMP4(SDTQ)=  -.75017954834D+02

   The energy labeled EUMP3 is the MP3 energy, and the various MP4-level
   corrections appear after it, with the MP4(SDTQ) value coming in the
   final line.
   The B2PLYP energy appears as follows in the output:

##  E2(B2PLYP) =    -0.3262340664D-01 E(B2PLYP) =    -0.39113226645200D+02

     * Description
     * Option
     * Availability
     * Examples
   The MPn method keywords request a Hartree-Fock calculation (by default,
   RHF for singlets, UHF for higher multiplicities) followed by a
   Møller-Plesset correlation energy correction [Moller34]:
     * MP2: The Møller-Plesset expansion is truncated at second-order
       [Frisch90b, Frisch90c, Head-Gordon88a, Saebo89, Head-Gordon94].
     * MP3: Third-order MP theory correction [Pople76, Pople77].
     * MP4: Fourth-order MP theory correction [Raghavachari78], which
       defaults to full MP4 with single, double, triple and quadruple
       substitutions [Raghavachari78, Raghavachari80] (MP4(SDTQ)).
     * MP4(DQ): Include only the space of double and quadruple
       substitutions in the MP expansion.
     * MP4(SDQ): Include only single, double and quadruple substitutions.
     * MP5: Fifth-order MP theory correction [Raghavachari90]. The MP5
       code has been written for the open-shell case only, and so
       specifying MP5 defaults to a UMP5 calculation. This method requires
       O^3V^3 disk storage and scales as O^4V^4 in cpu time.
   Analytic gradients are available for MP2 [Frisch90b, Frisch90c,
   Pople79, Handy84], MP3 and MP4(SDQ) [Trucks88, Trucks88a], and analytic
   frequencies are available for MP2 [Head-Gordon94]. ROMP2, ROMP3 and
   ROMP4 energies are also available [Knowles91, Lauderdale91,
   Lauderdale92].
Double-Hybrid Methods
   Gaussian 16 also includes some double hybrid methods that combine exact
   HF exchange with an MP2-like correlation to a DFT calculation. These
   methods have the same computational cost as MP2 (rather than that of
   DFT). Gaussian 16 includes:
     * Grimme’s B2PLYP [Grimme06a] and mPW2PLYP [Schwabe06] methods; the
       empirical dispersion corrected variations are specified by
       appending a D to the keyword name: e.g., B2PLYPD for B2PLYP with
       empirical dispersion [Schwabe07].
     * B2PLYPD3 requests the B2PLYP method combined with Grimme’s D3BJ
       dispersion [Grimme11, Goerigk11].
     * DSDPBEP86[Kozuch11,Kozuch13], a dispersion-corrected double hybrid
       functional with Grimme's D3BJ dispersion.
     * The PBE0DH [Bremond11] and PBEQIDH [Bremond14] double-hybrid
       functionals.
Frozen Core Options
FC
   All frozen core options are available with this keyword; a frozen core
   calculation is the default. See the discussion of the FC options for
   full information.
Algorithm Selection Options for MP2 and Double Hybrid Methods
   The appropriate algorithm for MP2 will be selected automatically based
   on the settings of %Mem and MaxDisk. Thus, the following options are
   almost never needed.
FullDirect
   Forces the fully direct algorithm, which requires no external storage
   beyond that for the SCF. Requires a minimum of 2OVN words of main
   memory (O=number of occupied orbitals, V=number of virtual orbitals,
   N=number of basis functions). This is seldom a good choice, except for
   machines with very large main memory and limited disk.
TWInCore
   Whether to store amplitudes and products in memory during higher-order
   post-SCF calculations. The default is to store these if possible, but
   to run off disk if memory is insufficient. TWInCore causes the program
   to terminate if these can not be held in memory, while NoTWInCore
   prohibits in-memory storage.
SemiDirect
   Forces the semi-direct algorithm.
Direct
   Requests some sort of direct algorithm. The choice between in-core,
   fully direct and semidirect is made by the program based on memory and
   disk limits and the dimensions of the problem.
InCore
   Forces the in-memory algorithm. This is very fast when it can be used,
   but requires N^4/4 words of memory. It is normally used in conjunction
   with SCF=InCore. NoInCore prevents the use of the in-core algorithm.
   MP2, B2PLYP methods, mPW2PLYP methods: Energies, analytic gradients,
   and analytic frequencies.
   MP3, MP4(DQ) and MP4(SDQ): Energies, analytic gradients, and numerical
   frequencies.
   MP4(SDTQ) and MP5: Analytic energies, numerical gradients, and
   numerical frequencies.
   RO may be combined with MP2, MP3 and MP4 for energies only.
   [/wonderplugin_tab_content] [wonderplugin_tab_content]
   Related Keywords
   HF, SCF, Transformation, MaxDisk
   The MP2 energy appears in the output as follows, labeled as EUMP2:

## E2=        -.3906492545D-01 EUMP2=        -.75003727493390D+02

   Here is the output from an MP4(SDTQ) calculation:
Time for triples=         .04 seconds.

## MP4(T)=    -.55601167D-04


## E3=        -.10847902D-01        EUMP3=       -.75014575395D+02


## E4(DQ)=    -.32068082D-02        UMP4(DQ)=    -.75017782203D+02


## E4(SDQ)=   -.33238377D-02        UMP4(SDQ)=   -.75017899233D+02


## E4(SDTQ)=  -.33794389D-02        UMP4(SDTQ)=  -.75017954834D+02

   The energy labeled EUMP3 is the MP3 energy, and the various MP4-level
   corrections appear after it, with the MP4(SDTQ) value coming in the
   final line.
   The B2PLYP energy appears as follows in the output:

##  E2(B2PLYP) =    -0.3262340664D-01 E(B2PLYP) =    -0.39113226645200D+02

   Last updated on: 05 January 2017. [G16 Rev. C.01]