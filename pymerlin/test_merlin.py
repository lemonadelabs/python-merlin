import pytest
import numpy.testing as npt
from datetime import datetime
from pymerlin import merlin
from pymerlin import actions

from pymerlin.processes import (BudgetProcess,
                                CallCenterStaffProcess,
                                BuildingMaintainenceProcess)


@pytest.fixture()
def computation_test_harness(sim) -> merlin.Simulation:

    # Configure sim properties
    sim.set_time_span(10)
    sim.add_attributes(['budget', 'capability', 'fixed_asset'])
    sim.add_unit_types(['$', 'desks', 'requests_handled'])

    sim_output = merlin.Output('requests_handled', name='requests handled')
    sim.outputs.add(sim_output)

    # Create Entities
    e_budget = merlin.Entity(
        name='Budget',
        attributes={'budget'})

    e_call_center = merlin.Entity(
        name='call center',
        attributes={'capability'})

    e_office = merlin.Entity(
        name='office building',
        attributes={'capability', 'fixed_asset'})

    sim.add_entities([e_budget, e_call_center, e_office])
    sim.set_source_entities([e_budget])

    # Create Entity Connections
    # Budget connections
    sim.connect_entities(e_budget, e_call_center, '$')
    sim.connect_entities(e_budget, e_office, '$')

    # Call center connections
    sim.connect_output(e_call_center, sim_output)

    # Office connections
    sim.connect_entities(e_office, e_call_center, 'desks')

    # Add entity processes
    p_budget = BudgetProcess(name='Budget')
    p_staff = CallCenterStaffProcess(name='Call Center Staff')
    p_building = BuildingMaintainenceProcess(name='Building Maintenance')
    e_budget.add_process(p_budget)
    e_call_center.add_process(p_staff)
    e_office.add_process(p_building)
    return sim


@pytest.fixture()
def sim() -> merlin.Simulation:
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
    out_con.add_input(in_con)
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


class TestIntegration:

    def test_output(self, computation_test_harness):
        sim = computation_test_harness
        sim.run()
        result = list(sim.outputs)[0].result
        expected_result = \
            [20.0, 40.0, 60.0, 80.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]

        for i in range(0, len(result)):
            npt.assert_almost_equal(result[i], expected_result[i])

    def test_input_requirement_exception(self, computation_test_harness):
        sim = computation_test_harness
        ccs = sim.get_process_by_name('Call Center Staff')
        salary_prop = ccs.get_prop('staff salary')
        salary_prop.set_value(6.00)
        sim.run()
        errors = sim.get_last_run_errors()
        first = errors[0]
        assert len(errors) == 10
        assert first.process == ccs
        assert first.process_input == ccs.inputs['$']
        assert first.input_value == 500.0
        assert first.value == 600.0


class TestSimulation:

    def test_telemetry_output(self, computation_test_harness):
        sim = computation_test_harness # type: merlin.Simulation
        sim.run()
        tel = sim.get_sim_telemetry()

        for to in tel:
            if 'result' in to['data']:
                assert len(to['data']['result']) == sim.num_steps
            if 'value' in to['data']:
                assert len(to['data']['value']) == sim.num_steps

    def test_source_entities(self, computation_test_harness):
        sim = computation_test_harness
        e = sim.get_entity_by_name('Budget')
        assert len(sim.source_entities) == 1
        assert e in sim.source_entities

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

    def test_get_process_by_id(self, computation_test_harness):
        sim = computation_test_harness
        bn = sim.get_process_by_name('Budget')
        bi = sim.get_process_by_id(bn.id)
        assert bi

    def test_get_process_value_by_name(self, computation_test_harness):
        sim = computation_test_harness
        bn = sim.get_process_by_name('Budget')
        val = bn.get_prop_value("amount")
        assert val

    def test_get_process_by_name(self, computation_test_harness):
        sim = computation_test_harness
        b = sim.get_process_by_name('Budget')
        assert b

    def test_connect_entities(self, sim):
        e1 = merlin.Entity(name='e1')
        e2 = merlin.Entity(name='e2')
        sim.add_entity(e1)
        sim.add_entity(e2)
        sim.connect_entities(e1, e2, 'unit_type')
        o_con = e1.get_output_by_type('unit_type')
        i_con = e2.get_input_by_type('unit_type')
        assert e1.get_input_by_type('unit_type') is None
        assert e2.get_output_by_type('unit_type') is None
        assert o_con
        assert i_con
        assert o_con.type == 'unit_type'
        assert i_con.type == 'unit_type'
        assert len(o_con.get_endpoints()) == 1
        assert i_con.source == o_con

    def test_disconnect_entities(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e1 = sim.get_entity_by_name("Budget")
        e2 = sim.get_entity_by_name("office building")
        assert len(e1.get_output_by_type('$').get_endpoints()) == 2
        assert len(e2.inputs) == 1
        sim.disconnect_entities(e1, e2, '$')
        assert len(e1.get_output_by_type('$').get_endpoints()) == 1
        assert len(e2.inputs) == 0


    def test_add_output(self, sim):
        o = merlin.Output('unit_type', name='output')
        sim.add_output(o)
        assert len(sim.outputs) == 1
        assert o.sim == sim

    def test_connect_output(self, sim):
        e1 = merlin.Entity(name='e1')
        o = merlin.Output('unit_type', name='output')
        sim.add_entity(e1)
        sim.add_output(o)
        sim.connect_output(e1, o)
        o_con = e1.get_output_by_type('unit_type')
        i_con = list(o.inputs)[0]
        assert o_con
        assert i_con


class TestEntity:

    def test_add_process(self, entity, process):
        entity.add_process(process)
        p = entity.get_process_by_name('test_process')
        assert p == process

    def test_get_process_by_id(self, entity, process):
        entity.add_process(process)
        p = entity.get_process_by_id(process.id)
        assert p == process

    def test_get_processes(self, entity, process):
        entity.add_process(process)
        ps = entity.get_processes()
        assert len(ps) == 1
        assert ps[0].name == 'test_process'

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
        assert seg[2] == o

    def test_get_input_by_type(self, simple_entity_graph):
        seg = simple_entity_graph
        i = seg[1].get_input_by_type('unit_type')
        assert seg[3] == i


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


class TestScenarios:

    def test_simple_scenario(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = merlin.Event.create(1, '+ Attribute foo bar baz')
        s = merlin.Scenario({e})
        assert sim.is_attribute('foo') == False
        assert sim.is_attribute('bar') == False
        assert sim.is_attribute('baz') == False
        sim.run(scenarios=[s])
        assert sim.is_attribute('foo')
        assert sim.is_attribute('bar')
        assert sim.is_attribute('baz')

    def test_multiple_action_scenario(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = merlin.Event.create(
            1,
            """
            + Attribute foo
            + UnitType cheese
            """)
        s = merlin.Scenario({e})
        assert sim.is_attribute('foo') == False
        assert sim.is_unit_type('cheese') == False
        sim.run(scenarios=[s])
        assert sim.is_attribute('foo') == True
        assert sim.is_unit_type('cheese') == True

    def test_event_time(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = merlin.Event.create(5, '+ Attribute foo')
        s = merlin.Scenario({e})
        assert sim.is_attribute('foo') == False
        sim.run(end=4, scenarios=[s])
        assert sim.is_attribute('foo') == False
        sim.run(end=6, scenarios=[s])
        assert sim.is_attribute('foo') == True


    def test_multiple_scenarios(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = merlin.Event.create(5, '+ Attribute foo')
        e2 = merlin.Event.create(7, '+ UnitType bar')
        s1 = merlin.Scenario({e})
        s2 = merlin.Scenario({e2})
        assert sim.is_attribute('foo') == False
        assert sim.is_unit_type('bar') == False
        sim.run(scenarios=[s1, s2])
        assert sim.is_attribute('foo') == True
        assert sim.is_unit_type('bar') == True


class TestEvents:

    def test_add_json_events(self, simple_entity_graph):
        e = merlin.Event.create(
            1,
            """
            [
                {
                    \"op\" : \"+\",
                    \"operand_1\" : {
                        \"type\" : \"Attribute\",
                        \"params\" : \"foo\"
                    },
                    \"operand_2\" : null
                },

                {
                    \"op\" : \"+\",
                    \"operand_1\" : {
                        \"type\" : \"UnitType\",
                        \"params\" : \"bar\"
                    },
                    \"operand_2\" : null
                }
            ]
            """)
        assert len(e.actions) == 2
        assert isinstance(e.actions[0], actions.AddAttributesAction)
        assert isinstance(e.actions[1], actions.UnitTypeAction)


    def test_add_attribute_event(self):
        e = merlin.Event.create(1, '+ Attribute foo bar baz')
        assert len(e.actions) == 1
        assert isinstance(e.actions[0], actions.AddAttributesAction)

    def test_multiple_actions(self):
        e = merlin.Event.create(
            1,
            """
            + Attribute foo
            + Attribute bar
            + Attribute baz
            """)
        assert len(e.actions) == 3

    def test_add_unit_type_event(self):
        e = merlin.Event.create(
            1,
            """
            + UnitType desks $
            """)
        assert len(e.actions) == 1
        assert isinstance(e.actions[0], actions.UnitTypeAction)

    def test_whitespace(self):
        e = merlin.Event.create(
            1,
            """
              +   UnitType   desks   $
            """
        )
        assert len(e.actions) == 1
        assert isinstance(e.actions[0], actions.UnitTypeAction)

    def test_invalid_type(self):
        with pytest.raises(merlin.MerlinScriptException):
            merlin.Event.create(
                1,
                """
                + FooBar desks
                """)

    def test_invalid_operator(self):
        with pytest.raises(merlin.MerlinScriptException):
            merlin.Event.create(
                1,
                """
                * UnitType
                """)

    def test_invalid_params(self):
        with pytest.raises(merlin.MerlinScriptException):
            merlin.Event.create(
                1,
                """
                + UnitType
                """)

    def test_remove_entity_event(self, computation_test_harness):
        sim = computation_test_harness
        b_entity = sim.get_entity_by_name('Budget')
        a = actions.create("- Entity {0}".format(b_entity.id))
        a[0].execute(sim)
        assert sim.get_entity_by_name('Budget') is None


    def test_add_entity_event(self, computation_test_harness):
        sim = computation_test_harness
        a = actions.create("+ Entity Budget_2")
        a[0].execute(sim)
        assert sim.get_entity_by_name("Budget_2") is not None

    def test_add_connection_event(self, sim):
        source = merlin.Entity(simulation=sim, name='source', attributes=set())
        sink = merlin.Entity(simulation=sim, name='sink', attributes=set())
        sim.add_entity(source)
        sim.add_entity(sink)
        axs = actions.create("Entity {0} > Entity {1} shoes 1 True".format(
            source.id, sink.id))
        assert len(axs) == 1
        a = axs[0]
        a.execute(sim)
        assert source.get_output_by_type('shoes')
        assert sink.get_input_by_type('shoes')


    def test_remove_connection_event(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e1 = sim.get_entity_by_name("Budget")
        e2 = sim.get_entity_by_name("office building")
        axs = actions.create("Entity {0} / Entity {1} $".format(e1.id, e2.id))
        assert len(axs) == 1
        axs[0].execute(sim)
        assert len(e1.get_output_by_type('$').get_endpoints()) == 1
        assert len(e2.inputs) == 0


    def test_add_process_event(self, computation_test_harness):
        # TODO: write test
        sim = computation_test_harness  # type: merlin.Simulation
        e1 = sim.get_entity_by_name('Budget')
        a = actions.create("""
            Entity {0} + Process BuildingMaintainenceProcess 200 pymerlin.processes b_maintainance
            """.format(e1.id))
        assert len(e1.get_processes()) == 1
        a[0].execute(sim)
        assert len(e1.get_processes()) == 2
        p = e1.get_process_by_name('b_maintainance')
        assert p
        assert p.priority == 200

    def test_modify_process_property_event(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = sim.get_entity_by_name('call center')
        p = e.get_process_by_name('Call Center Staff')
        prop = p.get_prop('staff salary')
        assert prop.get_value() == 5.0
        # a = actions.ModifyProcessPropertyAction(e.id, prop.id, 2.0)
        a = actions.create("Entity {0} = Property {1} 2.0".format(e.id, prop.id))
        assert len(a) == 1
        a[0].execute(sim)
        assert prop.get_value() == 2.0


    def test_parent_entity_event(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        child_ent = merlin.Entity(name="child_ent")
        parent_ent = sim.get_entity_by_name("Budget")
        sim.add_entity(child_ent)
        assert child_ent not in parent_ent.get_children()
        assert child_ent.parent is None
        a = actions.create("Entity {0} ^ Entity {1}".format(child_ent.id, parent_ent.id))
        assert len(a) == 1
        a[0].execute(sim)
        assert child_ent in parent_ent.get_children()
        assert child_ent.parent == parent_ent

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
        rca = actions.RemoveConnectionAction(seg[0].id, seg[1].id, seg[2].type)
        rca.execute(sim)
        assert seg[2] not in seg[0].outputs
        assert seg[3] not in seg[1].inputs

    def test_add_connection_action(self, sim):
        source = merlin.Entity(simulation=sim, name='source', attributes=set())
        sink = merlin.Entity(simulation=sim, name='sink', attributes=set())
        sim.add_entity(source)
        sim.add_entity(sink)
        aca = actions.AddConnectionAction(
            source.id,
            sink.id,
            'new_unit_type',
            apportioning=2,
            additive_write=True)
        aca.execute(sim)

        output_con = source.get_output_by_type('new_unit_type')
        input_con = sink.get_input_by_type('new_unit_type')
        assert output_con is not None
        assert input_con is not None
        assert output_con.parent == source
        assert input_con.parent == sink
        assert len(source.outputs) == 1
        assert len(source.inputs) == 0
        assert len(sink.inputs) == 1
        assert len(sink.outputs) == 0
        assert input_con in [ep[0] for ep in output_con.get_endpoints()]

    def test_add_process_action(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e1 = sim.get_entity_by_name('Budget')
        a = actions.AddProcessAction(
            e1.id,
            'BuildingMaintainenceProcess',
            200,
            process_module='pymerlin.processes',
            process_name='b_maintainance')
        assert len(e1.get_processes()) == 1
        a.execute(sim)
        assert len(e1.get_processes()) == 2
        p = e1.get_process_by_name('b_maintainance')
        assert p
        assert p.priority == 200


    def test_remove_process_action(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e1 = sim.get_entity_by_name("office building")
        p1 = e1.get_process_by_name('Building Maintenance')
        assert e1.get_process_by_name('Building Maintenance') is not None
        a = actions.RemoveProcessAction(e1.id, p1.id)
        a.execute(sim)
        assert e1.get_process_by_name('Building Maintenance') is None

    def test_parent_entity_action(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        child_ent = merlin.Entity(name="child_ent")
        parent_ent = sim.get_entity_by_name("Budget")
        sim.add_entity(child_ent)
        assert child_ent not in parent_ent.get_children()
        assert child_ent.parent is None
        a = actions.ParentEntityAction(child_ent.id, parent_ent.id)
        a.execute(sim)
        assert child_ent in parent_ent.get_children()
        assert child_ent.parent == parent_ent

    def test_modify_process_property_action(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = sim.get_entity_by_name('call center')
        p = e.get_process_by_name('Call Center Staff')
        prop = p.get_prop('staff salary')
        assert prop.get_value() == 5.0
        a = actions.ModifyProcessPropertyAction(e.id, prop.id, 2.0)
        a.execute(sim)
        assert prop.get_value() == 2.0

