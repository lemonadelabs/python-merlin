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
        self.add_input('other_expenses', 'other$')
        self.add_input('used_rent_expenses', 'used_rent_expenses')
        self.add_input('used_staff_expenses', 'used_staff_expenses')

        # Define Outputs
        self.add_output("operational_surplus", 'operational_surplus')
        self.add_output("files_stored", 'files_stored')
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
            "Storage Cost",
            'storage_cost',
            merlin.ProcessProperty.PropertyType.number_type,
            0,
            read_only=True
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
        # Calculations

        try:
            storage_cost = (
                (
                    self.get_input_available('used_rent_expenses') +
                    self.get_input_available('used_staff_expenses') +
                    self.get_input_available('other_expenses') -
                    self.get_input_available('fl_spare_other_expenses')
                ) /
                self.get_input_available('file_count')
            )
            self.get_prop('storage_cost').set_value(storage_cost)
        except ZeroDivisionError:
            storage_cost = 0

        files_stored = (
            self.get_input_available('file_count') *
            self.get_input_available('line_staff_fte') *
            self.get_prop_value('files_handled_per_lsfte')
        )

        service_revenue = (
            self.get_input_available('file_count') *
            self.get_prop_value('files_handled_per_lsfte') *
            self.get_input_available('line_staff_fte') *
            self.get_prop_value('storage_fee')
        )

        operational_surplus = (
            service_revenue -
            (
                self.get_input_available('used_rent_expenses') +
                self.get_input_available('used_staff_expenses') +
                self.get_input_available('fl_spare_other_expenses')

            )
        )

        budgetary_surplus = (
            self.get_input_available('fl_spare_other_expenses') +
            self.get_input_available('staff_expenses') +
            self.get_input_available('rent_expenses') -
            (
                self.get_input_available('used_staff_expenses') +
                self.get_input_available('used_rent_expenses')
            )
        )

        budget_consumed = (
            (
                self.get_input_available('file_count') /
                self.parent.sim.num_steps
            ) * storage_cost
        )

        try:
            management_required = (
                self.get_input_available('line_staff_fte') /
                self.get_prop_value('ohfte_lsfte_ratio')
            )
        except ZeroDivisionError:
            management_required = 0

        # Constraints
        sufficient_managment = (
            self.get_input_available('overhead_staff_fte') >=
            management_required
        )

        sufficient_funding = (
            self.get_input_available('other_expenses') >= budget_consumed
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
                'other_expenses',
                budget_consumed
            )

            # Provide outputs

            self.provide_output(
                'files_stored',
                files_stored
            )

            self.provide_output(
                'service_revenue',
                service_revenue
            )

            self.provide_output(
                'operational_surplus',
                operational_surplus
            )

            self.provide_output(
                'budgetary_surplus',
                budgetary_surplus
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
        self.add_input('other_expenses', 'other$')

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
            self.get_prop_value('file_logistics_OHSfte'))

        contract_funded = (
            self.get_input_available('other_expenses') >=
            monthly_cost
        )

        # Notify constraint violations
        if not contract_managed:
            self.notify_insufficient_input(
                'overhead_staff_fte',
                self.get_input_available('overhead_staff_fte'),
                self.get_prop_value('file_logistics_OHSfte')
            )

        if not contract_funded:
            self.notify_insufficient_input(
                'other_expenses',
                self.get_input_available('other_expenses'),
                monthly_cost
            )

        if contract_funded and contract_managed:

            self.consume_input(
                'overhead_staff_fte',
                self.get_prop_value('file_logistics_OHSfte'))

            self.consume_input(
                'other_expenses',
                monthly_cost
            )

            self.provide_output(
                'file_count',
                self.get_prop_value('actual_volume'))

            self.provide_output(
                'FL_spare_other_expenses',
                monthly_cost
            )

        else:
            self.write_zero_to_all()


class StaffAccommodationProcess(merlin.Process):
    """
    Documentation of template process
    """

    def __init__(
            self,
            name="staff accommodation",
            default_cost_m2=10,
            default_area_m2=100,
            default_staff_per_area_m2=0.2,
            default_lease_term=5
            ):
        super(StaffAccommodationProcess, self).__init__(name)

        # Define Inputs
        self.add_input('rent_expenses', 'rent$')

        # Define Outputs
        self.add_output('staff_accommodated', 'accommodatedStaff#')
        self.add_output('used_rent_expenses', 'used_rent_expenses')

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
            'area [m²]/staff [#]',
            'area_per_staff_m2',
            merlin.ProcessProperty.PropertyType.number_type,
            default_staff_per_area_m2
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

        rent_expenses = self.get_input_available("rent_expenses")

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
            self.notify_insufficient_input("rent_expenses",
                                           rent_expenses,
                                           used_rent_expenses)

        if sufficient_funding and lease_still_on:
            self.consume_input("rent_expenses",
                               rent_expenses)

            self.provide_output("staff_accommodated",
                                staff_accommodated)
            self.provide_output("used_rent_expenses",
                                used_rent_expenses)
        else:
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
        self.add_input('staff_expenses', 'staff$')
        self.add_input('staff_accommodated', 'accommodatedStaff#')

        # Define Outputs
        self.add_output('OHSfte', 'OH_FTE')
        self.add_output('LSfte', 'LS_FTE')
        self.add_output('used_staff_expenses', 'used_staff_expenses')

        # Define Properties
        # todo: this should become a "calculated" or "read only" property
        self.add_property(
            'staff #',
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
            'professional training [%]',
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

        line_staff_no = self.get_prop_value("line_staff_no")
        overhead_staff_no = self.get_prop_value("oh_staff_no")
        working_hours_per_week = self.get_prop_value("hours_per_week")
        working_weeks_per_year = self.get_prop_value("weeks_per_year")
        professional_training = self.get_prop_value(
            "prof_training_percent"
        )
        leave = self.get_prop_value("leave_percent")
        avg_line_salary = self.get_prop_value("avgLineSalary")
        avg_overhead_salary = self.get_prop_value("avgOHSalary")
        training_period = self.get_prop_value("hours_training")
        
        staff_expenses = self.get_input_available("staff_expenses")
        staff_accommodated = self.get_input_available("staff_accommodated")

        try:
            overhead_staff_fte = (
                (
                    working_hours_per_week * working_weeks_per_year *
                    professional_training/100 * leave/100 * overhead_staff_no
                ) -
                ((overhead_staff_no / line_staff_no) * training_period)
            ) / 12.0
        except ZeroDivisionError:
            logging.info("Overhead Staff FTE calc Zero Division Error")
            overhead_staff_fte = 0

        try:
            line_staff_fte = (
                (
                    working_hours_per_week * working_weeks_per_year *
                    professional_training/100 * leave/100 * line_staff_no
                ) -
                (
                    (1-(overhead_staff_no / line_staff_no)) * training_period
                )
            ) / 12.0
        except ZeroDivisionError:
            logging.info("Line Staff FTE calc Zero Division Error")
            line_staff_fte = 0

        used_staff_expenses = (
            (avg_line_salary * line_staff_no) +
            (avg_overhead_salary * overhead_staff_no)
        )
        
        sufficient_funding = (
            staff_expenses >=
            (
                ((avg_overhead_salary * overhead_staff_no) +
                (avg_line_salary * line_staff_no)) /
                self.parent.sim.num_steps
            )
        )

        sufficient_accommodation = (
            staff_accommodated >= overhead_staff_no + line_staff_no
        )
        
        if not sufficient_funding:
            self.notify_insufficient_input(
                "staff_expenses",
                staff_expenses,
                used_staff_expenses
            )
        
        if not sufficient_accommodation:
            self.notify_insufficient_input(
                "staff_accommodated",
                staff_accommodated,
                overhead_staff_no + line_staff_no
            )
            
        if sufficient_funding and sufficient_accommodation:
            self.consume_input("staff_expenses", staff_expenses)
            self.consume_input("staff_accommodated", staff_accommodated)
            self.provide_output("OHSfte", overhead_staff_fte)
            self.provide_output("LSfte", line_staff_fte)
            self.provide_output("used_staff_expenses", used_staff_expenses)
        else:
            self.write_zero_to_all()


class ICTDesktopContract(merlin.Process):

    def __init__(
            self,
            desktops_per_staff=0,
            cost_per_desktop=0,
            contract_ohfte=1,
            name="Desktop Contract"):
        super(ICTDesktopContract, self).__init__(name)

        # Define Inputs
        self.add_input('overhead_staff_fte', 'OH_FTE')
        self.add_input('contract_budget', 'other$')
        self.add_input('staff_accommodated', 'accommodatedStaff#')

        # Define Outputs
        self.add_output('desktops_accomodated', 'desktops')
        self.add_output('desktop_contract_overhead_fte', 'DC_OH_FTE')
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
            'desktop_contract_ohsfte',
            merlin.ProcessProperty.PropertyType.number_type,
            contract_ohfte
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
            self.get_input_available('overhead_staff_fte') >=
            self.get_prop_value('desktop_contract_ohsfte')
        )

        contract_funded = (
            self.get_input_available('contract_budget') >=
            budget_consumed
        )

        # Constraint notifications
        if not contract_managed:
            self.notify_insufficient_input(
                'overhead_staff_fte',
                self.get_input_available('overhead_staff_fte'),
                self.get_prop_value('desktop_contract_ohsfte')
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
                'overhead_staff_fte',
                self.get_prop_value('desktop_contract_ohsfte')
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
                'internal_desktop_overhead_fte',
                self.get_input_available('overhead_staff_fte')
            )

            self.provide_output(
                'budget_surplus',
                self.get_input_available('contract_budget')
            )

        else:
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
        self.add_input('overhead_staff_fte', 'OH_FTE')
        self.add_input('ict_budget', 'other$')

        # Define Outputs
        self.add_output('desktops_accomodated', 'desktops')
        self.add_output('internal_desktop_overhead_fte', 'IDS_OH_FTE')
        self.add_output('budget_surplus', 'IDS_other_exp')

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
            'Value / Desktop',
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
        overhead_fte_required = (
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

        ids_oh_ftes = (
            self.get_input_available('overhead_staff_fte') -
            self.get_prop_value('actual_it_staff')
        )

        # Constraints
        sufficient_overhead = (
            self.get_input_available('overhead_staff_fte') >=
            overhead_fte_required
        )

        sufficient_budget = (
            self.get_input_available('ict_budget') >=
            budget_required
        )

        sufficient_accomodation = (
            self.get_input_available('staff_accommodated') >=
            self.get_input_available('actual_it_staff')
        )

        # Constraint notifications
        if not sufficient_overhead:
            self.notify_insufficient_input(
                'overhead_staff_fte',
                self.get_input_available('overhead_staff_fte'),
                overhead_fte_required
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

        # Consume inputs and outputs
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
                'overhead_staff_fte',
                overhead_fte_required
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
                'internal_desktop_overhead_fte',
                ids_oh_ftes
            )

            self.provide_output(
                'budget_surplus',
                self.get_input_available('ict_budget')
            )

        else:
            self.write_zero_to_all()


# create entities
def createRecordStorage():
    # this is the capability, right now

    sim = merlin.Simulation()
    sim.add_attributes(["branch", "service", "deliverable", "budget",
                        "asset", "resource", "external capability"])
    sim.add_unit_types(["files", "LS_FTE", "OH_FTE", "other$",
                        "used_rent_expenses", "used_staff_expenses",
                        "used_other_expenses", "files_stored",
                        "operational_surplus", "service_revenue",
                        "budgetary_surplus", "OH_FTE", "other$",
                        "files", "used_other_expenses", "FL_OH_FTE",
                        "FL_other_exp", "other$", "FL_OHSfte", "rent$",
                        "accommodatedStaff#", "used_rent_expenses",
                        "staff$", "accommodatedStaff#", "OH_FTE", "LS_FTE",
                        "used_staff_expenses", "service_revenue",
                        "budgetary_surplus", "operational_surplus",
                        "files_stored", "rent$", "staff$", "other$"
                        ])

    # add a branch
    branch_e = merlin.Entity(sim, "the branch")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")

    # add the govRecordStorage capability
    storage_e = merlin.Entity(sim, "storage")
    sim.add_entity(storage_e, parent=branch_e)
    branch_e.add_child(storage_e)
    storage_e.attributes.add("service")

    # add the budget entities/processes
    # staff budget
    TheStaffBudget = merlin.Entity(sim, "Staff Budget")
    sim.add_entity(TheStaffBudget, is_source_entity=True)
    storage_e.add_child(TheStaffBudget)
    TheStaffBudget.attributes.add("budget")
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
    TheRentBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "rent budget",
            'start_amount': 4000000,
            'budget_type': "rent$"
        })

    # other budget
    TheOtherBudget = merlin.Entity(sim, "Other Budget")
    sim.add_entity(TheOtherBudget, is_source_entity=True)
    storage_e.add_child(TheOtherBudget)
    TheOtherBudget.attributes.add("budget")
    TheOtherBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "other budget",
            'start_amount': 4000000,
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
            'contracted_volumes': 100,
            'actual_volumes': 100,
            'contract_cost': 1000,
            'overage_cost_per_file': 10,
            'required_management_fte': 1
        })

    FileLogistics.attributes.add("external capability")

    StaffAccommodation = merlin.Entity(sim, "Staff Accommodation")
    sim.add_entity(StaffAccommodation)
    storage_e.add_child(StaffAccommodation)
    StaffAccommodation.create_process(
        StaffAccommodationProcess,
        {
            'name': "staff accommodation",
            'default_cost_m2': 10,
            'default_area_m2': 100,
            'default_staff_per_area_m2': 0.2,
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
            'default_oh_staff_no': 10,
            'default_hours_per_week': 40.0,
            'default_weeks_per_year': 52,
            'default_prof_training_percent': 20,
            'default_leave_percent': 10,
            'default_avg_oh_salary': 70e3,
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
            'default_lifecycle': 20,
            'default_storage_fee': 1,
            'default_ohfte_lsfte_ratio': 0.1,
            'default_files_handled_per_lsfte': 10000
        })

    StorageFacility.attributes.add("asset")

    opSurplus = merlin.Output("operational_surplus",
                              name="operational surplus")
    sim.add_output(opSurplus)
    sim.connect_output(StorageFacility, opSurplus)

    # todo: need an expectation
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

    # now connect all inputs of the services
    sim.connect_entities(TheStaffBudget, StorageFacility, "staff$")
    sim.connect_entities(TheStaffBudget, LineStaffRes, "staff$")

    sim.connect_entities(TheRentBudget, StorageFacility, "rent$")
    sim.connect_entities(TheRentBudget, StaffAccommodation, "rent$")

    sim.connect_entities(TheOtherBudget, FileLogistics, "other$")
    sim.connect_entities(TheOtherBudget, StorageFacility, "other$")

    sim.connect_entities(StaffAccommodation,
                         LineStaffRes,
                         "accommodatedStaff#")
    sim.connect_entities(StaffAccommodation,
                         StorageFacility,
                         "used_rent_expenses")

    sim.connect_entities(LineStaffRes, StorageFacility, "OH_FTE")
    sim.connect_entities(LineStaffRes, FileLogistics, "OH_FTE")
    sim.connect_entities(LineStaffRes, StorageFacility, "LS_FTE")
    sim.connect_entities(LineStaffRes, StorageFacility, "used_staff_expenses")

    sim.connect_entities(FileLogistics, StorageFacility, "FL_OH_FTE")
    sim.connect_entities(FileLogistics, StorageFacility, "files")
    sim.connect_entities(FileLogistics, StorageFacility, "FL_other_exp")

    return sim

if __name__ == "__main__":

    sim = createRecordStorage()

    sim.set_time_span(48)
    sim.run()
    result = list(sim.outputs)
    print(result[0].result, result[1].result)
