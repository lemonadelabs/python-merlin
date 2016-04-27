"""
.. module:: actions
    :synopsis: Contains the action classes for creating merlin simulation
     objects.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""
import importlib
from typing import List, Dict, Any
from pymerlin import merlin
import json


def create_from_dict(actions: List[Dict[str, Any]]) -> List[merlin.Action]:
    output = list()
    for a in actions:
        output.append(_generate_action(a))
    return output


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
        l = l.strip()
        tokens = _lex_tokens(l)
        # print("lexer result = {0}".format(tokens))
        output.append(_generate_action(_parse_action(tokens)))
    return output


def create_from_json(json_string: str) -> List[merlin.Action]:
    """
    Parses a list of actions from a json serilaised string
    :param str json_string:
    """
    output = list()
    j = json.loads(json_string)
    for a in j:
        output.append(_generate_action(a))
    return output


def _lex_tokens(line: str) -> List[str]:
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
        raise merlin.MerlinScriptException(
            "Parse error. Operator not found in line: {0}".format(line))

    if not parts[0] and parts[1] and parts[2]:
        # print("param part: {0}".format(parts[2]))
        operand_1_tokens = _lex_operand(parts[2])
        # print("lex result: {0}".format(operand_1_tokens))
        return [parts[1]] + operand_1_tokens
    else:
        operand_1_tokens = _lex_operand(parts[0])
        operand_2_tokens = _lex_operand(parts[2])
        return operand_1_tokens + [parts[1]] + operand_2_tokens


def _lex_operand(op_string: str) -> List[str]:
    output = list()
    if not op_string:
        return output
    op_string = op_string.strip()
    output.append(op_string.partition(' ')[0])
    arguments = op_string.partition(' ')[2]
    if arguments == op_string:
        raise merlin.MerlinScriptException(
            "Parse error. Expected type in operand: {0}".format(op_string)
        )
    output += [s.strip() for s in arguments.split(',')]
    return output


def _generate_action(a: Dict[str, Any]) -> merlin.Action:
    # work out type of action based on ast
    # Unary expressions
    if a['operand_2'] is None:
        if len(a['operand_1']['params']) == 0:
            raise merlin.MerlinScriptException(
                        "Invalid parameter size")

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

            elif a['operand_1']['type'] == 'UnitType':
                raise merlin.MerlinScriptException(
                    "Operation RemoveUnitType not supported")
        else:
            raise merlin.MerlinScriptException(
                "Invalid operator for unary expression, must be + or -")
    else:

        if len(a['operand_1']['params']) == 0 \
                or len(a['operand_2']['params']) == 0:
            raise merlin.MerlinScriptException(
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

        raise merlin.MerlinScriptException("No Process match!")


def _parse_action(tokens) -> Dict[str, Any]:
    op = _parse_op(tokens[0])
    if op:
        # this is a single operand command
        tokens = tokens[1:]
        # now look for a type
        type1 = _parse_type(tokens[0])
        if type1:
            # parse type 1 params
            type1_params = _parse_params(tokens[1:])
            return {
                'op': op,
                'operand_1': {
                    'type': type1,
                    'params': type1_params,
                    'props': None
                    },
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
            type1_props = _parse_props(tokens)
            tokens = tokens[len(type1_props):]
            op = _parse_op(tokens[0])
            if op:
                tokens = tokens[1:]
                type2 = _parse_type(tokens[0])
                if type2:
                    tokens = tokens[1:]
                    type2_params = _parse_params(tokens)
                    tokens = tokens[len(type2_params):]
                    type2_props = _parse_props(tokens)
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


def _parse_params(tokens: List[str]) -> List[str]:
    params = list()
    for t in tokens:
        if not t:
            raise merlin.MerlinScriptException(
                "Invalid param {0}".format(t))
        tt = _parse_type(t)
        to = _parse_op(t)
        if ('=' in t) and (':' in t):
            return params
        if tt or to:
            return params
        else:
            params.append(t)
    return params


def _parse_props(tokens: List[str]) -> Dict[str, Any]:
    # TODO: fix this function
    if not tokens:
        return None
    props = dict()
    for t in tokens:
        tt = _parse_type(t)
        to = _parse_op(t)
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
                        raise merlin.MerlinScriptException(
                            "invalid type {0}".format(val_type))
                    props[label] = val
    return props


def _parse_type(token):
    if token in ['Entity', 'Attribute', 'UnitType', 'Process', 'Property']:
        return token
    else:
        return None


def _parse_op(token):
    if token in ['+', '-', '>', '/', ':=', '^']:
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


class UnitTypeAction(merlin.Action):
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

class RemoveEntityAction(merlin.Action):
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


class RemoveConnectionAction(merlin.Action):
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

    def execute(self, simulation: merlin.Simulation):
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


class AddConnectionAction(merlin.Action):
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
            merlin.OutputConnector.ApportioningRules(int(apportioning))
        self.additive_write = bool(additive_write)

    def execute(self, simulation: merlin.Simulation):
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

class RemoveProcessAction(merlin.Action):
    """
    Removes a process from an entity
    """

    def __init__(self, entity_id, process_id):
        super(RemoveProcessAction, self).__init__()
        self.process_id = process_id
        self.entity_id = entity_id

    def execute(self, simulation: merlin.Simulation):
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


class AddProcessAction(merlin.Action):
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
           merlin.Process subclass
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
        if not issubclass(the_class, merlin.Process):
            raise TypeError("expecting sub class of merlin.Process")
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
            raise merlin.EntityNotFoundException(self.entity_id)

    def serialize(self) -> Dict[str, Any]:
        return {
            'op': '+',
            'operand_1':
                {
                    'type': 'Entity',
                    'params': [self.entity_id]
                },
            'operand_2':
                {
                    'type': 'Process',
                    'params': [
                        self._get_fullname_from_process_class(
                            self.process_class),
                        self.priority
                    ],
                    'data': self.process_params
                }
        }


class ModifyProcessPropertyAction(merlin.Action):

    def __init__(
            self,
            entity_id,
            property_id,
            value):
        super(ModifyProcessPropertyAction, self).__init__()
        self.entity_id = int(entity_id)
        self.property_id = int(property_id)
        self.value = float(value)

    def execute(self, simulation: merlin.Simulation):
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


class ParentEntityAction(merlin.Action):

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

    def execute(self, simulation: merlin.Simulation):
        parent_entity = simulation.get_entity_by_id(self.parent_entity_id)
        child_entity = simulation.get_entity_by_id(self.child_entity_id)
        if parent_entity and child_entity:
            simulation.parent_entity(parent_entity, child_entity)
