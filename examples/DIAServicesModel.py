"""
Created on 13/5/2016

..code-author:: Sam Win-Mason <sam@lemonadelabs.io>

This module provides an example services model for the first
phase of the Merlin project. It uses some classes from the other
exmaple files.
"""

from pymerlin import merlin
from pymerlin import processes
import logging

# Global logging settings
logging_level = logging.INFO
log_to_file = ''
logging.basicConfig(
    filename=log_to_file,
    level=logging_level,
    format='%(asctime)s: [%(levelname)s] %(message)s')


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
            default_files_handled_per_lswork_hr=20,
            default_annual_storage_rent=1.0e4,
            name="Storage Service"
            ):
        super(StorageServiceProcess, self).__init__(name)

        # Define Inputs
        self.add_input('file count', 'file#')
        self.add_input('monthly operational budget', "other$")
        self.add_input('monthly line staff work hrs', 'LS_work_hr')
        self.add_input('accommodation expenses', 'accommodationExpense$')
        self.add_input('staff expenses', 'staffExpense$')
        self.add_input('logistics expenses', 'logisticExpense$')

        # Define Outputs
        self.add_output("Additional Files Stored", 'file#')
        self.add_output("Service Revenue", 'revenue$')
        self.add_output("Budgetary Surplus", 'surplus$')
        self.add_output("Operational Surplus", 'opsurplus$')
#        self.add_output("Storage Cost Per File", "cost_per_file")

        self.add_property(
            "Access Fee / $",
            'storage_fee',
            merlin.ProcessProperty.PropertyType.number_type,
            default_storage_fee
        )

        self.add_property(
            "Files Handled / LS work hr",
            'files_handled_per_lswork_hr',
            merlin.ProcessProperty.PropertyType.number_type,
            default_files_handled_per_lswork_hr
        )

        self.add_property(
            "Annual Storage Rent",
            "storage_rent",
            merlin.ProcessProperty.PropertyType.number_type,
            default_annual_storage_rent
        )

    def reset(self):
        pass

    def compute(self, tick):
        # Calculations
        total_expenses = (self.get_input_available('accommodation expenses') +
                          self.get_input_available('staff expenses') +
                          self.get_input_available('logistics expenses') +
                          self.get_prop_value('storage_rent')/12.0)

#         try:
#             storage_cost = (total_expenses /
#                             self.get_input_available('file count'))
#             self.provide_output("Storage Cost Per File", storage_cost)
#         except ZeroDivisionError:
#             logging.info("Divide by zero error in storage_cost")
#             storage_cost = 0

        files_stored = min(
            self.get_input_available('file count'),
            self.get_input_available('monthly line staff work hrs') *
            self.get_prop_value('files_handled_per_lswork_hr')
        )

        service_revenue = (
            files_stored *
            self.get_prop_value('storage_fee')
        )

        operational_surplus = (
            service_revenue - total_expenses
        )

        budgetary_surplus = (
          self.get_input_available('monthly operational budget') -
          self.get_prop_value('storage_rent')/12.0
        )

        sufficient_funding = (
            budgetary_surplus >= 0
        )

        if not sufficient_funding:
            self.notify_insufficient_input(
                'monthly operational budget',
                self.get_input_available('monthly operational budget'),
                self.get_prop_value('storage_rent')/12.0
            )

        # Process inputs and outputs
        if sufficient_funding:

            # Consume inputs

            self.consume_input(
                'monthly line staff work hrs',
                self.get_input_available('monthly line staff work hrs')
            )

            self.consume_input(
                'monthly operational budget',
                self.get_prop_value('storage_rent')/12.0
            )

            # Provide outputs
            self.provide_output(
                'Additional Files Stored',
                files_stored
            )

            self.provide_output(
                'Service Revenue',
                service_revenue
            )

            self.provide_output(
                'Operational Surplus',
                operational_surplus
            )

            self.provide_output(
                'Budgetary Surplus',
                budgetary_surplus
            )

        else:
            self.consume_all_inputs(0)
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
            required_management_work_hr=1,
            default_contract_length=6
            ):
        super(OutsourcedFileLogisticsProcess, self).__init__(name)

        # Define Inputs
        self.add_input('overhead staff work hrs', 'OH_work_hr')
        self.add_input('Monthly Contract Budget', 'other$')

        # Define Outputs
        self.add_output('files handled', 'file#')
        self.add_output('budgetary surplus', 'other$')
        self.add_output('monthly logistics costs', "logisticExpense$")

        # Define Properties
        self.add_property(
            'Contracted Annual File Volume',
            'contract_volume',
            merlin.ProcessProperty.PropertyType.number_type,
            contracted_volumes
        )

        self.add_property(
            'Actual Annual File Volume',
            'actual_volume',
            merlin.ProcessProperty.PropertyType.number_type,
            actual_volumes
        )

        self.add_property(
            'Annual Contract Cost',
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
            'Annual Overhead Staff Hours',
            'file_logistics_OHSwork_hr',
            merlin.ProcessProperty.PropertyType.number_type,
            required_management_work_hr
        )

        self.add_property(
            "lenght of contrcat/yrs",
            "contract_yrs",
            merlin.ProcessProperty.PropertyType.number_type,
            default_contract_length
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
        oc = self.get_prop_value('additional_cost')
        total_cost = cc if overage <= 0 else cc + (overage * oc)
        monthly_cost = total_cost / 12

        # Constraints
        contract_managed = (
            self.get_input_available('overhead staff work hrs') >=
            self.get_prop_value('file_logistics_OHSwork_hr'))

        contract_funded = (
            self.get_input_available('Monthly Contract Budget') >=
            monthly_cost
        )

        # Notify constraint violations
        if not contract_managed:
            self.notify_insufficient_input(
                'overhead staff work hrs',
                self.get_input_available('overhead staff work hrs'),
                self.get_prop_value('file_logistics_OHSwork_hr') / 12.0
            )

        if not contract_funded:
            self.notify_insufficient_input(
                'Monthly Contract Budget',
                self.get_input_available('Monthly Contract Budget'),
                monthly_cost
            )

        if contract_funded and contract_managed:
            # consume it all!

            self.provide_output(
                'files handled',
                self.get_prop_value('actual_volume')/12.0)

            self.provide_output(
                'monthly logistics costs',
                monthly_cost
            )

            self.provide_output(
                "budgetary surplus",
                self.get_input_available('Monthly Contract Budget')-monthly_cost
            )

            self.consume_input(
                'Monthly Contract Budget',
                self.get_input_available('Monthly Contract Budget')
            )

            self.consume_input(
                'overhead staff work hrs',
                self.get_prop_value('file_logistics_OHSwork_hr'))

        else:
            self.consume_all_inputs(0)
            self.write_zero_to_all()


class StaffAccommodationProcess(merlin.Process):
    """
    Documentation of template process
    """

    def __init__(
            self,
            name="staff accommodation",
            default_cost_m2=400,
            default_area_m2=1500,
            default_area_per_staff_m2=15,
            default_lease_term=5
            ):
        super(StaffAccommodationProcess, self).__init__(name)

        # Define Inputs
        self.add_input('rent expenses', 'rent$')

        # Define Outputs
        self.add_output('staff accommodated', 'workspace#')
        self.add_output('rent expenses', 'accommodationExpense$')
        self.add_output('budgetary surplus', 'surplus$')

        # Define Properties
        self.add_property(
            'annual cost[$]/area [m²]',
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
            'area [m²]/staff',
            'area_per_staff_m2',
            merlin.ProcessProperty.PropertyType.number_type,
            default_area_per_staff_m2
        )
        self.add_property(
            'lease term [yr]',
            'lease_term',
            merlin.ProcessProperty.PropertyType.number_type,
            default_lease_term
        )

    def reset(self):
        pass

    def compute(self, tick):

        cost_per_area = self.get_prop_value("cost_per_m2")
        area_per_staff = self.get_prop_value("area_per_staff_m2")
        area = self.get_prop_value("area_m2")
        lease_term = self.get_prop_value("lease_term")

        rent_expenses = self.get_input_available("rent expenses")

        try:
            staff_accommodated = area / area_per_staff
        except ZeroDivisionError:
            staff_accommodated = 0

        used_rent_expenses = cost_per_area*area

        lease_still_on = (lease_term >= 1)
        sufficient_funding = (rent_expenses >= used_rent_expenses)

        if not lease_still_on:
            self.parent.sim.log_message(
                merlin.MerlinMessage.MessageType.warn,
                self,
                '{0}_lease_expired'.format(self.id),
                'The {{{{lease has expired}}}}',
                [self.get_prop('lease_term')]
            )
        if not sufficient_funding:
            self.notify_insufficient_input("rent expenses",
                                           rent_expenses,
                                           used_rent_expenses)

        if sufficient_funding and lease_still_on:
            self.consume_input("rent expenses",
                               rent_expenses)

            self.provide_output("budgetary surplus",
                                rent_expenses-used_rent_expenses)
            self.provide_output("staff accommodated",
                                staff_accommodated)
            self.provide_output("rent expenses",
                                used_rent_expenses)
        else:
            self.consume_all_inputs(0)
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
            default_admin_training_percent=20,
            default_leave_percent=20,
            default_avg_oh_salary=75e3,
            default_avg_line_salary=60e3,
            # todo: implement
            default_hours_training=100
            ):
        super(StaffProcess, self).__init__(name)

        # Define Inputs
        self.add_input('Staff Budget', 'staff$')
        self.add_input('Workplaces Available', 'workspace#')

        # Define Outputs
        self.add_output('Overhead work hrs', 'OH_work_hr')
        self.add_output('Line staff work hrs', 'LS_work_hr')
        self.add_output('Budgetary Surplus', 'surplus$')
        self.add_output('Staff Expenses', 'staffExpense$')

        # Define Properties
        self.add_property(
            'staff #',
            'total_staff_no',
            merlin.ProcessProperty.PropertyType.number_type,
            default_line_staff_no+default_oh_staff_no,
            read_only=True
        )
        self.add_property(
            'line staff #',
            'line_staff_no',
            merlin.ProcessProperty.PropertyType.number_type,
            default_line_staff_no
        )
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
            'admin & training [%]',
            'admin_training_percent',
            merlin.ProcessProperty.PropertyType.number_type,
            default_admin_training_percent
        )
        self.add_property(
            'annual leave [%]',
            'leave_percent',
            merlin.ProcessProperty.PropertyType.number_type,
            default_leave_percent
        )
        self.add_property(
            'avg annual overhead salary',
            'avgOHSalary',
            merlin.ProcessProperty.PropertyType.number_type,
            default_avg_oh_salary
        )
        self.add_property(
            'avg annual line salary',
            'avgLineSalary',
            merlin.ProcessProperty.PropertyType.number_type,
            default_avg_line_salary
        )
        self.add_property(
            'span of control',
            'span_of_control',
            merlin.ProcessProperty.PropertyType.number_type,
            default_hours_training
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

        line_staff_no = self.get_prop_value("line_staff_no")
        overhead_staff_no = self.get_prop_value("oh_staff_no")
        working_hours_per_week = self.get_prop_value("hours_per_week")
        working_weeks_per_year = 52  # this won't change that quickly, I guess
        professional_training = self.get_prop_value(
            "admin_training_percent"
        )
        leave = self.get_prop_value("leave_percent")
        avg_line_salary = self.get_prop_value("avgLineSalary")
        avg_overhead_salary = self.get_prop_value("avgOHSalary")
        training_period = self.get_prop_value("hours_training")  # todo!
        span_of_control = self.get_prop_value("span_of_control")

        staff_expenses = self.get_input_available("Staff Budget")
        staff_accommodated = self.get_input_available("Workplaces Available")

        FTE_hours = (working_hours_per_week * working_weeks_per_year *
                     (1.0-professional_training/100) * (1.0-leave/100))

        overhead_staff_work_hr = overhead_staff_no * FTE_hours / 12.0

        line_staff_work_hr = (min(line_staff_no,
                                  overhead_staff_no*span_of_control) *
                              FTE_hours / 12.0)

        used_staff_expenses = (
            (avg_line_salary * line_staff_no) +
            (avg_overhead_salary * overhead_staff_no) / 12.0
        )

        sufficient_funding = (
            staff_expenses >= used_staff_expenses
        )

        sufficient_accommodation = (
            staff_accommodated >= (overhead_staff_no + line_staff_no)
        )

        if not sufficient_funding:
            self.notify_insufficient_input(
                "Staff Budget",
                staff_expenses,
                used_staff_expenses
            )

        if not sufficient_accommodation:
            self.notify_insufficient_input(
                "Workplaces Available",
                staff_accommodated,
                overhead_staff_no + line_staff_no
            )

        if sufficient_funding and sufficient_accommodation:
            self.consume_input("Staff Budget", staff_expenses)
            self.consume_input("Workplaces Available", staff_accommodated)
            self.provide_output("Overhead work hrs", overhead_staff_work_hr)
            self.provide_output("Line staff work hrs", line_staff_work_hr)
            self.provide_output("Staff Expenses", used_staff_expenses)
            self.provide_output("Budgetary Surplus",
                                staff_expenses-used_staff_expenses)
        else:
            self.consume_all_inputs(0)
            self.write_zero_to_all()


class ICTDesktopContract(merlin.Process):

    def __init__(
            self,
            desktops_per_staff=0,
            cost_per_desktop=0,
            contract_ohwork_hr=1,
            name="Desktop Contract"):
        super(ICTDesktopContract, self).__init__(name)

        # Define Inputs
        self.add_input('overhead_staff_work_hr', 'OH_work_hr')
        self.add_input('contract_budget', 'other$')
        self.add_input('staff_accommodated', 'accommodatedStaff#')

        # Define Outputs
        self.add_output('desktops_accomodated', 'desktops')
        self.add_output('desktop_contract_overhead_work_hr', 'DC_OH_work_hr')
        self.add_output('budget_surplus', 'DC_other_exp')

        # Define Properties
        self.add_property(
            'Desktops / Staff',
            'desktops_per_staff',
            merlin.ProcessProperty.PropertyType.number_type,
            desktops_per_staff
        )

        self.add_property(
            'Cost / Desktop',
            'cost_per_desktop',
            merlin.ProcessProperty.PropertyType.number_type,
            cost_per_desktop
        )

        self.add_property(
            'Desktop Contract Overhead Staff',
            'desktop_contract_ohswork_hr',
            merlin.ProcessProperty.PropertyType.number_type,
            contract_ohwork_hr
        )

    def reset(self):
        pass

    def compute(self, tick):

        # Calculations
        budget_consumed = (
            self.get_prop_value('desktops_per_staff') *
            self.get_prop_value('cost_per_desktop') *
            self.get_input_available('staff_accommodated')
        )

        # Constraints
        contract_managed = (
            self.get_input_available('overhead_staff_work_hr') >=
            self.get_prop_value('desktop_contract_ohswork_hr')
        )

        contract_funded = (
            self.get_input_available('contract_budget') >=
            budget_consumed
        )

        # Constraint notifications
        if not contract_managed:
            self.notify_insufficient_input(
                'overhead_staff_work_hr',
                self.get_input_available('overhead_staff_work_hr'),
                self.get_prop_value('desktop_contract_ohswork_hr')
            )

        if not contract_funded:
            self.notify_insufficient_input(
                'contract_budget',
                self.get_input_available('contract_budget'),
                budget_consumed
            )

        # Process inputs and outputs
        if contract_managed and contract_funded:

            # Consume Inputs
            self.consume_input(
                'overhead_staff_work_hr',
                self.get_prop_value('desktop_contract_ohswork_hr')
            )

            self.consume_input(
                'contract_budget',
                budget_consumed
            )

            # Provide Outputs

            self.provide_output(
                'desktops_accomodated',
                (
                    self.get_input_available('staff_accommodated') *
                    self.get_prop_value('desktops_per_staff')
                )
            )

            self.provide_output(
                'internal_desktop_overhead_work_hr',
                self.get_input_available('overhead_staff_work_hr')
            )

            self.provide_output(
                'budget_surplus',
                self.get_input_available('contract_budget')
            )

        else:
            self.consume_all_inputs(0)
            self.write_zero_to_all()


class InternalICTDesktopService(merlin.Process):

    def __init__(
            self,
            actual_desktops=0,
            desktops_per_staff=0,
            actual_it_staff=0,
            it_staff_per_desktop=0,
            value_per_desktop=0,
            cost_per_desktop=0,
            name="Internal ICT Desktop Service"):
        super(InternalICTDesktopService, self).__init__(name)

        # Define Inputs
        self.add_input('staff_accommodated', 'accommodatedStaff#')
        self.add_input('overhead_staff_work_hr', 'OH_work_hr')
        self.add_input('ict_budget', 'other$')

        # Define Outputs
        self.add_output('desktops_accomodated', 'desktops')
        self.add_output('internal_desktop_overhead_work_hr', 'IDS_OH_work_hr')
        self.add_output('budget_surplus', 'IDS_other_exp')
        self.add_output("IT depreciation expenses",
                        "it_depreciation_expenses$")

        # Define Process Properties
        self.add_property(
            'Actual Desktops',
            'actual_desktops',
            merlin.ProcessProperty.PropertyType.number_type,
            actual_desktops
        )

        self.add_property(
            'Minimum Desktops / Staff',
            'min_desktop_per_staff',
            merlin.ProcessProperty.PropertyType.number_type,
            desktops_per_staff
        )

        self.add_property(
            'Actual IT Staff',
            'actual_it_staff',
            merlin.ProcessProperty.PropertyType.number_type,
            actual_it_staff
        )

        self.add_property(
            'Minimum IT Staff / Desktop',
            'min_it_staff_per_desktop',
            merlin.ProcessProperty.PropertyType.number_type,
            it_staff_per_desktop
        )

        self.add_property(
            'Acquisition Value [$] / Desktop',
            'value_per_desktop',
            merlin.ProcessProperty.PropertyType.number_type,
            value_per_desktop
        )

        self.add_property(
            'Maintenance Cost / Desktop',
            'maintenance_cost_per_desktop',
            merlin.ProcessProperty.PropertyType.number_type,
            cost_per_desktop
        )

    def reset(self):
        pass

    def compute(self, tick):

        # Calculations
        overhead_work_hr_required = (
            self.get_prop_value('min_it_staff_per_desktop') *
            self.get_prop_value('actual_desktops')
        )

        budget_required = (
            self.get_prop_value('actual_desktops') *
            (
                self.get_prop_value('maintenance_cost_per_desktop') +
                self.get_prop_value('value_per_desktop')
            )
        )

        ids_oh_work_hrs = (
            self.get_input_available('overhead_staff_work_hr') -
            self.get_prop_value('actual_it_staff')
        )

        # Constraints
        sufficient_overhead = (
            self.get_input_available('overhead_staff_work_hr') >=
            overhead_work_hr_required
        )

        sufficient_budget = (
            self.get_input_available('ict_budget') >=
            budget_required
        )

        sufficient_accomodation = (
            self.get_input_available('staff_accommodated') >=
            self.get_prop_value('actual_it_staff')
        )

        # Constraint notifications
        if not sufficient_overhead:
            self.notify_insufficient_input(
                'overhead_staff_work_hr',
                self.get_input_available('overhead_staff_work_hr'),
                overhead_work_hr_required
            )

        if not sufficient_budget:
            self.notify_insufficient_input(
                'ict_budget',
                self.get_input_available('ict_budget'),
                budget_required
            )

        if not sufficient_accomodation:
            self.notify_insufficient_input(
                'staff_accommodated',
                self.get_input_available('staff_accommodated'),
                self.get_prop_value('actual_it_staff')
            )

        # Consume inputs and provide outputs
        if (
                sufficient_accomodation and
                sufficient_overhead and
                sufficient_budget
        ):

            self.consume_input(
                'staff_accommodated',
                self.get_prop_value('actual_it_staff')
            )

            self.consume_input(
                'overhead_staff_work_hr',
                overhead_work_hr_required
            )

            self.consume_input(
                'ict_budget',
                budget_required
            )

            self.provide_output(
                'desktops_accomodated',
                self.get_prop_value('actual_desktops')
            )

            self.provide_output(
                'internal_desktop_overhead_work_hr',
                ids_oh_work_hrs
            )

            self.provide_output(
                'budget_surplus',
                self.get_input_available('ict_budget')
            )

            self.provide_output(
                'IT depreciation expenses',
                0.0  # todo
            )

        else:
            self.consume_all_inputs(0)
            self.write_zero_to_all()


class RegistrationServiceProcess(merlin.Process):
    """
    started as a modified copy of StorageServiceProcess

    """

    def __init__(
            self,
            default_lifecycle=20,
            default_registration_price=1,
            default_ohwork_hr_lswork_hr_ratio=0.1,
            default_applications_processed_per_lswork_hr=10000,
            name="Storage Service"
            ):
        super(RegistrationServiceProcess, self).__init__(name)

        # Define Inputs
        self.add_input('staff_expenses', 'staff$')
        self.add_input('rent_expenses', 'rent$')
        self.add_input('other_expenses', 'other$')
        self.add_input('line_staff_work_hr', 'LS_work_hr')
        self.add_input("desktops accommodated", "desktops")
        self.add_input('overhead_staff_work_hr', 'OH_work_hr')
        self.add_input('ids_overhead_staff_work_hr', 'IDS_OH_work_hr')
        # probably not needed in absence of another "File Logistics"
        # self.add_input('application_count', 'application_count')
        self.add_input('ids_spare_other_expenses', 'IDS_other_exp')
        self.add_input('used_rent_expenses', 'used_rent_expenses')
        self.add_input('used_staff_expenses', 'used_staff_expenses')
        self.add_input("IT depreciation expenses", "it_depreciation_expenses$")

        # Define Outputs
        self.add_output("operational_surplus", 'operational_surplus')
        self.add_output("applications_processed", 'applications_processed')
        self.add_output("service_revenue", 'service_revenue')
        self.add_output("budgetary_surplus", 'budgetary_surplus')

        # Define Properties
        # self.add_property(
        #     "lifecycle/years",
        #     'lifecycle',
        #     merlin.ProcessProperty.PropertyType.number_type,
        #     default_lifecycle
        # )

        self.add_property(
            "Registration Service Cost",
            'registration_cost',
            merlin.ProcessProperty.PropertyType.number_type,
            0,
            read_only=True
        )

        self.add_property(
            "Registration Price / $",
            'registration_price',
            merlin.ProcessProperty.PropertyType.number_type,
            default_registration_price
        )

        self.add_property(
            "Minimum OH work_hrs / LS work_hrs",
            'ohwork_hr_lswork_hr_ratio',
            merlin.ProcessProperty.PropertyType.number_type,
            default_ohwork_hr_lswork_hr_ratio
        )

        self.add_property(
            "Applications Processed / LS work_hr",
            'applications_processed_per_lswork_hr',
            merlin.ProcessProperty.PropertyType.number_type,
            default_applications_processed_per_lswork_hr
        )

    def reset(self):
        pass

    def compute(self, tick):
        # required to provide a value!
        self.get_prop('registration_cost').set_value(0.0)
        self.consume_all_inputs()
        self.write_zero_to_all()


#  create entities for record storage service
def createRecordStorage(sim=None):

    if sim is None:
        sim = merlin.Simulation()
    else:
        assert isinstance(sim, merlin.Simulation)

    # add a branch
    branch_e = merlin.Entity(sim, "Information Services Branch")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")

    # add the govRecordStorage capability
    storage_e = merlin.Entity(sim, "Storage Service")
    sim.add_entity(storage_e, parent=branch_e)
    branch_e.add_child(storage_e)
    storage_e.attributes.add("service")

    # add the budget entities/processes
    # staff budget
    TheStaffBudget = merlin.Entity(sim, "Budgeted - Staff Expenses")
    sim.add_entity(TheStaffBudget, is_source_entity=True)
    storage_e.add_child(TheStaffBudget)
    TheStaffBudget.attributes.add("budget")
    TheStaffBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "staff budget",
            'start_amount': 400000000,
            'budget_type': "staff$"
        })

    # rent budget
    TheRentBudget = merlin.Entity(sim, "Budgeted - Rent Expenses")
    sim.add_entity(TheRentBudget, is_source_entity=True)
    storage_e.add_child(TheRentBudget)
    TheRentBudget.attributes.add("budget")
    TheRentBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "rent budget",
            'start_amount': 400000000,
            'budget_type': "rent$"
        })

    # other budget
    TheOtherBudget = merlin.Entity(sim, "Budgeted - Other Expenses")
    sim.add_entity(TheOtherBudget, is_source_entity=True)
    storage_e.add_child(TheOtherBudget)
    TheOtherBudget.attributes.add("budget")
    TheOtherBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "other budget",
            'start_amount': 400000000,
            'budget_type': "other$"
        })

    # add specific entities and their processes
    FileLogistics = merlin.Entity(sim, "File Logistics")
    sim.add_entity(FileLogistics)
    storage_e.add_child(FileLogistics)
    FileLogistics.create_process(
        OutsourcedFileLogisticsProcess,
        {
            'name': "file logistics process",
            'contracted_volumes': 1e4,
            'actual_volumes': 1.1e4,
            'contract_cost': 100000,
            'overage_cost_per_file': 10,
            'required_management_work_hr': 1,
            'default_contract_length': 6
        })

    FileLogistics.attributes.add("external capability")

    StaffAccommodation = merlin.Entity(sim, "Staff Accommodation")
    sim.add_entity(StaffAccommodation)
    storage_e.add_child(StaffAccommodation)
    StaffAccommodation.create_process(
        StaffAccommodationProcess,
        {
            'name': "staff accommodation",
            'default_cost_m2': 400,
            'default_area_m2': 3500,
            'default_area_per_staff_m2': 15.0,
            'default_lease_term': 5
        })
    StaffAccommodation.attributes.add("resource")

    LineStaffRes = merlin.Entity(sim, "Staff")
    sim.add_entity(LineStaffRes)
    storage_e.add_child(LineStaffRes)
    LineStaffRes.create_process(
        StaffProcess,
        {
            'name': "line staff resource process",
            'default_line_staff_no': 100,
            'default_oh_staff_no': 11,
            'default_hours_per_week': 40.0,
            'default_admin_training_percent': 20,
            'default_leave_percent': 20,
            'default_avg_oh_salary': 75e3,
            'default_avg_line_salary': 60e3,
            'default_hours_training': 100
        })

    LineStaffRes.attributes.add("resource")

    StorageFacility = merlin.Entity(sim, "Storage Service")
    sim.add_entity(StorageFacility)
    storage_e.add_child(StorageFacility)
    StorageFacility.create_process(
        StorageServiceProcess,
        {
            'name': "storage facility process",
            'default_storage_fee': 1,
            'default_files_handled_per_lswork_hr': 20,
            "default_annual_storage_rent": 1.0e4
        })

    StorageFacility.attributes.add("asset")

    opSurplus = merlin.Output("opsurplus$",
                              name="Operational Surplus")
    sim.add_output(opSurplus)
    sim.connect_output(StorageFacility, opSurplus)

    # todo: need an expectation
    filesStored = merlin.Output("file#",
                                name="Additional Files Stored")
    sim.add_output(filesStored)
    sim.connect_output(StorageFacility, filesStored)

    # need an expectation
    serviceRevenue = merlin.Output("revenue$",
                                   name="Service Revenue")
    sim.add_output(serviceRevenue)
    sim.connect_output(StorageFacility, serviceRevenue)

    # need an expectation
    budgetarySurplus = merlin.Output("surplus$",
                                     name="Budgetary Surplus")
    sim.add_output(budgetarySurplus)
    sim.connect_output(StorageFacility, budgetarySurplus)  # for other
    sim.connect_output(LineStaffRes, budgetarySurplus)  # for staff
    sim.connect_output(StaffAccommodation, budgetarySurplus)  # for rent

    sim.connect_entities(TheRentBudget, StaffAccommodation, "rent$")

    sim.connect_entities(TheStaffBudget, LineStaffRes, "staff$")
    sim.connect_entities(StaffAccommodation,
                         LineStaffRes,
                         "workspace#")

    sim.connect_entities(LineStaffRes, FileLogistics, "OH_work_hr")
    sim.connect_entities(TheOtherBudget, FileLogistics, "other$")

    sim.connect_entities(FileLogistics, StorageFacility, "other$")
    sim.connect_entities(FileLogistics, StorageFacility, "file#")
    sim.connect_entities(LineStaffRes, StorageFacility, "LS_work_hr")
    sim.connect_entities(StaffAccommodation, StorageFacility,
                         "accommodationExpense$")
    sim.connect_entities(LineStaffRes, StorageFacility, "staffExpense$")
    sim.connect_entities(FileLogistics, StorageFacility, "logisticExpense$")

    return sim


def createRegistrationService(sim=None):
    # right now this is the registration service with inhouse desktops.
    # this function will change to have optionally the external and
    # later both.

    # this procedure might add this branch to an existing model.

    if sim is None:
        sim = merlin.Simulation()
    else:
        assert isinstance(sim, merlin.Simulation)

    # add a branch
    branch_e = merlin.Entity(sim, "Registration Services Branch")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")

    # add the registration service
    registration_e = merlin.Entity(sim, "Registration Service")
    sim.add_entity(registration_e, parent=branch_e)
    branch_e.add_child(registration_e)
    registration_e.attributes.add("service")

    # add the budget entities/processes
    # staff budget
    TheStaffBudget = merlin.Entity(sim, "Budgeted - Staff Expenses")
    sim.add_entity(TheStaffBudget, is_source_entity=True)
    registration_e.add_child(TheStaffBudget)
    TheStaffBudget.attributes.add("budget")
    TheStaffBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "staff budget",
            'start_amount': 4000000,
            'budget_type': "staff$"
        })

    # rent budget
    TheRentBudget = merlin.Entity(sim, "Budgeted - Rent Expenses")
    sim.add_entity(TheRentBudget, is_source_entity=True)
    registration_e.add_child(TheRentBudget)
    TheRentBudget.attributes.add("budget")
    TheRentBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "rent budget",
            'start_amount': 4000000,
            'budget_type': "rent$"
        })

    # other budget, provides for IT as well
    TheOtherBudget = merlin.Entity(sim, "Budgeted - Other Expenses")
    sim.add_entity(TheOtherBudget, is_source_entity=True)
    registration_e.add_child(TheOtherBudget)
    TheOtherBudget.attributes.add("budget")
    TheOtherBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "other budget",
            'start_amount': 4000000,
            'budget_type': "other$"
        })

    # file logistics is no longer existing
    # FileLogistics = merlin.Entity(sim, "File Logistics")

    StaffAccommodation = merlin.Entity(sim, "Staff Accommodation")
    sim.add_entity(StaffAccommodation)
    registration_e.add_child(StaffAccommodation)
    StaffAccommodation.create_process(
        StaffAccommodationProcess,
        {
            'name': "staff accommodation",
            'default_cost_m2': 400,
            'default_area_m2': 3500,
            'default_area_per_staff_m2': 15.0,
            'default_lease_term': 5
        })
    StaffAccommodation.attributes.add("resource")

    LineStaffRes = merlin.Entity(sim, "Staff")
    sim.add_entity(LineStaffRes)
    registration_e.add_child(LineStaffRes)
    LineStaffRes.create_process(
        StaffProcess,
        {
            'name': "line staff resource process",
            'default_line_staff_no': 100,
            'default_oh_staff_no': 10,
            'default_hours_per_week': 40.0,
            'default_weeks_per_year': 52,
            'default_prof_training_percent': 20,
            'default_leave_percent': 20,
            'default_avg_oh_salary': 75e3,
            'default_avg_line_salary': 60e3,
            'default_hours_training': 100
        })

    LineStaffRes.attributes.add("resource")

    InhouseDesktops = merlin.Entity(sim, "Inhouse Desktop Service")
    sim.add_entity(InhouseDesktops)
    registration_e.add_child(InhouseDesktops)
    InhouseDesktops.create_process(
        InternalICTDesktopService,
        {
            # todo: set to reasonable values!
            'actual_desktops': 0,
            'desktops_per_staff': 1.0,
            'actual_it_staff': 0,
            'it_staff_per_desktop': 1.0/15.0,
            'value_per_desktop': 4000.0,
            'cost_per_desktop': 0
         })
    InhouseDesktops.attributes.add("resource")

    RegistrationFacility = merlin.Entity(sim, "Registration Service")
    sim.add_entity(RegistrationFacility)
    registration_e.add_child(RegistrationFacility)
    RegistrationFacility.create_process(
        RegistrationServiceProcess,
        {
            'name': "registration facility process",
            'default_lifecycle': 20,
            'default_registration_price': 1,
            'default_ohwork_hr_lswork_hr_ratio': 0.1,
            'default_applications_processed_per_lswork_hr': 10000
        })

    RegistrationFacility.attributes.add("asset")

    opSurplus = merlin.Output("operational_surplus",
                              name="operational surplus")
    sim.add_output(opSurplus)
    sim.connect_output(RegistrationFacility, opSurplus)

    # todo: need an expectation
    applProcessed = merlin.Output("applications_processed",
                                  name="applications processed")
    sim.add_output(applProcessed)
    sim.connect_output(RegistrationFacility, applProcessed)

    # need an expectation
    serviceRevenue = merlin.Output("service_revenue",
                                   name="service revenue")
    sim.add_output(serviceRevenue)
    sim.connect_output(RegistrationFacility, serviceRevenue)

    # need an expectation
    budgetarySurplus = merlin.Output("budgetary_surplus",
                                     name="budgetary surplus")
    sim.add_output(budgetarySurplus)
    sim.connect_output(RegistrationFacility, budgetarySurplus)

    # now connect all inputs of the services
    sim.connect_entities(TheStaffBudget, LineStaffRes, "staff$")
    sim.connect_entities(StaffAccommodation, LineStaffRes,
                         "accommodatedStaff#")

    # all inputs from Inhouse Desktop Service
    sim.connect_entities(StaffAccommodation, InhouseDesktops,
                         "accommodatedStaff#")
    sim.connect_entities(LineStaffRes, InhouseDesktops, "OH_work_hr")
    sim.connect_entities(TheOtherBudget, InhouseDesktops, "other$")

    # all inputs from RegistrationFacility
    sim.connect_entities(TheStaffBudget, RegistrationFacility, "staff$")
    sim.connect_entities(TheRentBudget, RegistrationFacility, "rent$")
    sim.connect_entities(TheOtherBudget, RegistrationFacility, "other$")
    sim.connect_entities(LineStaffRes, RegistrationFacility, "LS_work_hr")
    sim.connect_entities(InhouseDesktops, RegistrationFacility,
                         "desktops")
    sim.connect_entities(LineStaffRes, RegistrationFacility, "OH_work_hr")
    sim.connect_entities(InhouseDesktops,
                         RegistrationFacility,
                         "IDS_OH_work_hr")
    sim.connect_entities(InhouseDesktops, RegistrationFacility,
                         "IDS_other_exp")
    sim.connect_entities(StaffAccommodation, RegistrationFacility,
                         "used_rent_expenses")
    sim.connect_entities(LineStaffRes, RegistrationFacility,
                         "used_staff_expenses")
    sim.connect_entities(InhouseDesktops, RegistrationFacility,
                         "it_depreciation_expenses$")

    sim.connect_entities(TheRentBudget, StaffAccommodation, "rent$")

    return sim

if __name__ == "__main__":

    sim = createRecordStorage()

    sim.set_time_span(48)
    sim.run()
    result = list(sim.outputs)
    print(result[0].result, result[1].result)
