from pymerlin import merlin


class AccumulatorProcess(merlin.Process):
    pass


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
    amount.

    Assumes, a tick being 1 month, so the annual budget is divided by 12.

    An updated budget value is in effect immediately.
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
        self.add_output("$", budget_type)

        # Define properties
        self.add_property("annual amount",
                          "amount",
                          merlin.ProcessProperty.PropertyType.number_type,
                          start_amount)

        self.instantaneous_update = True
        self.current_budget_amount = float(start_amount)

    def reset(self):
        # define internal instance variables on init
        self.current_budget_amount = self.get_prop_value("amount")

    def compute(self, tick):
        # Check to see that the start amount has changed, and if so
        # do a recompute of amount per step and current amount

        # reset the current budget value
        if tick % 12 == 1 or self.instantaneous_update:
            self.current_budget_amount = self.get_prop_value("amount")

        self.provide_output('$', max(0.0,
                                     self.current_budget_amount/12.0))


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
        pass

    def compute(self, tick):

        desks_required = (self.get_prop_value('staff number') /
                               self.get_prop_value('staff per desk'))

        funds_required = (self.get_prop_value('staff number') *
                           self.get_prop_value('staff salary'))
        maximal_output = self.get_prop_value('staff number')

        # check requirements

        if self.get_input_available('desks') < desks_required:

            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                msg="There are not enough {{desks provided}}, "
                    "call center currently needs {0} desks".format(
                    desks_required),
                msg_id="call_center_required_desks",
                context=[self.inputs['desks']]
            )
            raise merlin.InputRequirementException(
                self,
                self.inputs['desks'],
                self.inputs['desks'].connector.value,
                desks_required)
        if self.get_input_available('$') < funds_required:
            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                msg="There is not enough {{budget}} to pay staff, "
                    "call center currently needs ${0}".format(
                    funds_required),
                msg_id="call_center_required_salary",
                context=[self.inputs['$']]
            )

            raise merlin.InputRequirementException(
                self,
                self.inputs['$'],
                self.inputs['$'].connector.value,
                funds_required)

        # compute outputs
        output = maximal_output * self._train_modifier(tick)
        self.consume_input('desks', desks_required)
        self.consume_input('$', funds_required)
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


class StaffFTE(merlin.Process):

    def __init__(
            self,
            name="Staff FTE",
            ls_number=1000.0,
            oh_number=100,
            work_hours=40,
            work_weeks=52,
            training=0.8,
            leave=0.8,
            avg_oh_salary=50000,
            avg_ls_salary=90000
            ):
        super(StaffFTE, self).__init__(name)

        # Define inputs
        self.add_input("staff_budget", "staff$")
        self.add_input("staff_accom", "staff_accomodated")

        # Define outputs
        self.add_output("overhead_staff_fte", "OH_FTE")
        self.add_output("line_staff_fte", "LS_FTE")
        self.add_output("used_expenses", "used_staff_expenses")

        # Define properties
        self.add_property(
            'Line Staff Number',
            'ls_number',
            merlin.ProcessProperty.PropertyType.number_type,
            ls_number
        )

        self.add_property(
            'Overhead Staff Number',
            'oh_number',
            merlin.ProcessProperty.PropertyType.number_type,
            oh_number
        )

        self.add_property(
            'Weekly Working Hours',
            'working_hours',
            merlin.ProcessProperty.PropertyType.number_type,
            work_hours
        )

        self.add_property(
            'Working Weeks',
            'working_weeks',
            merlin.ProcessProperty.PropertyType.number_type,
            work_weeks
        )

        self.add_property(
            'Training Modifier',
            'training',
            merlin.ProcessProperty.PropertyType.number_type,
            training
        )

        self.add_property(
            'Leave Modifier',
            'leave',
            merlin.ProcessProperty.PropertyType.number_type,
            leave
        )

        self.add_property(
            'Average Overhead Salary',
            'avg_oh_salary',
            merlin.ProcessProperty.PropertyType.number_type,
            avg_oh_salary
        )

        self.add_property(
            'Average Line Staff Salary',
            'avg_ls_salary',
            merlin.ProcessProperty.PropertyType.number_type,
            avg_ls_salary
        )

    def reset(self):
        pass

    def compute(self, tick):

        # Salary Calculations
        total_staff = self.get_prop_value('ls_number') + self.get_prop_value('oh_number')
        total_ls_salary = self.get_prop_value('ls_number') * self.get_prop_value('avg_ls_salary')
        total_oh_salary = self.get_prop_value('oh_number') * self.get_prop_value('avg_oh_salary')
        total_salary = total_ls_salary + total_oh_salary
        salary_per_month = total_salary / 12.0

        # Check Constraints
        staff_accomodated = (total_staff <= self.get_input_available('staff_accom'))
        staff_paid = (salary_per_month <= self.get_input_available('staff_budget'))

        if not staff_accomodated:
            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                "{0}_staff_not_accomodated".format(self.id),
                "There is {{{{insufficent accomodation}}}} for the {{{{number of staff}}}}",
                context=[
                    self.inputs['staff_accom'].connector,
                    [self.get_prop('ls_number'), self.get_prop('oh_number')]]
            )

        if not staff_paid:
            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                "{0}_staff_not_paid".format(self.id),
                "There is {{{{insufficent funds}}}} to pay the {{{{monthly staff salary of {0}}}}}".format(salary_per_month),
                context=[
                    self.inputs['staff_budget'].connector,
                    [self.get_prop('avg_oh_salary'), self.get_prop('avg_ls_salary')]]
            )


        if staff_paid and staff_accomodated:
            # Do normal fte per month outputs
            oh_fte = (
                self.get_prop_value('oh_number') *
                self.get_prop_value('working_hours') *
                self.get_prop_value('working_weeks') *
                self.get_prop_value('training') *
                self.get_prop_value('leave')
            ) / 12

            ls_fte = (
                self.get_prop_value('ls_number') *
                self.get_prop_value('working_hours') *
                self.get_prop_value('working_weeks') *
                self.get_prop_value('training') *
                self.get_prop_value('leave')
            ) / 12

            self.consume_input('staff_budget', salary_per_month)
            self.consume_input('staff_accom', total_staff)
            self.provide_output('overhead_staff_fte', ls_fte)
            self.provide_output('line_staff_fte', oh_fte)
            self.provide_output('used_expenses', salary_per_month)

        else:
            self.write_zero_to_all()


class LeasedAccomodationProvider(merlin.Process):
    """
    This process represents the provision of physical
    accomodation that is provided via a lease agreement
    The accomodation could be for staff or equipment such
    as servers.
    """

    def __init__(
            self,
            provided_unit_type="staff_accomodated",
            accom_type="staff",
            name="LeasedAccomodationProvider",
            cost_per_area=0,
            area=1.0,
            accom_type_per_area=1.0,
            lease_duration=24
            ):
        super(LeasedAccomodationProvider, self).__init__(name)

        # Define inputs
        self.add_input('i_rent$', 'rent$')

        # Define ouputs
        self.add_output('o_accomodated', provided_unit_type)
        self.add_output('used_expenses', 'used_rent_expenses')

        # Define properties
        self.add_property(
            'cost / area (m2)',
            'cost_per_area',
            merlin.ProcessProperty.PropertyType.number_type,
            cost_per_area
        )

        self.add_property(
            'area',
            'area',
            merlin.ProcessProperty.PropertyType.number_type,
            area
        )

        self.add_property(
            '{0} / area (m2)'.format(accom_type),
            'accom_type_per_area'.format(accom_type),
            merlin.ProcessProperty.PropertyType.number_type,
            accom_type_per_area
        )

        self.add_property(
            'lease duration',
            'lease duration',
            merlin.ProcessProperty.PropertyType.date_type,
            lease_duration
        )

    def reset(self):
        pass

    def compute(self, tick):
        total_cost = (
            self.get_prop_value('cost_per_area') * self.get_prop_value('area')
        )

        sufficient_rent = (total_cost <= self.get_input_available('i_rent$'))
        sufficient_lease = (tick <= self.get_prop_value('lease duration'))

        # check to see if we have enough rent
        if not sufficient_rent:
            self.notify_insufficient_input(
                'rent$',
                self.get_input_available('i_rent$'),
                total_cost)
            self.provide_output('o_accomodated', 0.0)


        if not sufficient_lease:
            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                "{0}_lease_expired".format(self.id),
                "The lease has expired", context=list()
            )

        if sufficient_lease and sufficient_rent:
            accom_provided = (
                self.get_prop_value('accom_type_per_area') *
                self.get_prop_value('area')
            )

            # consume rent
            self.consume_input('i_rent$', total_cost)
            # provide some accom
            self.provide_output('o_accomodated', accom_provided)
            self.provide_output('used_expenses', total_cost)
        else:
            self.write_zero_to_all()


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

            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                msg_id="building_maint_underfund",
                msg=("Building maint is underfunded. {{{{It needs {0}}}}} but" +
                     " is {{{{receiving only {1}}}}}".format(
                         self.props['monthly maintenance cost'].get_value(),
                         self.inputs['$'].connector.value
                     )),
                context = [
                    self.props['monthly maintenance cost'],
                    self.inputs['$'].connector ]
                )

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
