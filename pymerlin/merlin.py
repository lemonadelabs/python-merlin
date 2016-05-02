"""
.. module:: merlin

This is the main module containing the core objects in
the system as well as some bootstrap and helper functions.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""

import logging
import uuid
import json
import importlib
from datetime import datetime
from enum import Enum
from json.decoder import JSONDecodeError
from typing import (Iterable, Set, Mapping, Any,
                    List, MutableSequence, Dict,
                    Union, MutableSet, MutableMapping)


class SimObject:
    """
    Basic properties of all sim objects.
    """
    def __init__(self, name: str=''):
        self.id = int(uuid.uuid4())  # type: int
        """auto-generated UUID"""

        self.name = name or str(self.id)
        """name or self.id (default)"""

        self._telemetry = dict()  # type: MutableMapping[str, Iterable[Any]]
        """
        Stores a series of properties and
        time series of values for that property
        """

    def reset_telemetry(self) -> None:
        self._telemetry = dict()

    def set_telemetry_value(self, prop: str, value: Any) -> None:

        if prop not in self._telemetry:
            self._telemetry[prop] = list()

        self._telemetry[prop].append(value)

    def get_telemetry_data(self) -> Mapping[str, Iterable[Any]]:
        return self._telemetry


class Simulation(SimObject):
    """
    A representation of a network with its associated entities, ruleset,
    scenarios and outputs.

    Any new :py:class:`.Entity` needs to be added to the
    simulation with the :py:meth:`.add_entities` methods.
    """

    def __init__(self, ruleset=None, config=None, outputs=None, name=''):
        super(Simulation, self).__init__(name)
        self._unit_types = set()  # type: MutableSet[str]
        self._attributes = set()  # type: MutableSet[str]
        self._entities = set()  # type: MutableSet[Entity]
        self._messages = list()  # type: List[MerlinMessage]
        self.ruleset = ruleset  # type: Ruleset
        self.initial_state = config or []
        self.source_entities = set()  # type: MutableSet[Entity]
        self.outputs = outputs or set()  # type: MutableSet[Entity]
        self.num_steps = 1  # type: int
        self.current_step = 1  # type: int
        self.run_errors = list()  # type: List[MerlinException]
        self.verbose = True  # type: bool

    def _run_senario_events(self, scenarios: List['Scenario']) -> None:
        for s in scenarios:
            for e in s.events:
                if (e.time + s.start_offset) == self.current_step:
                    for a in e.actions:
                        a.execute(self)

    def _get_object_telemetry(self, so: SimObject) -> Mapping[str, Any]:
        return {
            'type': so.__class__.__name__,
            'id': so.id,
            'name': so.name,
            'data': so.get_telemetry_data()}

    def parent_entity(
            self,
            parent_entity: 'Entity',
            child_entity: 'Entity') -> None:

        child_entity.parent = parent_entity
        parent_entity.add_child(child_entity)

    def disconnect_entities(
            self,
            from_entity: 'Entity',
            to_entity: 'Entity',
            unit_type: str) -> None:
        """
        Disconnects the connector of unit_type between
        from_entity and to_entity
        :param Entity from_entity:
        :param Entity to_entity:
        :param str unit_type:
        """
        i_con = to_entity.get_input_by_type(unit_type)
        o_con = from_entity.get_output_by_type(unit_type)

        if i_con and o_con:
            o_con.remove_input(i_con)
            to_entity.inputs.remove(i_con)

    def connect_entities(
            self,
            from_entity,
            to_entity,
            unit_type,
            input_additive_write=False,
            apportioning=None):
        """
        :param Entity from_entity:
        :param Entity to_entity:
        :param str unit_type: the exact InputConnector and OutputConnector
           are identified by their ``type`` attribute.
        :param bool input_additive_write: sets ``additive write`` for the
            :py:class:`InputConnector` (only if not already exists!)
        :param ApportioningRules apportioning: sets apportioning rule for
           :py:class:`.OutputConnector` (only if not already exists!)
        """

        o_con = from_entity.get_output_by_type(unit_type)
        i_con = to_entity.get_input_by_type(unit_type)

        if not o_con:
            o_con = OutputConnector(
                unit_type,
                from_entity,
                name='{0}_output'.format(unit_type),
                apportioning=apportioning)

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
            apportioning=None):
        """
        :param Entity entity:
        :param Output output:
        :param bool input_additive_write: sets ``additive write`` for the
            :py:class:`InputConnector` (only if not already exists!)
        :param ApportioningRules apportioning: sets apportioning rule for
           :py:class:`.OutputConnector` (only if not already exists!)
        """

        if output not in self.outputs:
            return

        o_con = entity.get_output_by_type(output.type)

        if not o_con:
            o_con = OutputConnector(
                output.type,
                entity,
                name='{0}_output'.format(output.type),
                apportioning=apportioning)

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
        """
        :param int num_months: number of months, acts as default stop value for
           :py:meth:`pymerlin.merlin.Simulation.run`. So, without parameters
           ``run`` will run from ``1`` to ``num_months`` (inclusive).
        """
        self.num_steps = num_months

    def add_attributes(self, ats):
        """
        :param iterable with str ats: iterable with string identifiers

        the attributes identify the entities as assets, resources, branch, ...
        used in the parameter for instantiating
        :py:class:`pymerlin.merlin.Entity`.
        """
        for a in ats:
            if a not in self._attributes:
                self._attributes.add(a)

    def get_attributes(self):
        return set(self._attributes)

    def add_unit_types(self, uts):
        """
        :param iterable with str uts: iterable with string identifiers for
            units

        used for instantiating :py:class:`pymerlin.merlin.ProcessOutput`,
        :py:class:`pymerlin.merlin.ProcessInput` and by
        :py:meth:`pymerlin.merlin.Simulation.connect_entities`
        """
        for ut in uts:
            if ut not in self._attributes:
                self._unit_types.add(ut)

    def get_unit_types(self):
        return set(self._unit_types)

    def is_attribute(self, a):
        return a in self._attributes

    def is_unit_type(self, ut):
        return ut in self._unit_types

    def set_source_entities(self, entities):
        """
        these entities are set as source entities, i.e. started first
        """
        for e in entities:
            if e in self._entities and e not in self.source_entities:
                self.source_entities.add(e)

    def get_entities(self):
        return self._entities

    def add_entities(self, es):
        """
        adds entities ``es`` to the simulation, but does not nest them
        into any :py:class:`.Entity`s
        """
        for e in es:
            self.add_entity(e)

    def add_output(self, o):
        if o not in self.outputs:
            self.outputs.add(o)
            o.sim = self

    def add_entity(self, e, is_source_entity=False, parent=None):
        """
        :param Entity e: The entity to add
        :param bool is_source_entity: a process containing entity, which has
            no inputs, so it is "naturally" a start of processing.
        :param .Entity parent: the parent entity,
            None if contained in simulation

        if not, the parent is the entity containing ``e`` and
        ``parent.add_child(e)`` needs to be called as well.
        """
        if e not in self._entities:
            self._entities.add(e)
            e.parent = parent
            e.sim = self
            if is_source_entity:
                self.source_entities.add(e)

    def remove_entity(self, e):
        """
        :param .Entity e: entity to be removed

        removes an entity if existing
        """
        if e in self._entities:
            self._entities.remove(e)

    def get_entity_by_name(self, name) -> 'Entity':
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

    def log_message(
            self,
            message_type: 'MerlinMessage.MessageType',
            sender: SimObject,
            msg_id: str="",
            msg: str="",
            context: List[SimObject]=list()):

        m = MerlinMessage(
            message_type,
            self.current_step,
            sender,
            msg_id,
            msg,
            context)

        self._messages.append(m)

    def get_run_messages(self) -> List[Dict[str, Any]]:
        return [m.serialize() for m in self._messages]

    def get_sim_telemetry(self) -> List[Dict[str, Any]]:
        output = list()
        for o in self.outputs:
            output.append(self._get_object_telemetry(o))

        for e in self.get_entities():

            connector_to_pinput = dict()

            for p in e.get_processes():
                for pprop in p.get_properties():
                    output.append(self._get_object_telemetry(pprop))

                for pinput in p.inputs.values():
                    if pinput.connector.id not in connector_to_pinput:
                        connector_to_pinput[pinput.connector.id] = list()
                    connector_to_pinput[pinput.connector.id].append(pinput)

            for i in e.inputs:

                # coalese all consumers of this import
                # into a single time series
                if i.id in connector_to_pinput:
                    master_consume = list()
                    master_consume += [0.0] * (self.num_steps -
                                               len(master_consume))
                    pinputs = connector_to_pinput[i.id]
                    for pi in pinputs:
                        if 'consume' in pi.get_telemetry_data():
                            td = pi.get_telemetry_data()['consume']
                            for x in range(0, len(td)):
                                master_consume[x] += td[x]

                    for x in master_consume:
                        i.set_telemetry_value('consume', x)

                output.append(self._get_object_telemetry(i))

            for o in e.outputs:
                output.append(self._get_object_telemetry(o))

        # Append run messages
        ms = dict()
        ms['messages'] = self.get_run_messages()
        output.append(ms)

        return output

    def run(
            self,
            start: int=1,
            end: int=-1,
            scenarios: List['Scenario']=list()) -> None:
        """
        :param int start:
        :param int end:
        :param List[Scenario] scenarios:

        runs the simulation in end-start+1 steps, where the end defaults to
        and is limited to ``self.num_steps``. Start is 1 or higher.
        """
        start_time = datetime.now()
        logging.info("Merlin simulation {0} started".format(self.name))
        self.run_errors.clear()
        self._messages.clear()

        if end > self.num_steps:
            self.num_steps = end

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
            self._run_senario_events(scenarios)
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
        """
        :param str unit_type: the string identifying the unit of the
            output value
        :param str name: the name string for the base class.

        This collects the outputs for a branch or department from the different
        entities containing :py:class:`pymerlin.merlin.Process`.

        ``unit_type`` needs to be added to the simulation with
        :py:meth:`pymerlin.merlin.add_unit_types`.

        :attr:`.expected_minimum` sets an expectation to the output value,
           which needs to be met and can be over-fulfilled.
        """
        super(Output, self).__init__(name)
        self.inputs = set()  # type: Set[InputConnector]
        self.current_time = None  # type: int
        self.processed = False
        self.type = unit_type
        self.result = list()  # type: MutableSequence[float]
        self.sim = None  # type: Union[Simulation, None]
        self.expected_minimum = None

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
                self.set_telemetry_value('value', o)


class Entity(SimObject):
    """
    A node in the network.

    Commonly used to represent a business capability, a resource or an asset.
    Entities can contain processes that modify data arriving at the entity's
    input connectors or generate new data that gets written to the entity's
    output connectors.
    """

    def __init__(
            self,
            simulation: Simulation=None,
            name: str='',
            attributes: Set[str]=set()):
        super(Entity, self).__init__(name)
        self._processes = dict()  # type: Dict[int, Set['Process']]
        self.sim = simulation  # type: Simulation
        self.attributes = set(attributes)  # shallow copy
        self.inputs = set()  # type: Set[InputConnector]
        self.outputs = set()  # type: Set[OutputConnector]
        self.parent = None  # type: Union[None, Entity]
        self._children = set()  # type: MutableSet[Entity]
        self.current_time = None  # type: int
        self.processed = False  # type: bool

    def __str__(self):
        return """
        <Entity: {7}>
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
            [(id(o), o.type) for o in self.outputs],
            "None" if self.parent is None else (
                id(self.parent), self.parent.name),
            [(id(c), c.name) for c in self._children],
            self._processes,
            id(self))

    def create_process(
            self,
            process_class: type,
            params: Dict[str, Any],
            priority: int=100) -> 'Process':
        """
        Creates a new process inside the entity and wires up
        the appropriate inputs and outputs afterward.

        This is the proper way to create processes going forward.

        :param process_class: the type of the process to create
        :param params: the keyword arguments to the constructor of the process
        :param priority: the priority of the process, lower = higher priority
        :return: The newly created Process
        """

        new_proc = process_class(**params)  # type: Process
        new_proc.default_params = params
        new_proc.priority = priority
        self._add_process(new_proc)
        return new_proc

    def add_child(self, entity):
        if entity not in self._children:
            self._children.add(entity)
            entity.parent = self
            entity.sim = self.sim

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
        """
        resets all processes in this entity to prepare for a new simulation
        run, (i.e. executing the ``tick`` method several times in sequence
        governed by the connector network.
        """
        for i in self.inputs:
            i.reset_telemetry()

        for o in self.outputs:
            o.reset_telemetry()

        self.reset_telemetry()
        procs = self._processes.values()
        for ps in procs:
            for p in ps:
                p.reset_telemetry()
                p.reset()

                for p_inputs in p.inputs.values():
                    p_inputs.reset_telemetry()

                for p_output in p.outputs.values():
                    p_output.reset_telemetry()

                for pprop in p.get_properties():
                    pprop.reset_telemetry()

    def remove_process(self, proc_id):
        proc = self.get_process_by_id(proc_id)
        if proc:
            proc.parent = None
            for po in proc.outputs.values():
                po.connector = None
            for pi in proc.outputs.values():
                pi.connector = None
            self._processes[proc.priority].remove(proc)

    def get_processes(self) -> List['Process']:
        procs = self._processes.values()
        output = []
        for ps in procs:
            output += ps
        return output

    def get_process_by_name(self, proc_name) -> 'Process':
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

    def get_output_by_type(self, unit_type) -> 'OutputConnector':
        for o in self.outputs:
            if o.type == unit_type:
                return o
        return None

    def get_input_by_type(self, unit_type) -> 'InputConnector':
        for o in self.inputs:
            if o.type == unit_type:
                return o
        return None

    def tick(self, time):
        """
        :param int time: tick integer

        Executes all processes within an entity if all inputs are updated.
        Once all processes are executed with :py:meth:`.Process.compute`,
        the control flow goes depth-first to :py:meth:`.Output.tick`.
        """
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
                self._update_process_telemetry()

    def _add_process(self, proc):
        """
        adds a :py:class:`pymerlin.merlin.Process` to an entity.

        If the Entity is already connected to other entities and the process
        inputs/outputs are matching, they are connected accordingly.

        This matching is done by ``type``!
        """

        # first check to see if the proc has already been added.
        if proc.id in [p.id for p in self.get_processes()]:
            return

        if proc.priority in self._processes.keys():
            self._processes[proc.priority].add(proc)
        else:
            self._processes[proc.priority] = {proc}
        proc.parent = self

        # Connect process outputs to entity outputs.
        # Create entity outputs if they don't exist.
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
        # Create entity inputs if they don't exist
        for pi in proc.inputs.values():
            i_con = self.get_input_by_type(pi.type)
            if not i_con:
                i_con = InputConnector(
                    pi.type,
                    self,
                    name='{0}_input'.format(pi.type))
                self.add_input(i_con)

            pi.connector = i_con

    def _update_process_telemetry(self):
        if self._processes.keys():
            for i in self._processes.keys():
                for proc in self._processes[i]:
                    for pprop in proc.get_properties():
                        pprop.set_telemetry_value('value', pprop.get_value())

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
    Must be sub-classed to create specific processes.

    Things to override in the subclass:

    * :py:attr:`inputs`: dictionary with ``{name: ProcessInput}``
    * :py:attr:`outputs`: dictionary with ``{name: ProcessOutput}``
    * :py:attr:`props`: process_properties dictionary with
      ``{name: ProcessProperty}``
    * :py:attr:`compute` and
    * :py:attr:`reset` if this process has internal states.

    The process object is added to an :py:class:`pymerlin.merlin.Entity` using
    the :py:meth:`pymerlin.merlin.Enitity.add_process` method *AFTER* the
    entities are connected to each other.
    """

    def __init__(self, name: str=''):
        super(Process, self).__init__(name)
        self.parent = None  # type: Entity
        self.priority = 1000
        """
        This number influences the execution order of the compute methods.
        The lower the number the earlier the compute method of this process
        will be executed. Processes with the same priority will be executed
        in an arbitrary order.

        To easily assign higher or lower priorities than the standard, the
        default is set to 1000.

        The priority needs to be an integer between 0 and +32767 incl. (this
        restriction comes from django's model implementation).
        """
        self.inputs = dict()  # type: Dict[str, 'ProcessInput']
        self.outputs = dict()  # type: Dict[str, 'ProcessOutput']
        self.props = dict()  # type: Dict[str, 'ProcessProperty']
        self.default_params = dict()  # type: Dict[str, Any]

    def get_prop(self, name) -> 'ProcessProperty':
        """
        :return: the property with this name, None otherwise
        :rtype: :py:class:`pymerlin.merlin.ProcessProperty`
        """

        if name in self.props:
            return self.props[name]
        else:
            # check SimObject name prop
            for pp in self.get_properties():
                if pp.name == name:
                    return pp
            return None

    def get_prop_value(self, name):
        """
        :return: the current (?) value of the property with this name,
            None otherwise
        :rtype: the type as indicated by
           :py:attr:`pymerlin.merlin.ProcessProperty.type`.
        """
        p = self.get_prop(name)
        if p:
            return p.get_value()
        else:
            return None

    def get_properties(self) -> List['ProcessProperty']:
        """
        :returns: an iterable of all :py:class:`.ProcessProperty` objects
        """
        return self.props.values()

    # create interface to self.inputs and self outputs to hide the
    # implementation details of the connectors

    def add_input(self, name, unit, connector=None):
        """
        :param str name: to identify within :py:class:`.Process`
        :param InputConnector connector: An optional input connector to bind to
        :param str unit: unit of this output, used for connecting the
           :py:class:`.ProcessInput` with the :py:class:`.Entity`s connectors.
        """
        inp = ProcessInput(name, unit, connector)
        self.inputs[name] = inp

    def add_output(self, name, unit):
        """
        :param str name: to identify within :py:class:`.Process`
        :param str unit: unit of this output, used for connecting the
           :py:class:`.ProcessInput` with the :py:class:`.Entity`s connectors.
        """
        out = ProcessOutput(name, unit)
        self.outputs[name] = out

    def add_property(self,
                     display_name,
                     name,
                     property_type,
                     default_value):
        """
        :param
        :param str display_name: will be exposed to front-end and is more
            expressive than name
        :param str name: to identify within :py:class:`.Process`
        :param PropertyType property_type: the representation of the value
        :param float default_value: the default value
        """
        if name in self.props:
            raise KeyError("property %s already exists" % (name,))

        prop = ProcessProperty(
                    display_name,
                    property_type=property_type,
                    default=default_value,
                    parent=self)
        self.props[name] = prop

    def remove_property(self, name):
        self.props[name].parent = None
        del self.props[name]

    def provide_output(self, name, value):
        """
        :param str name: name of output
        :param float value: the value made available/produced at
             the actual tick
        :returns: None
        """
        self.outputs[name].connector.write(value)

    def get_input_available(self, name):
        """
        :param str name: the name of the input
        :returns: the value provided/apportioned for the recent tick
        """
        return self.inputs[name].connector.value

    def consume_input(self, name, value):
        """
        :param str name: name of input
        :param float value: the value consumed at the actual tick
        :returns: None
        """
        assert self.get_input_available(name) >= value, \
            "consuming more input than available"
        self.inputs[name].consume(value)

    def notify_insufficient_input(self, name, available, required):
        assert name in self.inputs

        self.parent.sim.log_message(
            MerlinMessage.MessageType.warn,
            self,
            "{0}_{1}_insufficent_input".format(self.name, name),
            ("There is not enough {{{{{0}}}}} provided as an input. " +
                "We needed {1} but got {2}").format(
                    self.inputs[name].type,
                    required,
                    available),
            context=list([self.inputs[name]])
        )

    def compute(self, tick):
        """
        :param int tick: the actual tick from
           :py:meth:`pymerlin.merlin.Simulation.run`
        :return: None, see below for handling of compute results

        Called on each process every simulation step. override
        with your custom process function.

        Use the method :py:meth:`pymerlin.merlin.ProcessOutput.write` to
        provide the output value. The output write function allows the
        dependent processes to be executed, so even if nothing is produced,
        a ``write(0)`` is expected.

        .. code-block:: python3

            self.outputs["licensesPrinted"].connector.write(licenseNo)


        Use the :py:class:`pymerlin.merlin.InputConnector` to access the
        inputs available:

        .. code-block:: python3

            available = self.inputs['$'].connector.value
            self.inputs['$'].connector.consume(utilized)

        If a processes input requirement isn't met, raise an
        :py:exc:`pymerlin.merlin.InputRequirementException`.
        To allow the processes "downstream" to be executed, use a ``write(0)``
        before raising the exception

        .. note::
            It is safe to assume that :py:meth:`reset`, is called before this
            method.
        """
        print("This process does absolutely nothing")

    def reset(self):
        """
        Called at the start of a simulation run on each
        process so the process can initialize itself if necessary.
        override with your custom reset code.

        This method is called for all entities by
        :py:meth:`pymerlin.merlin.Simulation.run`.
        """
        pass


class ProcessInput(SimObject):
    """
    :param str name: name for :py:attr:`pymerlin.merlin.SimObject.name`
    :param str unit_type: string identifying the unit of the output value
    :param object connector: saved, but not used right now

    The outputs and inputs are connected via the entities using
    :py:meth:`pymerlin.merlin.Simulation.connect_entites` matching up the unit
    types.

    The name on the front-end is the :py:attr:`.InputConnector.name`.
    """

    def __init__(self, name, unit_type, connector=None):
        super(ProcessInput, self).__init__(name)
        self.type = unit_type  # type: str
        self.connector = connector  # type: InputConnector

    def __str__(self):
        return """
        <ProcessInput {2}>
            type: {0}
            connector: {1}""".format(self.type, self.connector, id(self))

    def consume(self, value):
        self.set_telemetry_value('consume', value)
        self.connector.value -= value


class ProcessOutput(SimObject):

    def __init__(self, name, unit_type, connector=None):
        """
        :param str name: name for :py:attr:`pymerlin.merlin.SimObject.name`
        :param str unit_type: string identifying the unit of the output value
        :param object connector: saved, but not used right now

        Used to define the outputs of a :py:class:`pymerlin.merlin.Process`.

        The outputs and inputs are connected via the entities using
        :py:meth:`pymerlin.merlin.Simulation.connect_entites` matching up the
        unit types.

        The unit needs to be registered with
        :py:meth:`pymerlin.Simuation.add_unit_types`

        The name on the front-end is the :py:attr:`.OutputConnector.name`.
        """
        super(ProcessOutput, self).__init__(name)
        self.type = unit_type
        self.connector = connector

    def __str__(self):
        return """
        <Process Output {0}>
            type: {1}
            connector: {2}
        """.format(id(self), self.type, self.connector)


class ProcessProperty(SimObject):
    """
    allows for parameterization of a process, e.g. productivity or
    cost per piece.

    the :attr:`.name` appears in the front-end graphics.
    """

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
        """
        :param str name: a name for easy identification
        :param Enum property_type: the type of the property, choose from
           :py:class:`PropertyType`
        :param object default: a default value for this property
        :param Process parent: the process using this property
        """

        super(ProcessProperty, self).__init__(name)
        self.type = property_type
        self.max_val = None
        self.min_val = None
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

    Stores the connected :py:class:`.InputConnector`s as
    :py:class:`.Endpoint`.
    """

    def __init__(
            self,
            unit_type,
            parent,
            name='',
            apportioning=None,
            endpoints=None):
        """
        is created by :py:meth:`.Simulation.connect_entities` or
        :py:meth:`.Simulation.connect_output`.

        :param str unit_type: the unit of the value put into this output
        :param Entity parent: the Entity featuring this output connector.

        :param .ApportioningRules apportioning: the rule how an output value
                 is split on the inputs, the default is ``weighted``.
        :param iterable of .InputConnector endpoints: or None to create an
                 empty set.
        """

        super(OutputConnector, self).__init__(unit_type, parent, name)
        self.apportioning = (self.ApportioningRules.weighted
                             if apportioning is None else apportioning)
        self._endpoints = endpoints or set()

    def __str__(self):
        return """
        <OutputConnector>
         name: {0},
         unit_type: {1},
         parent: {2},
         time: {3},
         apportioning: {4},
         endpoints: {5}
        """.format(
            self.name,
            self.type,
            self.parent,
            self.time,
            self.apportioning,
            self.get_endpoints())

    class Endpoint:
        """
        This class is used to organize the :py:class:`.InputConnector`s which
        are connected to an :py:class:`.OutputConnector`.

        The :py:attr:`.bias` allows for a weighted distribution of the values
        written to the :py:class:`.OutputConnector` instance.

        On connecting or removing end-points, the biases are recalculated to
        equal weight.
        """
        def __init__(self, connector=None, bias=0.0):
            self.connector = connector
            self.bias = bias

        def __str__(self):
            return """
            <Endpoint>
             connector: {0},
             bias: {1}
             """.format(self.connector, self.bias)

    class ApportioningRules(Enum):
        copy_write = 1
        weighted = 2
        absolute = 3

    def tick(self):
        """
        propagates the control flow along the end-points if they are ready for
        it, which is decided by the time stamps
        """
        if self.time == self.parent.current_time:
            for ep in self._endpoints:
                if ep.connector.time == self.time:
                    ep.connector.parent.tick(self.time)

    def write(self, value):
        """
        distribute or copy value to the :py:attr:`.Endpoint.connector`.

        The distribution is governed by :py:class:`.ApportioningRules`, using
        the values of :py:attr:`.Endpoint.connector.bias`.

        This method hands over the control flow to what is behind each
        end-point, resulting in a depth first like iteration.

        The apportioning rules are:

        ``copy_write``
            The value written is copied to all end-points.

        ``weighted``
            The bias values are used to apportion the value according
            to the weights. If all weights are 0, the value is split up in even
            parts over the end-points.

        ``absolute``
            The bias values are used as absolute values, i.e. in the
            simple case, these values are written to the outputs if their sum
            is not larger than the value parameter. In more general terms: The
            end-points are apportioned in to order of decreasing bias. Each
            endpoint gets the value of bias, if the sum of the values already
            apportioned is allowing for it. Otherwise it gets the remainder
            value or 0.
        """
        self.set_telemetry_value('value', value)

        logging.debug(
            "WRITING to Output {1} value: {0} ***".format(value, self))
        self.time = self.parent.current_time

        # pre-calculate the values to be written
        # and provide them in ep_output
        if self.apportioning is self.ApportioningRules.copy_write:
            # very simple rule, just copy
            ep_output = [(ep, value) for ep in self._endpoints]

        elif self.apportioning is self.ApportioningRules.weighted:
            # get an ordered version of the end-points
            eps = list(self._endpoints)
            biases = [ep.bias for ep in eps]
            assert all(b >= 0 for b in biases), "biases must not be negative"
            bias_sum = sum(biases)
            if bias_sum == 0:
                # handle no biases set (default case)
                biases = [1.0]*len(eps)
                bias_sum = sum(biases)
            ep_output = zip(eps, (b/bias_sum*value for b in biases))

        elif self.apportioning is self.ApportioningRules.absolute:
            # get sorted list of end-points, start with biggest one!
            eps = list(sorted(self._endpoints,
                              key=lambda ep: ep.bias,
                              reverse=True))
            value_remaining = value+0.0
            ep_output = []
            for ep in eps:
                out_val = min(value_remaining, max(ep.bias, 0.0))
                ep_output.append((ep, out_val))
                value_remaining -= out_val

        else:
            assert False, ("unexpected apportioning rule value "
                           "{}".format(self.apportioning))

        # now do the output writing
        for ep, dist_value in ep_output:
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
        """
        Get the :py:class:`.InputConnector`s and their biases connected to this
        :py:class:`.OutputConnector`.

        :rtype: list
        :returns: list of (:py:class:`.InputConnector`, bias)
        """
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
                "Biases parity must match number of endpoints")
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
        self.value = (self.value + value) if self.additive_write else value
        self.set_telemetry_value('value', self.value)


class Action(SimObject):
    """
    Represents a creation or modification act for a :class:`.Simulation`

    Action is considered and abstract class and should be sub-classed to create
    a specific Action.
    """

    @classmethod
    def create_from_dict(cls, actions: List[Dict[str, Any]]) -> 'List[Action]':
        output = list()
        for a in actions:
            output.append(Action._generate_action(a))
        return output

    @classmethod
    def create(cls, script: str) -> 'List[Action]':
        """
        Parses a MerlinScript string and returns a
        newly created list of action objects for the
        supplied merlin simulation.
        """
        output = list()

        script = script.strip()
        lines = script.splitlines()
        # break into tokens
        for l in lines:
            l = l.strip()
            tokens = Action._lex_tokens(l)
            # print("lexer result = {0}".format(tokens))
            output.append(
                Action._generate_action(
                    Action._parse_action(tokens)))
        return output

    @classmethod
    def create_from_json(cls, json_string: str) -> 'List[Action]':
        """
        Parses a list of actions from a json serilaised string
        :param str json_string:
        """
        output = list()
        j = json.loads(json_string)
        for a in j:
            output.append(Action._generate_action(a))
        return output

    @classmethod
    def _lex_tokens(cls, line: str) -> List[str]:
        """
        The lexer function for the script.
        :param line:
        :return: a list of tokens
        """

        # Find operator and split
        operators = [':=', '+', '-', '^', '/', '>']
        parts = None
        for o in operators:
            parts = line.partition(o)
            if parts[0] != line:
                break

        if parts[0] == line:
            raise MerlinScriptException(
                "Parse error. Operator not found in line: {0}".format(line))

        if not parts[0] and parts[1] and parts[2]:
            # print("param part: {0}".format(parts[2]))
            operand_1_tokens = Action._lex_operand(parts[2])
            # print("lex result: {0}".format(operand_1_tokens))
            return [parts[1]] + operand_1_tokens
        else:
            operand_1_tokens = Action._lex_operand(parts[0])
            operand_2_tokens = Action._lex_operand(parts[2])
            return operand_1_tokens + [parts[1]] + operand_2_tokens

    @classmethod
    def _lex_operand(cls, op_string: str) -> List[str]:
        output = list()
        if not op_string:
            return output
        op_string = op_string.strip()
        output.append(op_string.partition(' ')[0])
        arguments = op_string.partition(' ')[2]
        if arguments == op_string:
            raise MerlinScriptException(
                "Parse error. Expected type in operand: {0}".format(op_string)
            )
        output += [s.strip() for s in arguments.split(',')]
        return output

    @classmethod
    def _generate_action(cls, a: Dict[str, Any]) -> 'Action':
        # work out type of action based on ast
        # Unary expressions
        if a['operand_2'] is None:
            if len(a['operand_1']['params']) == 0:
                raise MerlinScriptException(
                    "Invalid parameter size")

            if a['op'] == '+':
                if a['operand_1']['type'] == 'Attribute':
                    try:
                        return AddAttributesAction(
                            [str(p) for p in a['operand_1']['params']])
                    except Exception:
                        raise MerlinScriptException(
                            "Invalid parameters for AddAttributeAction")

                elif a['operand_1']['type'] == 'Entity':
                    try:
                        return AddEntityAction(
                            a['operand_1']['params'][0],
                            attributes=a['operand_1']['params'][1:])
                    except Exception:
                        raise MerlinScriptException(
                            "Invalid parameters for AddEntityAction")

                elif a['operand_1']['type'] == 'UnitType':
                    try:
                        return UnitTypeAction(
                            [str(p) for p in a['operand_1']['params']])
                    except Exception:
                        raise MerlinScriptException(
                            "Invalid parameters for AddUnitTypeAction")
            elif a['op'] == '-':

                if a['operand_1']['type'] == 'Attribute':
                    raise MerlinScriptException(
                        "Operation RemoveAttribute not supported")

                elif a['operand_1']['type'] == 'Entity':
                    try:
                        return RemoveEntityAction(a['operand_1']['params'][0])
                    except Exception:
                        raise MerlinScriptException(
                            "Invalid parameters for RemoveEntityAction")

                elif a['operand_1']['type'] == 'UnitType':
                    raise MerlinScriptException(
                        "Operation RemoveUnitType not supported")
            else:
                raise MerlinScriptException(
                    "Invalid operator for unary expression, must be + or -")
        else:

            if len(a['operand_1']['params']) == 0 \
                    or len(a['operand_2']['params']) == 0:
                raise MerlinScriptException(
                    "Invalid parameter size")

            if a['op'] == '+':
                # Add process action
                return AddProcessAction(
                    *(a['operand_1']['params'] + a['operand_2']['params']),
                    **{'process_params': a['operand_2']['props']})

            if a['op'] == '-':
                return RemoveProcessAction(
                    *(a['operand_1']['params'] + a['operand_2']['params']))

            if a['op'] == ':=':
                # modify process property
                return ModifyProcessPropertyAction(
                    *(a['operand_1']['params'] + a['operand_2']['params']))

            if a['op'] == '/':
                # Disconnect operator
                return RemoveConnectionAction(
                    *(a['operand_1']['params'] + a['operand_2']['params']))

            if a['op'] == '^':
                # Parent operator
                return ParentEntityAction(
                    *(a['operand_1']['params'] + a['operand_2']['params']))

            if a['op'] == '>':
                # Connect operator
                return AddConnectionAction(
                    *(a['operand_1']['params'] + a['operand_2']['params']))

            raise MerlinScriptException("No Process match!")

    @classmethod
    def _parse_action(cls, tokens) -> Dict[str, Any]:
        op = Action._parse_op(tokens[0])
        if op:
            # this is a single operand command
            tokens = tokens[1:]
            # now look for a type
            type1 = Action._parse_type(tokens[0])
            if type1:
                # parse type 1 params
                type1_params = Action._parse_params(tokens[1:])
                return {
                    'op': op,
                    'operand_1': {
                        'type': type1,
                        'params': type1_params,
                        'props': None
                    },
                    'operand_2': None}
            else:
                raise MerlinScriptException(
                    "Syntax Error: {0} is not a valid type".format(tokens[0]))
        else:
            type1 = Action._parse_type(tokens[0])
            if type1:
                tokens = tokens[1:]
                type1_params = Action._parse_params(tokens)
                tokens = tokens[len(type1_params):]
                type1_props = Action._parse_props(tokens)
                tokens = tokens[len(type1_props):]
                op = Action._parse_op(tokens[0])
                if op:
                    tokens = tokens[1:]
                    type2 = Action._parse_type(tokens[0])
                    if type2:
                        tokens = tokens[1:]
                        type2_params = Action._parse_params(tokens)
                        tokens = tokens[len(type2_params):]
                        type2_props = Action._parse_props(tokens)
                        return \
                            {
                                'op': op,
                                'operand_1':
                                    {
                                        'type': type1,
                                        'params': type1_params,
                                        'props': type1_props
                                    },
                                'operand_2':
                                    {
                                        'type': type2,
                                        'params': type2_params,
                                        'props': type2_props
                                    }
                            }
                    else:
                        raise MerlinScriptException(
                            "Syntax Error: {0} is not a valid type".format(
                                tokens[0]))
                else:
                    raise MerlinScriptException(
                        "Syntax Error: Expected an operator, got {0}".format(
                            tokens[0]))
            else:
                raise MerlinScriptException(
                    "Syntax Error: {0} is not a valid type".format(
                        tokens[0]))

    @classmethod
    def _parse_params(cls, tokens: List[str]) -> List[str]:
        params = list()
        for t in tokens:
            if not t:
                raise MerlinScriptException(
                    "Invalid param {0}".format(t))
            tt = Action._parse_type(t)
            to = Action._parse_op(t)
            if ('=' in t) and (':' in t):
                return params
            if tt or to:
                return params
            else:
                params.append(t)
        return params

    @classmethod
    def _parse_props(cls, tokens: List[str]) -> Dict[str, Any]:
        # TODO: fix this function
        if not tokens:
            return None
        props = dict()
        for t in tokens:
            tt = Action._parse_type(t)
            to = Action._parse_op(t)
            if tt or to:
                return props
            else:
                type_p = t.partition(':')
                if type_p[0] == t:
                    print("type partition error")
                    return None
                else:
                    label = type_p[0].strip()
                    value_p = type_p[2].partition('=')
                    if value_p[0] == type_p[2]:
                        print("equality partiton error")
                        return None
                    else:
                        val_type = value_p[0].strip()
                        val = None
                        if val_type == 'bool':
                            val = (value_p[2].strip() == 'True')
                        elif val_type == 'float':
                            val = float(value_p[2].strip())
                        elif val_type == 'str':
                            val = value_p[2].strip()

                        if not val:
                            raise MerlinScriptException(
                                "invalid type {0}".format(val_type))
                        props[label] = val
        return props

    @classmethod
    def _parse_type(cls, token):
        if token in ['Entity', 'Attribute', 'UnitType', 'Process', 'Property']:
            return token
        else:
            return None

    @classmethod
    def _parse_op(cls, token):
        if token in ['+', '-', '>', '/', ':=', '^']:
            return token
        else:
            return None

    def __init__(self):
        super(Action, self).__init__(name='')

    def execute(self, simulation: Simulation):
        pass

    def serialize(self) -> Dict[str, Any]:
        return dict()


class Event(SimObject):
    """
    An event is a pairing of a time and a list of actions
    to be executed at that time.

    A collection of events make up a :class:`pymerlin.Simulation` scenario.
    """

    def __init__(
            self,
            actions: List[Action],
            time: int,
            name: str='') -> None:
        super(Event, self).__init__(name)
        self.actions = actions  # type: List[Action]
        self.time = time  # type: int

    @classmethod
    def create(cls, time: int, script: str) -> 'Event':
        try:
            json.loads(script)
            instance = cls(
                Action.create_from_json(script),
                time)
        except JSONDecodeError:
            instance = cls(
                Action.create(script),
                time)
        return instance

    @classmethod
    def create_from_dict(
            cls,
            time: int,
            data: List[Dict[str, Any]]) -> 'Event':

        return cls(Action.create_from_dict(data), time)

    def get_serialized_event_actions(self) -> List[Dict[str, Any]]:
        output = list()
        for a in self.actions:
            output.append(a.serialize())
        return output


class Scenario(SimObject):

    def __init__(
            self,
            events: Set[Event],
            sim: Simulation= None,
            start_offset: int= None,
            name: str=''):
        super(Scenario, self).__init__(name)
        self.events = events  # type: Set[Event]
        self.sim = sim   # type: Simulation
        self.start_offset = start_offset or 0  # type: int


class MerlinMessage:

    class MessageType(Enum):
        info = 0
        hint = 1
        warn = 2
        error = 3

    def __init__(
            self,
            message_type: MessageType,
            time: int,
            sender: SimObject,
            message_id: str="",
            message: str="",
            context: List[SimObject]=list()):
        self.message_type = message_type  # type: MerlinMessage.MessageType
        self.time = time  # type: int
        self.sender = sender  # type: SimObject
        self.message_id = message_id  # type: str
        self.message = message  # type: str
        context_data = list()
        for so in context:
            d = dict()
            d['id'] = so.id
            d['type'] = so.__class__.__name__
            context_data.append(d)
        self.context = context_data  # type: List[Dict[str, Any]

    def __str__(self):
        return self.serialize()

    def serialize(self) -> Dict[str, Any]:
        output = dict()
        output['type'] = self.message_type.value
        output['time'] = self.time
        output['sender'] = \
            {
                'id': self.sender.id,
                'type': self.sender.__class__.__name__
            }
        output['message_id'] = self.message_id
        output['message'] = self.message
        output['context'] = self.context
        return output


class Ruleset:
    """
    A validation class that checks the integrity of a particular
     :class:`pymerlin.Simulation`

    This is an abstract class that must be overridden by a specific ruleset for
    your simulation. In other words, each simulation will have it's own
    sub-class of Ruleset.

    In a future version of pymerlin, it would be desirable to have the rulset
    be desribed by a configuration file that could be generated from another
    product or application or written by hand.
    """

    pass


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
        """
        :param Process process: the :py:class:`pymerlin.merlin.Process`,
            typically the ``self`` of the ``compute`` method.
        :param ProcessInput process_input: the input, which was found
            insufficient
        :param number input_value: the value found insufficient
        :param number required_input: the (minimum) value expected

        often used in :py:meth:`pymerlin.merlin.Process.compute`, the
        simulation does not stop, but the exceptions are caught and collected
        for reporting/introspection purposes.

        todo: what if two inputs are insufficient?
        """

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


class MerlinScriptException(MerlinException):

    def __init__(self, value):
        super(MerlinException, self).__init__(value)


class AddAttributesAction(Action):
    """
    Adds global attributes to the sim
    """

    def __init__(self, attributes):
        super(AddAttributesAction, self).__init__()
        self.attributes = attributes

    def execute(self, simulation):
        simulation.add_attributes(self.attributes)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '+',
            'operand_1':
                {
                    'type': 'Attribute',
                    'params': self.attributes,
                    'props': None
                },
            'operand_2': None
        }


class UnitTypeAction(Action):
    """
    Adds global unittypes to the sim
    """

    def __init__(self, unit_types):
        super(UnitTypeAction, self).__init__()
        self.unit_types = unit_types

    def execute(self, simulation):
        simulation.add_unit_types(self.unit_types)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '+',
            'operand_1':
                {
                    'type': 'UnitType',
                    'params': self.unit_types,
                    'props': None
                },
            'operand_2': None
        }


# Entity Actions

class RemoveEntityAction(Action):
    """ Removes an enity from the simulation"""

    def __init__(self, entity_id):
        super(RemoveEntityAction, self).__init__()
        self.entity_id = int(entity_id)

    def execute(self, simulation):
        entity_to_remove = simulation.get_entity_by_id(self.entity_id)
        if entity_to_remove:
            self._remove_entity(entity_to_remove)
        else:
            # try name lookup
            entity_to_remove = simulation.get_entity_by_name(self.entity_id)
            if entity_to_remove:
                self._remove_entity(entity_to_remove)

    def _remove_entity(self, ent):
        # remove output connections
        for o in ent.outputs:
            eps = o.get_endpoints()
            for e in eps:
                e[0].parent.inputs.remove(e[0])

        # remove input connections
        for i in ent.inputs:
            i.source.remove_input(i)

        if ent.parent is None:
            ent.sim.remove_entity(ent)
        else:
            ent.parent.remove_child(ent.id)

        for child in ent.get_children():
            self._remove_entity(child)
        ent.sim.remove_entity(ent)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '-',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.entity_id],
                    'props': None
                },
            'operand_2': None
        }


class AddEntityAction(Action):
    """Adds an entity to the Simulation"""
    def __init__(
            self,
            entity_name,
            attributes=list(),
            parent=None):

        super(AddEntityAction, self).__init__()
        self.attributes = attributes
        self.entity_name = entity_name
        self.parent = parent

    def execute(self, simulation):
        e = Entity(simulation, self.entity_name, set(self.attributes))
        if self.parent == simulation or self.parent is None:
            simulation.add_entity(e)
        else:
            self.parent.add_child(e)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '+',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.entity_name],
                    'props': None
                },
            'operand_2': None
        }

# Connection Actions


class RemoveConnectionAction(Action):
    """
    removes a connecton from an entity
    """

    def __init__(
            self,
            from_entity_id,
            to_entity_id,
            unit_type):

        super(RemoveConnectionAction, self).__init__()
        self.from_entity_id = int(from_entity_id)
        self.to_entity_id = int(to_entity_id)
        self.unit_type = unit_type

    def execute(self, simulation: Simulation):
        from_entity = simulation.get_entity_by_id(self.from_entity_id)
        to_entity = simulation.get_entity_by_id(self.to_entity_id)
        if from_entity and to_entity:
            simulation.disconnect_entities(
                from_entity,
                to_entity,
                self.unit_type)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '/',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.from_entity_id],
                    'props': None
                },
            'operand_2':
                {
                    'type': 'Entity',
                    'params': [self.to_entity_id, self.unit_type],
                    'props': None
                }
        }


class AddConnectionAction(Action):
    """
    Adds a connection from an entity output to entity input(s).
    """

    def __init__(
            self,
            output_entity_id,
            input_entity_id,
            unit_type,
            apportioning=2,
            additive_write=False):

        super(AddConnectionAction, self).__init__()

        self.unit_type = unit_type
        self.output_entity_id = int(output_entity_id)
        self.input_entity_id = int(input_entity_id)
        self.apportioning = \
            OutputConnector.ApportioningRules(int(apportioning))
        self.additive_write = bool(additive_write)

    def execute(self, simulation: Simulation):
        from_entity = simulation.get_entity_by_id(self.output_entity_id)
        to_entity = simulation.get_entity_by_id(self.input_entity_id)
        simulation.connect_entities(
            from_entity,
            to_entity,
            self.unit_type,
            input_additive_write=self.additive_write,
            apportioning=self.apportioning)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '>',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.output_entity_id, self.apportioning],
                    'props': None
                },
            'operand_2':
                {
                    'type': 'Entity',
                    'params': [
                        self.input_entity_id,
                        self.unit_type,
                        self.additive_write],
                    'props': None
                }
        }


# Process Actions

class RemoveProcessAction(Action):
    """
    Removes a process from an entity
    """

    def __init__(self, entity_id, process_id):
        super(RemoveProcessAction, self).__init__()
        self.process_id = process_id
        self.entity_id = entity_id

    def execute(self, simulation: Simulation):
        e = simulation.get_entity_by_id(self.entity_id)
        e.remove_process(self.process_id)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '-',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.entity_id],
                    'props': None
                },
            'operand_2':
                {
                    'type': 'Process',
                    'params': [self.process_id],
                    'props': None
                }
        }


class AddProcessAction(Action):
    """
    Adds a process to an entity
    """

    def __init__(
            self,
            entity_id,
            process_class,
            priority,
            process_params=None):

        super(AddProcessAction, self).__init__()
        self.entity_id = int(entity_id)
        self.process_class = \
            self.get_process_class_from_fullname(process_class)
        self.process_params = process_params
        if priority:
            self.priority = int(priority)
        else:
            self.priority = 100

    def get_process_class_from_fullname(self, the_name: str) -> type:
        """
        :param str the_name: name used to import the module and find the
           pymerlin.merlin.Process subclass
        :returns: the class (not the object!)

        This is the inverse of the :py:func:`.get_process_class_from_fullname`.
        """
        # split name into parts
        mod_path = the_name.split(".")[:-1]
        if len(mod_path):
            try:
                namespace = importlib.import_module(
                    ".".join(mod_path)).__dict__
            except ImportError:
                raise ValueError(
                    """module containing process class {0}
                    could not be imported""".format(the_name))
        else:
            # don't like this!
            namespace = globals()
        class_def = the_name.split(".")[-1]
        if class_def not in namespace:
            raise ValueError('process class %s not found' % the_name)

        # execute this function
        return namespace[class_def]

    def _get_fullname_from_process_class(self, the_class: type) -> str:
        if not issubclass(the_class, Process):
            raise TypeError("expecting sub class of pymerlin.merlin.Process")
        proc_classname = the_class.__name__
        proc_module = the_class.__module__
        return "{0}.{1}".format(proc_module, proc_classname)

    def execute(self, simulation):
        entity = simulation.get_entity_by_id(self.entity_id)
        if entity:
            entity.create_process(
                self.process_class,
                self.process_params,
                priority=self.priority)
        else:
            raise EntityNotFoundException(self.entity_id)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '+',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.entity_id],
                    'props': None
                },
            'operand_2':
                {
                    'type': 'Process',
                    'params': [
                        self._get_fullname_from_process_class(
                            self.process_class),
                        self.priority
                    ],
                    'props': self.process_params
                }
        }


class ModifyProcessPropertyAction(Action):

    def __init__(
            self,
            entity_id,
            property_id,
            value):
        super(ModifyProcessPropertyAction, self).__init__()
        self.entity_id = int(entity_id)
        self.property_id = int(property_id)
        self.value = float(value)

    def execute(self, simulation: Simulation):
        e = simulation.get_entity_by_id(self.entity_id)
        for p in e.get_processes():
            for prop in p.get_properties():
                if prop.id == self.property_id:
                    prop.set_value(self.value)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': ':=',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.entity_id],
                    'props': None
                },
            'operand_2':
                {
                    'type': 'Property',
                    'params': [self.property_id, self.value],
                    'props': None
                }
        }


class ParentEntityAction(Action):

    def __init__(
            self,
            child_entity_id,
            parent_entity_id
            ):
        super(ParentEntityAction, self).__init__()
        self.parent_entity_id = int(parent_entity_id)
        self.child_entity_id = int(child_entity_id)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '^',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.child_entity_id],
                    'props': None
                },
            'operand_2':
                {
                    'type': 'Entity',
                    'params': [self.parent_entity_id],
                    'props': None
                }
        }

    def execute(self, simulation: Simulation):
        parent_entity = simulation.get_entity_by_id(self.parent_entity_id)
        child_entity = simulation.get_entity_by_id(self.child_entity_id)
        if parent_entity and child_entity:
            simulation.parent_entity(parent_entity, child_entity)
