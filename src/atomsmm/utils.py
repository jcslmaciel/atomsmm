"""
.. module:: utils
   :platform: Unix, Windows
   :synopsis: a module for auxiliary tasks.

.. moduleauthor:: Charlles R. A. Abreu <abreu@eq.ufrj.br>

"""

from copy import deepcopy

from simtk import openmm
from simtk import unit


class InputError(Exception):
    def __init__(self, msg):
        super(InputError, self).__init__("\033[1;31m" + msg + "\033[0m")


def LennardJones(r):
    return "4*epsilon*((sigma/%s)^12 - (sigma/%s)^6)" % (r, r)


def Coulomb(r):
    return "Kc*chargeprod/%s" % r


def LorentzBerthelot():
    mixingRule = "chargeprod = charge1*charge2;"
    mixingRule += "sigma = 0.5*(sigma1+sigma2);"
    mixingRule += "epsilon = sqrt(epsilon1*epsilon2);"
    return mixingRule


def countDegreesOfFreedom(system):
    """
    Counts the number of degrees of freedom in a system, given by:

    .. math::
        N_\\mathrm{DOF} = 3N_\\mathrm{moving particles} - 3 - N_\\mathrm{constraints}

    Parameters
    ----------
        system : openmm.System
            The system whose degrees of freedom will be summed up.

    """
    N = system.getNumParticles()
    dof = sum(3 for i in range(N) if system.getParticleMass(i)/unit.dalton > 0) - 3
    dof -= system.getNumConstraints()
    return dof


def findNonbondedForce(system, position=0):
    """
    Searches for a NonbondedForce object in an OpenMM system.

    Parameters
    ----------
        system : openmm.System
            The system to which the wanted NonbondedForce object is attached.
        position : int, optional, default=0
            The position index of the wanted force among the NonbondedForce objects attached to
            the system.

    Returns
    -------
        int
            The index of the wanted NonbondedForce object.

    """
    forces = [system.getForce(i) for i in range(system.getNumForces())]
    return [i for (i, f) in enumerate(forces) if isinstance(f, openmm.NonbondedForce)][position]


def hijackForce(system, index):
    """
    Extracts a Force_ object from an OpenMM system.

    .. warning::

        Side-effect: the passed system object will no longer have the hijacked Force_ object in
        its force list.

    Parameters
    ----------
        index : int
            The index of the Force_ object to be hijacked.

    Returns
    -------
        openmm.Force
            The hijacked Force_ object.

    .. _Force: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.Force.html

    """
    force = deepcopy(system.getForce(index))
    system.removeForce(index)
    return force


def splitPotentialEnergy(system, topology, positions):
    """
    Computes the potential energy of a system, with possible splitting into contributions of all
    Force_ objects attached to the system.

    .. _Force: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.Force.html

    Parameters
    ----------
        system : openmm.System
            The system whose energy is to be computed.
        topology : openmm.app.topology.Topology
            The topological information about a system.
        positions : list(tuple)
            A list of 3D vectors containing the positions of all atoms.

    Returns
    -------
        unit.Quantity or dict(str, unit.Quantity)
            The total potential energy or a dict containing all potential energy terms.

    """
    syscopy = deepcopy(system)
    forces = [syscopy.getForce(i) for i in range(syscopy.getNumForces())]
    for (index, force) in enumerate(forces):
        force.setForceGroup(index)
    platform = openmm.Platform.getPlatformByName('Reference')
    integrator = openmm.VerletIntegrator(0.0)
    simulation = openmm.app.Simulation(topology, syscopy, integrator, platform)
    simulation.context.setPositions(positions)
    terms = dict()
    energy = dict()
    for (index, force) in enumerate(forces):
        state = simulation.context.getState(getEnergy=True, groups=set([index]))
        forceType = force.__class__.__name__
        if forceType not in terms:
            terms[forceType] = 0
            energy[forceType] = state.getPotentialEnergy()
        else:
            terms[forceType] += 1
            energy["%s(%d)" % (forceType, terms[forceType])] = state.getPotentialEnergy()
    energy["Total"] = sum(energy.values(), 0.0*unit.kilojoules_per_mole)
    return energy
