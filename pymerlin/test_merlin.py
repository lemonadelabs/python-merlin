import pytest
import numpy.testing as npt
from datetime import datetime
from pymerlin import merlin
from pymerlin.processes import (BudgetProcess,
                                CallCenterStaffProcess,
                                BuildingMaintainenceProcess,
                                ConstantProvider)
from examples import RecordStorageFacility
from examples import DIAServicesModel


@pytest.fixture()
def dia_record_storage_model() -> merlin.Simulation:
    return DIAServicesModel.createRecordStorage()

@pytest.fixture()
def dia_reg_service() -> merlin.Simulation:
    return DIAServicesModel.createRegistrationServiceWExternalDesktops()

@pytest.fixture()
def record_storage_example() -> merlin.Simulation:
    return RecordStorageFacility.manyBudgetModel()


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
    e_budget.create_process(BudgetProcess, {'name': 'Budget'})
    e_call_center.create_process(CallCenterStaffProcess, {'name': 'Call Center Staff'})
    e_office.create_process(BuildingMaintainenceProcess, {'name': 'Building Maintenance'})
    return sim


@pytest.fixture()
def sim() -> merlin.Simulation:
    """ Returns a simulation object """
    return merlin.Simulation(
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

    def test_multiple_runs(self, record_storage_example):
        sim = record_storage_example  # type: merlin.Simulation
        # sim.run(end=10)
        sim.num_steps = 10
        sim.run()
        sim.run()
        assert len(list(sim.outputs)[0].result) != 0


    def test_output(self, computation_test_harness):
        sim = computation_test_harness
        sim.run()
        result = list(sim.outputs)[0].result
        expected_result = \
            [20.0, 40.0, 60.0, 80.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]

        for i in range(0, len(result)):
            npt.assert_almost_equal(result[i], expected_result[i])


class TestSimulation:

    def test_search_by_id(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        budget = sim.get_entity_by_name('Budget')
        assert budget is not None
        call_center = sim.get_entity_by_name('call center')
        assert call_center is not None
        output = list(sim.outputs)[0]
        assert output is not None
        output_con = budget.get_output_by_type('$')
        assert output_con is not None
        input_con = call_center.get_input_by_type('$')
        assert  input_con is not None
        call_center_process = call_center.get_process_by_name('Call Center Staff')
        assert call_center_process is not None
        staff_process_prop = call_center_process.get_prop('staff number')
        assert staff_process_prop is not None
        f_budget = sim.find_sim_object(budget.id, 'Entity')
        f_output = sim.find_sim_object(output.id, 'Output')
        f_output_con = sim.find_sim_object(output_con.id, 'OutputConnector')
        f_input_con = sim.find_sim_object(input_con.id, 'InputConnector')
        f_con = sim.find_sim_object(output_con.id, 'Connector')
        f_process = sim.find_sim_object(call_center_process.id, 'Process')
        f_pp = sim.find_sim_object(staff_process_prop.id, 'ProcessProperty')
        assert f_budget == budget
        assert f_con == output_con
        assert f_input_con == input_con
        assert f_output_con == output_con
        assert f_pp == staff_process_prop
        assert f_process == call_center_process
        assert f_output == output


    def test_search_by_name(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        budget = sim.get_entity_by_name('Budget')
        assert budget is not None
        call_center = sim.get_entity_by_name('call center')
        assert call_center is not None
        output = list(sim.outputs)[0]
        assert output is not None
        output_con = budget.get_output_by_type('$')
        assert output_con is not None
        input_con = call_center.get_input_by_type('$')
        assert input_con is not None
        call_center_process = call_center.get_process_by_name(
            'Call Center Staff')
        assert call_center_process is not None
        staff_process_prop = call_center_process.get_prop('staff number')
        assert staff_process_prop is not None
        f_budget = sim.find_sim_object(budget.name, 'Entity')
        f_output = sim.find_sim_object(output.name, 'Output')
        f_output_con = sim.find_sim_object(output_con.name, 'OutputConnector')
        f_con = sim.find_sim_object(output_con.name, 'Connector')
        f_process = sim.find_sim_object(call_center_process.name, 'Process')
        f_pp = sim.find_sim_object(staff_process_prop.name, 'ProcessProperty')
        assert f_budget == budget
        assert f_con == output_con
        assert f_output_con == output_con
        assert f_pp == staff_process_prop
        assert f_process == call_center_process
        assert f_output == output

    def test_telemetry_output(self, record_storage_example):
        sim = record_storage_example # type: merlin.Simulation
        sim.run()
        tel = sim.get_sim_telemetry()
        for to in tel:
            if 'data' in to:
                if 'value' in to['data']:
                    assert len(to['data']['value']) == sim.num_steps


    def test_consistant_telemetry_output_size(self, dia_record_storage_model):
        sim = dia_record_storage_model  # type: merlin.Simulation
        sim.num_steps = 10
        for i in range(0, 5):
            sim.run()
            tel = sim.get_sim_telemetry()
            for to in tel:
                if 'data' in to:
                    if 'value' in to['data']:
                        print(to['name'])
                        assert len(to['data']['value']) == sim.num_steps


    def test_consistant_telemetry_output_values(self, dia_reg_service):
        sim = dia_reg_service  # type: merlin.Simulation
        sim.num_steps = 48
        sim.run(end=48)
        output_1 = sim.get_sim_telemetry()
        sim.run(end=48)
        output_2 = sim.get_sim_telemetry()

        for t1 in output_1:
            if 'messages' in t1:
                continue
            for t2 in output_2:
                if 'messages' in t2:
                    continue
                if t2['id'] == t1['id']:
                    assert len(t1['data']['value']) == len(t2['data']['value'])
                    for i in range(0, len(t1['data']['value'])):
                        assert t1['data']['value'][i] == t2['data']['value'][i]


    def test_source_entities(self, computation_test_harness):
        sim = computation_test_harness
        e = sim.get_entity_by_name('Budget')
        assert len(sim.source_entities) == 1
        assert e in sim.source_entities

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

    def test_create_process(self, entity):
        assert len(entity.get_processes()) == 0
        assert len(entity.outputs) == 0
        assert len(entity.inputs) == 0
        entity.create_process(
            ConstantProvider,
            {
                'name': 'test_resource',
                'unit': 'snickers_bars',
                'amount': 100
            })
        p = entity.get_process_by_name('test_resource')
        assert p
        assert isinstance(p, ConstantProvider)
        assert len(entity.get_processes()) == 1
        assert len(entity.outputs) == 1
        assert len(entity.inputs) == 0
        assert entity.get_output_by_type('snickers_bars')
        assert p.get_prop('amount')
        assert p.get_prop('amount').get_value() == 100

    def test_get_process_by_id(self, entity):
        p1 = entity.create_process(BuildingMaintainenceProcess, {})
        p2 = entity.get_process_by_id(p1.id)
        assert p1 == p2

    def test_get_processes(self, entity):
        entity.create_process(BuildingMaintainenceProcess, {})
        ps = entity.get_processes()
        assert len(ps) == 1
        assert ps[0].name == 'Building Maintenance'

    def test_remove_process(self, entity):
        bmp = entity.create_process(BuildingMaintainenceProcess, {})
        entity.remove_process(bmp.id)
        p = entity.get_process_by_id(bmp.id)
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


class TestEvents:

    def test_add_dict_events(self):
        data = [
            {
                'op': '+',
                'operand_1': {
                    'type': "Attribute",
                    'params': ["foo"],
                    'props': None
                },
                'operand_2': None
            },

            {
                'op': '+',
                'operand_1': {
                    'type': "UnitType",
                    'params': ["bar"],
                    'props': None
                },
                'operand_2': None
            }
        ]

        e = merlin.Event.create_from_dict(1, data)
        assert len(e.actions) == 2
        assert isinstance(e.actions[0], merlin.AddAttributesAction)
        assert isinstance(e.actions[1], merlin.UnitTypeAction)


    def test_add_json_events(self):
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
        assert isinstance(e.actions[0], merlin.AddAttributesAction)
        assert isinstance(e.actions[1], merlin.UnitTypeAction)


    def test_add_attribute_event(self):
        e = merlin.Event.create(1, '+ Attribute foo, bar, baz')
        assert len(e.actions) == 1
        assert isinstance(e.actions[0], merlin.AddAttributesAction)

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
            + UnitType desks, $
            """)
        assert len(e.actions) == 1
        assert isinstance(e.actions[0], merlin.UnitTypeAction)

    def test_whitespace(self):
        e = merlin.Event.create(
            1,
            """
              +   UnitType   desks,   $
            """
        )
        assert len(e.actions) == 1
        assert isinstance(e.actions[0], merlin.UnitTypeAction)

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
        a = merlin.Action.create("- Entity {0}".format(b_entity.id))
        a[0].execute(sim)
        assert sim.get_entity_by_name('Budget') is None


    def test_add_entity_event(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        a = merlin.Action.create("+ Entity Budget_2, attr1, attr2")
        a[0].execute(sim)
        e = sim.get_entity_by_name("Budget_2")
        assert e is not None
        assert 'attr1' in e.attributes
        assert 'attr2' in e.attributes

    def test_add_connection_event(self, sim):
        source = merlin.Entity(simulation=sim, name='source', attributes=set())
        sink = merlin.Entity(simulation=sim, name='sink', attributes=set())
        sim.add_entity(source)
        sim.add_entity(sink)
        axs = merlin.Action.create("Entity {0} > Entity {1}, shoes, 1, True".format(
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
        axs = merlin.Action.create("Entity {0} / Entity {1}, $".format(e1.id, e2.id))
        assert len(axs) == 1
        axs[0].execute(sim)
        assert len(e1.get_output_by_type('$').get_endpoints()) == 1
        assert len(e2.inputs) == 0


    def test_add_process_event(self, sim, entity):
        sim.add_entity(entity)
        a = merlin.Action.create("""
            Entity {0} + Process pymerlin.processes.ConstantProvider, 200, name:str = mr_foo, unit:str = snickers bars, amount:float = 1000
            """.format(entity.id))
        assert len(entity.get_processes()) == 0
        a[0].execute(sim)
        assert len(entity.get_processes()) == 1


    def test_modify_process_property_event(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = sim.get_entity_by_name('call center')
        p = e.get_process_by_name('Call Center Staff')
        prop = p.get_prop('staff salary')
        assert prop.get_value() == 5.0
        # a = actions.ModifyProcessPropertyAction(e.id, prop.id, 2.0)
        a = merlin.Action.create("Entity {0} := Property {1}, 2.0".format(e.id, prop.id))
        assert len(a) == 1
        a[0].execute(sim)
        assert prop.get_value() == 2.0


    def test_additive_modify_process_property_event(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = sim.get_entity_by_name('call center')
        p = e.get_process_by_name('Call Center Staff')
        prop = p.get_prop('staff salary')
        assert prop.get_value() == 5.0
        a = merlin.Action.create(
            "Entity {0} := Property {1}, -2.0, additive:bool = {2}".format(e.id, prop.id, True))
        assert len(a) == 1
        a[0].execute(sim)
        assert prop.get_value() == 3.0


    def test_parent_entity_event(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        child_ent = merlin.Entity(name="child_ent")
        parent_ent = sim.get_entity_by_name("Budget")
        sim.add_entity(child_ent)
        assert child_ent not in parent_ent.get_children()
        assert child_ent.parent is None
        a = merlin.Action.create("Entity {0} ^ Entity {1}".format(child_ent.id, parent_ent.id))
        assert len(a) == 1
        a[0].execute(sim)
        assert child_ent in parent_ent.get_children()
        assert child_ent.parent == parent_ent


    def test_modify_output_minimum_event(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        output = list(sim.outputs)[0]
        output.minimum = 0
        a = merlin.Action.create(":= Output {0}, minimum:float = {1}".format(output.id, 10))
        assert len(a) == 1
        a[0].execute(sim)
        assert output.minimum == 10

    def test_modify_endpoint_bias(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        budget = sim.get_entity_by_name('Budget')
        o = budget.get_output_by_type('$')
        eps = o.get_endpoint_objects()
        for e in eps:
            npt.assert_almost_equal(e.bias, 0.5)
        a1 = merlin.Action.create("Entity {0} := Endpoint {1}, bias:float = {2}".format(budget.id,
                                                                                        eps[0].id,
                                                                                        0.7))
        a2 = merlin.Action.create(
            "Entity {0} := Endpoint {1}, bias:float = {2}".format(budget.id,
                                                                  eps[1].id,
                                                                  0.3))
        a1[0].execute(sim)
        a2[0].execute(sim)
        npt.assert_almost_equal(eps[0].bias, 0.7)
        npt.assert_almost_equal(eps[1].bias, 0.3)



class TestCoreActions:


    def test_remove_entity_action(self, sim, simple_entity_graph):
        seg = simple_entity_graph
        sim.add_entity(seg[0])
        sim.add_entity(seg[1])
        a = merlin.RemoveEntityAction(seg[1].id)
        a.execute(sim)
        assert seg[1] not in sim.get_entities()
        assert seg[2] not in seg[0].outputs

    def test_add_entity_action(self, sim, simple_entity_graph):
        seg = simple_entity_graph
        e1a = merlin.AddEntityAction(
            'new_entity1', parent=seg[0])
        e2a = merlin.AddEntityAction(
            'new_entity2', attributes=[], parent=None)
        e1a.execute(sim)
        e2a.execute(sim)
        assert seg[0].get_child_by_name('new_entity1') is not None
        assert sim.get_entity_by_name('new_entity2') is not None

    def test_remove_connection_action(self, sim, simple_entity_graph):
        seg = simple_entity_graph
        sim.add_entity(seg[0])
        sim.add_entity(seg[1])
        rca = merlin.RemoveConnectionAction(seg[0].id, seg[1].id, seg[2].type)
        rca.execute(sim)
        assert seg[2] not in seg[0].outputs
        assert seg[3] not in seg[1].inputs

    def test_add_connection_action(self, sim):
        source = merlin.Entity(simulation=sim, name='source', attributes=set())
        sink = merlin.Entity(simulation=sim, name='sink', attributes=set())
        sim.add_entity(source)
        sim.add_entity(sink)
        aca = merlin.AddConnectionAction(
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
        a = merlin.AddProcessAction(
            e1.id,
            'pymerlin.processes.BuildingMaintainenceProcess',
            200,
            {'name': 'b_maintainance'})
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
        a = merlin.RemoveProcessAction(e1.id, p1.id)
        a.execute(sim)
        assert e1.get_process_by_name('Building Maintenance') is None

    def test_parent_entity_action(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        child_ent = merlin.Entity(name="child_ent")
        parent_ent = sim.get_entity_by_name("Budget")
        sim.add_entity(child_ent)
        assert child_ent not in parent_ent.get_children()
        assert child_ent.parent is None
        a = merlin.ParentEntityAction(child_ent.id, parent_ent.id)
        a.execute(sim)
        assert child_ent in parent_ent.get_children()
        assert child_ent.parent == parent_ent

    def test_modify_process_property_action(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = sim.get_entity_by_name('call center')
        p = e.get_process_by_name('Call Center Staff')
        prop = p.get_prop('staff salary')
        assert prop.get_value() == 5.0
        a = merlin.ModifyProcessPropertyAction(e.id, prop.id, 2.0)
        a.execute(sim)
        assert prop.get_value() == 2.0

    def test_additve_modify_process_property_action(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        e = sim.get_entity_by_name('call center')
        p = e.get_process_by_name('Call Center Staff')
        prop = p.get_prop('staff salary')
        assert prop.get_value() == 5.0
        a = merlin.ModifyProcessPropertyAction(e.id, prop.id, -2.0, additive=True)
        a.execute(sim)
        assert prop.get_value() == 3.0

    def test_modify_output_minimum(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        output = list(sim.outputs)[0]
        output.minimum = 0
        a = merlin.ModifyOutputMinimumAction(output.id, 10)
        a.execute(sim)
        assert output.minimum == 10

    def test_modify_endpoint_bias(self, computation_test_harness):
        sim = computation_test_harness  # type: merlin.Simulation
        budget = sim.get_entity_by_name('Budget')
        o = budget.get_output_by_type('$')
        eps = o.get_endpoint_objects()
        for e in eps:
            npt.assert_almost_equal(e.bias, 0.5)
        a1 = merlin.ModifyEndpointBiasAction(budget.id, eps[0].id, bias=0.7)
        a2 = merlin.ModifyEndpointBiasAction(budget.id, eps[1].id, bias=0.3)
        a1.execute(sim)
        a2.execute(sim)
        npt.assert_almost_equal(eps[0].bias, 0.7)
        npt.assert_almost_equal(eps[1].bias, 0.3)


