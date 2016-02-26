"""
.. module:: actions
    :synopsis: Contains the action classes for creating merlin simulation
     objects.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""

from merlin import merlin
import importlib


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

    def __init__(self, entity_name):
        super(RemoveEntityAction, self).__init__()
        self.entity_name = entity_name

    def execute(self, simulation):
        for ent in simulation.entities():
            if ent.name == self.entity_name:
                entity_to_remove = ent
                break

        if entity_to_remove:
            _remove_entity(entity_to_remove)

    def _remove_entity(self, ent):
        # remove output connections
        for o in ent.outputs:
            eps = o.get_endpoints()
            for e in eps:
                e[0].parent.inputs.remove(e[0])

        # remove input connections
        for i in ent.inputs:
            for eps in i.source.remove_input(i)

        ent.parent.children.remove(ent)
        for child in ent.children:
            _remove_entity(child)
        simulation.remove_entity(ent)


class AddEntityAction(merlin.Action):
    """Adds an entity to the Simulation"""
    def __init__(
            self,
            entity_name,
            attributes=[],
            parent=None):

        super(AddEntityAction, self).__init__()
        self.attributes = attributes
        self.entity_name = entity_name
        self.parent = parent

    def execute(self, simulation):
        e = Entity(simulation, entity_name, attributes)
        if parent:
            if parent in [ent.name for ent in simulation.entities()]:
                for ent in simulation.entities():
                    if ent.name == parent:
                        ent.children.add(e)
                        e.parent = ent
            else:
                raise merlin.SimNameNotFoundException(parent)

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
        entity = simulation.get_entity_by_name(self.source_entity_id)
        output_con = entity.get_connector_by_id(self.output_connector_id)
        if isinstance(output_con, OutputConnector):
            for ep in output_con.get_endpoints():
                if ep[0].id == input_connector_id:
                    ep[0].parent.inputs.remove(ep[0])
                    output_con.remove_input(ep[0])
        else:
            raise merlin.MerlinException(
                "{0} is not an output  connector id.".format(
                    self.output_connector_id))


class AddConnectionAction(merlin.Action):
    """
    Adds or removes a connecton from an entity output to entity input(s).
    """

    def __init__(
            self,
            unit_type,
            output_entity_id,
            input_entity_ids,
            copy_write=False,
            additive_write=False
            connector_name=''):

        super(AddConnectionAction, self).__init__()

        self.unit_type = unit_type
        self.output_entity_id = output_entity_id
        self.input_entity_ids = input_entity_ids
        self.copy_write = copy_write
        self.additive_write = additive_write
        self.connector_name = connector_name

    def execute(self, simulation):
        # Gather entities involved
        output_entity = simulation.get_entity_by_id(self.output_entity_id)

        input_entities = \
            [simulation.get_entity_by_id(eid)
                for eid in self.input_entity_ids]

        # Create the output connector
        output_con = OutputConnector(
            self.unit_type,
            output_entity,
            name='{0}_output'.format(self.connector_name),
            copy_write=self.copy_write)
        output_entity.outputs.add(output_con)

        # Create the input connector(s)
        input_cons = \
            [InputConnector(
                self.unit_type,
                p,
                name='{0}_input'.format(self.connector_name),
                output_con,
                additive_write=self.additive_write) for p in input_entities]

        # Connect output endpoint(s)
        for ic in input_cons:
            output_con.add_input(ic)


# Process Actions

class RemoveProcessAction(merlin.Action):
    """
    Removes a process from an entity
    """

    def __init__(self, entity_name, process_name):
        super(RemoveProcessAction, self)._init__()
        self.entity_name = entity_name
        self.process_name = process_name

    def execute(self, simulation):
        entity = simulation.get_entity_by_name(self.entity_name)
        if entity:
            entity.remove_process(self.process_name)
        else:
            raise merlin.EntityNotFoundException(self.entity_name)


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

    def execute(self, simulation):
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
            raise merlin.EntityNotFoundException(self.entity_name)
