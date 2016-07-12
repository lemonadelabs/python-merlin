'''
Created on 5/07/2016

@author: achim
'''
import datetime
from .utilities import *  # @UnusedWildImport


def test_optimize():

    pcon = pareto_context()
    # pcon.enableIPP()
    # a minimal test to try out the interface
    from examples.DIAServicesModel import createRegistrationServiceWExternalDesktops as createModel  # @UnresolvedImport
    pcon.msim = createModel()

    from pymerlin import merlin
    pcon.mscen = [merlin.Scenario(name="bla",
                                  events=set(),
                                  sim=pcon.msim,
                                  start_offset=1)]

    pcon.allProjects = []

    pcon.timelineStart = datetime.date(2016, 7, 1)
    pcon.timelineLength = 12*4

    # project phase
    newPhase = projectphase(id=1,
                            name="test",
                            is_active=True,
                            start_date=datetime.date(2016, 7, 1),
                            end_date=datetime.date(2016, 12, 31),
                            service_cost=1e6,
                            investment_cost=1e6,
                            scenario_id=pcon.mscen[0].id,
                            capitalization_ratio=1.0
                            )

    # define some projects, at least for the financial calculations
    newProject = project(id=1,
                         name="test project",
                         phases=[newPhase]
                         )
    pcon.allProjects.append(newProject)

    from .algorithm import pareto
    p = pareto(pcon)
    assert len(p.generate_parameter_list(projectId=1,
                                         alignToQuarters=False)[1]
               ) == 43
    assert len(p.generate_parameter_list(projectId=1,
                                         phaseId=1,
                                         alignToQuarters=False)[1]
               ) == 43
    del p

    pcon.optimize(projectId=1, phaseId=1)


class pareto_context:
    """
    contains the data for the projects and the simulation
    furthermore some important environment settings:

    * project view length
    * financial data calculations

    also set the strategy for optimize and calculate stuff
    """

    def __init__(self):
        self.first_tick_start = 1
        self.mscen = None
        self.msim = None

    timelineLength = 10*12  # simulation run length in ticks/months
    planViewLength = 4*12  # planning horizon in months

    def enableIPP(self):
        # check for existence of default config
        import os.path
        ipp_config = os.path.join(os.environ["HOME"],
                                  ".ipython",
                                  "profile_default",
                                  "security",
                                  "ipcontroller-client.json")
        if os.path.isfile(ipp_config):
            from ipyparallel import Client
            import functools
            self.ippClientFactory = functools.partial(Client,
                                                      url_file=ipp_config)

    def tick_to_start_date(self, tick):
        # convert a simulation tick, as used in events/scenarios to
        # their calendar date.
        return monthsIncrement(self.timelineStart, tick-1)

    def updateScenarios(self, projects):
        # update the event timing for each project phase
        # the scenarios are updated in place
        for p in projects:
            for ph in p.phases:
                scen = next(s for s in self.mscen if s.id == ph.scenario_id)
                # adjust times of phase:
                length = monthsDifference(
                                    ph.end_date+datetime.timedelta(days=1),
                                    ph.start_date)
                scen.start_offset = monthsDifference(ph.start_date,
                                                     self.timelineStart) + 1
                if scen.events:
                    # set time for start and end events separately
                    evStartTick = min(ev.time for ev in scen.events)
                    for ev in scen.events:
                        # the minimum should be start
                        if ev.time == evStartTick:
                            ev.time = 0
                            # the other one an end event, which happens at the
                            # begin of the first month after start.
                        else:
                            ev.time = length

    def runSimulation(self, theProjects):
        self.updateScenarios(theProjects)
        pyScenarios = self.mscen
        # put in the scenarios from baseline and then the projects
        baselineScenIds = [b.id for b in pyScenarios if b.name == "baseline"]
        # also order projects by time (scenario.start_offset)
        phaseScenarioIds = [ph.id
                            for p in sorted(
                                    theProjects,
                                    key=lambda pp: min(pph.start_date
                                                       for pph in pp.phases))
                            for ph in p.phases if ph.is_active]
        # put baseline scenarios in front
        activeScenarios = ([m for m in pyScenarios
                            if m.id in baselineScenIds] +
                           # this doesn't preserve order of phaseScenarioIds!
                           [m for m in pyScenarios
                            if m.id in phaseScenarioIds])
        self.msim.run(scenarios=activeScenarios, end=self.timelineLength)
        tele = self.msim.get_sim_telemetry()
        return tele

    def optimize(self, projectId=None, phaseId=None):
        """
        runs the default optimization if not modified in context

        the context needs being populated with:

        * a python-merlin simulation
        * a list of projects related to this simulation
        * scenarios related to the project phase actions and including baseline
        * the length of the planning timeline and the start date
        """
        assert projectId is not None or phaseId is not None

        assert getattr(self, "msim", None) is not None
        assert getattr(self, "mscen", None) is not None
        assert getattr(self, "timelineLength", None) is not None
        assert getattr(self, "timelineStart", None) is not None

        from .algorithm import pareto
        return pareto(self).optimize(projectId, phaseId)

    def collectOutputs(self):

        # find all outputs, name, type, minimum
        # the data structure is used to differentiate between
        # service outputs and their financial indicators

        return {o.id: (o.name, o.type, o.minimum)
                for o in self.msim.outputs}
