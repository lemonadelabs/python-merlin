'''
Created on 29/03/2016

..code-author:: Achim Gaedke <Achim.Gaedke@lemonadelabs.io>

A printer with minimal staff required.
'''

import logging
from pymerlin import merlin
from pymerlin.test_merlin import BudgetProcess

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
        propStaffNo = merlin.ProcessProperty(
                    'staff Numbers',
                    property_type=merlin.ProcessProperty.PropertyType.int_type,
                    default=5,
                    parent=self)
        propAvgPay = merlin.ProcessProperty(
                'Avg Staff Pay',
                property_type=merlin.ProcessProperty.PropertyType.number_type,
                default=50000,
                parent=self)
        self.props = {"staffNo": propStaffNo,
                      "staffPay": propAvgPay}

        # set up the output/s
        outStaffBW = merlin.ProcessOutput('out_staffBW',
                                          'FTE')
        self.outputs = {"staff bandwidth": outStaffBW}

        # set up the input/s
        inBudget = merlin.ProcessInput("in_budget",
                                       "$")
        self.inputs = {"budget": inBudget}

    def compute(self, tick):

        budget_available = self.inputs["budget"].connector.value
        staff_no = self.props["staffNo"].get_value()
        # convert annual figure to monthly pay
        staff_pay = self.props["staffPay"].get_value()/12
        budget_required = staff_no * staff_pay
        if budget_available < budget_required:
            # not enough money there
            self.inputs["budget"].consume(budget_available)
            self.outputs["staff bandwidth"].connector.write(staff_no)
            raise merlin.InputRequirementException(
                        self,
                        self.inputs["budget"],
                        budget_available,
                        budget_required)

        # enough money there
        self.inputs["budget"].consume(budget_required)
        self.outputs["staff bandwidth"].connector.write(staff_no)


class ppPrinter(merlin.Process):

    def __init__(self, name="ppPrinter"):
        super(ppPrinter, self).__init__(name)
        propStaffNo = merlin.ProcessProperty(
                    'staff Numbers',
                    property_type=merlin.ProcessProperty.PropertyType.int_type,
                    default=5,
                    parent=self)

        propCostPerPP = merlin.ProcessProperty(
                'cost per print',
                property_type=merlin.ProcessProperty.PropertyType.number_type,
                default=20.0,
                parent=self)

        self.props = {"staffRequired": propStaffNo,
                      "costPerPrint": propCostPerPP}

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

        staff_available = self.inputs["staff"].connector.value
        staff_required = self.props["staffRequired"].get_value()

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
    sim.outputs.add(pp_delivered)

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
    e_budget.add_process(BudgetProcess("passportPrintingBudget",
                                       start_amount=400000))
    the_staff_process = ppStaff()
    the_staff_process.priority = -1  # pay the people first!
    e_staff.add_process(the_staff_process)
    e_printer.add_process(ppPrinter())

    # setup an apportioning bias for staff and printer budget
    budget_out_con = e_budget.get_output_by_type("$")
    budget_apportioning = {e_staff: 0.7, e_printer: 0.3}
    new_biases = []
    for ic, _ in budget_out_con.get_endpoints():
        # if entity not in the apportioning, then just give no funds
        new_biases.append((ic,
                           budget_apportioning.get(ic.parent, 0.0)))
    # set the endpoint biases
    budget_out_con.set_endpoint_biases(new_biases)

    return sim

if __name__ == "__main__":

    sim = IPSbranch()
    sim.run()
    result = list(sim.outputs)[0].result
    print(result)
