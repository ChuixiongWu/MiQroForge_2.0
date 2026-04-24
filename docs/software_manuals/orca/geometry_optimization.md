# Geometry Optimization

## Page 734

ORCA Manual, Release 6.0
Input Example
The fic-MRCC module can be started by specifying the CIType keyword in the %autoci block or by adding
fic-MRCC to the simple input line of an ORCA input file. The following example computes the singlet ground
state energy of four hydrogen atoms arranged as a square with a side length of 2𝑎0, which is commonly known as
the H4 model [418].
! cc-pVTZ Bohrs
# it is possible to add the `fic-MRCC' keyword here
# and omit the %autoci block below
%maxcore 10000
%casscf
nel 2
norb 2
mult 1
nroots 1
end
%autoci
# CAS settings are automatically copied from the CASSCF block!
citype fic-mrcc
end
* int 0 1
H 0 0 0 0.0
0.0 0.0
H 1 0 0 2.0
0.0 0.0
H 2 1 0 2.0 90.0 0.0
H 1 2 3 2.0 90.0 0.0
*
In this example, ORCA will first run a state-specific CASSCF calculation, and then immediately continue with the
fic-MRCC calculation on top of the CASSCF solution from the first step. It is, however, not required to always run a
CASSCF calculation before the autoci module. Any ORCA gbw/mp2nat/... file is accepted through %moinp,
although that route requires the user to specify the active space in the autoci block. autoci will then compute a
CASCI solution with the provided input orbitals and use that information to drive the correlated calculations.
Please be aware that fic-MRCC is a very extensive theory, which leads to long run times. The computational
effort depends mainly on the number of orbitals, the number of total electrons and the size of the active space.
On modestly modern hardware, calculations of ∼300 orbitals with a CAS(2,2) should be readily achievable. For
larger active spaces, such as a CAS(6,6), calculations with a total of ∼200 orbitals will also complete within a day.
7.26 Geometry Optimization
ORCA is able to calculate equilibrium structures (minima and transition states) using the quasi Newton update
procedure with the well known BFGS update [67, 241, 399, 763, 764, 765], the Powell or the Bofill update. The
optimization can be carried out in either redundant internal (recommended in most cases) or Cartesian displacement
coordinates. As initial Hessian the user can choose between a diagonal initial Hessian, several model Hessians
(Swart, Lindh, Almloef, Schlegel), an exact Hessian and a partially exact Hessian (both recommended for transition
state optimization) for both coordinate types. In redundant internal coordinates several options for the type of step
to be taken exist. The user can define constraints via two different paths. He can either define them directly (as
bond length, angle, dihedral or Cartesian constraints) or he can define several fragments and constrain the fragments
internally and with respect to other fragments. The ORCA optimizer can be used as an external optimizer, i.e.the
energy and gradient calculations done by ORCA.
714
Chapter 7. Detailed Documentation

## Page 735

ORCA Manual, Release 6.0
7.26.1 Input Options and General Considerations
The use of the geometry optimization module is relatively straightforward.1
%method RunTyp Opt # use geometry optimization.
#(equivalent is RunTyp=Geom)
end
# or simply "! Opt" in the keyword line
# details of the optimization are controlled here
%geom
MaxIter 50
# max. number of geometry iterations
#
(default is 3N (N = number of atoms), at least 50 )
# coordinate type control
coordsys redundant
# redundant internal coords (2022)
cartesian
# Cartesian coordinates
# fallback option to Cartesian step if internals fail
cartfallback true
# transition state (TS) optimization
TS_search EF
# Switch on TS search, EF means
#
"eigenvector following"
#
alternatively use "! OptTS"
TS_Mode {M 0} end # Choose the mode to follow uphill in the
#
TS optimization. {M X}: eigenvector of
#
the Hessian with X. lowest eigenvalue
#
(start counting at zero) (default: X=0)
# Instead of a mode choose an internal coordinate strongly
#
involved in the eigenmode followed uphill
TS_Mode {B 0 1} end
# bond between atoms 0 and 1
or
TS_Mode {A 2 1 0} end
# angle between atoms 2, 1 and 0
or
TS_Mode {D 3 2 1 0} end
# dihedral of atoms 3, 2, 1 and 0
# add or remove internal coordinates from the automatically
#
generated set of redundant internal coords
modify_internal
{ B 10 0 A }
# add a bond between atoms 0 and 10
{ A 8 9 10 R }
# remove the angle defined
#
by atoms 8, 9 and 10
{ D 7 8 9 10 R }
# remove the dihedral angle defined
end
#
by atoms 7, 8, 9 and 10
# constrain internal coordinates:
Constraints
{ B N1 N2 value C }
# the bond between N1 and N2
{ A N1 N2 N1 value C }
# the angle defined by N1, N2
#
and N3
{ D N1 N2 N3 N4 value C } # the dihedral defined by N1,
#
N2, N3 and N4
{ C N1 C }
# the cartesian position of N1
{ B N1 * C}
# all bonds involving N1
{ B * * C}
# all bonds
{ A * N2 * C }
# all angles with N2 as central atom
{ A * * * C }
# all angles
{ D * N2 N3 * C } # all dihedrals with N2 and N3 as
#
central atoms
{ D * * * * C }
# all dihedrals
end
# scan an internal coordinate:
Scan B N1 N2 = value1, value2, N end
(continues on next page)
1 But that doesn’t mean that geometry optimization itself is straightforward! Sometimes, even when it is not expected the convergence can
be pretty bad and it may take a better starting structure to come to a stationary point. In particular floppy structures with many possible rotations
around single bonds and soft dihedral angle modes are tricky. It may sometimes be advantageous to compute a Hessian matrix at a “cheap”
level of theory and then do the optimization in Cartesian coordinates starting from the calculated Hessian.
7.26. Geometry Optimization
715