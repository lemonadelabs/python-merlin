"""
.. module:: merlin
    :synopsis: This is the main module containing the core objects in
    the system
    as well as some bootstrap and helper functions.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""

import uuid
import logging
from datetime import datetime
from enum import Enum

# Global module settings
logging_level = logging.INFO
log_to_file = ''
logging.basicConfig(
    filename=log_to_file,
    level=logging_level,
    format='%(asctime)s: [%(levelname)s] %(message)s')


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

    def __init__(self, ruleset=None, config=None, outputs=None, name=''):
        super(Simulation, self).__init__(name)
        self._unit_types = set()
        self._attributes = set()
        self._entities = set()
        self.ruleset = ruleset
        self.initial_state = config or []
        self.senarios = set()
        self.source_entities = set()
        self.outputs = outputs or set()
        self.num_steps = 1
        self.current_step = 1
        self.run_errors = list()
        self.verbose = True

    def _run_senario_events(self):
        # TODO: Implement senario events
        pass

    def connect_entities(
            self,
            from_entity,
            to_entity,
            unit_type,
            input_additive_write=False,
            output_copy_write=False):

        o_con = from_entity.get_output_by_type(unit_type)
        i_con = to_entity.get_input_by_type(unit_type)

        if not o_con:
            o_con = OutputConnector(
                unit_type,
                from_entity,
                name='{0}_output'.format(unit_type),
                copy_write=output_copy_write)

        if not i_con:
            i_con = InputConnector(
                unit_type,
                to_entity,
                name='{0}_input'.format(unit_type),
                additive_write=input_additive_write)

        i_con.source = o_con
        o_con.add_input(i_con)
        from_entity.add_output(o_con)
        to_entity.add_input(i_con)

    def connect_output(
            self,
            entity,
            output,
            input_additive_write=False,
            output_copy_write=False):

        if output not in self.outputs:
            return

        o_con = entity.get_input_by_type(output.type)

        if not o_con:
            o_con = OutputConnector(
                output.type,
                entity,
                name='{0}_output'.format(output.type),
                copy_write=output_copy_write)

        i_con = InputConnector(
            output.type,
            output,
            name='{0}_input_from_{1}'.format(output.type, entity.id),
            additive_write=input_additive_write)

        i_con.source = o_con
        o_con.add_input(i_con)
        entity.add_output(o_con)
        if i_con not in output.inputs:
            output.inputs.add(i_con)

    def set_time_span(self, num_months):
        self.num_steps = num_months

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

    def set_source_entities(self, entities):
        for e in entities:
            if e in self._entities and e not in self.source_entities:
                self.source_entities.add(e)

    def get_entities(self):
        return self._entities

    def add_entities(self, es):
        for e in es:
            self.add_entity(e)

    def add_output(self, o):
        if o not in self.outputs:
            self.outputs.add(o)
            o.sim = self

    def add_entity(self, e, is_source_entity=False):
        if e not in self._entities:
            self._entities.add(e)
            e.parent = self
            e.sim = self
            if is_source_entity:
                self.source_entities.add(e)

    def remove_entity(self, e):
        if e in self._entities:
            self._entities.remove(e)

    def get_entity_by_name(self, name):
        for e in self._entities:
            if e.name == name:
                return e
        return None

    def get_entity_by_id(self, e_id):
        for e in self._entities:
            if e.id == e_id:
                return e
        return None

    def get_process_by_name(self, name):
        for e in self._entities:
            p = e.get_process_by_name(name)
            if p:
                return p
        return None

    def get_process_by_id(self, pid):
        for e in self._entities:
            p = e.get_process_by_id(pid)
            if p:
                return p
        return None

    def init_state(self):
        for action in self.initial_state:
            action.execute(self)

    def get_last_run_errors(self):
        return list(self.run_errors)

    def validate(self):
        # TODO: Write basic validation function for sim
        return True

    def run(self, start=1, end=-1, senario=set()):
        start_time = datetime.now()
        logging.info("Merlin simulation {0} started".format(self.name))
        self.run_errors = list()

        sim_start = start if start > 1 else 1
        sim_end = end if (0 < end < self.num_steps) else self.num_steps

        # clear data from the last run
        for o in self.outputs:
            o.result = list()

        # call reset on all processes
        for e in self._entities:
            e.reset()

        # run all the steps in the sim
        for t in range(sim_start, sim_end+1):
            logging.info('Simulation step {0}'.format(t))
            self.current_step = t
            self._run_senario_events()
            # get sim outputs
            for se in self.source_entities:
                try:
                    se.tick(t)
                except InputRequirementException as e:
                    self.run_errors.append(e)
        logging.info(
            "pymerlin simulation {0} finished in {1}".format(
                self.name,
                datetime.now() - start_time))


class Output(SimObject):
    """
    A network flow sink.
    """
    def __init__(self, unit_type, name=''):
        super(Output, self).__init__(name)
        self.inputs = set()
        self.current_time = None
        self.processed = False
        self.type = unit_type
        self.result = list()
        self.sim = None

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
                o = 0.0
                for i in self.inputs:
                    o += i.value
                self.result.append(o)


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

    def __str__(self):
        return """
        <Entity>
         name: {0},
         attributes: {1},
         inputs: {2},
         outputs: {3},
         parent: {4},
         children: {5},
         processes: {6}
        """.format(
            self.name,
            self.attributes,
            self.inputs,
            self.outputs,
            self.parent,
            self._children,
            self._processes)

    def add_child(self, entity):
        if entity not in self._children:
            self._children.add(entity)
            entity.parent = self

    def remove_child(self, entity_id):
        child_to_remove = None
        for c in self._children:
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

    def reset(self):
        procs = self._processes.values()
        for ps in procs:
            for p in ps:
                p.reset()

    def add_process(self, proc):
        # first check to see if the proc has already been added.
        if proc.id in [p.id for p in self._processes.values()]:
            return

        if proc.priority in self._processes.keys():
            self._processes[proc.priority].add(proc)
        else:
            self._processes[proc.priority] = {proc}
        proc.parent = self

        # Connect process outputs to entity outputs.
        # Create entity outputs if they dont exist.
        for po in proc.outputs.values():
            o_con = self.get_output_by_type(po.type)
            if not o_con:
                o_con = OutputConnector(
                    po.type,
                    self,
                    name='{0}_output'.format(po.type))
                self.add_output(o_con)

            po.connector = o_con

        # Connect process inputs to entity inputs
        # Create enity inputs if thet dont exist
        for pi in proc.inputs.values():
            i_con = self.get_input_by_type(pi.type)
            if not i_con:
                i_con = InputConnector(
                    pi.type,
                    self,
                    name='{0}_output'.format(pi.type))
                self.add_input(i_con)

            pi.connector = i_con

    def remove_process(self, proc_id):
        proc = self.get_process_by_id(proc_id)
        if proc:
            proc.parent = None
            for po in proc.outputs.values():
                po.connector = None
            for pi in proc.outputs.values():
                pi.connector = None
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

    def get_connector_by_id(self, cid):
        connectors = self.inputs.union(self.outputs)
        print(connectors)
        for c in connectors:
            if c.id == cid:
                return c
        return None

    def get_output_by_type(self, unit_type):
        for o in self.outputs:
            if o.type == unit_type:
                return o
        return None

    def get_input_by_type(self, unit_type):
        for o in self.inputs:
            if o.type == unit_type:
                return o
        return None

    def tick(self, time):
        logging.debug('Entity {0} received tick {1}'.format(self.name, time))
        if self.current_time and time < self.current_time:
            return

        if (self.current_time is None) or (time > self.current_time):
            logging.debug("Entity {0} time updated".format(self.name))
            self.processed = False
            self.current_time = time

        if time == self.current_time and not self.processed:
            # need to check if we have all inputs updated before processing
            up_to_date = True
            for i in self.inputs:
                # logging.debug(i)
                up_to_date = up_to_date and (i.time == self.current_time)

            if up_to_date:
                logging.debug(
                    "Entity {0} inputs are all refreshed, processing..".format(
                        self.name))
                self._process()

    def _process(self):
        self.processed = True
        if self._processes.keys():
            for i in sorted(self._processes.keys()):
                for proc in self._processes[i]:
                    logging.debug(
                        "Computing level {0} process {1}".format(i, proc.name))
                    proc.compute(self.current_time)
        for o in self.outputs:
            o.tick()


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
        self.props = dict()

    def get_prop(self, name):
        if name in self.props:
            return self.props[name]
        else:
            return None

    def get_prop_value(self, name):
        p = self.get_prop(name)
        if p:
            return p.value
        else:
            return None

    def get_properties(self):
        return self.props.values()

    def compute(self, tick):
        """
        Called on each process every simulation step. override
        with your custom process function. If a processes input
        requirement arn't met, raise an InputRequirementException
        """
        print("This process does absolutely nothing")

    def reset(self):
        """
        Called at the start of a simuation run on each
        process so the process can init itself if nessesary.
        override with your custom init code.
        """
        pass


class ProcessInput(SimObject):

    def __init__(self, name, unit_type, connector=None):
        super(ProcessInput, self).__init__(name)
        self.type = unit_type
        self.connector = connector

    def consume(self, value):
        self.connector.value -= value


class ProcessOutput(SimObject):

    def __init__(self, name, unit_type, connector=None):
        super(ProcessOutput, self).__init__(name)
        self.type = unit_type
        self.connector = connector


class ProcessProperty(SimObject):

    class PropertyType(Enum):
        bool_type = 1
        number_type = 2
        int_type = 3

    def __init__(
            self,
            name,
            property_type=PropertyType.number_type,
            default=0.0,
            parent=None):
        super(ProcessProperty, self).__init__(name)
        self.type = property_type
        self.max_val = default
        self.min_val = 0.0
        self.default = default
        self.parent = parent
        self._value = self.default

    def set_value(self, value):
        self._value = value

    def get_value(self):
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

    def __str__(self):
        return """
        <OutputConnector>
         name: {0},
         unit_type: {1},
         parent: {2},
         time: {3},
         copy_write: {4},
         endpoints: {5}
        """.format(
            self.name,
            self.type,
            self.parent,
            self.time,
            self.copy_write,
            self.get_endpoints())

    class Endpoint:
        def __init__(self, connector=None, bias=0.0):
            self.connector = connector
            self.bias = bias

        def __str__(self):
            return """
            <Endpoint>
             connector: {0},
             bias: {1}
             """.format(self.connector, self.bias)

    def tick(self):
        if self.time == self.parent.current_time:
            for ep in self._endpoints:
                if ep.connector.time == self.time:
                    ep.connector.parent.tick(self.time)

    def write(self, value):
        logging.debug(
            "WRITING to Output {1} value: {0} ***".format(value, self))
        self.time = self.parent.current_time
        if self._endpoints:
            for ep in self._endpoints:
                dist_value = (
                    value if self.copy_write else value *
                    ep.bias)
                logging.debug("dist_value: {0}".format(dist_value))
                ep.connector.write(dist_value)
                ep.connector.time = self.time

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

    def add_input(self, input_connector):
        if not self._get_endpoint(input_connector):
            ep = self.Endpoint(input_connector, 0.0)
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

    def __str__(self):
        return """
        <InputConnector>
          name: {0},
          unit_type: {1},
          parent: {2},
          time: {3},
          additive_write: {4},
          source: {5}
        """.format(
            self.name,
            self.type,
            self.parent,
            self.time,
            self.additive_write,
            self.source)

    def write(self, value):
        self.value = self.value + value if self.additive_write else value


class Action(SimObject):
    """
    Represents a creation or modification act for a :class:`pymerlin.Simulation`

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

    A collection of events make up a :class:`pymerlin.Simulation` senario.
    """

    def __init__(self, action, time, name=''):
        super(Event, self).__init__(name)
        self.action = action
        self.time = time


class Ruleset:
    """
    A validation class that checks the integrity of a particular
     :class:`pymerlin.Simulation`

    This is an abstract class that must be overridden by a specific ruleset for
     your simulation. In other words, each simulation will have it's own
      sublcass of Ruleset.

    In a future version of pymerlin, it would be desirable to have the rulset be
     desribed by a configuration file that could be generated from another
      product or application or written by hand.
    """

    def validate(self, action):
        return False

    def core_validate(self, action):
        self.validate(action)

# Core package exceptions


class MerlinException(Exception):
    """
    Base exception class for Merlin
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class InputRequirementException(MerlinException):
    """
    Should be thrown by a process if an input quantity produces a zero
    output by the compute function. Is used to indicate what input was
    deficient to make debugging the model easier.
    """

    def __init__(self, process, process_input, input_value, required_input):
        super(InputRequirementException, self).__init__(required_input)
        self.process = process
        self.process_input = process_input
        self.input_value = input_value
        logging.exception((
            "InputRequirementException in process {0} with " +
            "process input: {1}  input value = {2} / required value = " +
            "{3}").format(
                self.process.name,
                self.process_input.name,
                self.input_value,
                self.value))


class SimReferenceNotFoundException(MerlinException):

    def __init__(self, value):
        super(SimReferenceNotFoundException, self).__init__(value)


class EntityNotFoundException(MerlinException):

    def __init__(self, value):
        super(EntityNotFoundException, self).__init__(value)
