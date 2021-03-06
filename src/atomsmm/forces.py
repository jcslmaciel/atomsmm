"""
.. module:: forces
   :platform: Unix, Windows
   :synopsis: a module for defining the basis class :class:`Force` and derived classes.

.. moduleauthor:: Charlles R. A. Abreu <abreu@eq.ufrj.br>

.. _CustomBondForce: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.CustomBondForce.html
.. _CustomNonbondedForce: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.CustomNonbondedForce.html
.. _Force: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.Force.html
.. _NonbondedForce: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.NonbondedForce.html
.. _System: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.System.html

"""

from simtk import openmm
from simtk import unit

from atomsmm.utils import Coulomb
from atomsmm.utils import InputError
from atomsmm.utils import LennardJones
from atomsmm.utils import LorentzBerthelot


class Force:
    """
    The basis class of every AtomsMM Force object, which is a list of OpenMM Force_ objects treated
    as a single force.

    Parameters
    ----------
        forces : list(openmm.Force), optional, default=[]
            A list of OpenMM Force objects.

    """
    def __init__(self, forces):
        self.forces = forces
        self.setForceGroup(0)

    def setForceGroup(self, group):
        """
        Set the force group to which this :class:`Force` object belongs.

        Parameters
        ----------
            group : int
                The group index. Legal values are between 0 and 31 (inclusive).

        Returns
        -------
            :class:`Force`
                Although the operation is done inline, the modified Force is returned for chaining
                purposes.

        """
        for force in self.forces:
            force.setForceGroup(group)
        return self

    def getForceGroup(self):
        """
        Get the force group to which this :class:`Force` object belongs.

        Returns
        -------
            int
                The group index, whose value is between 0 and 31 (inclusive).

        """
        return self.forces[0].getForceGroup()

    def includeExceptions(self):
        """
        Incorporate non-exclusion exceptions when importing parameters via method
        :func:`~Force.importFrom`.

        Returns
        -------
            :class:`Force`
                The object is returned for chaining purposes.

        """
        exceptions = _CustomBondForce()
        exceptions.setForceGroup(self.getForceGroup())
        self.forces.append(exceptions)
        return self

    def addTo(self, system):
        """
        Add the :class:`Force` object to an OpenMM System_ object.

        Parameters
        ----------
            system : openmm.System
                The system to which the force is being added.

        Returns
        -------
            :class:`Force`
                The object is returned for chaining purposes.

        """
        for force in self.forces:
            system.addForce(force)
        return self

    def importFrom(self, force):
        """
        Import parameters from a provided OpenMM NonbondedForce_ object.

        .. _NonbondedForce: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.NonbondedForce.html

        Parameters
        ----------
            force : openmm.NonbondedForce
                The force from which the parameters will be imported.

        Returns
        -------
            :class:`Force`
                The object is returned for chaining purposes.

        """
        for f in self.forces:
            f.importFrom(force)
        return self


class _NonbondedForce(openmm.NonbondedForce):
    """
    An extension of OpenMM's NonbondedForce_ class. By default, long-range dispersion correction is
    employed and the method used for long-range electrostatic interactions is `PME`.

    .. warning::
        All exceptions are turned into exclusions. Non-exclusion exceptions must be handled
        separately using a :class:`_CustomBondForce` object.

    Parameters
    ----------
        cutoff_distance : Number or unit.Quantity
            The cutoff distance being used for nonbonded interactions.
        switch_distance : Number or unit.Quantity, optional, default=None
            The distance at which the switching function begins to reduce the interaction. If this
            is None, then no switching will be done.
        nonbondedMethod : method, optional, default=openmm.NonbondedForce.PME
            The method used for handling long range nonbonded interactions.

    """
    def __init__(self, cutoff_distance, switch_distance=None,
                 nonbondedMethod=openmm.NonbondedForce.PME):
        super(_NonbondedForce, self).__init__()
        self.setNonbondedMethod(nonbondedMethod)
        self.setCutoffDistance(cutoff_distance)
        self.setUseDispersionCorrection(True)
        if switch_distance is None:
            self.setUseSwitchingFunction(False)
        else:
            self.setUseSwitchingFunction(True)
            self.setSwitchingDistance(switch_distance)

    def importFrom(self, force):
        """
        Import all particles and exceptions from the a passed OpenMM NonbondedForce_ object and
        turn all non-exclusion exceptions into exclusion ones.

        Parameters
        ----------
            force : openmm.NonbondedForce
                The force from which the particles and exclusions will be imported.

        Returns
        -------
            :class:`Force`
                The object is returned for chaining purposes.

        """
        for index in range(force.getNumParticles()):
            self.addParticle(*force.getParticleParameters(index))
        for index in range(force.getNumExceptions()):
            i, j, chargeprod, sigma, epsilon = force.getExceptionParameters(index)
            self.addException(i, j, 0.0*chargeprod, sigma, 0.0*epsilon)
        return self


class _CustomNonbondedForce(openmm.CustomNonbondedForce):
    """
    An extension of OpenMM's CustomNonbondedForce_ class.

    Parameters
    ----------
        energy : str
            An algebraic expression giving the interaction energy between two particles as a
            function of their distance `r`, as well as any per-particle and global parameters.
        cutoff_distance : Number or unit.Quantity
            The cutoff distance being used for nonbonded interactions.
        switch_distance :  Number or unit.Quantity, optional, default=None
            The distance at which the switching function begins to reduce the interaction. If this
            is None, then no switching will be done.
        parameters : list(str), optional, default=["charge", "sigma", "epsilon"]
            A list of nonbonded force parameters that depend on the individual particles.
        **kwargs
            Keyword arguments defining names and values of global nonbonded force parameters.

    """
    def __init__(self, energy, cutoff_distance, switch_distance=None,
                 parameters=["charge", "sigma", "epsilon"], **kwargs):
        super(_CustomNonbondedForce, self).__init__(energy)
        for name in parameters:
            self.addPerParticleParameter(name)
        for (name, value) in kwargs.items():
            self.addGlobalParameter(name, value)
        self.setNonbondedMethod(openmm.CustomNonbondedForce.CutoffPeriodic)
        self.setCutoffDistance(cutoff_distance)
        self.setUseLongRangeCorrection(False)
        if switch_distance is None:
            self.setUseSwitchingFunction(False)
        else:
            self.setUseSwitchingFunction(True)
            self.setSwitchingDistance(switch_distance)

    def importFrom(self, force):
        """
        Import all particles and exceptions from the a passed OpenMM NonbondedForce_ object.

        .. warning::
            All exceptions are turned into exclusions.

        .. _NonbondedForce: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.NonbondedForce.html

        Parameters
        ----------
            force : openmm.NonbondedForce
                The force from which the particles and exclusions will be imported.

        Returns
        -------
            :class:`Force`
                The object is returned for chaining purposes.

        """
        for index in range(force.getNumParticles()):
            self.addParticle(force.getParticleParameters(index))
        for index in range(force.getNumExceptions()):
            i, j, chargeprod, sigma, epsilon = force.getExceptionParameters(index)
            self.addExclusion(i, j)
        return self


class _CustomBondForce(openmm.CustomBondForce):
    """
    An extension of OpenMM's CustomBondForce_ class used to handle NonbondedForce exceptions.

    """
    def __init__(self):
        energy = "%s+%s;" % (LennardJones("r"), Coulomb("r"))
        super(_CustomBondForce, self).__init__(energy)
        self.addGlobalParameter("Kc", 138.935456*unit.kilojoules/unit.nanometer)
        self.addPerBondParameter("chargeprod")
        self.addPerBondParameter("sigma")
        self.addPerBondParameter("epsilon")

    def importFrom(self, force):
        """
        Import all non-exclusion exceptions from the a passed OpenMM NonbondedForce_ object.

        Parameters
        ----------
            force : openmm.NonbondedForce
                The force from which the exceptions will be imported.

        Returns
        -------
            :class:`Force`
                The object is returned for chaining purposes.

        """
        for index in range(force.getNumExceptions()):
            i, j, chargeprod, sigma, epsilon = force.getExceptionParameters(index)
            if chargeprod/chargeprod.unit != 0.0 or epsilon/epsilon.unit != 0.0:
                self.addBond(i, j, [chargeprod, sigma, epsilon])
        return self


class DampedSmoothedForce(Force):
    """
    A damped-smoothed version of the Lennard-Jones/Coulomb potential.

    .. math::
        & V(r)=\\left\\{
            4\\epsilon\\left[
                \\left(\\frac{\\sigma}{r}\\right)^{12}-\\left(\\frac{\\sigma}{r}\\right)^6
            \\right]+\\frac{q_1 q_2}{4\\pi\\epsilon_0}\\frac{\\mathrm{erfc}(r)}{r}
        \\right\\}S(r) \\\\
        & \\sigma=\\frac{\\sigma_1+\\sigma_2}{2} \\\\
        & \\epsilon=\\sqrt{\\epsilon_1\\epsilon_2} \\\\
        & S(r)=[1+\\theta(r-r_\\mathrm{switch})u^3(15u-6u^2-10)] \\\\
        & u=\\frac{r^n-r_\\mathrm{switch}^n}{r_\\mathrm{cut}^n-r_\\mathrm{switch}^n}

    In the equations above, :math:`\\theta(x)` is the Heaviside step function. Note that the
    switching function employed here, with `u` being a quadratic function of `r`, is slightly
    different from the one normally used in OpenMM, in which `u` is a linear function of `r`.

    Parameters
    ----------
        alpha : Number or unit.Quantity
            The Coulomb damping parameter (in inverse distance unit).
        cutoff_distance : Number or unit.Quantity
            The distance at which the nonbonded interaction vanishes.
        switch_distance : Number or unit.Quantity
            The distance at which the switching function begins to smooth the approach of the
            nonbonded interaction towards zero.
        degree : int, optional, default=1
            The degree `n` in the definition of the switching variable `u` (see above).

    """
    def __init__(self, alpha, cutoff_distance, switch_distance, degree=1):
        if switch_distance/switch_distance.unit < 0.0 or switch_distance >= cutoff_distance:
            raise InputError("Switching distance must satisfy 0 <= r_switch < r_cutoff")
        energy = "S*(%s + erfc(alpha*r)*%s);" % (LennardJones("r"), Coulomb("r"))
        if degree == 1:
            energy += "S = 1;"
        else:
            energy += "S = 1 + step(r - rswitch)*u^3*(15*u - 6*u^2 - 10);"
            energy += "u = (r^%d - rswitch^%d)/(rcut^%d - rswitch^%d);" % ((degree,)*4)
        energy += LorentzBerthelot()
        force = _CustomNonbondedForce(energy, cutoff_distance,
                                      switch_distance if degree == 1 else None,
                                      Kc=138.935456*unit.kilojoules/unit.nanometer,
                                      alpha=alpha, rswitch=switch_distance, rcut=cutoff_distance)
        super(DampedSmoothedForce, self).__init__([force])


class NonbondedExceptionsForce(Force):
    """
    A special class designed to compute only the exceptions of an OpenMM NonbondedForce object.

    """
    def __init__(self):
        super(NonbondedExceptionsForce, self).__init__([_CustomBondForce()])


class NearNonbondedForce(Force):
    """
    A smoothed version of the (optionally) shifted Lennard-Jones+Coulomb potential.

    .. math::
        & V(r)=\\left[U(r)-\\delta_\\mathrm{shift}U(r_\\mathrm{cut})\\right]S(r) \\\\
        & U(r)=4\\epsilon\\left[
                \\left(\\frac{\\sigma}{r}\\right)^{12}-\\left(\\frac{\\sigma}{r}\\right)^6
            \\right]+\\frac{1}{4\\pi\\epsilon_0}\\frac{q_1 q_2}{r} \\\\
        & \\sigma=\\frac{\\sigma_1+\\sigma_2}{2} \\\\
        & \\epsilon=\\sqrt{\\epsilon_1\\epsilon_2} \\\\
        & S(r)=\\theta(r_\\mathrm{cut}-r)[1+\\theta(r-r_\\mathrm{switch})u^3(15u-6u^2-10)] \\\\
        & u=\\frac{r-r_\\mathrm{switch}}{r_\\mathrm{cut}-r_\\mathrm{switch}}

    In the equations above, :math:`\\theta(x)` is the Heaviside step function. The constant
    :math:`\\delta_\\mathrm{shift}` is the numerical value (that is, 1 or 0) of the optional
    boolean argument `shifted`.

    .. note::
        Except for the shifting, this model is the "near" part of the RESPA2 scheme of
        Refs. :cite:`Zhou_2001` and :cite:`Morrone_2010`, with the switching function applied to
        the potential rather than to the force.

    Parameters
    ----------
        cutoff_distance : Number or unit.Quantity
            The distance at which the nonbonded interaction vanishes.
        switch_distance : Number or unit.Quantity
            The distance at which the switching function begins to smooth the approach of the
            nonbonded interaction towards zero.
        shifted : Bool, optional, default=True
            If True, a potential shift is done for both the Lennard-Jones and the Coulomb term
            prior to the potential smoothing.

    """
    def __init__(self, cutoff_distance, switch_distance, shifted=True):
        globalParams = {"Kc": 138.935456*unit.kilojoules/unit.nanometer,
                        "rc0": cutoff_distance}
        potential = "%s+%s" % (LennardJones("r"), Coulomb("r"))
        if shifted:
            potential += "-(%s+%s)" % (LennardJones("rc0"), Coulomb("rc0"))
        energy = "%s; %s" % (potential, LorentzBerthelot())
        force = _CustomNonbondedForce(energy, cutoff_distance, switch_distance, **globalParams)
        super(NearNonbondedForce, self).__init__([force])
        self.index = 0
        self.rswitch = switch_distance
        self.rcut = cutoff_distance
        self.shifted = shifted


class FarNonbondedForce(Force):
    """
    The complement of NearNonbondedForce and NonbondedExceptionsForce classes in order to form a
    complete OpenMM NonbondedForce.

    .. note::
        Except for the shifting, this model is the "far" part of the RESPA2 scheme of
        Refs. :cite:`Zhou_2001` and :cite:`Morrone_2010`, with the switching function applied to
        the potential rather than to the force.

    Parameters
    ----------
        preceding : :class:`NearNonbondedForce`
            The NearNonbondedForce object with which this Force is supposed to match.
        cutoff_distance : Number or unit.Quantity
            The distance at which the nonbonded interaction vanishes.
        switch_distance : Number or unit.Quantity, optional, default=None
            The distance at which the switching function begins to smooth the approach of the
            nonbonded interaction towards zero. If this is None, then no switching will be done
            prior to the potential cutoff.
        nonbondedMethod : openmm.NonbondedForce.Method, optional, default=PME
            The method to use for nonbonded interactions. Allowed values are NoCutoff,
            CutoffNonPeriodic, CutoffPeriodic, Ewald, PME, or LJPME.

    """
    def __init__(self, preceding, cutoff_distance, switch_distance=None,
                 nonbondedMethod=openmm.NonbondedForce.PME):
        if not isinstance(preceding, NearNonbondedForce):
            raise InputError("argument 'preceding' must be an internal RESPA force")
        rsi = "rs" + str(preceding.index)
        rci = "rc" + str(preceding.index)
        globalParams = {"Kc": 138.935456*unit.kilojoules/unit.nanometer,
                        rsi: preceding.rswitch, rci: preceding.rcut}
        potential = "-(%s+%s)" % (LennardJones("r"), Coulomb("r"))
        if preceding.shifted:
            potential += "+%s+%s" % (LennardJones(rci), Coulomb(rci))
        energy = "step(%s-r)*S*(%s);" % (rci, potential)
        energy += "S = 1 + step(r - %s)*u^3*(15*u - 6*u^2 - 10);" % rsi
        energy += "u = (r - %s)/(%s - %s);" % (rsi, rci, rsi)
        energy += LorentzBerthelot()
        discount = _CustomNonbondedForce(energy, cutoff_distance, None, **globalParams)
        total = _NonbondedForce(cutoff_distance, switch_distance, nonbondedMethod)
        super(FarNonbondedForce, self).__init__([total, discount])
