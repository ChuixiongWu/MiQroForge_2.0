# Frequency Calculations

## Page 750

ORCA Manual, Release 6.0
7.27.1 Restarting Numerical Frequency calculations
To restart a numerical frequencies calculation, use:
%FREQ
restart true
END
and ORCA will look for basename.res.{} files in the same folder where the calculation is being run, check for what
already has been done and restart where it is needed.
7.28 Intrinsic Reaction Coordinate
The Intrinsic Reaction Coordinate (IRC) method finds a path connecting a transition state (TS) with its downhill-
nearest intermediates. The implementation in ORCA follows the method suggested by Morokuma and cowork-
ers.[412]
The IRC method follows the gradient of the nuclear coordinates. As the gradient is negligible at a TS, first an initial
displacement from the TS structure has to be carried out, based on the eigenmodes of the Hessian, in order to get
to a region with nonnegligible gradient. For the initial displacement the eigenvector of the eigenmode with lowest
frequency (hessMode=0) is normalized and then scaled by Scale_Displ_SD (which by default is chosen such that
an energy change of Init_Displ_DE can be expected). Two initial displacements, forward and backward, are taken
by adding the resulting displacement vector (multiplied with +1 and -1, respectively) to the initial structure. If the
user requests the downhill direction (e.g. from a previous unconverged IRC run), it is assumed that the gradient is
nonzero and thus no initial displacement is carried out.
After the initial displacement the iterations of the IRC method begin. Each iteration consists of two main steps,
which each consist again of multiple SP and gradient runs:
1. Initial steepest descent (SD) step:
1. The gradient (grad0) of the starting geometry (G0) is normalized, scaled by Scale_Displ_SD, and the
resulting displacement vector (SD1) is applied to G0.
2. Optional (if SD_ParabolicFit is true): If SD1 increases the energy, a linear search is taken along the
direction of the displacement vector:
1. The displacement vector SD1 is scaled by 0.5 (SD2 = 0.5 x SD1) and again added to G0.
2. A parabolic fit for finding the displacement vector (SD3) which leads to minimal energy is carried
out using the three SP energies (G0, geometry after SD1 and after SD2 step). SD3 has the same
direction as SD1 and SD2, but can have a different length.
3. The keyword Interpolate_only controls whether the length of SD3 has to be in between 0 and and
the length of SD1. If that is the case, the maximum length is determined by SD1, the minimum
length is zero.
3. At the resulting geometry G1 (G0+SD1 or G0+SD3) the gradient is calculated (grad1).
2. Optional (if Do_SD_Corr is true): Correction to the steepest descent step:
1. Based on grad0 and grad1 a vector is computed which represents a correction to the first SD (SD1 or
SD3) step. This correction brings the geometry closer to the IRC.
2. This vector is normalized, scaled by Scale_Displ_SD_Corr times the length of SD1 or SD3, and the
resulting displacement vector (SDC1) is applied to G1.
3. Optional (if SD_Corr_ParabolicFit is true):
1. If the energy increases after applying step SDC1, SDC1 is scaled by 0.5 (SDC2 = 0.5 x SD1), if
the energy decreases, SDC1 is scaled by 2 (SDC2 = 2 x SD1). SDC2 is then added to G1.
730
Chapter 7. Detailed Documentation