"""
.. module:: merlin
    :synopsis: This is the main module containing the core objects in
    the system
    as well as some bootstrap and helper functions.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""

import uuid
import sys
from enum import Enum

# Core classes


class Application:
    """
    Represents a set of simulations with their associated outputs.

    It is really a convienience grouping and typically a single client would
    have one :class:`merlin.Application` instance.
    """

    def __init__(self, app_name=None):
        self.simulations = set()
        self.id = uuid.uuid4()
        self.name = app_name or str(self.id)

    def create_simulation(self, config, ruleset, outputs, name=None):
        """
        Create a new simulation object and populate it with entities, a ruleset
         and outputs.

        :param config: A list of Actions to create the intial state of the
        :class:`Simulation`.
        :type config: [Action]
        :param ruleset: A subclass of the :class:`Ruleset` object that contains
         the rules for the simulation.
        :type ruleset: Ruleset
        :param outputs: A list of outputs for the simulation.
        :type outputs: [Output]
        :return: A Simulation object id
        :rtype: int
        """
        sim = Simulation(ruleset, config, outputs, name)
        self.simulations.add(sim)


class SimObject:
    """
    Basic properties of all sim objects.
    """
    def __init__(self, name=''):
        self.id = uuid.uuid4()
        self.name = name or str(self.id)


class Simulation(SimObject):
    """
    A representation of a network with its assocated entities, ruleset,
     senarios and outputs.
    """

    def __init__(self, ruleset=None, config=[], outputs=set(), name=''):
        super(Simulation, self).__init__(name)
        self._unit_types = set()
        self._attributes = set()
        self._entities = set()
        self.ruleset = ruleset
        self.initial_state = config
        self.senarios = set()
        self.source_entities = set()
        self.outputs = outputs
        self.current_time_interval = None
        self.current_time = None
        self.init_state()

    def add_attributes(self, ats):
        for a in ats:
            if a not in self._attributes:
                self._attributes.add(a)

    def add_unit_types(self, uts):
        for ut in uts:
            if ut not in self._attributes:
                self._unit_types.add(ut)

    def is_attribute(self, a):
        return a in self._attributes

    def is_unit_type(self, ut):
        return ut in self._unit_types

    def get_entities(self):
        return self._entities

    def add_entity(self, e):
        if e not in self._entities:
            self._entities.add(e)
            e.parent = self
            e.sim = self

    def remove_entity(self, e):
        if e in self._entities:
            self._entities.remove(e)

    def get_entity_by_name(self, name):
        for e in self._entities:
            if e.name == name:
                return e
        return None

    def get_entity_by_id(self, id):
        for e in self._entities:
            if e.id == id:
                return e
        return None

    def init_state(self):
        for action in self.initial_state:
            action.execute(self)

    def run(self, start, end, stepsize, senario=None):
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

    Commonly used to represent a business capability, a resource or an asset.
     Entities can contain processes that modify data arriving at the entity's
      input connectors or generate new data that gets written to the entity's
       output connectors.
    """

    def __init__(self, simulation=None, name='', attributes=set()):
        super(Entity, self).__init__(name)
        self._processes = dict()
        self.sim = simulation
        self.attributes = attributes
        self.inputs = set()
        self.outputs = set()
        self.parent = None
        self._children = set()
        self.current_time = None
        self.processed = False

    def add_child(self, entity):
        if entity not in self._children:
            self._children.add(entity)
            entity.parent = self

    def remove_child(self, entity_id):
        child_to_remove = None
        for c in self.children():
            if c.id == entity_id:
                child_to_remove = c
        if child_to_remove:
            child_to_remove.parent = None
            self._children.remove(child_to_remove)

    def get_children(self):
        return self._children

    def get_child_by_id(self, entity_id):
        for c in self.get_children():
            if c.id == entity_id:
                return c
        return None

    def get_child_by_name(self, entity_name):
        for c in self.get_children():
            if c.name == entity_name:
                return c
        return None

    def add_input(self, input_con):
        if input_con not in self.inputs:
            input_con.parent = self
            self.inputs.add(input_con)

    def add_output(self, output_con):
        if output_con not in self.outputs:
            output_con.parent = self
            self.outputs.add(output_con)

    def add_process(self, proc):
        # first check to see if the proc has already been added.
        if proc.id in [p.id for p in self._processes.values()]:
            return

        if proc.priority in self._processes.keys():
            self._processes[proc.priority].add(proc)
        else:
            self._processes[proc.priority] = set({proc})
        proc.parent = self

    def remove_process(self, proc_id):
        proc = self.get_process_by_id(proc_id)
        if proc:
            proc.parent = None
            self._processes[proc.priority].remove(proc)

    def get_process_by_name(self, proc_name):
        procs = self._processes.values()
        for ps in procs:
            for p in ps:
                if p.name == proc_name:
                    return p
        return None

    def get_process_by_id(self, proc_id):
        procs = self._processes.values()
        for ps in procs:
            for p in ps:
                if p.id == proc_id:
                    return p
        return None

    def get_connector_by_id(self, id):
        connectors = self.inputs.union(self.outputs)
        print(connectors)
        for c in connectors:
            if c.id == id:
                return c
        return None

    def get_output_by_type(self, unit_type):
        result = set()
        for o in self.outputs:
            if o.type == unit_type:
                result.add(o)
        return result

    def get_input_by_type(self, unit_type):
        result = set()
        for o in self.inputs:
            if o.type == unit_type:
                result.add(o)
        return result

    def tick(self, time):
        if self.current_time and time < self.current_time:
            return

        if (self.current_time is None) or (time > self.current_time):
            self.processed = False
            self.current_time = time

        if time == self.current_time and not self.processed:
            # need to check if we have all inputs updated before processing
            up_to_date = True
            for i in self.inputs:
                up_to_date = up_to_date and (i.time == self.current_time)

            if up_to_date:
                self._process()

    def _process(self):
        self.processed = True
        if self._processes.keys():
            for i in list(self._processes.keys()).sort():
                for proc in self._processes[i]:
                    proc.compute(self.current_time)


class Process(SimObject):
    """
    A generator, processor and/or consumer of units

    Makes up the core of the graph processing and is considered abstract.
    Must be subclassed to create specific processes.
    Things to override in the subclass:
    * inputs
    * outputs
    * process_properties
    * compute
    """

    def __init__(self, name=''):
        super(Process, self).__init__(name)
        self.parent = None
        self.priority = 0
        self.inputs = dict()
        self.outputs = dict()
        self.process_properties = dict()

    def get_prop(name):
        if name in self.process_properties:
            return self.process_properties[name].value

    def get_properties():
        return self.process_properties.values()

    def compute(self, tick):
        print("This process does absolutely nothing")


class ProcessInput(SimObject):

    def __init__(self, name, unit_type, connector=None, requirement=None):
        super(ProcessInput, self).__init__(name)
        self.type = unit_type
        self.requirement = requirement
        self.connector = connector

    def get_requirement():
        return self.requirement()

    def read():
        pass


class ProcessOutput(SimObject):

    def __init__(self, name, unit_type, connector=None):
        super(ProcessOutput, self).__init__(name)
        self.type = unit_type
        self.connector = connector

    def write():
        pass


class ProcessProperty(SimObject):

    class PropertyType(Enum):
        bool_type = 1
        float_type = 2
        int_type = 3

    def __init__(
            self,
            name,
            property_type=PropertyType.float_type,
            default=0.0,
            parent=None):
        super(ProcessProperty, self).__init__(name)
        self.type = property_type
        self.max_val = 0.0
        self.min_val = 0.0
        self.default = default
        self.parent = parent
        self._value = self.default

    def set_value(value):
        value = value if value >= self.min_val else self.min_val
        value = value if value <= self.max_val else self.max_val
        self._value = value

    def get_value():
        return self._value


class Connector(SimObject):
    """
    abstract base class for input and output connectors.
    """

    def __init__(
            self,
            unit_type,
            parent,
            name=''):

        super(Connector, self).__init__(name)
        self.type = unit_type
        self.parent = parent
        self.time = None


class OutputConnector(Connector):
    """
    Represents an outgoing entity connection.
    """

    def __init__(
            self,
            unit_type,
            parent,
            name='',
            copy_write=False,
            endpoints=None):

        super(OutputConnector, self).__init__(unit_type, parent, name)
        self.copy_write = copy_write
        self._endpoints = endpoints or set()

    class Endpoint():
        def __init__(self, connector=None, bias=0.0):
            self.connector = connector
            self.bias = bias

    def write(self, value):
        self.time = self.parent.current_time
        if self._endpoints:
            for ep in self._endpoints:
                dist_value = (
                    value if self.copy_write else value /
                    ep.bias)
                ep.connector.write(dist_value)
                ep.connector.time = self.time
                ep.connector.parent.tick(self.time)

    def _get_endpoint(self, input_connector):
        result = None
        for ep in self._endpoints:
            if ep.connector == input_connector:
                result = ep
        return result

    def get_endpoints(self):
        return [(e.connector, e.bias) for e in self._endpoints]

    def _ballance_bias(self):
        val = 1.0 / float(len(self._endpoints))
        for ep in self._endpoints:
            ep.bias = val

    def add_input(self, input_connector, bias=0.0):
        if not self._get_endpoint(input_connector):
            ep = self.Endpoint(input_connector, bias)
            self._endpoints.add(ep)
            self._ballance_bias()

    def remove_input(self, input_connector):
        ep = self._get_endpoint(input_connector)
        if ep:
            self._endpoints.remove(ep)
            if self._endpoints:
                self._ballance_bias()
            else:
                self.parent.outputs.remove(self)

    def set_endpoint_bias(self, input_connector, bias):
        ep = self._get_endpoint(input_connector)
        if ep:
            old_bias = ep.bias
            ep.bias = bias
            bias_diff = old_bias - bias
            # redistribute difference amongst other inputs
            for e in self._endpoints:
                if e != ep:
                    e.bias = e.bias + bias_diff

    def set_endpoint_biases(self, biases):
        """
        biases are in the form [(connector, bias)...n]
        where n is len(self._endpoints)
        """
        if len(biases) != len(self._endpoints):
            raise MerlinException(
                "Biases arity must match number of endpoints")
        else:
            for b in biases:
                ep = self._get_endpoint(b[0])
                if ep:
                    ep.bias = b[1]
                else:
                    raise SimReferenceNotFoundException(
                        "endpoint does not exist")


class InputConnector(Connector):
    """
    Represents an incoming entity connection.
    """

    def __init__(
            self,
            unit_type,
            parent,
            name='',
            source=None,
            additive_write=False):

        super(InputConnector, self).__init__(unit_type, parent, name)
        self.source = source
        self.additive_write = additive_write
        self.value = 0.0

    def write(self, value):
        self.value = self.value + value if self.additive_write else value


class Action(SimObject):
    """
    Represents a creation or modification act for a :class:`merlin.Simulation`

    Action is considered and abstract class and should be subclassed to create
    a specific Action.
    """

    def __init__(self):
        super(Action, self).__init__(name='')

    def execute(self, simulation):
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
    A validation class that checks the integrity of a particular
     :class:`merlin.Simulation`

    This is an abstract class that must be overridden by a specific ruleset for
     your simulation. In other words, each simulation will have it's own
      sublcass of Ruleset.

    In a future version of merlin, it would be desirable to have the rulset be
     desribed by a configuration file that could be generated from another
      product or application or written by hand.
    """

    def validate(self, action):
        return False

    def core_validate(self, action):
        self.validate(action)


class MerlinException(Exception):
    """
    Base exception class for Merlin
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SimNameNotFoundException(MerlinException):

    def __init__(self, value):
        super(SimReferenceNotFoundException, self).__init__(value)


class EntityNotFoundException(MerlinException):

    def __init__(self, value):
        super(EntityNotFoundException, self).__init__(value)
