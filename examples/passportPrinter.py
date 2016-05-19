'''
Created on 29/03/2016

..code-author:: Achim Gaedke <Achim.Gaedke@lemonadelabs.io>

A printer with minimal staff required.
'''

import logging
from pymerlin import merlin
from pymerlin.processes import BudgetProcess

# Global logging settings
logging_level = logging.DEBUG
log_to_file = ''
logging.basicConfig(
    filename=log_to_file,
    level=logging_level,
    format='%(asctime)s: [%(levelname)s] %(message)s')


class ppStaff(merlin.Process):

    def __init__(self, name="ppStaff"):

        super(ppStaff, self).__init__(name)

        # set up the properties
        self.add_property(
                    'staff Numbers',
                    'staff Numbers',
                    merlin.ProcessProperty.PropertyType.int_type,
                    5)
        self.add_property(
                'Avg Staff Pay',
                'Avg Staff Pay',
                merlin.ProcessProperty.PropertyType.number_type,
                50000)

        # set up the output/s
        outStaffBW = merlin.ProcessOutput('out_staffBW',
                                          'FTE')
        self.outputs = {"staff bandwidth": outStaffBW}

        # set up the input/s
        inBudget = merlin.ProcessInput("in_budget",
                                       "$")
        self.inputs = {"budget": inBudget}

    def compute(self, tick):

        budget_available = self.get_input_available("budget")
        staff_no = self.get_prop_value("staff Numbers")
        # convert annual figure to monthly pay
        staff_pay = self.get_prop_value("Avg Staff Pay")/12
        budget_required = staff_no * staff_pay
        if budget_available < budget_required:
            # not enough money there
            self.consume_input("budget", budget_available)
            self.provide_output("staff bandwidth", staff_no)
            self.notify_insufficient_input("budget",
                                           budget_available,
                                           budget_required)

        # enough money there
        self.consume_input("budget", budget_required)
        self.provide_output("staff bandwidth", staff_no)


class ppPrinter(merlin.Process):

    def __init__(self, name="ppPrinter"):
        super(ppPrinter, self).__init__(name)
        self.add_property(
                    'staff Numbers',
                    'staffRequired',
                    merlin.ProcessProperty.PropertyType.int_type,
                    5)

        self.add_property(
                    'cost per print',
                    'costPerPrint',
                    merlin.ProcessProperty.PropertyType.number_type,
                    20.0)

        outPP = merlin.ProcessOutput("out_PassportsPrinted",
                                     "count")
        self.outputs = {"passportsPrinted": outPP}

        # set up the input/s
        inBudget = merlin.ProcessInput("in_budget",
                                       "$")
        inStaff = merlin.ProcessInput("in_staffNo",
                                      "FTE")
        self.inputs = {"budget": inBudget,
                       "staff": inStaff}

    def compute(self, tick):

        staff_available = self.get_input_available("staff")
        staff_required = self.get_prop_value("staffRequired")

        if staff_available < staff_required:
            self.outputs["passportsPrinted"].connector.write(0)
            raise merlin.InputRequirementException(
                                        self,
                                        self.inputs["staff"],
                                        staff_available,
                                        staff_required)

        self.inputs["staff"].consume(staff_required)

        budget_available = self.inputs["budget"].connector.value
        cost_per_print = self.props["costPerPrint"].get_value()

        if budget_available < 0.0:
            self.outputs["passportsPrinted"].connector.write(0)
            raise merlin.InputRequirementException(
                                        self,
                                        self.inputs["budget"],
                                        budget_available,
                                        0.0)

        passports = int(budget_available//cost_per_print)
        self.inputs["budget"].consume(passports*cost_per_print)
        self.outputs["passportsPrinted"].connector.write(passports)


def IPSbranch():

    sim = merlin.Simulation()
    sim.set_time_span(12)
    sim.add_attributes(["budget", "asset", "resource"])
    sim.add_unit_types(["FTE", "$", "count"])

    # define outputs
    pp_delivered = merlin.Output("count",
                                 name="passports printed")
    sim.add_output(pp_delivered)

    e_budget = merlin.Entity(name="budget",
                             attributes={'budget'})
    e_staff = merlin.Entity(name="staff",
                            attributes={"resource"})
    e_printer = merlin.Entity(name="printer",
                              attributes={"asset"})

    sim.add_entities([e_budget, e_staff, e_printer])
    sim.set_source_entities([e_budget])

    # connect all entities
    sim.connect_entities(e_budget, e_staff, "$")
    sim.connect_entities(e_budget, e_printer, "$")
    sim.connect_entities(e_staff, e_printer, "FTE")
    sim.connect_output(e_printer, pp_delivered)

    # and finally add the processes to the entities
    # so the processes are automatically hooked up to the
    # entities connectors
    e_budget.create_process(
        BudgetProcess,
        {
            'name': "passportPrintingBudget",
            'start_amount': 4000000,
        })

    e_staff.create_process(
        ppStaff,
        {
        })
    e_staff.get_processes()[0].priority = 10

    e_printer.create_process(
        ppPrinter,
        {
        })

    # setup an apportioning bias for staff and printer budget
    budget_out_con = e_budget.get_output_by_type("$")
    budget_apportioning = {e_staff: 0.7, e_printer: 0.3}
    new_biases = []
    for ic, _ in budget_out_con.get_endpoints():
        # if entity not in the apportioning, then just give no funds
        new_biases.append((ic,
                           budget_apportioning.get(ic.parent, 0.0)))
    # set the end-point biases
    budget_out_con.set_endpoint_biases(new_biases)

    return sim

if __name__ == "__main__":

    sim = IPSbranch()
    sim.run()
    result = list(sim.outputs)[0].result
    print(result)
