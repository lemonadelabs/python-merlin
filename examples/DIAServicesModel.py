'''
Created on 13/5/2016

..code-author:: Sam Win-Mason <sam@lemonadelabs.io>

This module provides an example services model for the first
phase of the Merlin project. It uses some classes from the other
exmaple files.
'''

from pymerlin import merlin

class OutsourcedFileLogistics(merlin.Process):
    '''
    Represents an outsourced cloud storage provider or
    datacenter.
    '''

    def __init__(
            self,
            name="Outsourced File Logistics",
            contracted_volumes=100,
            actual_volumes=100,
            contract_cost=1000,
            overage_cost_per_file=10,
            required_management_fte=1
            ):
        super(OutsourcedFileLogistics, self).__init__(name)

        # Define Inputs
        i_ohfte = merlin.ProcessInput('overhead_staff_fte', 'OH_FTE')
        i_budget = merlin.ProcessInput('outsource_budget', 'other$')

        self.inputs = {
            'overhead_staff_fte': i_ohfte,
            'outsource_budget': i_budget
        }

        # Define Outputs
        o_file_count = merlin.ProcessOutput('file_count', 'files')
        o_used_expenses = merlin.ProcessOutput(
            'used_expenses',
            'used_file_logistic_expenses')

        self.outputs = {
            'file_count': o_file_count,
            'used_file_logistic_expenses': o_used_expenses
        }

        # Define Properties

        self.add_property(
            'Contracted File Volume',
            'contract_volume',
            merlin.ProcessProperty.PropertyType.number_type,
            contracted_volumes
        )

        self.add_property(
            'Actual File Volume',
            'actual_volume',
            merlin.ProcessProperty.PropertyType.number_type,
            actual_volumes
        )

        self.add_property(
            'Contract Cost',
            'contract_cost',
            merlin.ProcessProperty.PropertyType.number_type,
            contract_cost
        )

        self.add_property(
            'Overage cost / File',
            'overage_cost',
            merlin.ProcessProperty.PropertyType.number_type,
            overage_cost_per_file
        )

        self.add_property(
            'Contract Management',
            'contract_management',
            merlin.ProcessProperty.PropertyType.number_type,
            required_management_fte
        )

    def reset(self):
        pass

    def compute(self, tick):

        # Calculations
        overage = (
            self.get_prop_value('actual_volume') -
            self.get_prop_value('contract_volume')
        )

        cc = self.get_prop_value('contract_cost')
        oc = self.get_prop_value('overage_cost')
        total_cost = cc if overage <= 0 else cc + (overage * oc)
        monthly_cost = total_cost / 12

        # Constraints
        contract_managed = (
            self.get_input_available('overhead_staff_fte') >=
            self.get_prop_value('contract_management'))

        contract_funded = (
            self.get_input_available('outsource_budget') >=
            monthly_cost
        )

        # Notify constraint violations
        if not contract_managed:
            self.notify_insufficient_input(
                'overhead_staff_fte',
                self.get_input_available('overhead_staff_fte'),
                self.get_prop_value('contract_management')
            )

        if not contract_funded:
            self.notify_insufficient_input(
                'outsource_budget',
                self.get_input_available('outsource_budget'),
                monthly_cost
            )

        if contract_funded and contract_managed:

            self.consume_input(
                'overhead_staff_fte',
                self.get_prop_value('contract_management'))

            self.consume_input(
                'outsource_budget',
                monthly_cost
            )

            self.provide_output(
                'file_count',
                self.get_prop_value('actual_volume'))

            self.provide_output(
                'used_file_logistic_expenses',
                monthly_cost
            )

        else:
            self.write_zero_to_all()
