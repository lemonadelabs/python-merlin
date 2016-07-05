import builtins

from .utilities import *


def rank_by_similarity(origOffsets, successfulParameters):

    # rank according to different keys
    def rankingKey(x):
        return builtins.sum(abs(a-b)
                            for a, b in zip(x, origOffsets))

    successfulParameters.sort(key=rankingKey)


def get_paretoFront(resultSpace):

    # collect all tuples of result space, which are at the Pareto Frontier
    paretoFront = []
    for r in resultSpace:
        if builtins.all((not isParetoDominant(rr, r))
                        for rr in resultSpace if rr != r):
            paretoFront.append(r)

#     successfulParameters = [k for k, v in changedChoiceMap.items()
#                             if v in paretoFront]
    return paretoFront


def isParetoDominant(aa, bb):
    """
    returns True if aa Pareto dominant to bb
    """
    from builtins import all, any
    return bool(all((a >= b) for a, b in zip(aa, bb)) and
                any((a > b) for a, b in zip(aa, bb)))


def offset_generator(max_sum=0, no_entries=0):
    """
    generates lists of integers >=0, which are exactly no_entries long and
    their sum is maximal max_sum (inclusive)
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

    def generate_parameter_list(self, projectId, phaseId=None):
        """
        generate offset parameter list

        todo: collect outputs somewhere else!
        """
        # go for a particular project
        theProject_id = projectId
        allProjects = self.myContext.allProjects
        timelineStart = self.myContext.timelineStart
        timelineLength = self.myContext.timelineLength

        # determine the combined length of the phases,
        # the maximal sum of times inbetween
        thePhases = next(p.phases
                         for p in allProjects if p.id == theProject_id)
        thePhases.sort(key=lambda ph: ph.start_date)

        origOffsets = [monthsDifference(ph2.start_date,
                                        (timelineStart if ph1 is None
                                         else (ph1.end_date +
                                               datetime.timedelta(days=1))))
                       for ph1, ph2 in zip([None]+thePhases[:-1], thePhases)]

        # check for overlapping phases
        assert builtins.all(o >= 0 for o in origOffsets)

        phaseLengths = [monthsDifference(ph.end_date+datetime.timedelta(days=1),
                                         ph.start_date)
                        for ph in thePhases]

        if phaseId is None:
            # act on the project, so change all phases
            offsetMax = timelineLength - sum(phaseLengths)
            possibleOffsets = list(offset_generator(offsetMax,
                                                    len(phaseLengths)))
        else:
            # act on one phase, so change the offset before and after
            phaseIdx = next(i for i, ph in enumerate(thePhases)
                            if ph.id == phaseId)
            ooList = origOffsets + [timelineLength -
                                    sum(phaseLengths) - sum(origOffsets)]
            possibleOffsets = []
            for o in range(-ooList[phaseIdx], ooList[phaseIdx+1]+1):
                newOffset = ooList[:]  # copy
                newOffset[phaseIdx] += o
                newOffset[phaseIdx+1] -= o
                possibleOffsets.append(tuple(newOffset[:-1]))

        return origOffsets, possibleOffsets

    def compute_choice(self, offs, theProject_id):
        """
        todo: get info on what to calculate and how from context
        """

        msim = self.myContext.msim
        mscen = self.myContext.mscen
        allProjects = self.myContext.allProjects
        # have functions nested for serialization
        timelineLength = self.myContext.timelineLength

        modProjects = modifyProjectFromOffsets(allProjects,
                                               theProject_id,
                                               newOffsets=offs)

        totalInv, remainingInvFund, capCosts = financialDataFromProjects(
                                                                modProjects)

        underfundingSum = float(builtins.sum(
                                    (s for i, s in enumerate(remainingInvFund)
                                     if i % 12 == 11 and s < 0), 0.0))

        tele = runSimulation(modProjects, msim, mscen, timelineLength)
        t_outputs = {t["id"]: t for t in tele
                     if "type" in t and t["type"] == "Output"}
        t_messages = next((t for t in tele if "messages" in t),
                          {"messages": []})["messages"]

        output_id = next(o.id for o in msim.outputs
                         if o.name == "Applications Processed")

        outputSum = sum(t_outputs[output_id]["data"]["value"])

        return (underfundingSum, outputSum, -len(t_messages), -sum(capCosts))

    def optimize(self, projectId, phaseId):
        # go for a particular project
        origOffsets, possibleOffsets = self.generate_parameter_list(projectId,
                                                                    phaseId)

        if False:
            from ipyparallel import Client  # @UnresolvedImport

            def compute_something(param):
                import algorithms.pareto
                from importlib import reload
                reload(algorithms.pareto)
                from algorithms.pareto import pareto
                con, off, theProject_id = param
                return pareto(con).compute_choice(off, theProject_id)

            rrc = Client()
            res = rrc[:].map_sync(compute_something,
                                  ((self.myContext, o, projectId)
                                   for o in possibleOffsets)
                                  )
            choiceMap = dict(zip(possibleOffsets, res))

        else:
            choiceMap = {o: self.compute_choice(o, projectId)
                         for o in possibleOffsets}

        # filter this result space, rejecting business rule violating ones
        # investment fund never negative
        resultSpace = set(v for v in choiceMap.values() if v[0] >= 0)
        if len(resultSpace) == 0:
            print("dropping the business rules")
            changedChoiceMap = {k: (v[1], v[2], v[3])
                                for k, v in choiceMap.items()}
            resultSpace = set(changedChoiceMap.values())
        else:
            changedChoiceMap = choiceMap

        paretoFront = get_paretoFront(resultSpace)

        successfulParameters = [k for k, v in changedChoiceMap.items()
                                if v in paretoFront]

        # in place operation!
        rank_by_similarity(origOffsets, successfulParameters)

        # convert back to phase ids.
        optSetup = modifyProjectFromOffsets(self.myContext.allProjects,
                                            projectId,
                                            successfulParameters[0])

        thePhases = next(p for p in optSetup if p.id == projectId).phases
        return {ph.id: ph.start_date for ph in thePhases}
