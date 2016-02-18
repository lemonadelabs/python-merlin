"""
.. module:: actions
    :synopsis: Contains the action classes for creating merlin simulation objects.

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""

from merlin import merlin

# Exceptions

class SimNameNotFoundException(merlin.MerlinException):

    def __init__(self, value):
        super(SimReferenceNotFoundException, self).__init__(value)


# Simulation Actions

class SimAttributesAction(merlin.Action):
    """
    Adds or removes global attributes to the sim
    """

class UnitTypeAction(merlin.Action):
    """
    Adds or removes global unittypes to the sim
    """

# Entity Actions

class EntityAction(merlin.Action):
    """Adds or Removes an entity from the Simulation"""
    def __init__(
        self,
        entity_name,
        parent=None
        add=True
        attributes=[]
        ):

        super(CreateEntityAction, self).__init__()
        self.attributes = attributes
        self.entity_name = entity_name

    def execute(simulation):
        if self.add:
            e = Entity(simulation, entity_name, attributes)
            if parent:
                if parent in [ent.name for ent in simulation.entities]:
                    for ent in simulation.entities:
                        if ent.name == parent:
                            ent.children.append(e)
                            e.parent = ent
                else:
                    raise SimNameNotFoundException(parent)
            else:
                simulation.entities.append(e)
        else:
            for ent in simulation.entities:
                if ent.name = entity_name:
                    entity_to_remove = ent
                    break

            _remove_entity(entity_to_remove)


    def _remove_entity(ent):
        connectors = ent.inputs + ent.outputs
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
        simulation.entities.remove(ent)


# Connection Actions

class ConnectionAction(merlin.Action):
    """
    Adds or removes a connecton from an entity output to entity input(s).
    """

    def __init__(
        self,
        unit_type,
        parent,
        endpoints,
        add=True
        copy_value=False
        additive_output=False):

        super(ConnectionAction, self).__init__()
        self.unit_type = unit_type
        self.parent = parent
        self.endpoints = endpoints
        self.copy_value = copy_value
        self.additive_output = additive_output
        self.add = add

    def execute(simulation):

        entity_list = list(self.endpoints)
        entity_list.append(self.parent)

        # Make sure all entites involved do actually exist in the simulation.
        for e in entity_list:
            if e not in [ent.name for ent in simulation.entities]:
                raise SimNameNotFoundException(e)

        source_entity = simulation.get_entity_by_name(self.parent)
        endpoint_entities = [simulation.get_entity_by_name(n) for n in self.endpoints]

        # Does an output of this unit_type currently exist?
        existing_output = source_entity.get_output_by_type(self.unit_type)

        if not existing_output:
            # create new output
            new_output = Connector(
                self.unit_type,
                existing_output,
                []
                ''
                self.copy_value
                self.additive_output
                )
            source_entity.outputs.append(new_output)

        output = existing_output or new_output

        new_input_cons = list()

        # add new endpoint connectors
        for ee in endpoint_entities:
            new_input = Connector(
                self.unit_type,
                ee,
                list(output)
                ''
                self.copy_value
                self.additive_output
                )
            ee.inputs.append(new_input)
            new_input_cons.append(new_input)

        output.endpoints = new_input_cons

# Process Actions

class ProcessAction(merlin.Action):
    """
    Adds or removes a process from an entity
    """
