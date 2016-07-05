'''
Created on 5/07/2016

@author: achim
'''

from collections import namedtuple
import datetime
import builtins
from numpy import zeros

from .utilities import *


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
        this pulls together all data from the database
        the project and phase ids are specified somewhere else.

        this method might go into the django-merlin project.
        """

        # this essentially comes from the start of the plan view
        # and now from the simulation object of the database
        self.first_tick_start = djangoModels.Simulation.objects.get(
                                    pk=theSimulation_id).start_date
        self.timelineStart = self.first_tick_start

        # also the full model and the scenarios
        from merlin_api.pymerlin_adapter import \
            django2pymerlin, django_scenario2pymerlin  # @UnresolvedImport

        self.msim = django2pymerlin(djangoModels.Simulation.objects.get(
                                                        pk=theSimulation_id))
        # convert all scenarios
        # collect data and be simulation specific
        allScenarios = {s for s in djangoModels.Scenario.objects.filter(
                                                    sim__id=theSimulation_id)}

        # Scenario.name
        # baseline -> everything added in the services view
        # haircut -> everything added from haircut view
        # all others are (hopefully) project related

        self.mscen = [django_scenario2pymerlin(s, self.msim)
                      for s in allScenarios if s.name != "haircut"]
        # return msim, mscen

        # collect all projects, phases, scenarios from DB
        self.allProjects = []
        for p in sorted(djangoModels.Project.objects.all(),
                        key=lambda pp: min(ph.start_date
                                           for ph in pp.phases.all())):

            theProject = project(id=p.id, phases=[], name=p.name)

            for ph in sorted(p.phases.all(),
                             key=lambda pp: pp.start_date):
                # is it possible to have a project referring to
                # different simulations?
                if ph.scenario.sim.id == theSimulation_id:
                    theProject.phases.append(projectphase(
                                      scenario_id=ph.scenario.id,
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
