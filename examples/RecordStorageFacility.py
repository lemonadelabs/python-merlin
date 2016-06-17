'''
Created on 14/04/2016

..code-author:: Achim Gaedke <Achim.Gaedke@lemonadelabs.io>

'''

import math
import logging
from pymerlin import merlin, processes

# Global logging settings
logging_level = logging.INFO
log_to_file = ''
logging.basicConfig(
    filename=log_to_file,
    level=logging_level,
    format='%(asctime)s: [%(levelname)s] %(message)s')


class SubBudgetProcess(merlin.Process):

    def __init__(self, name="subBudgetProcess", **inputOutputs):
        super(SubBudgetProcess, self).__init__(name)

        # expecting 1 input, many outputs
        # each output can be qualified with some rules
        # there might be some global rules

        in_unit = inputOutputs["in_unit"]
        inBudget = merlin.ProcessInput("in_budget",
                                       in_unit)
        self.inputs = {"in_budget": inBudget}

        # set up the output/s
        for out_name, out_unit in inputOutputs.items():
            if out_name.startswith("out_"):
                # set up the input/s
                outBudget = merlin.ProcessOutput(out_name,
                                                 out_unit)

                self.outputs[out_name] = outBudget

    def compute(self, tick):

        # right now: split things evenly across budgets
        inputBudget = self.get_input_available("in_budget")
        no_outputs = len(self.outputs)

        for o in self.outputs.keys():
            self.provide_output(o, inputBudget/no_outputs)

        self.consume_input("in_budget", inputBudget)


class LineStaffProcess(merlin.Process):

    def __init__(self, name="lineStaffProcess"):
        super(LineStaffProcess, self).__init__(name)

        # set up the output/s
        outStaffBW = merlin.ProcessOutput('out_LineStaffBW',
                                          'lineFTE')
        self.outputs = {"line staff bandwidth": outStaffBW}

        # set up the input/s
        inLineStaff = merlin.ProcessInput("line staff pool",
                                          "lineStaffNo")
        inOHStaff = merlin.ProcessInput("overhead staff pool",
                                        "ohFTE")

        self.inputs = {"line staff no": inLineStaff,
                       "overhead staff no": inOHStaff}

        self.add_property("Training time",
                          "trainingTime",
                          merlin.ProcessProperty.PropertyType.number_type,
                          1)
        self.add_property("max utilisation", "maxUtil",
                          merlin.ProcessProperty.PropertyType.number_type,
                          0.8)

    def compute(self, tick):
        oh_staff_req = 1

        if oh_staff_req > self.get_input_available("overhead staff no"):
            self.provide_output("line staff bandwidth", 0.0)
            self.notify_insufficient_input(
                                "overhead staff no",
                                self.get_input_available("overhead staff no"),
                                oh_staff_req)

        staff_available = self.get_input_available("line staff no")
        util = self.get_prop_value("maxUtil")

        # todo: training time!

        self.consume_input("line staff no", staff_available)
        self.provide_output("line staff bandwidth", staff_available*util)


class StorageFacilityProcess(merlin.Process):

    def __init__(self, name="StorageFacilityProcess"):
        super(StorageFacilityProcess, self).__init__(name)

        # set up the output/s
        outFilesHandled = merlin.ProcessOutput('out_FilesHandled',
                                               'files handled')
        outFilesStored = merlin.ProcessOutput('out_FilesStored',
                                              'files stored')

        self.outputs = {"files stored": outFilesStored,
                        "files handled": outFilesHandled}

        # set up the input/s
        inLineStaff = merlin.ProcessInput('in_LineStaffBW',
                                          'lineFTE')
        inOHStaff = merlin.ProcessInput('in_OverheadStaffBW',
                                        'ohFTE')

        inRent = merlin.ProcessInput('in_Rent',
                                     'rent$')
        inMaintenance = merlin.ProcessInput('in_Maintenance',
                                            'maint$')
        opCosts = merlin.ProcessInput("in_OpCosts",
                                      "op$")
        fileLog = merlin.ProcessInput("in_FileLogistic",
                                      "file count")

        self.add_property("monthly rent", "rent",
                          merlin.ProcessProperty.PropertyType.number_type,
                          100000)
        self.add_property("monthly maintenance", "maintenance",
                          merlin.ProcessProperty.PropertyType.number_type,
                          100000)
        self.add_property("cost per access",
                          "costPerAccess",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)
        self.add_property("cost per storage",
                          "costPerStorage",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)
        self.add_property("staff time per access",
                          "timePerAccess",
                          merlin.ProcessProperty.PropertyType.number_type,
                          0.001)
        self.add_property("staff time per storage",
                          "timePerStorage",
                          merlin.ProcessProperty.PropertyType.number_type,
                          0.001)
        # this is no of access over no of storages
        self.add_property("ratio access to storage",
                          "rAccessStorage",
                          merlin.ProcessProperty.PropertyType.number_type,
                          0.1)
        self.add_property("minimum line staff",
                          "min line staff",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)
        self.add_property("ratio overhead to line staff",
                          "rOverheadLineStaff",
                          merlin.ProcessProperty.PropertyType.number_type,
                          0.1)

        self.inputs = {"line staff bandwidth": inLineStaff,
                       "overhead staff bandwidth": inOHStaff,
                       "rent": inRent,
                       "maintenance": inMaintenance,
                       "operational costs": opCosts,
                       "file logistic bandwidth": fileLog}

    def compute(self, tick):

        rentReq = self.get_prop_value("rent")
        rentProv = self.get_input_available("rent")
        if rentReq > rentProv:
            self.provide_output("files stored", 0)
            self.provide_output("files handled", 0)
            self.notify_insufficient_input("rent",
                                           rentProv, rentReq)
        else:
            self.consume_input("rent", rentReq)

        maintReq = self.get_prop_value("maintenance")
        maintProv = self.get_input_available("maintenance")
        if maintReq > maintProv:
            self.provide_output("files stored", 0)
            self.provide_output("files handled", 0)
            self.notify_insufficient_input("maintenance",
                                           maintProv, maintReq)
        else:
            self.consume_input("maintenance", maintReq)

        lineStaffReq = self.get_prop_value("min line staff")
        lineStaffProv = self.get_input_available("line staff bandwidth")
        if lineStaffReq > lineStaffProv:
            self.provide_output("files stored", 0)
            self.provide_output("files handled", 0)
            self.notify_insufficient_input("line staff bandwidth",
                                           lineStaffProv, lineStaffReq)

        ratio = self.get_prop_value("rAccessStorage")

        storageByOpBudget = (self.get_input_available("operational costs") /
                             (self.get_prop_value("costPerStorage") +
                              ratio*self.get_prop_value("costPerAccess")))
        storageByStaff = (self.get_input_available("line staff bandwidth") /
                          (self.get_prop_value("timePerStorage") +
                           ratio*self.get_prop_value("timePerAccess")))
        storageByLogistics = (
                        self.get_input_available("file logistic bandwidth") /
                        (1 + ratio))

        # now calculate the documents, which can be handled:
        storageFiles = math.floor(min(storageByOpBudget,
                                      storageByStaff,
                                      storageByLogistics))

        opCosts = storageFiles*(self.get_prop_value("costPerStorage") +
                                ratio*self.get_prop_value("costPerAccess"))
        lineStaff = storageFiles*(self.get_prop_value("timePerStorage") +
                                  ratio*self.get_prop_value("timePerAccess"))
        fileLog = storageFiles*(1+ratio)

        overheadReq = self.get_prop_value("rOverheadLineStaff")*lineStaff
        overheadProv = self.get_input_available("overhead staff bandwidth")
        if overheadReq > overheadProv:
            self.provide_output("files stored", 0)
            self.provide_output("files handled", 0)
            self.notify_insufficient_input("overhead staff bandwidth",
                                           overheadProv,
                                           overheadReq)
        else:
            self.consume_input("overhead staff bandwidth",
                               overheadReq)

        self.consume_input("line staff bandwidth", lineStaff)
        self.consume_input("operational costs", opCosts)
        self.consume_input("file logistic bandwidth", fileLog)

        self.provide_output("files stored", storageFiles)
        self.provide_output("files handled", storageFiles*ratio)


class FileLogisticsProcess(merlin.Process):

    def __init__(self, name="FileLogisticsProcess"):
        super(FileLogisticsProcess, self).__init__(name)

        # set up the output/s
        outFilesHandled = merlin.ProcessOutput('out_FilesHandled',
                                               'file count')
        self.outputs = {"files handled": outFilesHandled}

        opCosts = merlin.ProcessInput("in_ContractCosts",
                                      "op$")
        inOHStaff = merlin.ProcessInput('in_OverheadStaffBW',
                                        'ohFTE')
        self.inputs = {"overhead staff bandwidth": inOHStaff,
                       "contract costs": opCosts}

        self.add_property("monthly contract costs", "minCosts",
                          merlin.ProcessProperty.PropertyType.number_type,
                          1e6/12)
        self.add_property("contracted handling no",
                          "baseHandling",
                          merlin.ProcessProperty.PropertyType.number_type,
                          1e5)
        self.add_property("costs per additional file",
                          "addHandlingCosts",
                          merlin.ProcessProperty.PropertyType.number_type,
                          13)

    def compute(self, tick):

        opCosts = self.get_input_available("contract costs")
        minConCosts = self.get_prop_value("minCosts")
        if minConCosts > opCosts:
            self.provide_output("files handled", 0)
            self.notify_insufficient_input("contract costs",
                                           opCosts, minConCosts)
        else:
            self.consume_input("contract costs", minConCosts)
            self.provide_output("files handled",
                                self.get_prop_value("baseHandling"))

        # todo: implement addHandlingCosts


def govRecordStorageCore():
    # this is the capability, right now

    sim = merlin.Simulation()

    # add a branch
    branch_e = merlin.Entity(sim, "the branch")
    sim.add_entity(branch_e, parent=None)
    branch_e.attributes.add("branch")

    # add the govRecordStorage capability
    storage_e = merlin.Entity(sim, "the storage")
    sim.add_entity(storage_e, parent=branch_e)
    branch_e.add_child(storage_e)
    branch_e.attributes.add("capability")

    # add entities and their processes
    FileLogistics = merlin.Entity(sim, "file logistics")
    sim.add_entity(FileLogistics)
    storage_e.add_child(FileLogistics)
    # the_file_log_process = FileLogisticsProcess("file logistics process")
    # FileLogistics.add_process(the_file_log_process)
    FileLogistics.create_process(
        FileLogisticsProcess,
        {
            'name': "file logistics process"
        })

    FileLogistics.attributes.add("external capability")

    LineStaffRes = merlin.Entity(sim, "line staff resource")
    sim.add_entity(LineStaffRes)
    storage_e.add_child(LineStaffRes)
    LineStaffRes.create_process(
        LineStaffProcess,
        {
            'name': "line staff resource process"
        })

    LineStaffRes.attributes.add("resource")

    StorageFacility = merlin.Entity(sim, "storage facility")
    sim.add_entity(StorageFacility)
    storage_e.add_child(StorageFacility)
    sim.connect_entities(FileLogistics, StorageFacility, "file count")
    sim.connect_entities(LineStaffRes, StorageFacility, "lineFTE")
    StorageFacility.create_process(
        StorageFacilityProcess,
        {
            'name': "storage facility process"
        })

    StorageFacility.attributes.add("asset")

    # do these outputs go into a capability or branch?
    # need an expectation
    filesStored = merlin.Entity(sim, "files stored", is_output=True)
    filesStored.create_process(
        processes.OutputProcess,
        {
            'name': 'Output - Files Stored',
            'unit': 'files stored',
        }
    )

    sim.add_entity(filesStored)
    sim.connect_entities(StorageFacility, filesStored, 'files stored')

    # need an expectation
    filesAccessed = merlin.Entity(sim, "files handled", is_output=True)
    filesAccessed.create_process(
        processes.OutputProcess,
        {
            'name': 'Output - Files Handled',
            'unit': 'files handled'
        }
    )
    sim.add_entity(filesAccessed)
    sim.connect_entities(StorageFacility, filesAccessed, "files handled")
    return sim


def manyBudgetModel():

    sim = govRecordStorageCore()
    branch_e = sim.get_entity_by_name("the branch")
    storage_e = branch_e.get_child_by_name("the storage")
    StorageFacility = storage_e.get_child_by_name("storage facility")
    FileLogistics = storage_e.get_child_by_name("file logistics")
    LineStaffRes = storage_e.get_child_by_name("line staff resource")

    TheMaintenance = merlin.Entity(sim, "maintenance budget")
    sim.add_entity(TheMaintenance, is_source_entity=True)
    storage_e.add_child(TheMaintenance)
    TheMaintenance.attributes.add("budget")
    sim.connect_entities(TheMaintenance, StorageFacility, "maint$")
    # maint_proc = processes.BudgetProcess(name="maintenance budget",
    #                                      start_amount=4000000,
    #                                      budget_type="maint$")
    # TheMaintenance.add_process(maint_proc)
    TheMaintenance.create_process(
        processes.BudgetProcess,
        {
            'name': "maintenance budget",
            'start_amount': 4000000,
            'budget_type': "maint$"
        })

    TheOperationalCosts = merlin.Entity(sim, "operational costs")
    sim.add_entity(TheOperationalCosts, is_source_entity=True)
    storage_e.add_child(TheOperationalCosts)
    TheOperationalCosts.attributes.add("budget")
    sim.connect_entities(TheOperationalCosts, StorageFacility, "op$")
    sim.connect_entities(TheOperationalCosts, FileLogistics, "op$")
    # opcost_proc = processes.BudgetProcess(name="operational budget",
    #                                       start_amount=4000000,
    #                                       budget_type="op$")
    # TheOperationalCosts.add_process(opcost_proc)
    TheOperationalCosts.create_process(
        processes.BudgetProcess,
        {
            'name': "operational budget",
            'start_amount': 4000000,
            'budget_type': "op$"
        })

    TheRent = merlin.Entity(sim, "rent costs")
    sim.add_entity(TheRent, is_source_entity=True)
    TheRent.attributes.add("budget")
    storage_e.add_child(TheRent)
    sim.connect_entities(TheRent, StorageFacility, "rent$")
    # rent_proc = processes.BudgetProcess(name="rent budget",
    #                                     start_amount=4000000,
    #                                     budget_type="rent$")
    # TheRent.add_process(rent_proc)
    TheRent.create_process(
        processes.BudgetProcess,
        {
            'name': "rent budget",
            'start_amount': 4000000,
            'budget_type': "rent$"
        })

    # todo add another capability
    # add the govRecordStorage capability
#     printer_e = merlin.Entity("the printer")
#     sim.add_entity(printer_e, parent=branch_e)
#     branch_e.add_child(printer_e)

    # these are the Entities providing budget and staff numbers
    # they are replaced by connections in the agency wide model
    TheLineStaff = merlin.Entity(sim, "line staff")
    sim.add_entity(TheLineStaff, is_source_entity=True)
    storage_e.add_child(TheLineStaff)
    TheLineStaff.attributes.add("resource")
    # lineStaff_proc = processes.ConstantProvider(name="line staff no",
    #                                             unit="lineStaffNo",
    #                                             amount=20)
    # TheLineStaff.add_process(lineStaff_proc)
    TheLineStaff.create_process(
        processes.ConstantProvider,
        {
            'name': "line staff no",
            'unit': "lineStaffNo",
            'amount': 20
        })

    sim.connect_entities(TheLineStaff, LineStaffRes, "lineStaffNo")

    TheOverheadStaff = merlin.Entity(sim, "overhead staff")
    sim.add_entity(TheOverheadStaff, is_source_entity=True)
    storage_e.add_child(TheOverheadStaff)
    TheOverheadStaff.attributes.add("resource")
    # overheadStaff_proc = processes.ConstantProvider(name="overhead staff no",
    #                                                 unit="ohFTE",
    #                                                 amount=5)
    # TheOverheadStaff.add_process(overheadStaff_proc)
    TheOverheadStaff.create_process(
        processes.ConstantProvider,
        {
            'name': "overhead staff no",
            'unit': "ohFTE",
            'amount': 5
        })

    sim.connect_entities(TheOverheadStaff, LineStaffRes, "ohFTE")
    sim.connect_entities(TheOverheadStaff, FileLogistics, "ohFTE")
    sim.connect_entities(TheOverheadStaff, StorageFacility, "ohFTE")

    return sim


def big_one_with_sub_budgets():
    sim = govRecordStorageCore()

    branch_e = sim.get_entity_by_name("the branch")
    storage_e = branch_e.get_child_by_name("the storage")
    StorageFacility = storage_e.get_child_by_name("storage facility")
    FileLogistics = storage_e.get_child_by_name("file logistics")
    LineStaffRes = storage_e.get_child_by_name("line staff resource")

    # add a big budget

    TheMaintenance = merlin.Entity(sim, "maintenance budget")
    sim.add_entity(TheMaintenance)
    storage_e.add_child(TheMaintenance)
    TheMaintenance.attributes.add("budget")
    sim.connect_entities(TheMaintenance, StorageFacility, "maint$")
    TheMaintenance.create_process(
        SubBudgetProcess,
        {
            'name': "maintenance budget",
            'out_maintenance': "maint$",
            'in_unit': "$"
        })

    TheOperationalCosts = merlin.Entity(sim, "operational costs")
    sim.add_entity(TheOperationalCosts)
    storage_e.add_child(TheOperationalCosts)
    TheOperationalCosts.attributes.add("budget")
    sim.connect_entities(TheOperationalCosts, StorageFacility, "op$")
    sim.connect_entities(TheOperationalCosts, FileLogistics, "op$")
    TheOperationalCosts.create_process(
        SubBudgetProcess,
        {
            'name': "operational budget",
            "out_operational": "op$",
            'in_unit': "$"
        })

    TheRent = merlin.Entity(sim, "rent costs")
    sim.add_entity(TheRent)
    TheRent.attributes.add("budget")
    storage_e.add_child(TheRent)
    sim.connect_entities(TheRent, StorageFacility, "rent$")
    TheRent.create_process(
        SubBudgetProcess,
        {
            'name': "rent budget",
            "out_rent": "rent$",
            'in_unit': "$"
        })

    # these are the Entities providing budget and staff numbers
    # they are replaced by connections in the agency wide model
    TheLineStaff = merlin.Entity(sim, "line staff")
    sim.add_entity(TheLineStaff, is_source_entity=True)
    branch_e.add_child(TheLineStaff)
    TheLineStaff.attributes.add("resource")
    # lineStaff_proc = processes.ConstantProvider(name="line staff no",
    #                                             unit="lineStaffNo",
    #                                             amount=20)
    # TheLineStaff.add_process(lineStaff_proc)
    TheLineStaff.create_process(
        processes.ConstantProvider,
        {
            'name': "line staff no",
            'unit': "lineStaffNo",
            'amount': 20
        })

    sim.connect_entities(TheLineStaff, LineStaffRes, "lineStaffNo")

    TheOverheadStaff = merlin.Entity(sim, "overhead staff")
    sim.add_entity(TheOverheadStaff, is_source_entity=True)
    branch_e.add_child(TheOverheadStaff)
    TheOverheadStaff.attributes.add("resource")
    # overheadStaff_proc = processes.ConstantProvider(name="overhead staff no",
    #                                                 unit="ohFTE",
    #                                                 amount=5)
    # TheOverheadStaff.add_process(overheadStaff_proc)
    TheOverheadStaff.create_process(
        processes.ConstantProvider,
        {
            'name': "overhead staff no",
            'unit': "ohFTE",
            'amount': 5
        })

    sim.connect_entities(TheOverheadStaff, LineStaffRes, "ohFTE")
    sim.connect_entities(TheOverheadStaff, FileLogistics, "ohFTE")
    sim.connect_entities(TheOverheadStaff, StorageFacility, "ohFTE")

    # now create a branch budget
    branchBudget = merlin.Entity(sim, "branch budget")
    sim.add_entity(branchBudget)
    branch_e.add_child(branchBudget)
    branchBudget.attributes.add("budget")
    branchBudget.create_process(
        SubBudgetProcess,
        {
            'name': "branch budget",
            "in_unit": "$",
            'out_cap1': "$"
        })
    sim.connect_entities(branchBudget, TheOperationalCosts, "$")
    sim.connect_entities(branchBudget, TheMaintenance, "$")
    sim.connect_entities(branchBudget, TheRent, "$")

    departmentBudget = merlin.Entity(sim, "department staff")
    sim.add_entity(departmentBudget, is_source_entity=True)
    # and for the sake of it a department budget
    departmentBudget.attributes.add("budget")
    departmentBudget.create_process(
        processes.BudgetProcess,
        {
            'name': "department budget",
            'start_amount': 12000000,
            'budget_type': "$"
        })
    sim.connect_entities(departmentBudget, branchBudget, "$")

    return sim

# legacy name
govRecordStorage = manyBudgetModel

if __name__ == "__main__":

    sim = big_one_with_sub_budgets()
    # sim = manyBudgetModel()

    sim.set_time_span(48)
    sim.run()
    telem = sim.get_sim_telemetry()


