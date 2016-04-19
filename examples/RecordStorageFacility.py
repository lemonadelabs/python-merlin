'''
Created on 14/04/2016

..code-author:: Achim Gaedke <Achim.Gaedke@lemonadelabs.io>

'''

import math
import logging
from pymerlin import merlin, processes

# Global logging settings
logging_level = logging.DEBUG
log_to_file = ''
logging.basicConfig(
    filename=log_to_file,
    level=logging_level,
    format='%(asctime)s: [%(levelname)s] %(message)s')


class LineStaffProcess(merlin.Process):

    def __init__(self, name):
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
                          "0.8")

    def compute(self, tick):
        oh_staff_req = 2

        if oh_staff_req > self.get_input_available("ohFTE"):
            self.provide_output("line staff bandwidth", 0.0)
            self.notify_insufficient_input("ohFTE",
                                           self.get_input_available("ohFTE"),
                                           oh_staff_req)

        staff_available = self.get_input_available("line staff no")
        util = self.get_prop_value("maxUtil")

        # todo: training time!

        self.consume_input("line staff no", staff_available)
        self.provide_output("line staff bandwidth", staff_available*util)


class StorageFacilityProcess(merlin.Process):

    def __init__(self, name):
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
                                     '$')
        inMaintenance = merlin.ProcessInput('in_Maintenance',
                                            '$')
        opCosts = merlin.ProcessInput("in_OpCosts",
                                      "$")
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
                          10)
        self.add_property("staff time per storage",
                          "timePerStorage",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)
        # this is no of access over no of storages
        self.add_property("ratio access to storage",
                          "rAccessStorage",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)
        self.add_property("minimum line staff",
                          "min line staff",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)
        self.add_property("ratio overhead to line staff",
                          "rOverheadLineStaff",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)

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

    def __init__(self, name):
        super(FileLogisticsProcess, self).__init__(name)

        # set up the output/s
        outFilesHandled = merlin.ProcessOutput('out_FilesHandled',
                                               'file count')
        self.outputs = {"files handled": outFilesHandled}

        opCosts = merlin.ProcessInput("in_ContractCosts",
                                      "$")
        inOHStaff = merlin.ProcessInput('in_OverheadStaffBW',
                                        'ohFTE')
        self.inputs = {"overhead staff bandwidth": inOHStaff,
                       "contract costs": opCosts}

        self.add_property("min contract costs", "minCosts",
                          merlin.ProcessProperty.PropertyType.number_type,
                          1e6)
        self.add_property("contracted handling no",
                          "baseHandling",
                          merlin.ProcessProperty.PropertyType.number_type,
                          1e6)
        self.add_property("additional costs per file",
                          "addHandlingCosts",
                          merlin.ProcessProperty.PropertyType.number_type,
                          20)

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


def govRecordStorage():
    # this is the capability, right now

    sim = merlin.Simulation()
    sim.add_attributes(["branch", "capability", "deliverable", "budget",
                        "asset", "resource", "external capability"])
    sim.add_unit_types(["file count", "lineStaffNo", "$", "files handled",
                        "files stored", "ohFTE", "lineFTE"])

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
    the_file_log_process = FileLogisticsProcess("file logistics process")
    FileLogistics.add_process(the_file_log_process)
    FileLogistics.attributes.add("external capability")

    LineStaffRes = merlin.Entity(sim, "line staff resource")
    sim.add_entity(LineStaffRes)
    storage_e.add_child(LineStaffRes)
    the_line_staff_process = LineStaffProcess("line staff resource process")
    LineStaffRes.add_process(the_line_staff_process)
    LineStaffRes.attributes.add("resource")

    StorageFacility = merlin.Entity(sim, "storage facility")
    sim.add_entity(StorageFacility)
    storage_e.add_child(StorageFacility)
    sim.connect_entities(FileLogistics, StorageFacility, "file count")
    sim.connect_entities(LineStaffRes, StorageFacility, "lineFTE")
    the_stor_fac_process = StorageFacilityProcess("storage facility process")
    StorageFacility.add_process(the_stor_fac_process)
    StorageFacility.attributes.add("asset")

    # these are the Entities providing budget and staff numbers
    # they are replaced by connections in the agency wide model
    TheLineStaff = merlin.Entity(sim, "line staff")
    sim.add_entity(TheLineStaff, is_source_entity=True)
    storage_e.add_child(TheLineStaff)
    lineStaff_proc = processes.ConstantProvider(name="line staff no",
                                                unit="lineStaffNo",
                                                amount=20)
    TheLineStaff.add_process(lineStaff_proc)
    sim.connect_entities(TheLineStaff, LineStaffRes, "lineStaffNo")

    TheOverheadStaff = merlin.Entity(sim, "overhead staff")
    sim.add_entity(TheOverheadStaff, is_source_entity=True)
    storage_e.add_child(TheOverheadStaff)
    overheadStaff_proc = processes.ConstantProvider(name="overhead staff no",
                                                    unit="ohFTE",
                                                    amount=3)
    TheOverheadStaff.add_process(overheadStaff_proc)
    sim.connect_entities(TheOverheadStaff, LineStaffRes, "ohFTE")
    sim.connect_entities(TheOverheadStaff, FileLogistics, "ohFTE")
    sim.connect_entities(TheOverheadStaff, StorageFacility, "ohFTE")

    TheMaintenance = merlin.Entity(sim, "maintenance budget")
    sim.add_entity(TheMaintenance, is_source_entity=True)
    storage_e.add_child(TheMaintenance)
    TheMaintenance.attributes.add("budget")
    sim.connect_entities(TheMaintenance, StorageFacility, "$")
    maint_proc = processes.BudgetProcess(name="maintenance budget",
                                         start_amount=100000)
    TheMaintenance.add_process(maint_proc)

    TheOperationalCosts = merlin.Entity(sim, "operational costs")
    sim.add_entity(TheOperationalCosts, is_source_entity=True)
    storage_e.add_child(TheOperationalCosts)
    TheOperationalCosts.attributes.add("budget")
    sim.connect_entities(TheOperationalCosts, StorageFacility, "$")
    sim.connect_entities(TheOperationalCosts, FileLogistics, "$")
    opcost_proc = processes.BudgetProcess(name="operational budget",
                                          start_amount=100000)
    TheOperationalCosts.add_process(opcost_proc)

    TheRent = merlin.Entity(sim, "rent costs")
    sim.add_entity(TheRent, is_source_entity=True)
    TheRent.attributes.add("budget")
    storage_e.add_child(TheRent)
    sim.connect_entities(TheRent, StorageFacility, "$")
    rent_proc = processes.BudgetProcess(name="rent budget",
                                        start_amount=100000)
    TheRent.add_process(rent_proc)

    # do these outputs go into a capability or branch?
    # need an expectation
    filesStored = merlin.Output("files stored",
                                name="files stored")
    sim.outputs.add(filesStored)
    sim.connect_output(StorageFacility, filesStored)

    # need an expectation
    filesAccessed = merlin.Output("files handled",
                                  name="files accessed")
    sim.outputs.add(filesAccessed)
    sim.connect_output(StorageFacility, filesAccessed)

    # todo add another capability
    # add the govRecordStorage capability
#     printer_e = merlin.Entity("the printer")
#     sim.add_entity(printer_e, parent=branch_e)
#     branch_e.add_child(printer_e)

    return sim

if __name__ == "__main__":

    sim = govRecordStorage()
    sim.set_time_span(12)
    sim.run()
    result = list(sim.outputs)[0].result
    print(result)
