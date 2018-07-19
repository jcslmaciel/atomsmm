from __future__ import print_function

import pytest
from simtk import openmm
from simtk import unit
from simtk.openmm import app

import atomsmm


def execute(degree, target):
    rcut = 10*unit.angstroms
    rswitch = 9.5*unit.angstroms
    alpha = 0.29/unit.angstroms
    pdb = app.PDBFile('tests/data/q-SPC-FW.pdb')
    forcefield = app.ForceField('tests/data/q-SPC-FW.xml')
    system = forcefield.createSystem(pdb.topology, nonbondedMethod=app.CutoffPeriodic)
    force = atomsmm.DampedSmoothedForce(alpha, rswitch, rcut, degree=degree)
    force.importFrom(atomsmm.HijackNonbondedForce(system)).addTo(system)
    integrator = openmm.VerletIntegrator(0.0*unit.femtoseconds)
    platform = openmm.Platform.getPlatformByName('Reference')
    simulation = app.Simulation(pdb.topology, system, integrator, platform)
    simulation.context.setPositions(pdb.positions)
    state = simulation.context.getState(getEnergy=True)
    potential = state.getPotentialEnergy()
    assert potential/potential.unit == pytest.approx(target)


def test_linear():
    execute(1, 1766.0240800207146)


def test_quadratic():
    execute(2, 1765.940220790936)
