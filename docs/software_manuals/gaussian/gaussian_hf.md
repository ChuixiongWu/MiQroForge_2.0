# Gaussian 16 Hartree-Fock Method

   This method keyword requests a Hartree-Fock calculation [Roothaan51].
   Unless explicitly specified, RHF is used for singlets and UHF for
   higher multiplicities. In the latter case, separate α and β orbitals
   will be computed [Berthier54, Pople54] ([McWeeny68] for electron
   correlation methods starting from a UHF reference). RHF, ROHF or UHF
   can also be specified explicitly.
   Availability
   Energies, analytic gradients, and analytic frequencies for RHF and UHF
   and numerical frequencies for ROHF.
   Examples
   The Hartree-Fock energy appears in the output as follows:
      SCF Done:  E(RHF) =  -74.9646569691     A.U. after    4 cycles
      Conv  =     0.48D-08          -V/T =  2.0038
   For UHF jobs, the output also prints S^2 and related values:
 SCF Done:  E(UHF) =  -38.7068863059     A.U. after   11 cycles
             Convg  =    0.7647D-08             -V/T =  2.0031
 <Sx>= 0.0000 <Sy>= 0.0000 <Sz>= 1.0000 <S**2>= 2.0142 S= 1.0047

 Annihilation of the first spin contaminant:
 S**2 before annihilation     2.0142,   after     2.0001
   The second and third lines give the SCF convergence limit and the
   expectation value of S^2.
   Last updated on: 11 April 2017. [G16 Rev. C.01]