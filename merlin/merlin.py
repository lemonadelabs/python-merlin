"""
.. module:: merlin
    :synopsis: This is the main module containing the core objects in the system
    as well as some bootstrap and helper functions.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""

import uuid

# Core classes

class Application:
    """
    Represents a set of simulations with their associated outputs.

    It is really a convienience grouping and typically a single client would have one :class:`merlin.Application` instance.
    """

    def __init__(self, app_name=None):
        self.simulations = []
        self.id = uuid.uuid4()
        self.name = app_name or str(self.id)

    def create_simulation(self, config, ruleset, outputs, name=None):
        """
        Create a new simulation object and populate it with entities, a ruleset and outputs.

        :param config: A list of Actions to create the intial state of the :class:`Simulation`.
        :type config: [Action]
        :param ruleset: A subclass of the :class:`Ruleset` object that contains the rules for the simulation.
        :type ruleset: Ruleset
        :param outputs: A list of outputs for the simulation.
        :type outputs: [Output]
        :return: A Simulation object id
        :rtype: int
        """

        sim = Simulation(ruleset, config, outputs, name)
        self.simulations.append(sim)



class Simulation:
    """
    A representation of a network with its assocated entities, ruleset, senarios and outputs.
    """

    def __init__(self, ruleset=None, config=[], outputs=[], name=None):
        self.entities = []
        self.id = uuid.uuid4()
        self.name = name or str(self.id)
        self.ruleset = ruleset
        self.initial_state = config
        self.senarios = []
        self.source_entities = []
        self.outputs = outputs
        init_state()

    def init_state():
        for action in self.initial_state:
            action.execute(self)

    def run(start, end, stepsize):
        pass

class Output:
    """
    A network flow sink.
    """

class Entity:
    """
    A node in the network.

    Commonly used to represent a business capability, a resource or an asset. Entities can contain processes that modify data arriving at the entity's input connectors or generate new data that gets written to the entity's output connectors.
    """



class Process:
    """
    A generator, processor and/or consumer of units

    Makes up the core of the graph processing and is considered abstract. Must be subclassed to create specific processes. A process is the most granualr part of a :class:`merlin.Simulation`
    """

    def __init__(self):
        pass

class Connector:
    """
    An input or output connection to 1 or more endpoints. Can be written to or read from by processes.
    """

class Action:
    """
    Represents a creation or modification act for a :class:`merlin.Simulation`

    Action is considered and abstract class and should be subclassed to create a specific Action.
    """
    def execute(simulation):
        pass

class Event:
    """
    An event is a pairing of a time and an action.

    A collection of events make up a :class:`merlin.Simulation` senario.
    """

class Ruleset:
    """
    A validation class that checks the integrity of a particular :class:`merlin.Simulation`

    This is an abstract class that must be overridden by a specific ruleset for your simulation. In other words, each simulation will have it's own sublcass of Ruleset.

    In a future version of merlin, it would be desirable to have the rulset be desribed by a configuration file that could be generated from another product or application or written by hand.
    """
