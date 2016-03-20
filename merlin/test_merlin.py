import pytest
import numpy.testing as npt
from datetime import datetime
from merlin import merlin
from merlin import actions

# Test Processes


# module fixtures

@pytest.fixture()
def sim():
    """ Returns a simulation object """
    return merlin.Simulation(
        ruleset=None,
        config=[],
        outputs=set(),
        name='test_sim')


@pytest.fixture()
def process():
    return merlin.Process(name='test_process')


@pytest.fixture()
def entity():
    """Returns a vanilla entity object"""
    return merlin.Entity(name='test_entity')


@pytest.fixture()
def simple_entity_graph():
    """Creates two Entities connected by one connector"""
    source = merlin.Entity(name='source')
    sink = merlin.Entity(name='sink')
    in_con = merlin.InputConnector(
        'unit_type',
        sink,
        name='input')
    out_con = merlin.OutputConnector(
        'unit_type',
        source,
        name='output')
    in_con.source = out_con
    out_con.add_input(in_con, bias=1.0)
    source.outputs.add(out_con)
    sink.inputs.add(in_con)
    return (source, sink, out_con, in_con)


@pytest.fixture()
def simple_branching_output_graph():
    """
    Creates an entity with a single output that connects to two sink entities
    """
    source = merlin.Entity(name='source')
    sink1 = merlin.Entity(name='sink1')
    sink2 = merlin.Entity(name='sink2')

    in_con1 = merlin.InputConnector(
        'unit_type',
        sink1,
        name='input')
    in_con2 = merlin.InputConnector(
        'unit_type',
        sink2,
        name='input')
    out_con = merlin.OutputConnector(
        'unit_type',
        source,
        name='output')

    in_con1.source = out_con
    in_con2.source = out_con
    out_con.add_input(in_con1)
    out_con.add_input(in_con2)

    source.outputs.add(out_con)
    sink1.inputs.add(in_con1)
    sink2.inputs.add(in_con2)
    return (source, sink1, sink2, out_con, in_con1, in_con2)


class TestSimulation:

    def test_add_attribute(self, sim):
        sim.add_attributes(['attr'])
        assert sim.is_attribute('attr')

    def test_add_unit_type(self, sim):
        sim.add_unit_types(['unit_type'])
        assert sim.is_unit_type('unit_type')

    def test_add_entity(self, sim, entity):
        sim.add_entity(entity)
        assert (entity in sim.get_entities())

    def test_remove_entity(self, sim, entity):
        sim.add_entity(entity)
        sim.remove_entity(entity)
        assert entity not in sim.get_entities()

    def test_get_entity_by_name(self, sim, entity):
        sim.add_entity(entity)
        e = sim.get_entity_by_name('test_entity')
        assert e == entity

    def test_get_entity_by_id(self, sim, entity):
        sim.add_entity(entity)
        e = sim.get_entity_by_id(entity.id)
        assert e == entity


class TestEntity:

    def test_add_process(self, entity, process):
        entity.add_process(process)
        p = entity.get_process_by_name('test_process')
        assert p == process

    def test_get_process_by_id(self, entity, process):
        entity.add_process(process)
        p = entity.get_process_by_id(process.id)
        assert p == process

    def test_remove_process(self, entity, process):
        entity.add_process(process)
        entity.remove_process(process.id)
        p = entity.get_process_by_id(process.id)
        assert p is None

    def test_get_connector_by_id(self, simple_entity_graph):
        seg = simple_entity_graph
        c = seg[0].get_connector_by_id(seg[2].id)
        assert c == seg[2]

    def test_get_output_by_type(self, simple_entity_graph):
        seg = simple_entity_graph
        o = seg[0].get_output_by_type('unit_type')
        assert seg[2] in o

    def test_get_input_by_type(self, simple_entity_graph):
        seg = simple_entity_graph
        i = seg[1].get_input_by_type('unit_type')
        assert seg[3] in i


class TestOutputConnector:

    def test_write(self, simple_entity_graph):
        seg = simple_entity_graph
        seg[0].current_time = datetime.now()
        seg[2].write(100.0)
        assert seg[3].value == 100.0
        assert seg[3].time == seg[2].time

    def test_get_endpoints(self, simple_entity_graph):
        seg = simple_entity_graph
        assert seg[2].get_endpoints() == [(seg[3], 1.0)]

    def test_remove_input(self, simple_entity_graph):
        seg = simple_entity_graph
        seg[2].remove_input(seg[3])
        assert seg[2].get_endpoints() == []
        assert seg[2] not in seg[0].outputs

    def test_set_endpoint_bias(self, simple_branching_output_graph):
        g = simple_branching_output_graph
        g[3].set_endpoint_bias(g[4], 0.8)
        eps = g[3].get_endpoints()
        for e in eps:
            if e[0] == g[4]:
                npt.assert_almost_equal(e[1], 0.8)
            else:
                npt.assert_almost_equal(e[1], 0.2)

    def test_set_endpoint_biases(self, simple_branching_output_graph):
        g = simple_branching_output_graph
        new_epb = [(g[4], 0.9), (g[5], 0.1)]
        g[3].set_endpoint_biases(new_epb)
        eps = g[3].get_endpoints()
        for e in eps:
            if e[0] == g[4]:
                npt.assert_almost_equal(e[1], 0.9)
            else:
                npt.assert_almost_equal(e[1], 0.1)


class TestCoreActions:

    def test_add_attributes_action(self, sim):
        a = actions.AddAttributesAction(['attr'])
        a.execute(sim)
        assert sim.is_attribute('attr')

    def test_add_unit_type_action(self, sim):
        a = actions.UnitTypeAction(['unit_type'])
        a.execute(sim)
        assert sim.is_unit_type('unit_type')

    def test_remove_entity_action(self, sim, simple_entity_graph):
        seg = simple_entity_graph
        sim.add_entity(seg[0])
        sim.add_entity(seg[1])
        a = actions.RemoveEntityAction(seg[1].id)
        a.execute(sim)
        assert seg[1] not in sim.get_entities()
        assert seg[2] not in seg[0].outputs

    def test_add_entity_action(self, sim, simple_entity_graph):
        seg = simple_entity_graph
        e1a = actions.AddEntityAction(
            'new_entity1', parent=seg[0])
        e2a = actions.AddEntityAction(
            'new_entity2', attributes=[], parent=None)
        e1a.execute(sim)
        e2a.execute(sim)
        assert seg[0].get_child_by_name('new_entity1') is not None
        assert sim.get_entity_by_name('new_entity2') is not None

    def test_remove_connection_action(self, sim, simple_entity_graph):
        seg = simple_entity_graph
        sim.add_entity(seg[0])
        sim.add_entity(seg[1])
        rca = actions.RemoveConnectionAction(seg[0].id, seg[3].id, seg[2].id)
        rca.execute(sim)
        assert seg[2] not in seg[0].outputs
        assert seg[3] not in seg[1].inputs

    def test_add_connection_action(self, sim):
        source = merlin.Entity(simulation=sim, name='source', attributes=set())
        sink = merlin.Entity(simulation=sim, name='sink', attributes=set())
        sim.add_entity(source)
        sim.add_entity(sink)
        aca = actions.AddConnectionAction(
            'new_unit_type',
            source.id,
            [sink.id],
            copy_write=True,
            additive_write=True,
            connector_name='new_con')
        aca.execute(sim)

        output_con = list(source.get_output_by_type('new_unit_type'))[0]
        input_con = list(sink.get_input_by_type('new_unit_type'))[0]
        assert output_con is not None
        assert input_con is not None
        assert output_con.parent == source
        assert input_con.parent == sink
        assert len(source.outputs) == 1
        assert len(source.inputs) == 0
        assert len(sink.inputs) == 1
        assert len(sink.outputs) == 0
        assert input_con in [ep[0] for ep in output_con.get_endpoints()]

        # TODO Create tests for process actions.
