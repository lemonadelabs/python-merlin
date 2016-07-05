'''
Created on 5/07/2016

@author: achim
'''

from collections import namedtuple
import datetime
from numpy import zeros

# this needs to come from the context!
first_tick_start = datetime.date(2016, 7, 1)
timelineLength = 12*4
timelineStart = first_tick_start

# have own data structure for projects/phases
# boils down to: project:
# project id, phases
# ignored: attractiveness, achievability and is_ringfenced,
# priority, type, dependencies
project = namedtuple("project", ["id", "phases", "name"])

# for the phase:
# start date, end date, is_active
# phase id, scenario id, service cost and investment cost, capitalization
projectphase = namedtuple("projectphase", ["id", "name",
                                           "scenario_id", "is_active",
                                           "start_date", "end_date",
                                           "service_cost", "investment_cost",
                                           "capitalization_ratio"])


def monthsDifference(d1, d2):
    """
    helper for (mathematical) difference between two months
    both dates need to be the month's start
    """
    assert (d1.day == 1 and d2.day == 1)
    return (d1.year-d2.year)*12+d1.month-d2.month


def monthsIncrement(d, i):
    """
    safe to use with day==1, but not with day==31
    """
    return d.replace(year=d.year+(d.month+i-1)//12,
                     month=(d.month+i-1) % 12+1)


def updateScenarios(mscen, projects):
    # update the event timing for each project phase
    # the scenarios are updated in place
    for p in projects:
        for ph in p.phases:
            scen = next(s for s in mscen if s.id == ph.scenario_id)
            # adjust times of phase:
            length = monthsDifference(ph.end_date+datetime.timedelta(days=1),
                                      ph.start_date)
            scen.start_offset = monthsDifference(ph.start_date,
                                                 first_tick_start) + 1
            # set start, set end
            evStartTick = min(ev.time for ev in scen.events)
            for ev in scen.events:
                # the minimum should be start
                if ev.time == evStartTick:
                    ev.time = 0
                    # the other one an end event, which happens at the begin of
                    # the first month after start.
                else:
                    ev.time = length


def runSimulation(theProjects, pySimulation, pyScenarios, simTime):
    updateScenarios(pyScenarios, theProjects)
    # put in the scenarios from baseline and then the projects
    baselineScenIds = [b.id for b in pyScenarios if b.name == "baseline"]
    # also order projects by time (scenario.start_offset)
    phaseScenarioIds = [ph.id
                        for p in sorted(theProjects,
                                        key=lambda pp: min(pph.start_date
                                                           for pph in pp.phases
                                                           ))
                        for ph in p.phases if ph.is_active]
    # put baseline scenarios in front
    activeScenarios = ([m for m in pyScenarios if m.id in baselineScenIds] +
                       [m for m in pyScenarios if m.id in phaseScenarioIds])
    pySimulation.run(scenarios=activeScenarios, end=simTime)
    tele = pySimulation.get_sim_telemetry()
    return tele


def modifyProjectFromOffsets(projects,
                             projectId,
                             newOffsets=None,
                             setActive=None):

    if newOffsets is None and setActive is None:
        # this is a no-op
        return projects

    newProjects = []
    for p in projects:
        if p.id != projectId:
            newProjects.append(p)
            continue

        newPh = []
        if newOffsets is None:
            # don't do anything with the phase dates
            for ph in p.phases:
                newPh.append(ph._replace(is_active=ph.is_active
                                         if setActive is None else setActive))
        else:
            lastDate = timelineStart
            for ph, o in zip(sorted(p.phases, key=lambda x: x.start_date),
                             newOffsets):
                new_start = monthsIncrement(lastDate, o)
                lastDate = monthsIncrement(new_start,
                                           monthsDifference(
                                                ph.end_date +
                                                datetime.timedelta(days=1),
                                                ph.start_date))

                newPh.append(ph._replace(
                    start_date=new_start,
                    end_date=lastDate-datetime.timedelta(days=1),
                    is_active=ph.is_active if setActive is None else setActive
                    ))

            newProjects.append(p._replace(phases=newPh))

        return newProjects


# calculate the financial data as far as possible from the project data structure
# total investment, ongoing capitalization costs, "fuel tank"
def financialDataFromProjects(theProjects):

    totalInvestment = zeros(timelineLength)
    for p in theProjects:
        for ph in p.phases:
            start_date = ph.start_date
            end_date = ph.end_date+datetime.timedelta(days=1)
            # get the length of the phase in months
            length = monthsDifference(end_date, start_date)
            startOffset = monthsDifference(start_date, timelineStart)
            totalInvestment[max(0, startOffset):
                            min(startOffset+length, timelineLength)
                            ] += (ph.investment_cost+ph.service_cost)/length

    # the fuel tank or capital investment available
    capitalInvestments = zeros(timelineLength)
    for p in theProjects:
        for ph in p.phases:
            start_date = ph.start_date
            end_date = ph.end_date+datetime.timedelta(days=1)
            # get the length of the phase in months
            length = monthsDifference(end_date, start_date)
            startOffset = monthsDifference(start_date, timelineStart)
            capitalInvestments[max(0, startOffset):
                               min(startOffset+length, timelineLength)
                               ] += ph.investment_cost/length

    # this is the closing balance for each month
    remainingCapitalInvestmentFund = zeros(timelineLength)
    # assume timeline starts at financial year
    annualCapitalFund = 50e6
    for o in range(timelineLength):
        if o % 12 == 0:
            # by now: start fresh every financial year
            carryOver = annualCapitalFund
        else:
            carryOver = remainingCapitalInvestmentFund[o-1]
        remainingCapitalInvestmentFund[o] = carryOver-capitalInvestments[o]

    baseCapitalisationCosts = 0
    capitalisationCosts = zeros(timelineLength)
    capitalisationCosts += baseCapitalisationCosts
    for p in theProjects:
        for ph in p.phases:
            end_date = ph.end_date+datetime.timedelta(days=1)
            # the capitalisation costs start after the project phase
            offset = monthsDifference(end_date, timelineStart)
            # a value between 0.0 and 1.0
            capitalisationRatio = ph.capitalization_ratio
            # lifetime in months, right now no end (within this view)
            lifetime = timelineLength
            # this is done monthly
            capitalisationCosts[max(0, offset):
                                min(timelineLength, offset+lifetime)
                                ] += (ph.investment_cost+ph.service_cost
                                      )*0.25*capitalisationRatio/12.0

    return totalInvestment, remainingCapitalInvestmentFund, capitalisationCosts
