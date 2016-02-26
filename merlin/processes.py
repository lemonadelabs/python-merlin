"""
.. module:: merlin
    :synopsis: Contains some core processes for use in Merlin simulations

.. moduleauthor:: Sam Win-Mason <sam@lemonadelabs.io>
"""

from merlin import merlin


class GeneratorProcess(merlin.Process):
    """
    Generates a fixed amount of a specific unittype per tick and sends them to
    a number of compatible outputs. The store of unittype can be infinite or
     fixed.

    Args:
        unittype (str): a valid unittype to produce

        unit_rate (float): the units generated per tick or per timedelta

        store (float): the maximum units that can be produced by this generator
        in the simulation. Set to -1 to allow infinite supply.

    Kwargs:
        name (str): An optional human-readible name for the generator instance
        restrict ([str]): a list of connection outputs to exclude.

        production_per_timedelta (timedelta): if this is not None, generator
          will produce ((time_interval/timedelta) * unit_rate). If None, it
          will produce unit_rate every tick.

    Returns:
        None

    Raises:
        None

    """
    def __init__(
            self,
            unittype,
            unit_rate,
            store,
            restrict=[],
            production_per_timedelta=None,
            name=''):

        super(GeneratorProcess, self).__init__(name)
        self.unittype = unittype
        self.unit_rate = unit_rate
        self.prod_per_t = production_per_timedelta
        self.store = store
        self.restrict = restrict

    def compute(self, current_time):
        unit = _get_unit()

        valid_outputs = filter(
            lambda x: x.id not in self.restrict, self.parent.outputs)

        valid_outputs = filter(
            lambda x: x.type == self.unittype, valid_outputs)

        unit_per_output = unit/len(valid_outputs)
        for o in self.parent.outputs:
            o.write(unit_per_output)

    def _get_unit(self, ):
        if self.prod_per_t:
            output = (
                self.parent.sim.current_time_interval.total_seconds() /
                self.prod_per_t.total_seconds()) * self.unit_rate
        else:
            output = self.unit_rate

        return output
