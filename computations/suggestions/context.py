'''
Created on 5/07/2016

@author: achim
'''
from .utilities import *  # @UnusedWildImport


class pareto_context:
    """
    contains the data for the projects and the simulation
    furthermore some important environment settings:

    * project view length
    * financial data calculations

    also set the strategy for optimize and calculate stuff
    """

    timelineLength = 4*12  # this is the planning horizon in months

    def tick_to_start_date(self, tick):
        # convert a simulation tick, as used in events/scenarios to
        # their calendar date.
        return monthsIncrement(self.first_tick_start, tick-1)

    def createFromDjango(self, djangoModels, theSimulation_id):
        """
        this method pulls together all data from the database
        This method might go into the django-merlin project.

        The project and phase ids for the optimization task are
        specified somewhere else.
        """

        # this essentially comes from the start of the plan view
        # and now from the simulation object of the database
        self.first_tick_start = djangoModels.Simulation.objects.get(
                                    pk=theSimulation_id).start_date
        self.timelineStart = self.first_tick_start

        # also the full model and the scenarios
        from merlin_api.pymerlin_adapter import \
            django2pymerlin, django_scenario2pymerlin  # @UnresolvedImport

        queryset = djangoModels.Simulation.objects.prefetch_related(
                                "entities", "outputs",
                                "outputs__inputs",
                                "unittypes", "attributes",
                                "entities__parent",
                                "entities__children",
                                "entities__outputs",
                                "entities__outputs__unit_type",
                                "entities__outputs__endpoints",
                                "entities__outputs__endpoints__input",
                                "entities__outputs__endpoints__sim_output",
                                "entities__inputs",
                                "entities__inputs__unit_type",
                                "entities__inputs__source",
                                "entities__processes",
                                "entities__processes__properties")

        self.msim = django2pymerlin(queryset.get(pk=theSimulation_id))
        # convert all scenarios
        # collect data and be simulation specific
        queryset = djangoModels.Scenario.objects
        allScenarios = {s for s in queryset.filter(sim__id=theSimulation_id)}

        # Scenario.name
        # baseline -> everything added in the services view
        # haircut -> everything added from haircut view
        # all others are (hopefully) project related
        self.mscen = [django_scenario2pymerlin(s, self.msim)
                      for s in allScenarios if s.name != "haircut"]

        # collect all projects, phases, scenarios from DB
        self.allProjects = []
        for p in djangoModels.Project.objects.all():
            theProject = project(id=p.id, phases=[], name=p.name)

            for ph in p.phases.all():
                theProject.phases.append(projectphase(
                    # is it possible to have a project referring to
                    # different simulations?
                    scenario_id=(ph.scenario.id
                                 if ph.scenario.sim.id == theSimulation_id
                                 else None),
                    start_date=ph.start_date,
                    end_date=ph.end_date,
                    id=ph.id,
                    name=ph.name,
                    is_active=ph.is_active,
                    investment_cost=ph.investment_cost,
                    service_cost=ph.service_cost,
                    capitalization_ratio=ph.capitalization
                    ))
            self.allProjects.append(theProject)

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
                                                     first_tick_start) + 1
                # set start, set end
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
                           [m for m in pyScenarios
                            if m.id in phaseScenarioIds])
        self.msim.run(scenarios=activeScenarios, end=self.timelineLength)
        tele = self.msim.get_sim_telemetry()
        return tele
