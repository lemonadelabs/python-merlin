"""
.. module:: actions
    :synopsis: Contains the action classes for creating merlin simulation
     objects.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""
from typing import List, Dict, Any
from pymerlin import merlin
import importlib


def create(script: str) -> List[merlin.Action]:
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
        tokens = l.split()
        output.append(_generate_action(_parse_action(tokens)))
    return output


def _generate_action(a: Dict[str, Any]) -> merlin.Action:
    # work out type of action based on ast
    # Unary expressions
    if a['operand_2'] is None:
        if a['op'] == '+':

            if a['operand_1']['type'] == 'Attribute':
                try:
                    return AddAttributesAction(
                        [str(p) for p in a['operand_1']['params']])
                except Exception:
                    raise merlin.MerlinScriptException(
                        "Invalid parameters for AddAttributeAction")

            elif a['operand_1']['type'] == 'Entity':
                try:
                    return AddEntityAction(
                        a['operand_1']['params'][0],
                        attributes=a['operand_1']['params'][1:])
                except Exception:
                    raise merlin.MerlinScriptException(
                        "Invalid parameters for AddEntityAction")

            elif a['operand_1']['type'] == 'Process':
                try:
                    # convert priority to a number
                    if len(a['operand_1']['params']) >= 3:
                        a['operand_1']['params'][2] = \
                            int(a['operand_1']['params'][2])
                    return AddProcessAction(*a['operand_1']['params'])
                except:
                    raise merlin.MerlinScriptException(
                        "Invalid parameters for AddEntityAction")

            elif a['operand_1']['type'] == 'UnitType':
                try:
                    return UnitTypeAction(
                        [str(p) for p in a['operand_1']['params']])
                except Exception:
                    raise merlin.MerlinScriptException(
                        "Invalid parameters for AddUnitTypeAction")
        elif a['op'] == '-':

            if a['operand_1']['type'] == 'Attribute':
                raise merlin.MerlinScriptException(
                    "Operation RemoveAttribute not supported")

            elif a['operand_1']['type'] == 'Entity':
                try:
                    return RemoveEntityAction(a['operand_1']['params'][0])
                except Exception:
                    raise merlin.MerlinScriptException(
                        "Invalid parameters for RemoveEntityAction")

            elif a['operand_1']['type'] == 'Process':
                try:
                    return RemoveProcessAction(*a['operand_1']['params'])
                except Exception:
                    raise merlin.MerlinScriptException(
                        "Invalid parameters for RemoveProcessAction")

            elif a['operand_1']['type'] == 'UnitType':
                raise merlin.MerlinScriptException(
                    "Operation RemoveUnitType not supported")
        else:
            raise merlin.MerlinScriptException(
                "Invalid operator for unary expression, must be + or -")
    else:
        # Binary expressions
        if a['op'] in ['/', '^', '>']:

            if a['op'] == '/':
                # Disconnect operator
                return RemoveConnectionAction(
                    *(a['operand_1']['params'] + a['operand_2']['params']))
                pass

            elif a['op'] == '^':
                raise NotImplementedError
                pass

            elif a['op'] == '>':
                return AddConnectionAction(
                    *(a['operand_1']['params'] + a['operand_2']['params']))
                pass
        else:
            raise merlin.MerlinScriptException(
                "Invalid operator for binary expression, must be /, ^ or >")


def _parse_action(tokens) -> Dict[str, Any]:
    op = _parse_op(tokens[0])
    if op:
        # this is a single operand command
        tokens = tokens[1:]
        # now look for a type
        type1 = _parse_type(tokens[0])
        if type1:
            # parse type 1 params
            type1_params = tokens
            return {
                'op': op,
                'operand_1': {
                    'type': type1,
                    'params': type1_params},
                'operand_2': None}
        else:
            raise merlin.MerlinScriptException(
                "Syntax Error: {0} is not a valid type".format(tokens[0]))
    else:
        type1 = _parse_type(tokens[0])
        if type1:
            tokens = tokens[1:]
            type1_params = _parse_params(tokens)
            tokens = tokens[len(type1_params):]
            op = _parse_op(tokens[0])
            if op:
                tokens = tokens[1:]
                type2 = _parse_type(tokens[0])
                if type2:
                    tokens = tokens[1:]
                    type2_params = _parse_params(tokens)
                    return {
                        'op': op,
                        'operand_1': {
                            'type': type1,
                            'params': type1_params},
                        'operand_2': {
                            'type': type2,
                            'params': type2_params}}
                else:
                    raise merlin.MerlinScriptException(
                        "Syntax Error: {0} is not a valid type".format(
                            tokens[0]))
            else:
                raise merlin.MerlinScriptException(
                    "Syntax Error: Expected an operator, got {0}".format(
                        tokens[0]))
        else:
            raise merlin.MerlinScriptException(
                "Syntax Error: {0} is not a valid type".format(
                    tokens[0]))


def _parse_params(tokens):
    params = list()
    for t in tokens:
        tt = _parse_type(t)
        to = _parse_op(t)
        if tt or to:
            return params
        else:
            params.append(t)
    return params


def _parse_type(token):
    if token in ['Entity', 'Attribute', 'UnitType', 'Process']:
        return token
    else:
        return None


def _parse_op(token):
    if token in ['+', '-', '>', '/']:
        return token
    else:
        return None

# Simulation Actions


class AddAttributesAction(merlin.Action):
    """
    Adds global attributes to the sim
    """

    def __init__(self, attributes):
        super(AddAttributesAction, self).__init__()
        self.attributes = attributes

    def execute(self, simulation):
        simulation.add_attributes(self.attributes)


class UnitTypeAction(merlin.Action):
    """
    Adds global unittypes to the sim
    """

    def __init__(self, unit_types):
        super(UnitTypeAction, self).__init__()
        self.unit_types = unit_types

    def execute(self, simulation):
        simulation.add_unit_types(self.unit_types)


# Entity Actions

class RemoveEntityAction(merlin.Action):
    """ Removes an enity from the simulation"""

    def __init__(self, entity_id):
        super(RemoveEntityAction, self).__init__()
        self.entity_id = entity_id

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


class AddEntityAction(merlin.Action):
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
        e = merlin.Entity(simulation, self.entity_name, self.attributes)
        if self.parent == simulation or self.parent is None:
            simulation.add_entity(e)
        else:
            self.parent.add_child(e)


# Connection Actions


class RemoveConnectionAction(merlin.Action):
    """
    removes a connecton from an entity
    """

    def __init__(
            self,
            source_entity_id,
            input_connector_id,
            output_connector_id):

        super(RemoveConnectionAction, self).__init__()
        self.source_entity_id = source_entity_id
        self.input_connector_id = input_connector_id
        self.output_connector_id = output_connector_id

    def execute(self, simulation):
        entity = simulation.get_entity_by_id(self.source_entity_id)
        output_con = entity.get_connector_by_id(self.output_connector_id)
        if isinstance(output_con, merlin.OutputConnector):
            for ep in output_con.get_endpoints():
                if ep[0].id == self.input_connector_id:
                    ep[0].parent.inputs.remove(ep[0])
                    output_con.remove_input(ep[0])
        else:
            raise merlin.MerlinException(
                "{0} is not an output  connector id.".format(
                    self.output_connector_id))


class AddConnectionAction(merlin.Action):
    """
    Adds a connection from an entity output to entity input(s).
    """

    def __init__(
            self,
            unit_type,
            output_entity_id,
            input_entity_ids,
            apportioning=None,
            additive_write=False,
            connector_name=''):

        super(AddConnectionAction, self).__init__()

        self.unit_type = unit_type
        self.output_entity_id = output_entity_id
        self.input_entity_ids = input_entity_ids
        self.apportioning = apportioning
        self.additive_write = additive_write
        self.connector_name = connector_name

    def execute(self, simulation):
        # Gather entities involved
        output_entity = simulation.get_entity_by_id(self.output_entity_id)

        input_entities = \
            [simulation.get_entity_by_id(eid)
                for eid in self.input_entity_ids]

        # Create the output connector
        output_con = merlin.OutputConnector(
            self.unit_type,
            output_entity,
            name='{0}_output'.format(self.connector_name),
            apportioning=self.apportioning)
        output_entity.outputs.add(output_con)

        # Create the input connector(s)
        input_cons = \
            [merlin.InputConnector(
                self.unit_type,
                p,
                name='{0}_input'.format(self.connector_name),
                source=output_con,
                additive_write=self.additive_write) for p in input_entities]

        # Connect output endpoint(s)
        for ic in input_cons:
            ic.parent.add_input(ic)
            output_con.add_input(ic)


# Process Actions

class RemoveProcessAction(merlin.Action):
    """
    Removes a process from an entity
    """

    def __init__(self, entity_id, process_id):
        super(RemoveProcessAction, self).__init__()
        self.entity_id = entity_id
        self.process_id = process_id

    def execute(self, simulation):
        entity = simulation.get_entity_by_id(self.entity_id)
        if entity:
            entity.remove_process(self.process_id)
        else:
            raise merlin.EntityNotFoundException(self.entity_id)


class AddProcessAction(merlin.Action):
    """
    Adds a process to an entity
    """

    def __init__(
            self,
            entity_name,
            process_class,
            priority=100,
            process_name='',
            process_module='__main__'):

        super(AddProcessAction, self).__init__()
        self.entity_name = entity_name
        self.process_module = process_module
        self.process_class = process_class
        self.priority = priority
        self.process_name = process_name

    def execute(self, simulation):
        entity = simulation.get_entity_by_name(self.entity_name)
        if entity:
            module = importlib.import_module(self.process_module)
            p_class = getattr(module, self.process_class)
            p_instance = p_class(self.process_name)
            p_instance.priority = self.priority
            entity.add_process(p_instance)
        else:
            raise merlin.EntityNotFoundException(self.entity_name)
