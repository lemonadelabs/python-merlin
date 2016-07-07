'''
Created on 5/07/2016

@author: achim
'''
import datetime
from .utilities import *  # @UnusedWildImport

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

    timelineLength = 4*12  # this is the planning horizon in months

    def tick_to_start_date(self, tick):
        # convert a simulation tick, as used in events/scenarios to
        # their calendar date.
        return monthsIncrement(self.first_tick_start, tick-1)

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
                                                     self.first_tick_start) + 1
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
