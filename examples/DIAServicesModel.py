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
import math

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
                self.get_input_available('monthly operational budget')
            )

            self.consume_input(
                'file count',
                files_stored
            )

            self.consume_input(
                'accommodation expenses',
                self.get_input_available('accommodation expenses')
            )

            self.consume_input(
                'staff expenses',
                self.get_input_available('staff expenses')
            )

            self.consume_input(
                'logistics expenses',
                self.get_input_available('logistics expenses')
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
            self.get_prop_value('file_logistics_OHSwork_hr') / 12.0)

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
            staff_accommodated = math.floor(area / area_per_staff)
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
            default_hours_training=100,
            default_span_of_control=10
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
            default_span_of_control
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
            self.provide_output("Overhead work hrs",
                                # this is the remaining oh staff capacity
                                max(0.0, (overhead_staff_work_hr -
                                          line_staff_work_hr /
                                          span_of_control)))
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
            actual_desktops=0,
            cost_per_extra_desktop=0,
            contract_ohwork_hr=100,
            min_contract_no=0,
            base_contract_costs=0,
            contract_duration=6,
            name="Desktop Contract"):
        super(ICTDesktopContract, self).__init__(name)

        # Define Inputs
        self.add_input("desktops from other providers", "desktop#")
        self.add_input("IT expenses other providers", "ITexpense$")
        self.add_input('overhead_staff_work_hr', 'OH_work_hr')
        self.add_input('contract_budget', 'surplus$')

        # Define Outputs
        self.add_output('desktops provided', 'desktop#')
        self.add_output('IT expenses', "ITexpense$")
        self.add_output('budget_surplus', 'surplus$')
        self.add_output('remaining OH work hours', 'OH_work_hr')

        # Define Properties
        self.add_property(
            'actual desktops',
            'actual_desktops',
            merlin.ProcessProperty.PropertyType.number_type,
            actual_desktops
        )

        self.add_property(
            'Cost / extra Desktop',
            'cost_per_extra_desktop',
            merlin.ProcessProperty.PropertyType.number_type,
            cost_per_extra_desktop
        )

        self.add_property(
            'Contract Management OH hours',
            'desktop_contract_oh_work_hr',
            merlin.ProcessProperty.PropertyType.number_type,
            contract_ohwork_hr
        )

        self.add_property(
            "min desktops contracted",
            "min_desktop_contracted",
            merlin.ProcessProperty.PropertyType.number_type,
            min_contract_no
        )

        self.add_property(
            "annual base contract costs",
            "base_contract_costs",
            merlin.ProcessProperty.PropertyType.number_type,
            base_contract_costs
        )

        self.add_property(
            "contract duration/yrs",
            "contract_duration",
            merlin.ProcessProperty.PropertyType.number_type,
            contract_duration
        )

    def reset(self):
        pass

    def compute(self, tick):

        # pull in all values available
        desktops_from_others = self.get_input_available(
                                        "desktops from other providers")
        IT_expenses_others = self.get_input_available(
                                        "IT expenses other providers")
        oh_work_hrs = self.get_input_available(
                                        'overhead_staff_work_hr')
        budget = self.get_input_available('contract_budget')

        contract_duration = self.get_prop_value("contract_duration")
        base_contract_costs = self.get_prop_value("base_contract_costs")
        min_contract_no = self.get_prop_value("min_desktop_contracted")
        contract_ohwork_hr = self.get_prop_value("desktop_contract_oh_work_hr")
        cost_per_extra_desktop = self.get_prop_value("cost_per_extra_desktop")
        actual_desktops = self.get_prop_value("actual_desktops")

        # calculations
        expenses = (base_contract_costs +
                    max(0, actual_desktops-min_contract_no) *
                    cost_per_extra_desktop) / 12.0

        # constraints
        contract_managed = (oh_work_hrs >= contract_ohwork_hr / 12.0)
        sufficient_funding = (budget >= expenses)

        # Constraint notifications
        if not contract_managed:
            self.notify_insufficient_input(
                'overhead_staff_work_hr',
                self.get_input_available('overhead_staff_work_hr'),
                self.get_prop_value('desktop_contract_ohswork_hr')
            )

        # Process inputs and outputs
        if contract_managed and sufficient_funding:

            # Consume Inputs
            self.consume_input(
                "desktops from other providers",
                desktops_from_others
            )

            self.consume_input(
                "IT expenses other providers",
                IT_expenses_others
            )

            self.consume_input(
                   "overhead_staff_work_hr",
                   oh_work_hrs
            )

            self.consume_input(
                "contract_budget",
                budget
            )

            # Provide Outputs
            self.provide_output('desktops provided',
                                desktops_from_others+actual_desktops)
            self.provide_output('IT expenses',
                                IT_expenses_others+expenses)
            self.provide_output('budget_surplus',
                                budget-expenses)
            self.provide_output('remaining OH work hours',
                                oh_work_hrs-contract_ohwork_hr)

        else:
            self.consume_all_inputs(0)
            self.write_zero_to_all()


class InternalICTDesktopService(merlin.Process):

    def __init__(
            self,
            actual_desktops=0,
            it_hrs_per_desktop=0,
            acq_cost_per_desktop=0,
            maint_cost_per_desktop=0,
            depr_period=4,
            financial_charge_percent=8,
            life_time=6,
            name="Internal ICT Desktop Service"):
        super(InternalICTDesktopService, self).__init__(name)

        # Define Inputs
        self.add_input('line staff work hrs', 'LS_work_hr')
        self.add_input('IT budget', 'other$')

        # Define Outputs
        self.add_output('desktops provided', 'desktop#')
        self.add_output('budgetary surplus', 'surplus$')
        self.add_output("IT expenses", "ITexpense$")
        self.add_output('remaining line staff work hrs', 'LS_work_hr')

        # Define Process Properties
        self.add_property(
            'Actual Desktops',
            'actual_desktops',
            merlin.ProcessProperty.PropertyType.number_type,
            actual_desktops
        )

        self.add_property(
            'Annual Support Hours Per Desktop',
            'hrs_per_desktop',
            merlin.ProcessProperty.PropertyType.number_type,
            it_hrs_per_desktop
        )

        self.add_property(
            'Acquisition Costs / Desktop',
            'cost_per_desktop',
            merlin.ProcessProperty.PropertyType.number_type,
            acq_cost_per_desktop
        )

        self.add_property(
            "Desktop Lifetime",
            "life_time",
            merlin.ProcessProperty.PropertyType.number_type,
            life_time
        )

        self.add_property(
            'Annual Maintenance Cost / Desktop',
            'maintenance_cost_per_desktop',
            merlin.ProcessProperty.PropertyType.number_type,
            maint_cost_per_desktop
        )

        self.add_property(
            'depreciation period',
            'depreciation_period',
            merlin.ProcessProperty.PropertyType.number_type,
            depr_period
        )

        self.add_property(
            "financial charge %",
            "fin_charge_percent",
            merlin.ProcessProperty.PropertyType.number_type,
            financial_charge_percent
        )

    def reset(self):
        pass

    def compute(self, tick):

        # get Inputs
        work_hrs = self.get_input_available('line staff work hrs')
        it_budget = self.get_input_available('IT budget')
        # get Process Properties
        actual_desktops = self.get_prop_value('actual_desktops')
        it_hrs_per_desktop = self.get_prop_value('hrs_per_desktop')
        acq_cost_per_desktop = self.get_prop_value('cost_per_desktop')
        maint_cost_per_desktop = self.get_prop_value(
                                            'maintenance_cost_per_desktop')
        depr_period = self.get_prop_value('depreciation_period')
        financial_charge_percent = self.get_prop_value("fin_charge_percent")
        # life_time = self.get_prop_value("life_time")

        desktops_provided = actual_desktops

        work_hrs_required = desktops_provided * it_hrs_per_desktop / 12.0

        expenses = (desktops_provided * maint_cost_per_desktop +
                    # todo: think about that! is contained in depreciation...
                    # desktops_provided * acq_cost_per_desktop / life_time +
                    desktops_provided * acq_cost_per_desktop / depr_period +
                    desktops_provided * acq_cost_per_desktop *
                    financial_charge_percent / 100.0
                    ) / 12.0

        sufficient_budget = (
            it_budget >= expenses
        )

        sufficient_staffing = (
            work_hrs >= work_hrs_required
        )

        # Constraint notifications

        if not sufficient_budget:
            self.notify_insufficient_input(
                "IT budget",
                it_budget,
                expenses
            )

        if not sufficient_staffing:
            self.notify_insufficient_input(
                'line staff work hrs',
                work_hrs,
                work_hrs_required
            )

        # Consume inputs and provide outputs
        if (
                sufficient_staffing and
                sufficient_budget
        ):

            self.consume_input(
                'line staff work hrs', work_hrs
            )

            self.consume_input(
                'IT budget',
                it_budget
            )

            self.provide_output(
                'desktops provided',
                desktops_provided
            )

            self.provide_output(
                'remaining line staff work hrs',
                work_hrs - work_hrs_required
            )

            self.provide_output(
                'budgetary surplus',
                it_budget - expenses
            )

            self.provide_output(
                'IT expenses',
                expenses
            )

        else:
            self.consume_all_inputs(0)
            self.write_zero_to_all()


class RegistrationServiceProcess(merlin.Process):
    """
    registrations of successfully re-enacted dreams
    """

    def __init__(
            self,
            default_registration_fee=10.0,
            default_applications_processed_per_lswork_hr=10,
            default_applications_submitted=100000,
            name="Storage Service"
            ):
        super(RegistrationServiceProcess, self).__init__(name)

        # Define Inputs
        self.add_input('Staff Expenses', 'staffExpense$')
        self.add_input('Accommodation Expenses', 'accommodationExpense$')
        self.add_input('IT Expenses', 'ITexpense$')
        self.add_input('line staff work hours', 'LS_work_hr')
        self.add_input("desktops provided", "desktop#")

        # Define Outputs
        self.add_output("Applications Processed", 'appl#')
        # self.add_output("cost per registration", "cost_per_appl")
        self.add_output("Service Revenue", 'revenue$')
        self.add_output("Operational Surplus", 'opsurplus$')

        # Define Properties
        self.add_property(
            "Registration Fee / $",
            'registration_fee',
            merlin.ProcessProperty.PropertyType.number_type,
            default_registration_fee
        )

        self.add_property(
            "Applications Processed / LS work_hr",
            'applications_processed_per_lswork_hr',
            merlin.ProcessProperty.PropertyType.number_type,
            default_applications_processed_per_lswork_hr
        )

        self.add_property(
            "Applications Submitted Per Year",
            'applications_submitted',
            merlin.ProcessProperty.PropertyType.number_type,
            default_applications_submitted
        )

    def reset(self):
        pass

    def compute(self, tick):

        # get Inputs
        staff_expenses = self.get_input_available('Staff Expenses')
        accommodation_expenses = self.get_input_available('Accommodation Expenses')
        it_expenses = self.get_input_available('IT Expenses')
        work_hrs = self.get_input_available('line staff work hours')
        desktops = self.get_input_available("desktops provided")

        # get Properties
        registration_fee = self.get_prop_value("registration_fee")
        applications_processed_per_lswork_hr = self.get_prop_value(
                            'applications_processed_per_lswork_hr')
        applications_submitted = self.get_prop_value('applications_submitted')

        revenue = applications_submitted * registration_fee / 12.0

        total_expenses = (staff_expenses + accommodation_expenses +
                          it_expenses)

        sufficient_process_staff = (applications_submitted / 12.0 <=
                                    applications_processed_per_lswork_hr *
                                    work_hrs)

        monthly_work_hrs_pp = 52.0*40.0*0.8*0.8/12
        desktops_required = work_hrs / monthly_work_hrs_pp
        sufficient_desktops = (desktops >= desktops_required)

        if not sufficient_desktops:
            self.notify_insufficient_input(
                'desktops provided',
                desktops,
                desktops_required
            )

        if not sufficient_process_staff:
            self.notify_insufficient_input(
                'line staff work hours',
                work_hrs,
                (applications_submitted / 12.0 /
                 applications_processed_per_lswork_hr)
            )

        # Process inputs and outputs
        if sufficient_desktops and sufficient_process_staff:

            # Consume inputs

            self.consume_input(
                'line staff work hours',
                work_hrs
            )

            self.consume_input(
                'Staff Expenses',
                self.get_input_available('Staff Expenses')
            )

            self.consume_input(
                'Accommodation Expenses',
                self.get_input_available('Accommodation Expenses')
            )

            self.consume_input(
                'IT Expenses',
                self.get_input_available('IT Expenses')
            )

            self.consume_input(
                "desktops provided",
                self.get_input_available("desktops provided")
            )

            # Provide outputs
            self.provide_output(
                'Applications Processed',
                applications_submitted / 12.0
            )

            self.provide_output(
                'Service Revenue',
                revenue
            )

            self.provide_output(
                'Operational Surplus',
                revenue - total_expenses
            )

        else:
            self.consume_all_inputs(0)
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
    TheStaffBudget = merlin.Entity(sim, "Budgeted – Staff Expenses")
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
    TheRentBudget = merlin.Entity(sim, "Budgeted – Rent Expenses")
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
    TheOtherBudget = merlin.Entity(sim, "Budgeted – Other Expenses")
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
            'default_hours_training': 100,
            'default_span_of_control': 10
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


def createRegistrationService(sim=None, with_external_provider=False):
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
    service_name = "Registration Service"
    if with_external_provider:
        service_name += " using DaaS"
    registration_e = merlin.Entity(sim, service_name)
    sim.add_entity(registration_e, parent=branch_e)
    branch_e.add_child(registration_e)
    registration_e.attributes.add("service")

    # add the budget entities/processes
    # staff budget
    TheStaffBudget = merlin.Entity(sim, "Budgeted – Staff Expenses")
    sim.add_entity(TheStaffBudget, is_source_entity=True)
    registration_e.add_child(TheStaffBudget)
    TheStaffBudget.attributes.add("budget")
    TheStaffBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "staff budget",
            'start_amount': 80000000,
            'budget_type': "staff$"
        })

    # rent budget
    TheRentBudget = merlin.Entity(sim, "Budgeted – Rent Expenses")
    sim.add_entity(TheRentBudget, is_source_entity=True)
    registration_e.add_child(TheRentBudget)
    TheRentBudget.attributes.add("budget")
    TheRentBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "rent budget",
            'start_amount': 20000000,
            'budget_type': "rent$"
        })

    # other budget, provides for IT as well
    TheOtherBudget = merlin.Entity(sim, "Budgeted – Other Expenses")
    sim.add_entity(TheOtherBudget, is_source_entity=True)
    registration_e.add_child(TheOtherBudget)
    TheOtherBudget.attributes.add("budget")
    TheOtherBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "other budget",
            'start_amount': 8000000,
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
            'default_admin_training_percent': 20,
            'default_leave_percent': 20,
            'default_avg_oh_salary': 75e3,
            'default_avg_line_salary': 60e3,
            'default_hours_training': 100,
            'default_span_of_control': 10
        })

    LineStaffRes.attributes.add("resource")

    InhouseDesktops = merlin.Entity(sim, "In-house Desktop Service")
    sim.add_entity(InhouseDesktops)
    registration_e.add_child(InhouseDesktops)
    InhouseDesktops.create_process(
        InternalICTDesktopService,
        {
            # todo: set to reasonable values!
            'actual_desktops': 100,
            'it_hrs_per_desktop': 40.0,
            'acq_cost_per_desktop': 4000.0,
            'maint_cost_per_desktop': 400.0,
            'depr_period': 4,
            'financial_charge_percent': 8,
            'life_time': 6
         })
    InhouseDesktops.attributes.add("asset")

    RegistrationFacility = merlin.Entity(sim, "Registration Service")
    sim.add_entity(RegistrationFacility)
    registration_e.add_child(RegistrationFacility)
    RegistrationFacility.create_process(
        RegistrationServiceProcess,
        {
            'name': "registration facility process",
            'default_registration_fee': 50.0,
            'default_applications_processed_per_lswork_hr': 10,
            "default_applications_submitted": 1000000,
        })
    RegistrationFacility.attributes.add("asset")

    opSurplus = merlin.Output("opsurplus$",
                              name="Operational Surplus")
    sim.add_output(opSurplus)
    sim.connect_output(RegistrationFacility, opSurplus)

    # need an expectation
    applProcessed = merlin.Output("appl#",
                                  name="Applications Processed")
    sim.add_output(applProcessed)
    sim.connect_output(RegistrationFacility, applProcessed)

    # need an expectation
    serviceRevenue = merlin.Output("revenue$",
                                   name="Service Revenue")
    sim.add_output(serviceRevenue)
    sim.connect_output(RegistrationFacility, serviceRevenue)

    # need an expectation
    budgetarySurplus = merlin.Output("surplus$",
                                     name="Budgetary Surplus")
    sim.add_output(budgetarySurplus)
    # sim.connect_output(RegistrationFacility, budgetarySurplus)
    sim.connect_output(StaffAccommodation, budgetarySurplus)
    sim.connect_output(LineStaffRes, budgetarySurplus)

    sim.connect_entities(TheRentBudget, StaffAccommodation, "rent$")

    sim.connect_entities(TheStaffBudget, LineStaffRes, "staff$")
    sim.connect_entities(StaffAccommodation,
                         LineStaffRes,
                         "workspace#")

    # all inputs from Inhouse Desktop Service
    sim.connect_entities(LineStaffRes, InhouseDesktops, "LS_work_hr")
    sim.connect_entities(TheOtherBudget, InhouseDesktops, "other$")

    if with_external_provider:
        ExternalDesktops = merlin.Entity(sim, "External Desktop Service")
        sim.add_entity(ExternalDesktops)
        registration_e.add_child(ExternalDesktops)
        ExternalDesktops.create_process(
            ICTDesktopContract,
            {
                # todo: set to reasonable values!
                "actual_desktops": 0,
                "cost_per_extra_desktop": 0,
                "contract_ohwork_hr": 0,
                "min_contract_no": 0,
                "base_contract_costs": 0,
                "contract_duration": 6,
             })
        ExternalDesktops.attributes.add("external capability")

        sim.connect_entities(InhouseDesktops, ExternalDesktops, "desktop#")
        sim.connect_entities(LineStaffRes, ExternalDesktops, "OH_work_hr")
        sim.connect_entities(InhouseDesktops, ExternalDesktops, "surplus$")
        sim.connect_entities(InhouseDesktops, ExternalDesktops, "ITexpense$")

        # the output "remaining OH work hours" is left open.

        sim.connect_output(ExternalDesktops, budgetarySurplus)
        # inputs for RegistrationFacility
        sim.connect_entities(ExternalDesktops, RegistrationFacility,
                             "desktop#")
        sim.connect_entities(ExternalDesktops, RegistrationFacility,
                             "ITexpense$")
    else:
        # No external desktop provider
        sim.connect_output(InhouseDesktops, budgetarySurplus)
        # inputs for RegistrationFacility
        sim.connect_entities(InhouseDesktops, RegistrationFacility,
                             "desktop#")
        sim.connect_entities(InhouseDesktops, RegistrationFacility,
                             "ITexpense$")

    sim.connect_entities(StaffAccommodation, RegistrationFacility,
                         "accommodationExpense$")
    sim.connect_entities(InhouseDesktops, RegistrationFacility,
                         "LS_work_hr")
    sim.connect_entities(LineStaffRes, RegistrationFacility,
                         "staffExpense$")

    return sim


def createRegistrationServiceWExternalDesktops(sim=None):
    return createRegistrationService(sim, with_external_provider=True)

if __name__ == "__main__":

    # sim = createRecordStorage()
    sim = createRegistrationService(with_external_provider=True)

    sim.set_time_span(48)
    sim.run()
    result = list(sim.outputs)
    print(result[0].result, result[1].result)
