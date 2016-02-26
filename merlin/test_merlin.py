import pytest
from merlin import merlin
from merlin import actions
from merlin import processes

# module fixtures


@pytest.fixture()
def sim():
    """ Returns a simulation object """
    return merlin.Simulation(
        ruleset=None,
        config=[],
        outputs=set(),
        name='test_sim')

# basic action functionality tests
# core ruleset tests are out of scope


def test_add_attribute(sim):
    sim.add_attributes(['attr'])
    assert sim.is_attribute('attr')
