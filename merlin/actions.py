"""
.. module:: actions
    :synopsis: Contains the action classes for creating merlin simulation
     objects.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""

from merlin import merlin
import importlib

# Exceptions


class SimNameNotFoundException(merlin.MerlinException):
    """
    foo
    """

    def __init__(self, value):
        super(SimReferenceNotFoundException, self).__init__(value)


class EntityNotFoundException(merlin.MerlinException):

    def __init__(self, value):
        super(EntityNotFoundException, self).__init__(value)

# Simulation Actions


class AddAttributesAction(merlin.Action):
    """
    Adds global attributes to the sim
    """

    def __init__(self, attributes):
        super(AddAttributesAction, self).__init__()
        self.attributes = attributes

    def execute(simulation):
        simulation.add_attributes(self.attributes)


class UnitTypeAction(merlin.Action):
    """
    Adds global unittypes to the sim
    """

    def __init__(self, unit_types):
        super(UnitTypeAction, self).__init__()
        self.unit_types = unit_types

    def execute(simulation):
        simulation.add_unit_types(self.unit_types)


# Entity Actions

class EntityAction(merlin.Action):
    """Adds or Removes an entity from the Simulation"""
    def __init__(
            self,
            entity_name,
            attributes=[],
            parent=None,
            add=True):

        super(CreateEntityAction, self).__init__()
        self.attributes = attributes
        self.entity_name = entity_name
        self.parent = parent
        self.add = add

    def execute(simulation):
        if self.add:
            e = Entity(simulation, entity_name, attributes)
            if parent:
                if parent in [ent.name for ent in simulation.entities()]:
                    for ent in simulation.entities():
                        if ent.name == parent:
                            ent.children.add(e)
                            e.parent = ent
                else:
                    raise SimNameNotFoundException(parent)
            else:
                simulation.add_entity(e)
        else:
            for ent in simulation.entities():
                if ent.name == entity_name:
                    entity_to_remove = ent
                    break

            _remove_entity(entity_to_remove)

    def _remove_entity(ent):
        connectors = ent.inputs.union(ent.outputs)
        for i in connectors:
            for ep in i.endpoints:
                ep.endpoints.remove(i)
                if not ep.endpoints:
                    if ep in ep.parent.inputs:
                        ep.parent.inputs.remove(ep)
                    else:
                        ep.parent.outputs.remove(ep)
        ent.parent.children.remove(ent)
        for child in ent.children:
            _remove_entity(child)
        simulation.remove_entity(ent)


# Connection Actions

class RemoveConnectionAction(merlin.Action):
    """
    removes a connecton from an entity
    """

    def __init__(self, entity_name, connector_id):
        super(RemoveConnectionAction, self).__init__()
        self.entity_name = entity_name
        self.connector_id = connector_id

    def execute(simulation):
        entity = simulation.get_entity_by_name(self.entity_name)
        con = entity.get_connector_by_id(self.connector_id)
        for ep in con.endpoints:
            ep.endpoints.remove(con)
            if not ep.endpoints:
                if ep in ep.parent.inputs:
                    ep.parent.inputs.remove(ep)
                else:
                    ep.parent.outputs.remove(ep)
        if con in entity.inputs:
            entity.inputs.remove(con)
        else:
            entity.outputs.remove(con)


class AddConnectionAction(merlin.Action):
    """
    Adds or removes a connecton from an entity output to entity input(s).
    """

    def __init__(
            self,
            unit_type,
            parent,
            endpoints,
            copy_value=False,
            additive_output=False):

        super(ConnectionAction, self).__init__()
        self.unit_type = unit_type
        self.parent = parent
        self.endpoints = endpoints
        self.copy_value = copy_value
        self.additive_output = additive_output
        self.add = add

    def execute(simulation):

        entity_list = set(self.endpoints)
        entity_list.add(self.parent)

        # Make sure all entites involved do actually exist in the simulation.
        for e in entity_list:
            if e not in [ent.name for ent in simulation.entities()]:
                raise SimNameNotFoundException(e)

        source_entity = simulation.get_entity_by_name(self.parent)
        endpoint_entities = (
            [simulation.get_entity_by_name(n) for n in self.endpoints])

        # Does an output of this unit_type currently exist?
        existing_output = source_entity.get_output_by_type(self.unit_type)

        if not existing_output:
            # create new output
            new_output = Connector(
                self.unit_type,
                existing_output,
                [],
                '',
                self.copy_value,
                self.additive_output
                )
            source_entity.outputs.add(new_output)

        output = existing_output or new_output

        new_input_cons = set()

        # add new endpoint connectors
        for ee in endpoint_entities:
            new_input = Connector(
                self.unit_type,
                ee,
                list(output),
                '',
                self.copy_value,
                self.additive_output
                )
            ee.inputs.add(new_input)
            new_input_cons.add(new_input)

        output.endpoints = new_input_cons

# Process Actions


class RemoveProcessAction(merlin.Action):
    """
    Removes a process from an entity
    """

    def __init__(self, entity_name, process_name):
        super(RemoveProcessAction, self)._init__()
        self.entity_name = entity_name
        self.process_name = process_name

    def execute(simulation):
        entity = simulation.get_entity_by_name(self.entity_name)
        if entity:
            entity.remove_process(self.process_name)
        else:
            raise EntityNotFoundException(self.entity_name)


class AddProcessAction(merlin.Action):
    """
    Adds a process to an entity
    """

    def __init__(
            self,
            entity_name,
            process_class,
            property_config,
            process_name='',
            process_module='__main__',
            priority=0):

        super(AddProcessAction, self).__init__()
        self.entity_name = entity_name
        self.process_module = process_module
        self.process_class = process_class
        self.property_config = property_config
        self.priority = priority
        self.process_name = process_name

    def execute(simulation):
        entity = simulation.get_entity_by_name(self.entity_name)
        if entity:
            module = importlib.import_module(self.process_module)
            PClass = getattr(module, self.process_class)
            p_instance = PClass(self.process_name)
            p_instance.priority = self.priority
            for prop in self.property_config.keys:
                setattr(p_instance, prop, self.property_config[prop])
            entity.add_process(p_instance)
        else:
            raise EntityNotFoundException(self.entity_name)
