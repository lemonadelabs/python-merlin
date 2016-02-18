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



class SimObject:
    """
    Basic properties of all sim objects.
    """
    def __init__(self, name=''):
        self.id = uuid.uuid4()
        self.name = name or str(self.id)


class Simulation(SimObject):
    """
    A representation of a network with its assocated entities, ruleset, senarios and outputs.
    """

    def __init__(self, ruleset=None, config=[], outputs=[], name=''):
        super(Simulation, self).__init__(name)
        self.entities = []
        self.ruleset = ruleset
        self.initial_state = config
        self.senarios = []
        self.source_entities = []
        self.outputs = outputs
        self.unit_types = []
        self.attributes = []
        self.current_time_interval
        self.current_time
        init_state()

    def get_entity_by_name(name):
        for e in self.entities:
            if e.name == name:
                return e
        return None

    def init_state():
        for action in self.initial_state:
            action.execute(self)

    def run(start, end, stepsize, senario=None):
        pass

class Output(SimObject):
    """
    A network flow sink.
    """
    def __init__(self, name=''):
        super(Output, self).__init__(name)
        self.inputs = []
        self.type = None


class Entity(SimObject):
    """
    A node in the network.

    Commonly used to represent a business capability, a resource or an asset. Entities can contain processes that modify data arriving at the entity's input connectors or generate new data that gets written to the entity's output connectors.
    """

    def __init__(self, simulation, name='', attributes=[]):
        super(Entity, self).__init__(name)
        self.sim = simulation
        self.attributes = attributes
        self.inputs = []
        self.outputs = []
        self.parent = None
        self.children = []
        self.processes = {}
        self.current_time = None
        self.processed = False

    def add_process(self, proc):
        # first check to see if the proc has already been added.
        if proc.id in [p.id for p in self.processes.values()]:
            return

        if self.processes.has_key(proc.priority):
            self.processes[proc.priority].append(proc)
        else:
            self.processes[proc.priority] = list(proc)


    def remove_process(self, proc):
        if proc.id not in [p.id for p in self.processes.values()]:
            return
        self.processes[proc.priority].remove(proc)

    def get_output_by_type(unit_type):
        for o in self.outputs:
            if o.type == unit_type:
                return o
        return None

    def get_input_by_type(unit_type):
        for o in self.inputs:
            if o.type == unit_type:
                return o
        return None


    def tick(self, time):
        if time < self.current_time:
            return

        if time > self.current_time:
            self.processed = False
            self.current_time = time

        if time == self.current_time and not self.processed:
            # need to check if we have all inputs updated before processing
            up_to_date = True
            for i in self.inputs:
                up_to_date = up_to_date and (i.time == self.current_time)

            if up_to_date:
                _process()

    def _process(self):
        self.processed = True
        for i in self.processes.keys().sort():
            for proc in self.processes[i]:
                proc.compute(self.current_time)

class Process(SimObject):
    """
    A generator, processor and/or consumer of units

    Makes up the core of the graph processing and is considered abstract. Must be subclassed to create specific processes. A process is the most granualr part of a :class:`merlin.Simulation`
    """

    def __init__(self, name=''):
        super(Process, self).__init__(name)
        self.parent = None
        self.requires = []
        self.priority = 0

    def compute(self, tick):
        pass

class Connector(SimObject):
    """
    An input or output connection to 1 or more endpoints. Can be written to or read from by processes.
    """

    def __init__(
        self,
        unit_type,
        parent,
        endpoints,
        name='',
        copy_value=False
        additive_output=False):

        super(Connector, self).__init__(name)
        self.type = unit_type
        self.parent = parent
        self.value = 0.0
        self.endpoints = endpoints
        self.time = None
        self.copy = copy_value
        self.additive = additive_output

    def write(self, value):
        self.time = self.parent.current_time
        if self.endpoints:

            dist_value = value if self.copy else value / float(len(self.endpoints))

            for ep in self.endpoints:
                ep.value = ep.value + dist_value if self.additive else dist_value
                ep.time = self.time
                ep.parent.tick(self.time)

    def read(self):
        return self.value


class Action(SimObject):
    """
    Represents a creation or modification act for a :class:`merlin.Simulation`

    Action is considered and abstract class and should be subclassed to create a specific Action.
    """

    def __init__(self):
        super(Action, self).__init__(name='')

    def execute(simulation):
        pass

class Event(SimObject):
    """
    An event is a pairing of a time and an action.

    A collection of events make up a :class:`merlin.Simulation` senario.
    """

    def __init__(self, action, time, name=''):
        super(Event, self).__init__(name)
        self.action = action
        self.time = time

class Ruleset:
    """
    A validation class that checks the integrity of a particular :class:`merlin.Simulation`

    This is an abstract class that must be overridden by a specific ruleset for your simulation. In other words, each simulation will have it's own sublcass of Ruleset.

    In a future version of merlin, it would be desirable to have the rulset be desribed by a configuration file that could be generated from another product or application or written by hand.
    """

    def validate(self, action):
        pass

    def core_validate(self, action):
        validate(action)

class MerlinException(Exception):
    """
    Base exception class for Merlin
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
