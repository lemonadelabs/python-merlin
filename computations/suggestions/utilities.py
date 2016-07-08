'''
Created on 5/07/2016

@author: achim
'''
from collections import namedtuple
import datetime

__all__ = ["project", "projectphase",
           "monthsDifference", "monthsIncrement"]


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


def test_monthsUtils():
    import pytest
    testDate = datetime.date(2014, 7, 1)
    assert monthsIncrement(testDate, 0) == testDate

    with pytest.raises(AssertionError):
        monthsDifference(testDate, testDate.replace(day=2))

    assert -12 == monthsDifference(testDate,
                                   testDate.replace(year=testDate.year+1))
