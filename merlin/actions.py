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
    Adds or removes a connecton from an entity
    """

# Process Actions

class ProcessAction(merlin.Action):
    """
    Adds or removes a process from an entity
    """
