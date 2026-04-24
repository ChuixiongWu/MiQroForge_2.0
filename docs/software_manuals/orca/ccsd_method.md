# CCSD Method

## Page 1272

ORCA Manual, Release 6.0
A.2.5 Excited states
• Analytical gradient for meta-GGA functionals
• Small bugfix to spin-adapted triplets and NACMEs.
• The FolllowIRoot for excited state optimization uses now a much more robust algorithm.
A.2.6 Relativity
• Enabled NumGrad with relativistic methods
• Second order DKH picture-change correction of contact density
• Minor fixes in DKH picture-change corrections of magnetic properties
• Picture change corrections are activated automatically
A.2.7 Multiscale
• Reading PDB files for 10k+ atoms with HETATMs now possible
• Enabled correct FlipSpin behavior with QMMM
• More efficient MM Module
• Implemented wall potential
A.2.8 Coupled cluster / DLPNO
• Implemented energy ordering for PNO generation
• Added semicore treatment for DLPNO
• Enable DLPNO-CCSD(T) calculations to run DLPNO-CCSD unrelaxed densities
A.2.9 MP2
• Corrected memory estimates and batching in response and gradient
• Removed the slow and limited analytic (RI-)MP2 Hessian code
• Removed non-default Gamma-in-core option for RI-MP2 response
• Disabled single-precision calculations
• Disabled SemiDirect option in AO-MP2
• Enabled range-separated DHDFT gradients with RIJDX
A.2.10 NEB
• Improved IDPP initial path
• More efficient GFN-xTB runs for NEB
1252
Appendix A. Detailed change log