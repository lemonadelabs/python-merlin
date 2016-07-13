import builtins
import logging
import datetime
import statistics

from .utilities import *  # @UnusedWildImport
from .businessrules import financialDataFromProjects


def rank_by_similarity(origOffsets, successfulParameters):
    # in place operation!
    # rank according to different keys
    def rankingKey(x):
        return builtins.sum(abs(a-b)
                            for a, b in zip(x, origOffsets))

    successfulParameters.sort(key=rankingKey)


def get_paretoFront(resultSpace, mask=None):
    # collect all tuples of result space, which are at the Pareto Frontier
    # this algorithms should be faster by using the Simple Cull algorithm, see
    # http://www.es.ele.tue.nl/pareto/papers/date2007_paretocalculator_final.pdf
    # BUT be aware of using two comparisons & reflexive dominance operator!
    if not resultSpace:
        return []

    if mask is None:
        mask = [1.0]*len(next(iter(resultSpace)))

    paretoFront = []
    for r in resultSpace:
        if builtins.all((not isParetoDominant(rr, r, mask))
                        for rr in resultSpace if rr != r):
            paretoFront.append(r)

    return paretoFront


def isParetoDominant(aa, bb, mask):
    """
    returns True if aa Pareto dominant to bb
    mask provides comparison mode for each dimension:
    1: maximize, -1: minimize, 0 ignore
    """
    return bool(all((a*m >= b*m)
                    for a, b, m in zip(aa, bb, mask)
                    if m != 0) and
                any((a*m > b*m)
                    for a, b, m in zip(aa, bb, mask)
                    if m != 0))


def test_pareto_dominant():

    assert isParetoDominant((2,), (1,), (1,))
    assert not isParetoDominant([0]*10, [0]*10, [1]*10)
    assert isParetoDominant([1]*10, [0]*10, [1]*10)
    assert isParetoDominant([1]*10+[2], [1]*10+[0], [1]*11)


def offset_generator(max_sum=0, no_entries=0):
    """
    generates all possible lists of integers >=0, which are exactly no_entries
    long and their sum is maximal max_sum (inclusive)
    """
    assert no_entries >= 0
    if no_entries == 0:
        yield ()
    elif no_entries == 1:
        # this is a "duplication" of the clause before
        # but sort of faster, as it avoids one recursion
        for i in range(max_sum+1):
            yield (i,)
    else:
        for i in range(max_sum+1):
            for j in offset_generator(max_sum-i, no_entries-1):
                yield (i,)+j


class pareto:

    def __init__(self, myContext):
        # this is a read-only copy!
        # except from the mscen data structure, which is updated in place
        self.myContext = myContext

    def lengths_and_offsets(self, projectId):
        # go for a particular project
        theProject_id = projectId
        allProjects = self.myContext.allProjects
        timelineStart = self.myContext.timelineStart

        # determine the combined length of the phases,
        # the maximal sum of times in between
        thePhases = next(p.phases
                         for p in allProjects if p.id == theProject_id)[:]

        # this is an in-place sort, i.e. modifies the object,
        # so working on a copy
        thePhases.sort(key=lambda ph: ph.start_date)

        origOffsets = [monthsDifference(ph2.start_date,
                                        (timelineStart if ph1 is None
                                         else (ph1.end_date +
                                               datetime.timedelta(days=1))))
                       for ph1, ph2 in zip([None]+thePhases[:-1],
                                           thePhases)]

        # check for overlapping phases
        assert builtins.all(o >= 0 for o in origOffsets), \
            "phases are overlapping"

        phaseLengths = [monthsDifference(
                                ph.end_date+datetime.timedelta(days=1),
                                ph.start_date)
                        for ph in thePhases]

        assert builtins.all(l > 0 for l in phaseLengths)

        return phaseLengths, origOffsets

    def generate_parameter_list(self,
                                projectId,
                                phaseId=None,
                                alignToQuarters=True):
        """
        generate offset parameter list
        """
        # go for a particular project
        theProject_id = projectId
        allProjects = self.myContext.allProjects
        planViewLength = self.myContext.planViewLength

        phaseLengths, origOffsets = self.lengths_and_offsets(projectId)
        if alignToQuarters:
            assert all(l % 3 == 0 for l in phaseLengths), \
                "phase lengths are not full quarters"
            assert all(o % 3 == 0 for o in origOffsets), \
                "offsets are not aligned to full quarters"
            increments = 3  # increments only in quarters
        else:
            increments = 1  # increments in months

        if phaseId is None:
            # act on the project, so change all phases
            offsetMax = planViewLength - sum(phaseLengths)
            possibleOffsets = []
            for o in offset_generator(offsetMax//increments,
                                      len(phaseLengths)):
                possibleOffsets.append(tuple(oo*increments for oo in o))
        else:
            thePhases = next(p.phases
                             for p in allProjects if p.id == theProject_id)[:]

            # this is an in-place sort, i.e. modifies the object,
            # so working on a copy
            thePhases.sort(key=lambda ph: ph.start_date)

            # act on one phase, so change the offset before and after
            phaseIdx = next(i for i, ph in enumerate(thePhases)
                            if ph.id == phaseId)
            ooList = origOffsets + [planViewLength -
                                    sum(phaseLengths) - sum(origOffsets)]
            possibleOffsets = []
            for o in range(-ooList[phaseIdx],
                           ooList[phaseIdx+1]+increments,
                           increments):
                newOffset = ooList[:]  # copy
                newOffset[phaseIdx] += o
                newOffset[phaseIdx+1] -= o
                possibleOffsets.append(tuple(newOffset[:-1]))

        return origOffsets, possibleOffsets

    def modifyProjectFromOffsets(self,
                                 projectId,
                                 newOffsets=None,
                                 setActive=None):

        projects = self.myContext.allProjects

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
                                             if setActive is None
                                             else setActive))
            else:
                lastDate = self.myContext.timelineStart
                # the order of the new offsets is according to the time order
                # of the phases, so sort!
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
                        is_active=(ph.is_active
                                   if setActive is None
                                   else setActive)
                        ))

                newProjects.append(p._replace(phases=newPh))

        return newProjects

    def computeServiceHealth(self, projects, tele):
        # calculate number of warning/error messages from simulation, see
        # https://github.com/lemonadelabs/django-merlin/wiki/Merlin-Messages
        # messages from outputs are ignored, as they are counted somewhere
        # else

        t_messages = next((t for t in tele if "messages" in t),
                          {"messages": []})["messages"]

        # count messages which are process related and
        # output related separately, decide by sender
        other_msgs = sum(1 for t in t_messages
                         if t["sender"]["type"] != "Output" and t["type"] >= 2)

        return (other_msgs,)

    def computeOutputs(self, projects, tele):
        # compute the average monthly outputs normalized to its minimum
        # return a tuple of these, always in the same order (sorted by id)
        # count the number of months below minimum separately

        t_outputs = {t["id"]: t for t in tele
                     if "type" in t and t["type"] == "Output"}

        # returns a dictionary with id: (name, unit, min)
        outputs = self.myContext.collectOutputs()

        output_ids = [o_id for o_id, (name, unit, minimum)  # @UnusedVariables
                      in outputs.items()
                      if "$" not in unit]

        # they are ordered to have comparable results!
        output_ids.sort()

        # todo: find the minimum per month
        # there seems to be no telemetry about changing output minima

        outputSums = [statistics.mean(t_outputs[o_id]["data"]["value"]) /
                      outputs[o_id][-1]
                      for o_id in output_ids]
        minCounts1yr = [sum(1 for o in t_outputs[o_id]["data"]["value"][:12]
                        if o < outputs[o_id][-1])
                        for o_id in output_ids]
        minCounts4yr = [sum(1 for o in t_outputs[o_id]["data"]["value"][:12*4]
                        if o < outputs[o_id][-1])
                        for o_id in output_ids]
        minCounts = [sum(1 for o in t_outputs[o_id]["data"]["value"]
                         if o < outputs[o_id][-1])
                     for o_id in output_ids]

        return tuple(outputSums+minCounts+minCounts1yr+minCounts4yr)

    def computeFinancialIndicators(self, projects, tele):

        (totalInv, remainingInvFund, capCosts  # @UnusedVariable
         ) = financialDataFromProjects(self.myContext, projects)

        # look at funds at end of June and add up the negative ones
        underfundingSum = float(builtins.sum(
                                    (s for i, s in enumerate(remainingInvFund)
                                     if i % 12 == 11 and s < 0), 0.0))

        return (underfundingSum, sum(capCosts))

    def compute_choice(self, offs, theProject_id):
        """
        modify the projects and run the simulation
        after that extract results by running the computeResult functions
        """
        modProjects = self.modifyProjectFromOffsets(theProject_id,
                                                    newOffsets=offs)
        tele = self.myContext.runSimulation(modProjects)

        return sum((f(modProjects, tele) for f in self.resultProcessors),
                   ())

    def investmentFundsLimit(self, choiceMap):
        # filter this result space, rejecting business rule violating ones
        # investment fund never negative
        # assume the fuel tank is the first parameter!
        idx = self.resultDescription.index("underfundingSum")
        return {p: r for p, r
                in choiceMap.items()
                if r[idx] >= 0}

    def noUnderperforming1Year(self, choiceMap):
        indexes = [i for i, n in enumerate(self.resultDescription)
                   if n.startswith("insufficient1_")]
        return {p: r for p, r
                in choiceMap.items()
                if all(r[i] == 0 for i in indexes)}

    def noUnderperforming4Year(self, choiceMap):
        indexes = [i for i, n in enumerate(self.resultDescription)
                   if n.startswith("insufficient4_")]
        return {p: r for p, r
                in choiceMap.items()
                if all(r[i] == 0 for i in indexes)}

    def noUnderperforming10Year(self, choiceMap):
        indexes = [i for i, n in enumerate(self.resultDescription)
                   if n.startswith("insufficient_")]
        return {p: r for p, r
                in choiceMap.items()
                if all(r[i] == 0 for i in indexes)}

    def noError10Year(self, choiceMap):
        idx = self.resultDescription.index("nMessages_full")
        return {p: r for p, r
                in choiceMap.items()
                if r[idx] == 0}

    def optimize(self, projectId, phaseId):
        # generate the input parameter vector space

        # go for a particular project or phase
        origOffsets, possibleOffsets = self.generate_parameter_list(projectId,
                                                                    phaseId)
        # calculate input array size
        self.parameterDescription = ["offset %d" % i
                                     for i in range(len(origOffsets))]

        # setup list of function calls to
        # calculate result vectors for each input parameter vector
        self.resultProcessors = [self.computeFinancialIndicators,
                                 self.computeOutputs,
                                 self.computeServiceHealth]

        # define elements in result vector
        outputs = self.myContext.collectOutputs()
        outputNames = [outputs[k][0] for k in sorted(outputs.keys())
                       if "$" not in outputs[k][1]]

        self.resultDescription = (["underfundingSum", "capCostsSum"] +
                                  ["avg_"+n for n in outputNames] +
                                  ["insufficient_"+n for n in outputNames] +
                                  ["insufficient1_"+n for n in outputNames] +
                                  ["insufficient4_"+n for n in outputNames] +
                                  ["nMessages_full"])

        # default: all max!
        # define vector with 1 (maximize), 0 (ignore), -1 (minimize)
        self.resultMask = [1.0]*len(self.resultDescription)

        # minimize capitalization costs
        self.resultMask[self.resultDescription.index("capCostsSum")] = -1.0
        #  and messages
        self.resultMask[self.resultDescription.index("nMessages_full")] = -1.0
        # and the insufficient-messages
        for i, rd in enumerate(self.resultDescription):
            if rd.startswith("insufficient"):
                self.resultMask[i] = -1.0

        # now calculate result vectors for all parameters
        if hasattr(self.myContext, "ippClientFactory"):
            rrc = self.myContext.ippClientFactory()
            res = rrc[:].map_sync(self.compute_choice,
                                  possibleOffsets,
                                  (projectId,)*len(possibleOffsets))
            rrc.close()
            del rrc
            choiceMap = dict(zip(possibleOffsets, res))
        else:
            choiceMap = {o: self.compute_choice(o, projectId)
                         for o in possibleOffsets}

        # print out the choice map description
        logging.info("%s -> %s",
                     self.parameterDescription,
                     self.resultDescription)
        logging.info("initial parameter: %s",
                     origOffsets)
        logging.info("%d parameter sets calculated", len(choiceMap))

        # print out the choice map
        # for p, r in choiceMap.items():
        #    logging.debug("%s -> %s", p, r)

        # progressively filter results
        resultSpaceFilters = [self.investmentFundsLimit,
                              self.noUnderperforming1Year,
                              self.noUnderperforming4Year,
                              self.noUnderperforming10Year,
                              self.noError10Year]

        for theFilter in resultSpaceFilters:
            filteredResults = theFilter(choiceMap)

            if filteredResults:
                logging.info("applying filter %s - %d parameter sets left",
                             theFilter.__func__.__name__,
                             len(filteredResults))
                choiceMap = filteredResults
            else:
                break

        logging.info("after filtering: %d parameter sets", len(choiceMap))
        # print out the choice map
        # for p, r in choiceMap.items():
        #    logging.info("%s -> %s", p, r)

        resultSpace = set(choiceMap.values())

        # slim down the result space to pareto front
        # todo: eliminate dimensions in result space
        paretoFrontResults = get_paretoFront(resultSpace, self.resultMask)
        logging.info("%d results, %d in pareto front",
                     len(resultSpace), len(paretoFrontResults))

        # and find the front in parameter space
        paretoFrontParameters = [k for k, v in choiceMap.items()
                                 if v in paretoFrontResults]
        logging.info("%d parameter sets for pareto front",
                     len(paretoFrontParameters))

        # tuples do not compare with lists!
        if not paretoFrontParameters:
            # if there is none left!
            logging.info("using original parameters as none are left "
                         "to choose from")
            suggestedParameters = tuple(origOffsets)

        elif tuple(origOffsets) in paretoFrontParameters:
            # boring but honest choice
            suggestedParameters = origOffsets
            logging.info("selecting original parameters")

        else:
            # in place operation!
            rank_by_similarity(origOffsets, paretoFrontParameters)
            suggestedParameters = paretoFrontParameters[0]
            logging.info("selecting highest ranked parameters %s",
                         suggestedParameters)

        # convert back to phase starts and their ids
        optSetup = self.modifyProjectFromOffsets(projectId,
                                                 suggestedParameters)

        sortedPhases = sorted((ph for p in optSetup for ph in p.phases
                               if ph.is_active),
                              key=lambda x: x.start_date)

        logging.info("scenario ids of projects: %s",
                     [ph.scenario_id for ph in sortedPhases])

        thePhases = next(p for p in optSetup if p.id == projectId).phases
        return thePhases
