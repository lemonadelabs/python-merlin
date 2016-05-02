from pymerlin import merlin


class ConstantProvider(merlin.Process):
    """
    always return the same number
    """

    def __init__(self, name='resource', unit='', amount=1.0):

        super(ConstantProvider, self).__init__(name)
        # Define outputs
        p_output = merlin.ProcessOutput('output_'+name,
                                        unit,
                                        connector=None)
        self.outputs = {"amount": p_output}
        # Define properties
        self.add_property("amount",
                          "amount",
                          merlin.ProcessProperty.PropertyType.number_type,
                          amount)

    def compute(self, tick):
        a = self.get_prop_value("amount")
        self.provide_output("amount", a)


class BudgetProcess(merlin.Process):
    """
    Split the budget amount into even parts over a year and provide this
    amount, keep track of the amount spent.

    Assumes, a tick being 1 month, so the annual budget is divided by 12.

    Every 12 month this amount is renewed, the "old" amount is discarded.
    (This could be changed, introducing another option.)
    """

    def __init__(self, name='Budget', start_amount=10000.00, budget_type="$"):
        """
        :param str name:
        :param float start_amount: the annually budgeted amount
        :param str budget_type: to keep track of different moneys, names can
            be assigned to the output dollar figures.
        """
        super(BudgetProcess, self).__init__(name)

        # Define outputs
        p_output = merlin.ProcessOutput('output_$',
                                        budget_type,
                                        connector=None)

        # Define properties
        self.add_property("amount",
                          "amount",
                          merlin.ProcessProperty.PropertyType.number_type,
                          start_amount)

        self.outputs = {'$': p_output}

    def reset(self):
        # define internal instance variables on init
        self.current_amount = self.get_prop_value("amount")
        self.amount_per_step = (self.current_amount /
                                min(self.parent.sim.num_steps, 12))

    def compute(self, tick):
        if self.current_amount > 0.00:
            output = self.amount_per_step
            if output > self.current_amount:
                output = self.current_amount
            self.current_amount -= output
            self.provide_output('$', output)
        else:
            self.provide_output('$', 0.0)

        if tick % 12 == 0:
            self.current_amount = self.get_prop_value("amount")


class CallCenterStaffProcess(merlin.Process):

    def __init__(self, name='Call Center Staff'):
        super(CallCenterStaffProcess, self).__init__(name)

        # Define inputs
        i_desks = merlin.ProcessInput('i_desks', 'desks', connector=None)
        i_funds = merlin.ProcessInput('i_$', '$', connector=None)
        self.inputs = {'desks': i_desks, '$': i_funds}

        # Define outputs
        o_requests_handled = merlin.ProcessOutput(
            'o_requests_handled',
            'requests_handled',
            connector=None)
        self.outputs = {'requests_handled': o_requests_handled}

        # Define properties
        self.add_property(
            'staff number',
            'staff number',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default_value=100)

        self.add_property(
            'staff salary',
            'staff salary',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default_value=5.00)

        self.add_property(
            'staff per desk',
            'staff per desk',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default_value=1)

        self.add_property(
            'months to train',
            'months to train',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default_value=5)

    def reset(self):
        # Calculations that
        # you do not expect to change should be put in the
        # reset function as this is called only once at the
        # start of the simulation run.
        self.desks_required = (self.get_prop_value('staff number') /
                               self.get_prop_value('staff per desk'))
        self.funds_required = (self.get_prop_value('staff number') *
                               self.get_prop_value('staff salary'))
        self.maximal_output = self.get_prop_value('staff number')

    def compute(self, tick):
        # check requirements
        if self.get_input_available('desks') < self.desks_required:

            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                msg="There are not enough {{desks provided}}, "
                    "call center currently needs {0} desks".format(self.desks_required),
                msg_id="call_center_required_desks",
                context=
                [
                    {
                        'id': self.inputs['desks'].id,
                        'type': self.inputs['desks'].__class__.__name__
                    }
                ]
            )
            raise merlin.InputRequirementException(
                self,
                self.inputs['desks'],
                self.inputs['desks'].connector.value,
                self.desks_required)
        if self.get_input_available('$') < self.funds_required:
            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                msg="There is not enough {{budget}} to pay staff, "
                    "call center currently needs ${0}".format(
                    self.funds_required),
                msg_id="call_center_required_salary",
                context=
                [
                    {
                        'id': self.inputs['$'].id,
                        'type': self.inputs['$'].__class__.__name__
                    }
                ]
            )

            raise merlin.InputRequirementException(
                self,
                self.inputs['$'],
                self.inputs['$'].connector.value,
                self.funds_required)

        # compute outputs
        output = self.maximal_output * self._train_modifier(tick)
        self.consume_input('desks', self.desks_required)
        self.consume_input('$', self.funds_required)
        self.provide_output('requests_handled', output)

    def _train_modifier(self, tick):
        # This is just a linear function with the
        # slope steepness = months to train
        mtt = self.get_prop_value('months to train')
        train_slope = 1.0 / float(mtt)
        if tick < mtt:
            return tick * train_slope
        else:
            return 1.0


class BuildingMaintainenceProcess(merlin.Process):
    def __init__(self, name='Building Maintenance'):
        super(BuildingMaintainenceProcess, self).__init__(name)

        # Define inputs
        i_funds = merlin.ProcessInput('i_$', '$', connector=None)
        self.inputs = {'$': i_funds}

        # Define outputs
        o_desks = merlin.ProcessOutput('o_desks', 'desks', connector=None)
        self.outputs = {'desks': o_desks}

        # Define properties
        self.add_property(
            'monthly maintenance cost',
            'monthly maintenance cost',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default_value=500.00)

        self.add_property(
            'desks provided',
            'desks provided',
            property_type=merlin.ProcessProperty.PropertyType.number_type,
            default_value=100.0)

    def reset(self):
        pass

    def compute(self, tick):
        # Check requirements
        # logging.debug(self.inputs['$'].connector)
        # logging.debug(self.inputs['$'].connector.value)
        if (self.get_input_available('$') <
                self.get_prop_value('monthly maintenance cost')):
            raise merlin.InputRequirementException(
                self,
                self.inputs['$'],
                self.inputs['$'].connector.value,
                self.props['monthly maintenance cost'].get_value())

        # Compute outputs
        self.consume_input('$',
                           self.get_prop_value('monthly maintenance cost'))
        self.provide_output('desks',
                            self.get_prop_value('desks provided'))
