"""
Created on 13/5/2016

..code-author:: Sam Win-Mason <sam@lemonadelabs.io>

This module provides an example services model for the first
phase of the Merlin project. It uses some classes from the other
exmaple files.
"""

from pymerlin import merlin


class StorageService(merlin.Process):
    """
    Represents a file processing service that
    generates revenue.
    """

    def __init__(
            self,
            access_cost=10,
            access_storage_ratio=0.2,
            access_price=20,
            storage_price=40,
            ohfte_lsfte_ratio=1,
            files_processed_per_lsfte=1,
            name="Storage Service"
            ):
        super(StorageService, self).__init__(name)

        # Define Inputs
        self.add_input('file_count', 'files')
        self.add_input('line_staff_fte', 'LS_FTE')
        self.add_input('overhead_staff_fte', 'OH_FTE')
        self.add_input('storage_budget', 'other$')
        self.add_input('used_rent_expenses', 'used_rent_expenses')
        self.add_input('used_staff_expenses', 'used_staff_expenses')
        self.add_input('used_fl_expenses', 'used_other_expenses')

        # Define Outputs
        self.add_output("files_stored", 'files_stored')
        self.add_output("files_accessed", 'files_accessed')
        self.add_output("service_revenue", 'service_revenue')
        self.add_output("used_expenses", 'used_other_expenses')

        # Define Properties

        self.add_property(
            "File Access Cost",
            'access_cost',
            merlin.ProcessProperty.PropertyType.number_type,
            access_cost
        )

        self.add_property(
            "Access / Storage",
            'access_storage_ratio',
            merlin.ProcessProperty.PropertyType.number_type,
            access_storage_ratio
        )

        self.add_property(
            "Access Price",
            'access_price',
            merlin.ProcessProperty.PropertyType.number_type,
            access_price
        )

        self.add_property(
            "Storage Price",
            'storage_price',
            merlin.ProcessProperty.PropertyType.number_type,
            storage_price
        )

        self.add_property(
            "Minimum OH FTEs / LS FTEs",
            'ohfte_lsfte_ratio',
            merlin.ProcessProperty.PropertyType.number_type,
            ohfte_lsfte_ratio
        )

        self.add_property(
            "Files Processed / LS FTE",
            'files_processed_per_lsfte',
            merlin.ProcessProperty.PropertyType.number_type,
            files_processed_per_lsfte
        )

    def reset(self):
        pass

    def compute(self, tick):

        # Calculations
        storage_cost = (
            (
                self.get_input_available('used_rent_expenses') +
                self.get_input_available('used_staff_expenses') +
                self.get_input_available('storage_budget')
            ) /
            self.get_input_available('file_count')
        )

        files_accessed = (
            self.get_input_available('file_count') *
            self.get_prop_value('line_staff_fte') *
            self.get_prop_value('files_processed_per_lsfte') *
            self.get_prop_value('access_storage_ratio')
        )

        files_stored = (
            self.get_input_available('file_count') *
            self.get_prop_value('line_staff_fte') *
            self.get_prop_value('files_processed_per_lsfte')
        )

        service_revenue = (
            self.get_input_available('file_count') *
            (
                (
                    self.get_prop_value('storage_price') +
                    self.get_prop_value('access_price')
                ) *
                self.get_prop_value('access_storage_ratio')
            )
        )

        budget_consumed = (
            self.get_input_available('file_count') *
            (
                (storage_cost + self.get_prop_value('access_cost')) *
                self.get_prop_value('access_storage_ratio')
            )
        )

        management_required = (
            self.get_input_available('line_staff_fte') /
            self.get_prop_value('ohfte_lsfte_ratio')
        )

        # Constraints
        sufficient_managment = (
            self.get_input_available('overhead_staff_fte') >=
            management_required
        )

        sufficient_funding = (
            self.get_input_available('storage_budget') >= budget_consumed
        )

        # Constraint Notifications
        if not sufficient_managment:
            self.notify_insufficient_input(
                'overhead_staff_fte',
                self.get_input_available('overhead_staff_fte'),
                management_required
            )

        if not sufficient_funding:
            self.notify_insufficient_input(
                'storage_budget',
                self.get_input_available('storage_budget'),
                budget_consumed
            )

        # Process inputs and outputs
        if sufficient_funding and sufficient_managment:

            # Consume inputs

            self.consume_input(
                'line_staff_fte',
                self.get_input_available('line_staff_fte')
            )

            self.consume_input(
                'overhead_staff_fte',
                management_required
            )

            self.consume_input(
                'storage_budget',
                budget_consumed
            )

            # Provide outputs

            self.provide_output(
                'files_stored',
                files_stored
            )

            self.provide_output(
                'files_accessed',
                files_accessed
            )

            self.provide_output(
                'service_revenue',
                service_revenue
            )

            self.provide_output(
                'used_expenses',
                budget_consumed
            )

        else:
            self.write_zero_to_all()


class OutsourcedFileLogistics(merlin.Process):
    """
    Represents an outsourced cloud storage provider or
    datacenter.
    """

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
        self.add_input('overhead_staff_fte', 'OH_FTE')
        self.add_input('outsource_budget', 'other$')

        # Define Outputs
        self.add_output('file_count', 'files')
        self.add_output('used_expenses', 'used_other_expenses')

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
