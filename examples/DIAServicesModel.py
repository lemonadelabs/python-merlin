"""
Created on 13/5/2016

..code-author:: Sam Win-Mason <sam@lemonadelabs.io>

This module provides an example services model for the first
phase of the Merlin project. It uses some classes from the other
exmaple files.
"""
from enum import Enum
from pymerlin import merlin
from pymerlin import processes
import logging
import math
import random

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
#                self.get_input_available('monthly line staff work hrs')
                (files_stored/self.get_prop_value('files_handled_per_lswork_hr')
                 if self.get_prop_value('files_handled_per_lswork_hr') > 0
                 else 0.0)
            )

            self.consume_input(
                'monthly operational budget',
                self.get_prop_value('storage_rent')/12.0
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
            "length of contract/yrs",
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
                self.get_prop_value('file_logistics_OHSwork_hr')/12
            )

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

        self.enable_rent_inflation = False
        self.rent_inflation = 0.012
        self.current_cost_per_area = None

    def reset(self):
        self.current_cost_per_area = None

    def compute(self, tick):

        cost_per_area = self.get_prop_value("cost_per_m2")
        area_per_staff = self.get_prop_value("area_per_staff_m2")
        area = self.get_prop_value("area_m2")
        lease_term = self.get_prop_value("lease_term")
        rent_expenses = self.get_input_available("rent expenses")

        if (self.current_cost_per_area is None) or (self.get_prop('cost_per_m2').changed):
            self.current_cost_per_area = cost_per_area

        # Calculate inflation
        if tick % 12.0 == 0.0 and self.enable_rent_inflation:
            self.current_cost_per_area += (self.rent_inflation * self.current_cost_per_area)

        try:
            staff_accommodated = math.floor(area / area_per_staff)
        except ZeroDivisionError:
            staff_accommodated = 0

        used_rent_expenses = self.current_cost_per_area*area

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
            default_hours_training=2400,
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
        # self.add_property(
        #     'staff #',
        #     'total_staff_no',
        #     merlin.ProcessProperty.PropertyType.number_type,
        #     default_line_staff_no+default_oh_staff_no,
        #     read_only=True
        # )
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

        # Layoff phase structure
        # duration = layoff event time offset
        # reduction % decrease from original pre-event number
        self.layoff_phases = [
            {
                'duration': 3,
                'reduction': 0.6
            },
            {
                'duration': 4,
                'reduction': 0.3
            },
            {
                'duration': 5,
                'reduction': 0.1
            }
        ]

        # The period over which new staff come on board
        self.staff_hire_period = 4

        # Training function parameters
        self.training_hours_per_month = 400.0

        # logistic function parameters
        self.m = 5.0 # curve slope
        self.k = 1.0 # function height
        self.b = 0.0 # y intercept
        self.c = 0.5 # inflection point offset

        # A list of tuples t where t[0] = number of staff
        # and t[1] = months trained so far
        self.training_cohorts = list()

        self.salary_growth = 0.012
        self.enable_salary_growth = False

        # internal flags and counters
        self.ls_adjustment_month = 0
        self.ohs_adjustment_month = 0
        self.actual_line_staff = -1
        self.actual_overhead_staff = -1
        self.ls_reduction_baseline = 0
        self.ohs_reduction_baseline = 0
        self.current_line_salary = None
        self.current_oh_salary = None


    def reset(self):
        self.current_line_salary = None
        self.current_oh_salary = None
        self.training_cohorts.clear()
        self.ls_adjustment_month = 0
        self.ohs_adjustment_month = 0
        self.actual_line_staff = -1
        self.actual_overhead_staff = -1
        self.ohs_reduction_baseline = -1
        self.ls_reduction_baseline = -1

    def _calculate_staff_fte(self,
                             baseline_fte_hours,
                             overhead_staff=False) -> float:
        # ((1 * k) / (1 + (EXP(-1 * m * (x - c))))) + b
        max_train_hours = self.get_prop_value('hours_training')
        staff_type = 'oh_staff' if overhead_staff else 'ls_staff'
        total_staff = self.actual_overhead_staff if overhead_staff else self.actual_line_staff
        staff_in_training = sum([c[staff_type] for c in self.training_cohorts])
        trained_staff = total_staff - staff_in_training

        # span of control handling
        if not overhead_staff:
            staff_controlled = self.get_prop_value("span_of_control") * self.actual_overhead_staff
            staff_uncontroled = max(0, (total_staff - staff_controlled))

            # remove uncontrolled staff from trained staff
            trained_staff_removed = min(trained_staff, staff_uncontroled)
            trained_staff -= trained_staff_removed
            staff_uncontroled -= trained_staff_removed
        else:
            staff_uncontroled = 0

        trained_staff_fte = (baseline_fte_hours * trained_staff) / 12.0
        training_staff_fte = 0.0

        for c in self.training_cohorts:
            assert c['train'] * self.training_hours_per_month <= max_train_hours

            if overhead_staff:
                effective_staff = c[staff_type]
            else:
                assert staff_uncontroled >= 0
                rem_staff = min(c[staff_type], staff_uncontroled)
                effective_staff = c[staff_type] - rem_staff
                staff_uncontroled -= rem_staff
                staff_uncontroled = max(0, staff_uncontroled)

            # logistic function implementation expects a normalised value between 0-1
            normalised_train_time = (c['train'] * self.training_hours_per_month) / max_train_hours

            # see constructor for expalnation of b,c,m,k logistic variables
            fte_modifier = (
                (1.0 * self.k) /
                (1.0 + math.exp(-1.0 * self.m * (normalised_train_time - self.c)))
            )

            # clamp result (should not be nessesary)
            fte_modifier = max(0, fte_modifier)
            fte_modifier = min(1.0, fte_modifier)

            training_staff_fte += (((baseline_fte_hours * effective_staff) / 12.0) * fte_modifier)
        return (training_staff_fte + trained_staff_fte)



    def compute(self, tick):

        # first tick init stuff
        if self.actual_overhead_staff == -1:
            self.actual_overhead_staff = self.get_prop_value('oh_staff_no')
            self.actual_line_staff = self.get_prop_value('line_staff_no')
            self.ohs_reduction_baseline = -1
            self.ls_reduction_baseline = -1

        line_staff_no = self.get_prop_value("line_staff_no")
        overhead_staff_no = self.get_prop_value("oh_staff_no")
        hours_training = self.get_prop_value("hours_training")

        new_training_cohort = None

        # Check for line staff adjustments
        if self.actual_line_staff != line_staff_no:
            if line_staff_no < self.actual_line_staff:

                # reducing staff...
                if self.ls_adjustment_month == 0:
                    self.ls_reduction_baseline = self.actual_line_staff

                layoff_phase = None

                # See if this is a month we are laying off staff
                for lp in self.layoff_phases:
                    if lp['duration'] == self.ls_adjustment_month:
                        layoff_phase = lp
                if layoff_phase:

                    staff_to_reduce = math.ceil(
                        float(self.ls_reduction_baseline) * layoff_phase['reduction'])
                    # print('ls_adjustment_month: {0}'.format(self.ls_adjustment_month))
                    # print('staff to reduce: {0}'.format(staff_to_reduce))
                    # print('reduction %: {0}'.format(layoff_phase['reduction']))
                    # print('tick: {0}'.format(tick))
                    self.actual_line_staff -= staff_to_reduce
                    # If due to rounding we have gone below out target then clamp to target
                    self.actual_line_staff = line_staff_no \
                        if self.actual_line_staff < line_staff_no else\
                        self.actual_line_staff
            else:
                # hire staff...
                # print('hiring staff')
                if self.ls_adjustment_month < self.staff_hire_period:
                    staff_hired = random.randint(0, (line_staff_no - self.actual_line_staff))
                    # print('ls staff_hired: {0}'.format(staff_hired))
                    self.actual_line_staff += staff_hired
                    new_training_cohort = {
                        'ls_staff' : staff_hired,
                        'oh_staff': 0,
                        'train': 0
                    }
                elif self.ls_adjustment_month == self.staff_hire_period:
                    self.actual_line_staff = line_staff_no
                    new_training_cohort = {
                        'ls_staff' : line_staff_no - self.actual_line_staff,
                        'oh_staff': 0,
                        'train': 0
                    }
            self.ls_adjustment_month += 1
        else:
            # No adjustments nessesary, reset variable
            self.ls_adjustment_month = 0

        # Check for line staff adjustments
        # TODO: refactor into a reusuable function rather than this dupilication
        if self.actual_overhead_staff != overhead_staff_no:
            if overhead_staff_no < self.actual_overhead_staff:

                # reducing staff...
                if self.ohs_adjustment_month == 0:
                    self.ohs_reduction_baseline = self.actual_overhead_staff

                layoff_phase = None

                # See if this is a month we are laying off staff
                for lp in self.layoff_phases:
                    if lp['duration'] == self.ohs_adjustment_month:
                        layoff_phase = lp
                if layoff_phase:
                    staff_to_reduce = math.ceil(
                        float(self.ohs_reduction_baseline) * layoff_phase[
                            'reduction'])
                    # print('oh_adjustment_month: {0}'.format(self.ohs_adjustment_month))
                    # print('staff to reduce: {0}'.format(staff_to_reduce))
                    # print('reduction %: {0}'.format(layoff_phase['reduction']))
                    # print('tick: {0}'.format(tick))
                    self.actual_overhead_staff -= staff_to_reduce
                    # If due to rounding we have gone below out target then clamp to target
                    self.actual_overhead_staff = overhead_staff_no \
                        if self.actual_overhead_staff < overhead_staff_no else \
                        self.actual_overhead_staff
            else:
                # hire staff...
                # print('hiring staff')
                if self.ohs_adjustment_month < self.staff_hire_period:
                    staff_hired = random.randint(0, (
                    overhead_staff_no - self.actual_overhead_staff))
                    # print('oh staff_hired: {0}'.format(staff_hired))
                    self.actual_overhead_staff += staff_hired
                    if new_training_cohort:
                        new_training_cohort['oh_staff'] = staff_hired
                    else:
                        new_training_cohort = {
                            'oh_staff' : staff_hired,
                            'ls_staff': 0,
                            'train': 0
                        }
                elif self.ohs_adjustment_month == self.staff_hire_period:
                    self.actual_overhead_staff = overhead_staff_no
                    if new_training_cohort:
                        new_training_cohort['oh_staff'] = (overhead_staff_no - self.actual_overhead_staff)
                    else:
                        new_training_cohort = {
                            'oh_staff': (overhead_staff_no - self.actual_overhead_staff),
                            'ls_staff': 0,
                            'train': 0
                        }

            self.ohs_adjustment_month += 1
        else:
            # No adjustments nessesary, reset variable
            self.ohs_adjustment_month = 0

        # age existing training cohorts
        for c in self.training_cohorts:
            c['train'] += 1

        # remove fully trained staff cohorts
        self.training_cohorts = \
            [c for c in self.training_cohorts
             if (c['train'] * self.training_hours_per_month) < hours_training]

        # add new cohort
        if new_training_cohort:
            self.training_cohorts.append(new_training_cohort)

        # print('actual: {0}'.format(self.actual_line_staff))
        # print('ls: {0}'.format(line_staff_no))

        working_hours_per_week = self.get_prop_value("hours_per_week")
        working_weeks_per_year = 52  # this won't change that quickly, I guess
        professional_training = self.get_prop_value(
            "admin_training_percent"
        )
        leave = self.get_prop_value("leave_percent")
        avg_line_salary = self.get_prop_value("avgLineSalary")
        avg_overhead_salary = self.get_prop_value("avgOHSalary")
        span_of_control = self.get_prop_value("span_of_control")

        if (self.current_line_salary is None) or (self.get_prop('avgLineSalary').changed):
            self.current_line_salary = avg_line_salary

        if (self.current_oh_salary is None) or (self.get_prop('avgOHSalary').changed):
            self.current_oh_salary = avg_overhead_salary

        # Calculate wage rises after 12 months
        if tick % 12.0 == 0.0 and self.enable_salary_growth:
            self.current_line_salary += (self.current_line_salary * self.salary_growth)
            self.current_oh_salary += (self.current_oh_salary * self.salary_growth)

        staff_expenses = self.get_input_available("Staff Budget")
        staff_accommodated = self.get_input_available("Workplaces Available")

        FTE_hours = (working_hours_per_week * working_weeks_per_year *
                     (1.0-professional_training/100) * (1.0-leave/100))

        overhead_staff_work_hr = self._calculate_staff_fte(FTE_hours, overhead_staff=True)
        line_staff_work_hr = self._calculate_staff_fte(FTE_hours)

        used_staff_expenses = (
            (self.current_line_salary * self.actual_line_staff) +
            (self.current_oh_salary * self.actual_overhead_staff) / 12.0
        )

        sufficient_funding = (
            staff_expenses >= used_staff_expenses
        )

        sufficient_accommodation = (
            staff_accommodated >= (self.actual_overhead_staff + self.actual_line_staff)
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
                self.actual_overhead_staff + self.actual_line_staff
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
                oh_work_hrs,
                contract_ohwork_hr
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
                                oh_work_hrs-contract_ohwork_hr / 12)

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
            "Desktop Lifetime [yrs]",
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
            'depreciation Period [yrs]',
            'depreciation_period',
            merlin.ProcessProperty.PropertyType.number_type,
            depr_period
        )

        self.add_property(
            "Financial Charge %",
            "fin_charge_percent",
            merlin.ProcessProperty.PropertyType.number_type,
            financial_charge_percent
        )

        # Currently non-exposed desktop depeciation/disposal settings
        # Starting desktop cohort assigning method
        self.random_cohort_spread = True

        # Starting desktop lifespan range in years, must be <= life_time
        self.starting_cohort_range = 6

        # The number of times starting desktops were purchased per year
        # must perfectly divide by 12
        self.cohorts_per_year = 3

        # data structure to hold cohorts for depreciating
        self.cohorts = list()

        # random seed value for testing predictability leave None for
        # default random.seed() gen
        self.random_seed = 7891011

        # A flag used to generate an initial scenario
        self._generated = False

        # Should desktops be auto-purchased to make up numbers?
        self.auto_purchase_cohorts = False


    def create_desktop_simulation(self):

        # Create starting cohorts
        num_starting_cohorts = self.starting_cohort_range * self.cohorts_per_year
        months_per_cohort =  (self.starting_cohort_range * 12) / num_starting_cohorts

        for i in range(0, num_starting_cohorts):
            cohort = dict()
            cohort['age'] = i * months_per_cohort
            cohort['desktops'] = 0
            self.cohorts.append(cohort)

        # Distribute existing desktops amongst starting cohorts
        try:
            desktops_to_distribute = int(self.get_prop_value('actual_desktops'))
            desktops_to_distribute = 0 if desktops_to_distribute < 0 else desktops_to_distribute
        except ValueError:
            desktops_to_distribute = 0

        if self.random_cohort_spread:
            for i in range(0, desktops_to_distribute):
                rand_index = random.randint(0, num_starting_cohorts - 1)
                self.cohorts[rand_index]['desktops'] += 1
        else:
            i = 0
            while desktops_to_distribute > 0:
                self.cohorts[i]['desktops'] += 1
                desktops_to_distribute -= 1
                i += 1
                if i == len(self.cohorts):
                    i = 0

        assert desktops_to_distribute == \
               sum([c['desktops'] for c in self.cohorts])


    def reset(self):
        self._generated = False
        if self.random_seed:
            random.seed(self.random_seed)
        self.cohorts.clear()

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
        life_time = self.get_prop_value("life_time")

        if not self._generated:
            self._generated = True
            self.create_desktop_simulation()

        # Do the disposal steps
        legacy_desktops = sum([c['desktops'] for c in self.cohorts])

        # Dispose of end-of-life desktop cohort
        cohorts_to_dispose = [c for c in self.cohorts if c['age'] > (life_time * 12.0)]
        for c in cohorts_to_dispose:
            self.cohorts.remove(c)

        # Get the number of desktops to dispose
        desktops_to_dispose = sum([c['desktops'] for c in cohorts_to_dispose])

        if ((legacy_desktops - desktops_to_dispose) < actual_desktops) and self.auto_purchase_cohorts:
            # We need to purchase a new cohort of pcs this month
            desktops_to_purchase = actual_desktops - (legacy_desktops - desktops_to_dispose)
            new_cohort = dict()
            new_cohort['desktops'] = desktops_to_purchase
            new_cohort['age'] = 0
            self.cohorts.append(new_cohort)
            desktops_provided = actual_desktops
        else:
            desktops_provided = (legacy_desktops - desktops_to_dispose)

        # age cohorts
        for c in self.cohorts:
            c['age'] += 1

        work_hrs_required = desktops_provided * it_hrs_per_desktop / 12.0

        expenses = (desktops_provided * maint_cost_per_desktop +
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

    class ApplicationsTrend(Enum):
        CONSTANT = 0
        DECLINE = 1
        INCREASE = 2
        RANDOM_FLUCTUATION = 3

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

        self.application_trend = RegistrationServiceProcess.ApplicationsTrend.DECLINE
        # sin + decline + jitter

        # Settings for the different application trends
        self.rate = 0.02
        self.jitter = 1000.0
        self.sin_magnitude = 30000
        self.random_range = 100000
        self.current_applications = None

    def _compute_applications(self, tick):
        applications_submitted = self.get_prop_value('applications_submitted')

        if (self.current_applications is None) or (self.get_prop('applications_submitted').changed):
            self.current_applications = applications_submitted

        if tick % 12 == 0:
            at = self.application_trend
            if at == RegistrationServiceProcess.ApplicationsTrend.DECLINE:
                self.current_applications -= (self.current_applications * self.rate)
            elif at == RegistrationServiceProcess.ApplicationsTrend.INCREASE:
                self.current_applications += (self.current_applications * self.rate)
            elif at == RegistrationServiceProcess.ApplicationsTrend.RANDOM_FLUCTUATION:
                self.current_applications += (random.randint(-self.random_range, self.random_range))

        # random.seed()
        # self.current_applications += float(random.randint(-self.jitter, self.jitter))
        # self.current_applications += math.sin(tick) * self.sin_magnitude



    def reset(self):
        self.current_applications = None

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

        self._compute_applications(tick)



        total_expenses = (staff_expenses + accommodation_expenses +
                          it_expenses)

        sufficient_process_staff = (self.current_applications / 12.0 <=
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
                (self.current_applications / 12.0 /
                 applications_processed_per_lswork_hr)
            )


        modified_current_applications = self.current_applications

        if not sufficient_desktops:
            # reduce applications processed if lacking desktops and by extension, staff
            desktop_deficit = (desktops_required - desktops) / desktops_required
            application_deficit = self.current_applications * desktop_deficit
            modified_current_applications -= application_deficit
            modified_current_applications = max(0, modified_current_applications)

        revenue = modified_current_applications * registration_fee / 12.0

        # Process inputs and outputs

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
            modified_current_applications / 12.0
        )

        self.provide_output(
            'Service Revenue',
            revenue
        )

        self.provide_output(
            'Operational Surplus',
            revenue - total_expenses
        )




#  create entities for record storage service
def createRecordStorage(branch_e=None):
    """
    :param Enitity branch_e: the branch to add the service to

    If `branch_e` is `None`, a simulation object with the
    "Information Services Branch" entity containing the service is
    created and returned.
    """

    if branch_e is None:
        sim = merlin.Simulation()
        # add a branch
        branch_e = merlin.Entity(sim, "Information Services Branch")
        sim.add_entity(branch_e, parent=None)
        branch_e.attributes.add("branch")
    else:
        assert (isinstance(branch_e, merlin.Entity) and
                "branch" in branch_e.attributes)
        sim = branch_e.sim

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
            'start_amount': 10.8e6,
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
            'start_amount': 4.0e6,
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
            'start_amount': 1e6,
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
            'contracted_volumes': 150e3,
            'actual_volumes': 125e3,
            'contract_cost': 150000,
            'overage_cost_per_file': 10,
            'required_management_work_hr': 1640,
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
            'default_area_m2': 500,
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
            'default_line_staff_no': 20,
            'default_oh_staff_no': 3,
            'default_hours_per_week': 40.0,
            'default_admin_training_percent': 20,
            'default_leave_percent': 20,
            'default_avg_oh_salary': 60e3,
            'default_avg_line_salary': 40e3,
            'default_hours_training': 100,
            'default_span_of_control': 12
        })

    LineStaffRes.attributes.add("resource")

    StorageFacility = merlin.Entity(sim, "Storage Service")
    sim.add_entity(StorageFacility)
    storage_e.add_child(StorageFacility)
    StorageFacility.create_process(
        StorageServiceProcess,
        {
            'name': "storage facility process",
            'default_storage_fee': 98,
            'default_files_handled_per_lswork_hr': 2000,
            "default_annual_storage_rent": 500e3
        })

    StorageFacility.attributes.add("asset")

    opSurplus = merlin.Output("opsurplus$",
                              name="Operational Surplus")
    sim.add_output(opSurplus)
    sim.connect_output(StorageFacility, opSurplus)

    # todo: need an expectation
    filesStored = merlin.Output("file#",
                                name="Additional Files Stored")
    filesStored.minimum = 12e4/12
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


def createRegistrationService(branch_e=None, with_external_provider=False):
    """
    :param Enitity branch_e: the branch to add the service to
    :param Bool with_external_provider: enables the external desktop provider

    If `branch_e` is `None`, a simulation object with the
    "Registration Services Branch" entity containing the service is
    created and the simulation object returned.

    if `with_external_provider` is True another entity "External Desktop
    Service" with process is added to the service.
    """

    # right now this is the registration service with inhouse desktops.
    # this function will change to have optionally the external and
    # later both.

    if branch_e is None:
        sim = merlin.Simulation()
        # add a branch
        branch_e = merlin.Entity(sim, "Registration Services Branch")
        sim.add_entity(branch_e, parent=None)
        branch_e.attributes.add("branch")
    else:
        assert (isinstance(branch_e, merlin.Entity) and
                "branch" in branch_e.attributes)
        sim = branch_e.sim

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
            'start_amount': 73e6,
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
            'start_amount': 18e6,
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
            'start_amount': 800e3,
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
            'default_area_m2': 1650,
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
            'default_hours_training': 2400,
            'default_span_of_control': 12
        })

    LineStaffRes.attributes.add("resource")

    InhouseDesktops = merlin.Entity(sim, "In-house Desktop Service")
    sim.add_entity(InhouseDesktops)
    registration_e.add_child(InhouseDesktops)
    InhouseDesktops.create_process(
        InternalICTDesktopService,
        {
            # todo: set to reasonable values!
            'actual_desktops': 110,
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
            'default_registration_fee': 85.0,
            'default_applications_processed_per_lswork_hr': 10,
            "default_applications_submitted": 1e6,
        })
    RegistrationFacility.attributes.add("asset")

    opSurplus = merlin.Output("opsurplus$",
                              name="Operational Surplus")
    sim.add_output(opSurplus)
    sim.connect_output(RegistrationFacility, opSurplus)

    # provide an expectation
    applProcessed = merlin.Output("appl#",
                                  name="Applications Processed")
    applProcessed.minimum = 360e3/12*2.82
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


def createIdentificationService(branch_e=None):
    """
    :param Enitity branch_e: the branch to add the service to

    If `branch_e` is `None`, a simulation object with the
    "Identification Services Branch" entity containing the service is
    created and the simulation object returned.
    """

    # right now this is the registration service with inhouse desktops.
    # this function will change to have optionally the external and
    # later both.

    # this procedure might add this service to an existing model.

    if branch_e is None:
        sim = merlin.Simulation()
        # add a branch
        branch_e = merlin.Entity(sim, "Identification Services Branch")
        sim.add_entity(branch_e, parent=None)
        branch_e.attributes.add("branch")
    else:
        assert (isinstance(branch_e, merlin.Entity) and
                "branch" in branch_e.attributes)
        sim = branch_e.sim

    # add the registration service
    service_name = "Identification Service"
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
            'start_amount': 36e6,
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
            'start_amount': 15e6,
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
            'start_amount': 800e3,
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
            'default_cost_m2': 300,
            'default_area_m2': 1050,
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
            'default_line_staff_no': 60,
            'default_oh_staff_no': 7,
            'default_hours_per_week': 40.0,
            'default_admin_training_percent': 20,
            'default_leave_percent': 20,
            'default_avg_oh_salary': 60e3,
            'default_avg_line_salary': 45e3,
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
            'actual_desktops': 70,
            'it_hrs_per_desktop': 40.0,
            'acq_cost_per_desktop': 4000.0,
            'maint_cost_per_desktop': 400.0,
            'depr_period': 4,
            'financial_charge_percent': 8,
            'life_time': 6
         })
    InhouseDesktops.attributes.add("asset")

    RegistrationFacility = merlin.Entity(sim, "Identification Service")
    sim.add_entity(RegistrationFacility)
    registration_e.add_child(RegistrationFacility)
    RegistrationFacility.create_process(
        RegistrationServiceProcess,
        {
            'name': "registration facility process",
            'default_registration_fee': 49.0,
            'default_applications_processed_per_lswork_hr': 10,
            "default_applications_submitted": 0.75e6,
        })
    RegistrationFacility.attributes.add("asset")

    opSurplus = merlin.Output("opsurplus$",
                              name="Operational Surplus")
    sim.add_output(opSurplus)
    sim.connect_output(RegistrationFacility, opSurplus)

    # need an expectation
    applProcessed = merlin.Output("appl#",
                                  name="Applications Processed")
    applProcessed.minimum = 60e3
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


def createAllServicesInOneModel():
    """
    creates a simulation with all three services nested as follows

    sim
       registration branch (attr branch)
          service registration service (attr service)
              nodes (div attrs)
       information service branch (attr branch)
           storage service (attr service)
                nodes (div attrs)
       identity service branch (attr branch)
            identity service (attr service)
                 nodes (div attrs)
    outputs from all services (as they are not entities, they have no containment)

    """

    sim = merlin.Simulation()

    branch_e = merlin.Entity(sim, "Identification Services Branch")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")
    createIdentificationService(branch_e)

    # add a branch
    branch_e = merlin.Entity(sim, "Information Services Branch")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")
    createRecordStorage(branch_e)

    branch_e = merlin.Entity(sim, "Registration Services Branch")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")
    createRegistrationServiceWExternalDesktops(branch_e)
    return sim


def createRegistrationAndKnowledgeBranch():
    """
    creates a simulation with all three services nested as follows

    sim
       Registration and Knowledge Services (attr branch)
          service registration service (attr service)
              nodes (div attrs)
           storage service (attr service)
                nodes (div attrs)
            identity service (attr service)
                 nodes (div attrs)
    outputs from all services (as they are not entities, they have no containment)
    """
    sim = merlin.Simulation()
    # add the one branch
    branch_e = merlin.Entity(sim, "Registration and Knowledge Services")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")

    createIdentificationService(branch_e)
    createRecordStorage(branch_e)
    createRegistrationServiceWExternalDesktops(branch_e)

    return sim

if __name__ == "__main__":

    # sim = createRecordStorage()
    sim = createAllServicesInOneModel()

    sim.set_time_span(48)
    sim.run()
    result = list(sim.outputs)
    print(result[0].result, result[1].result)
