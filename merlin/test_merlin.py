import pytest
import numpy.testing as npt
from datetime import datetime
from merlin import merlin
from merlin import actions


class BudgetProcess(merlin.Process):

    def __init__(self, name='Budget', start_amount=10000000.00):
        super(BudgetProcess, self).__init__(name)

        # Define outputs
        p_output = merlin.ProcessOutput('output_$', '$', connector=None)

        # Define properties
        p_property = merlin.ProcessProperty(
            'amount',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default=start_amount,
            parent=self)

        self.outputs = {'$': p_output}
        self.props = {'amount': p_property}

    def reset(self):
        # define internal instance variables on init
        self.current_amount = self.props['amount'].get_value()
        self.amount_per_step = self.current_amount / self.parent.sim.num_steps

    def compute(self, tick):
        if self.current_amount > 0.00:
            output = self.amount_per_step if self.amount_per_step >= \
                self.current_amount else self.current_amount
            self.current_amount -= output
            self.outputs['$'].connector.write(output)
        self.outputs['$'].connector.write(0.00)


class CallCenterStaffProcess(merlin.Process):

    def __init__(self, name='Call Center Staff'):
        super(CallCenterStaffProcess, self).__init__(name)

        # Define inputs
        i_desks = merlin.ProcessInput('i_desks', 'desks', connector=None)
        i_funds = merlin.ProcessInput('i_$', '$', connector=None)

        # Define outputs
        o_requests_handled = merlin.ProcessOutput(
            'o_requests_handled',
            'requests_handled',
            connector=None)

        # Define properties
        p_staff = merlin.ProcessProperty(
            'staff number',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default=100,
            parent=self)

        p_staff_salary = merlin.ProcessProperty(
            'staff salary',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default=100.00,
            parent=self)

        p_staff_per_desk = merlin.ProcessProperty(
            'staff per desk',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default=1,
            parent=self)

        p_months_to_train = merlin.ProcessProperty(
            'months to train',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default=2,
            parent=self)

        self.props = {
            'staff_number': p_staff,
            'staff_salary': p_staff_salary,
            'staff_per_desk': p_staff_per_desk,
            'months_to_train': p_months_to_train}

        self.inputs = {'desks': i_desks, '$': i_funds}
        self.outputs = {'requests_handled': o_requests_handled}

    def reset(self):
        # Calculations that
        # you do not expect to change should be put in the
        # reset function as this is called only once at the
        # start of the simualtion run.
        self.desks_required = (
            self.props['staff_number'].get_value() /
            self.props['staff_per_desk'].get_value())
        self.funds_required = (
            self.props['staff_number'].get_value() *
            self.props['staff_salary'].get_value())
        self.maximal_output = self.props['staff_number'].get_value()
        self.train_slope = 1.0 / self.props['months_to_train'].get_value()

    def compute(self, tick):
        # check requirements
        if self.inputs['desks'].connector.value < self.desks_required:
            raise merlin.InputRequirementException(
                self,
                self.inputs['desks'],
                self.inputs['desks'].connector.value,
                self.desks_required)
        if self.inputs['$'].connector.value < self.funds_required:
            raise merlin.InputRequirementException(
                self,
                self.inputs['$'],
                self.inputs['$'].connector.value,
                self.funds_required)

        # compute outputs
        output = self.maximal_output * _train_modifier(tick)
        self.inputs['desks'].consume(self.desks_required)
        self.inputs['$'].consume(self.funds_required)
        self.outputs['requests_handled'].connector.write(output)

    def _train_modifier(self, tick):
        if tick < self.props['months_to_train'].get_value():
            return tick * train_slope
        else:
            return 1.0


class BuildingMaintainenceProcess(merlin.Process):
    """foo"""
    def __init__(self, name='Building Maintainance'):
        super(BuildingMaintainenceProcess, self).__init__(name)

        # Define inputs
        i_funds = merlin.ProcessInput('i_$', '$', connector=None)

        # Define outputs
        o_desks = merlin.ProcessOutput('o_desks', 'desks', connector=None)

        # Define properties
        p_maintainance_cost = merlin.ProcessProperty(
            'monthly maintainance cost',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default=10.00,
            parent=self)

        p_desks_provided = merlin.ProcessProperty(
            'desks provided',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default=100,
            parent=self)

        self.props = {
            'cost': p_maintainance_cost,
            'desks': p_desks_provided}

        self.inputs = {'$': i_funds}
        self.outputs = {'desks': o_desks}

    def reset(self):
        pass

    def compute(self, tick):
        # Check requirements
        if self.inputs['$'].connector.value < self.props['cost'].get_value():
            raise merlin.InputRequirementException(
                self,
                self.inputs['$'],
                self.inputs['$'].connector.value,
                self.props['cost'].get_value())

        # Compute outputs
        self.inputs['$'].consume(self.props['cost'].get_value())
        self.outputs['desks'].connector.write(self.props['desks'].get_value())


@pytest.fixture()
def computation_test_harness(sim):

    # Configure sim properties
    sim.set_time_span(12)
    sim.add_attributes(['budget', 'capability', 'fixed_asset'])
    sim.add_unit_types(['$', 'desks', 'requests_handled'])

    sim_output = merlin.Output('requests_handled', name='requests handled')
    sim_output.type = 'requests_handled'
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

    # Create Entity Connectons
    # Budget connections
    sim.connect_entities(e_budget, e_call_center, '$')
    sim.connect_entities(e_budget, e_office, '$')

    # Call center connections
    sim.connect_output(e_call_center, sim_output)

    # Office connections
    sim.connect_entities(e_office, e_call_center, 'desks')

    # Add entity processes
    p_budget = BudgetProcess(name='Budget', start_amount=1000.00)
    p_staff = CallCenterStaffProcess(name='Call Center Staff')
    p_building = BuildingMaintainenceProcess(name='Building Maintainance')
    e_budget.add_process(p_budget)
    e_call_center.add_process(p_staff)
    e_office.add_process(p_building)
    return sim


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
        cth = computation_test_harness
        cth.run()
        print(list(cth.outputs)[0].result)
        assert False


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

        # TODO Create tests for process actions.
