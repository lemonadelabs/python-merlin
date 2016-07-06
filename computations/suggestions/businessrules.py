'''
Created on 6/07/2016

@author: achim
'''

from numpy import zeros
import datetime
from .utilities import *  # @UnusedWildImport


def financialDataFromProjects(context, theProjects):
    """
    calculate the financial data as far as possible from the project data
    total investment, ongoing capitalization costs, "fuel tank"
    """

    timelineLength = context.timelineLength
    timelineStart = context.timelineStart

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
