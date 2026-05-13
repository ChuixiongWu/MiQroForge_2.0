# Gaussian 16 Time-Dependent DFT

   time-dependent Hartree-Fock or DFT method [Bauernschmitt96a, Casida98,
   Stratmann98, VanCaillie99, VanCaillie00, Furche02, Scalmani06];
   analytic gradients [Furche02, Scalmani06] and frequencies [Liu11,
   Liu11a, WilliamsYoung17p] are available in Gaussian 16. For a review of
   using TD-DFT to predict excited state properties, see [Adamo13,
   Laurent13].
   Time-dependent DFT calculations can employ the Tamm-Dancoff
   approximation, via the TDA keyword. TD-DFTB calculations can also be
   performed [Trani11].
   Note that the normalization criteria used is <X+Y|X-Y>=1.
   Electronic circular dichroism (ECD) analysis is also performed during
   these calculations [Helgaker91, Bak93, Bak95, Olsen95, Hansen99,
   Autschbach02].
   Options
Options for Closed Shell Singlets Only
   The following options apply to closed-shell singlet systems only. If
   the system is not a closed-shell singlet, these options are ignored.
Singlets
   Solve only for singlet excited states. This is the default for closed
   shell systems.
Triplets
   Solve only for triplet excited states.
50-50
   Solve for half triplet and half singlet states.
General Options
Root=N
   Specifies the “state of interest”. The default is the first excited
   state (N=1).
NStates=M
   Solve for M states (the default is 3). If 50-50 is requested, NStates
   gives the number of each type of state for which to solve (i.e., the
   default is 3 singlets and 3 triplets).
   The keyword Read may also be specified as the parameter to the NStates
   option. In this case, the number of states to compute is read from the
   input stream. This features is typically used in EET calculations.
Add=N
   Read converged states off the checkpoint file and solve for an
   additional N states. This option implies Read as well.
Read
   Reads initial guesses for the states off the checkpoint file. Note
   that, unlike for SCF, an initial guess for one basis set cannot be used
   for a different one.
Restart
   This option restarts a TD calculation after the last completed
   iteration. A failed job may be restarted from its checkpoint file by
   simply repeating the route section of the original job, adding the
   Restart option to the keyword/option. No other input is required.
EqSolv
   Whether to perform equilibrium or non-equilibrium PCM solvation.
   NonEqSolv is the default except for excited state optimizations and
   when the excited state density is requested (e.g., with Density=Current
   or All).
IVOGuess
   Force use of IVO guess. This is the default for TD Hartree-Fock.
   NoIVOGuess forces the use of canonical single excitations for guess,
   and it is the default for TD-DFT. The HFIVOGuess option forces the use
   of Hartree-Fock IVOs for the guess, even for TD-DFT.
SOS
   Do sum-over states polarizabilities, etc. By default, all excited
   states are solved for. A list of frequencies at which to do the sums is
   read in. Zero frequency is always done and need not be in the list.
NonAdiabaticCoupling
   Requests that the ground-to-excited-state non-adiabatic coupling be
   computed [Send10, Lingerfelt16]. NAC is a synonym for this option.
   NoNonAdiabaticCoupling and NoNAC suppress this behavior. The default is
   NoNAC when computing energies or energies+gradients because the extra
   cost is non-trivial. The default is NAC during frequency calculations
   where the extra cost is negligible.
Conver=N
   Sets the convergence calculations to 10^–N on the energy and 10^-(N-2)
   on the wavefunction. The default is N=4 for single points and N=6 for
   gradients.
Energy Range Options
   An energy range can be specified for CIS and TD excitation energies
   using the following options to CIS, TD and TDA.
GOccSt=N
   Generate initial guesses using only active occupied orbitals N and
   higher.
GOccEnd=N
   Generate initial guesses: if N>0, use only the first N active occupied
   orbitals; if N<0, do not use the highest |N| occupieds.
GDEMin=N
   Generate guesses having estimated excitation energies ≥ N/1000 eV.
DEMin=N
   Converge only states having excitation energy ≥ N/1000 eV; if N=-2,
   read threshold from input; if N<-2, set the threshold to |N|/1000
   Hartrees. [Liang11, Lestrange15]
IFact=N
   Specify factor by which the number of states updated during initial
   iterations is increased. The default for IFact is Max(4,g) where g is
   the order of the Abelian point group.
WhenReduce=M
   Reduce to the desired number of states after iteration M. The default
   for WhenReduce is 1 for TD and 2 for TDA. Larger values may be needed
   if there are many states in the range of interest.
   Availability
   Energies, gradients and frequencies using Hartree-Fock or a DFT method.
   Gradients and frequencies are not available for functionals for which
   third and fourth derivatives are not implemented: the exchange
   functionals G96, P86, PKZB, wPBEh and PBEh; the correlation functional
   PKZB; the hybrid functionals OHSE1PBE and OHSE2PBE.
   Related Keywords
   CIS, ZIndo, Output
   Examples
   Here is the key part of the output from a TD excited states
   calculation:
 Excitation energies and oscillator strengths:
 Excited State 1:  Singlet-A2  4.0147 eV  308.83 nm  f=0.0000  <S**2>=0.000
       8 ->  9         0.70701
 This state for optimization and/or second-order correction.
 Copying the excited state density for this state as the 1-particle RhoCI densit
y.
 Excited State 2:  Singlet-B1  9.1612 eV  135.34 nm  f=0.0017  <S**2>=0.000
       6 ->  9         0.70617
 Excited State 3:  Singlet-B2  9.5662 eV  129.61 nm  f=0.1563  <S**2>=0.000
       8 -> 10         0.70616
   The results on each state are summarized, including the spin and
   spatial symmetry, the excitation energy, the oscillator strength, the
   S^2, and (on the second line for each state) the largest coefficients
   in the CI expansion.
   The ECD results appear slightly earlier in the output as follows:
 1/2[<0|r|b>*<b|rxdel|0> + (<0|rxdel|b>*<b|r|0>)*]
 Rotatory Strengths (R) in cgs (10**-40 erg-esu-cm/Gauss)
   state         XX          YY          ZZ     R(length)     R(au)
     1        0.0000      0.0000      0.0000      0.0000      0.0000
     2        0.0000      0.0000      0.0000      0.0000      0.0000
     3        0.0000      0.0000      0.0000      0.0000      0.0000
  1/2[<0|del|b>*<b|r|0> + (<0|r|b>*<b|del|0>)*] (Au)
   state         X           Y           Z         Dip. S.   Osc.(frdel)
     1         0.0000      0.0000      0.0000      0.0000      0.0000
     2        -0.0050      0.0000      0.0000      0.0050      0.0033
     3         0.0000     -0.2099      0.0000      0.2099      0.1399
   Last updated on: 31 May 2023. [G16 Rev. C.01]