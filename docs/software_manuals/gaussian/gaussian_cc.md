# Gaussian 16 Coupled Cluster Methods

   [Bartlett78], using double substitutions from the Hartree-Fock
   determinant for CCD [Pople78], or both single and double substitutions
   for CCSD [Cizek69, Purvis82, Scuseria88, Scuseria89]. CC and QCID are
   synonyms for CCD. RO may be combined with CCSD for a restricted
   open-shell energy calculation [Watts93].
   Options
FC
   All frozen core options are available with this keyword; a frozen core
   calculation is the default. See the discussion of the FC options for
   full information.
T
   Include triple excitations non-iteratively [Purvis82, Pople87] (CCSD
   only). CCSD-T is a synonym for CCSD(T).
E4T
   Used with the T option to request inclusion of triple excitations for
   both the complete MP4 as well as CCSD(T).
T1Diag
   Computes the T1 diagnostic of T. J. Lee and coworkers [Lee89] (CCSD
   only).
Conver=N
   Sets the convergence calculations to 10^-N on the energy and 10^-(N-2)
   on the wavefunction. The default is N=7 for single points and N=8 for
   gradients.
MaxCyc=N
   Specifies the maximum number of cycles for CCSD calculations.
TWInCore
   Whether to store amplitudes and products in memory during higher-order
   post-SCF calculations. The default is to store these if possible, but
   to run off disk if memory is insufficient. TWInCore causes the program
   to terminate if these can not be held in memory, while NoTWInCore
   prohibits in-memory storage.
SaveAmplitudes
   Saves the converged amplitudes in the checkpoint file for use in a
   subsequent calculation (e.g., using a larger basis set). Using this
   option results in a very large checkpoint file, but also may
   significantly speed up later calculations.
ReadAmplitudes
   Reads the converged amplitudes from the checkpoint file (if present).
   Note that the new calculation can use a different basis set, method (if
   applicable), etc. than the original one.
   Availability
   Analytic energies and gradients for CCD and CCSD, numerical gradients
   for CCSD(T), and numerical frequencies for all methods.
   The restricted open-shell (RO) method is available for CCSD and CCSD(T)
   energy calculations.
   Related Keywords
   MP4, Transformation
   Examples
   The Coupled Cluster energy appears in the output as follows following
   the final correlation iteration. The CCSD energy is given in the first
   line below, and the final line reports the energy with triples
   included:
 Wavefunction amplitudes converged. E(Corr)=     -75.001924366
 …

\##  CCSD(T)= -0.75002048348D+02

   The CCSD energy is labeled E(CORR), and the energy including the
   non-iterative triples contribution is given in the final line.
   Last updated on: 05 January 2017. [G16 Rev. C.01]