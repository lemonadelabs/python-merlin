"""
Created on 13/5/2016

..code-author:: Sam Win-Mason <sam@lemonadelabs.io>

This module provides an example services model for the first
phase of the Merlin project. It uses some classes from the other
exmaple files.
"""

from pymerlin import merlin
from pymerlin import processes


# a template for a new process
class TemplateProcess(merlin.Process):
    """
    Documentation of template process
    """

    def __init__(
            self,
            name="Template",
            template_volumes=100,
            ):
        super(TemplateProcess, self).__init__(name)

        # Define Inputs
        self.add_input('template input name', 'template_in_unit')

        # Define Outputs
        self.add_output('template_output_name', 'template_out_unit')

        # Define Properties
        self.add_property(
            'Contracted File Volume',
            'contract_volume',
            merlin.ProcessProperty.PropertyType.number_type,
            template_volumes
        )

    def reset(self):
        pass

    def compute(self, tick):
        self.write_zero_to_all()


# all processes for this model

class StorageServiceProcess(merlin.Process):
    """
    Represents a file processing service that
    generates revenue.
    """

    def __init__(
            self,
            default_lifecycle=20,
            default_storage_fee=1,
            default_ohfte_lsfte_ratio=0.1,
            default_files_handled_per_lsfte=10000,
            name="Storage Service"
            ):
        super(StorageServiceProcess, self).__init__(name)

        # Define Inputs
        self.add_input('staff_expenses', 'staff$')
        self.add_input('rent_expenses', 'rent$')
        self.add_input('line_staff_fte', 'LS_FTE')
        self.add_input('overhead_staff_fte', 'OH_FTE')
        self.add_input('fl_overhead_staff_fte', 'FL_OH_FTE')
        self.add_input('file_count', 'files')
        self.add_input('fl_spare_other_expenses', 'FL_other_exp')
        self.add_input('other_expenses', 'other_exp')
        self.add_input('used_rent_expenses', 'used_rent_expenses')
        self.add_input('used_staff_expenses', 'used_staff_expenses')

        # Define Outputs
        self.add_output("operational_surplus", 'operational_surplus')
        self.add_output("files_stored", 'files_stored')
        self.add_output("service_revenue", 'service_revenue')
        self.add_output("budgetary_surplus", 'budgetary_surplus')

        # Define Properties
        self.add_property(
            "lifecycle/years",
            'lifecycle',
            merlin.ProcessProperty.PropertyType.number_type,
            default_lifecycle
        )

        default_storage_cost = 0  # todo
        self.add_property(
            "Storage Cost",
            'storage_cost',
            merlin.ProcessProperty.PropertyType.number_type,
            default_storage_cost
        )

        self.add_property(
            "Storage Fee",
            'storage_fee',
            merlin.ProcessProperty.PropertyType.number_type,
            default_storage_fee
        )

        self.add_property(
            "Minimum OH FTEs / LS FTEs",
            'ohfte_lsfte_ratio',
            merlin.ProcessProperty.PropertyType.number_type,
            default_ohfte_lsfte_ratio
        )

        self.add_property(
            "Files Handled / LS FTE",
            'files_handled_per_lsfte',
            merlin.ProcessProperty.PropertyType.number_type,
            default_files_handled_per_lsfte
        )

    def reset(self):
        pass

    def compute(self, tick):
        # todo: output changed
        self.write_zero_to_all()
        return

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


class OutsourcedFileLogisticsProcess(merlin.Process):
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
        super(OutsourcedFileLogisticsProcess, self).__init__(name)

        # Define Inputs
        self.add_input('overhead_staff_fte', 'OH_FTE')
        self.add_input('other_expenses', 'other_exp')

        # Define Outputs
        self.add_output('fl_overhead_staff_fte', 'FL_OH_FTE')
        self.add_output('file_count', 'files')
        self.add_output('FL_spare_other_expenses', 'FL_other_exp')

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
            'additional cost / file',
            'additional_cost',
            merlin.ProcessProperty.PropertyType.number_type,
            overage_cost_per_file
        )

        self.add_property(
            'file logistics OHSfte',
            'file_logistics_OHSfte',
            merlin.ProcessProperty.PropertyType.number_type,
            required_management_fte
        )

    def reset(self):
        pass

    def compute(self, tick):
        # todo: redo calculations
        self.write_zero_to_all()
        return

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


class StaffAccomodationProcess(merlin.Process):
    """
    Documentation of template process
    """

    def __init__(
            self,
            name="staff accomodation",
            default_cost_m2=10,
            default_area_m2=100,
            default_staff_per_area_m2=0.2,
            default_lease_term=5
            ):
        super(TemplateProcess, self).__init__(name)

        # Define Inputs
        self.add_input('rent_expenses', 'rent$')

        # Define Outputs
        self.add_output('staff_accomodated', 'accomodatedStaff#')
        self.add_output('used_rent_expenses', 'usedRent$')

        # Define Properties
        self.add_property(
            'cost[$]/area [m²]',
            'cost_per_m2',
            merlin.ProcessProperty.PropertyType.number_type,
            default_cost_m2
        )
        self.add_property(
            'area [m²]',
            'area_m2',
            merlin.ProcessProperty.PropertyType.number_type,
            default_area_m2
        )
        self.add_property(
            'staff [#]/area [m²]',
            'staff_per_area_m2',
            merlin.ProcessProperty.PropertyType.number_type,
            default_staff_per_area_m2
        )
        self.add_property(
            'lease term[yr]/todo',
            'lease_term',
            merlin.ProcessProperty.PropertyType.number_type
        )

    def reset(self):
        pass

    def compute(self, tick):
        # todo
        self.write_zero_to_all()


class StaffProcess(merlin.Process):
    """
    Documentation of template process
    """

    def __init__(
            self,
            name="Staff",
            default_line_staff_no=100,
            default_oh_staff_no=10,
            default_hours_per_week=40.0,
            default_weeks_per_year=52,
            default_prof_training_percent=20,
            default_leave_percent=10,
            default_avg_oh_salary=70e3,
            default_avg_line_salary=60e3,
            # todo: implement
            default_hours_training=100
            ):
        super(StaffProcess, self).__init__(name)

        # Define Inputs
        self.add_input('staff_expenses', 'staffExp$')
        self.add_input('staff_accomodated', 'accomodatedStaff#')

        # Define Outputs
        self.add_output('OHSfte', 'OH_FTE')
        self.add_output('LSfte', 'LS_FTE')
        self.add_output('used_staff_expenses', 'used_staff_expenses')

        # Define Properties
        # todo: this should become a "calculated" or "read only" property
        self.add_property(
            'Staff #',
            'total_staff_no',
            merlin.ProcessProperty.PropertyType.number_type,
            default_line_staff_no+default_oh_staff_no  # as calculated
        )
        self.add_property(
            'line staff #',
            'line_staff_no',
            merlin.ProcessProperty.PropertyType.number_type,
            default_line_staff_no
        )
        # Define Properties
        self.add_property(
            'overhead staff #',
            'oh_staff_no',
            merlin.ProcessProperty.PropertyType.number_type,
            default_oh_staff_no
        )
        self.add_property(
            'working hours per week',
            'hours_per_week',
            merlin.ProcessProperty.PropertyType.number_type,
            default_hours_per_week
        )
        self.add_property(
            'working weeks per year',
            'weeks_per_year',
            merlin.ProcessProperty.PropertyType.number_type,
            default_weeks_per_year
        )
        self.add_property(
            'professional training[%]',
            'prof_training_percent',
            merlin.ProcessProperty.PropertyType.number_type,
            default_prof_training_percent
        )
        self.add_property(
            'annual leave [%]',
            'leave_percent',
            merlin.ProcessProperty.PropertyType.number_type,
            default_leave_percent
        )
        self.add_property(
            'avg overhead salary',
            'avgOHSalary',
            merlin.ProcessProperty.PropertyType.number_type,
            default_avg_oh_salary
        )
        self.add_property(
            'avg line salary',
            'avgLineSalary',
            merlin.ProcessProperty.PropertyType.number_type,
            default_avg_line_salary
        )
        self.add_property(
            'hours of training period',
            'hours_training',
            merlin.ProcessProperty.PropertyType.number_type,
            default_hours_training
        )

    def reset(self):
        pass

    def compute(self, tick):
        self.write_zero_to_all()


# create entities
def createRecordStorage():
    # this is the capability, right now

    sim = merlin.Simulation()
    sim.add_attributes(["branch", "capability", "deliverable", "budget",
                        "asset", "resource", "external capability"])
    # todo: create
    sim.add_unit_types(["files", "LS_FTE", "OH_FTE", "other$", "used_rent_expenses", "used_staff_expenses", "used_other_expenses",
                        "files_stored", "operational_surplus", "service_revenue", "budgetary_surplus",
                        "OH_FTE", "other$", "files", "used_other_expenses", "FL_OH_FTE", "FL_other_exp", "other_exp", "FL_OHSfte",
                        "rent$", "accomodatedStaff#", "usedRent$",
                        "staffExp$", "accomodatedStaff#", "OH_FTE", "LS_FTE", "used_staff_expenses",
                        "service_revenue", "budgetary_surplus", "operational_surplus", "files_stored"
                        "rent$", "staff$", "other$"
                        ])

    # add a branch
    branch_e = merlin.Entity(sim, "the branch")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")

    # add the govRecordStorage capability
    storage_e = merlin.Entity(sim, "storage")
    sim.add_entity(storage_e, parent=branch_e)
    branch_e.add_child(storage_e)
    branch_e.attributes.add("capability")

    # add the budget entities/processes
    # staff budget
    TheStaffBudget = merlin.Entity(sim, "Staff Budget")
    sim.add_entity(TheStaffBudget, is_source_entity=True)
    storage_e.add_child(TheStaffBudget)
    TheStaffBudget.attributes.add("budget")
    #sim.connect_entities(TheMaintenance, StorageFacility, "maint$")
    TheStaffBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "staff budget",
            'start_amount': 4000000,
            'budget_type': "staff$"
        })

    # rent budget
    TheRentBudget = merlin.Entity(sim, "Rent Budget")
    sim.add_entity(TheRentBudget, is_source_entity=True)
    storage_e.add_child(TheRentBudget)
    TheRentBudget.attributes.add("budget")
    #sim.connect_entities(TheMaintenance, StorageFacility, "maint$")
    TheRentBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "rent budget",
            'start_amount': 4000000,
            'budget_type': "rent$"
        })

    # other budget
    TheOhterBudget = merlin.Entity(sim, "Ohter Budget")
    sim.add_entity(TheOhterBudget, is_source_entity=True)
    storage_e.add_child(TheOhterBudget)
    TheOhterBudget.attributes.add("budget")
    #sim.connect_entities(TheMaintenance, StorageFacility, "maint$")
    TheOhterBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "other budget",
            'start_amount': 4000000,
            'budget_type': "other$"
        })


    # add entities and their processes
    FileLogistics = merlin.Entity(sim, "File Logistics")
    sim.add_entity(FileLogistics)
    storage_e.add_child(FileLogistics)
    # the_file_log_process = FileLogisticsProcess("file logistics process")
    # FileLogistics.add_process(the_file_log_process)
    FileLogistics.create_process(
        OutsourcedFileLogisticsProcess,
        {
            'name': "file logistics process"
        })

    FileLogistics.attributes.add("external capability")

    LineStaffRes = merlin.Entity(sim, "Staff")
    sim.add_entity(LineStaffRes)
    storage_e.add_child(LineStaffRes)
    # the_line_staff_process = LineStaffProcess("line staff resource process")
    # LineStaffRes.add_process(the_line_staff_process)
    LineStaffRes.create_process(
        StaffProcess,
        {
            'name': "line staff resource process"
        })

    LineStaffRes.attributes.add("resource")

    StorageFacility = merlin.Entity(sim, "Storage Service")
    sim.add_entity(StorageFacility)
    storage_e.add_child(StorageFacility)
    # todo
    #sim.connect_entities(FileLogistics, StorageFacility, "file count")
    #sim.connect_entities(LineStaffRes, StorageFacility, "lineFTE")
    # the_stor_fac_process = StorageFacilityProcess("storage facility process")
    # StorageFacility.add_process(the_stor_fac_process)
    StorageFacility.create_process(
        StorageServiceProcess,
        {
            'name': "storage facility process"
        })

    StorageFacility.attributes.add("asset")

    # need an expectation
    opSurplus = merlin.Output("operational_surplus",
                              name="operational surplus")
    sim.add_output(opSurplus)
    sim.connect_output(StorageFacility, opSurplus)

    filesStored = merlin.Output("files_stored",
                                name="files stored")
    sim.add_output(filesStored)
    sim.connect_output(StorageFacility, filesStored)

    # need an expectation
    serviceRevenue = merlin.Output("service_revenue",
                                   name="service revenue")
    sim.add_output(serviceRevenue)
    sim.connect_output(StorageFacility, serviceRevenue)

    # need an expectation
    budgetarySurplus = merlin.Output("budgetary_surplus",
                                     name="budgetary surplus")
    sim.add_output(budgetarySurplus)
    sim.connect_output(StorageFacility, budgetarySurplus)

    return sim
