'''
Created on 14/04/2016

..code-author:: Achim Gaedke <Achim.Gaedke@lemonadelabs.io>

'''

from pymerlin import merlin, processes


class LineStaffProcess(merlin.Process):

    def __init__(self, name):
        super(LineStaffProcess, self).__init__(name)

        # set up the output/s
        outStaffBW = merlin.ProcessOutput('out_LineStaffBW',
                                          'FTE')
        self.outputs = {"line staff bandwidth": outStaffBW}

        # set up the input/s
        inLineStaff = merlin.ProcessInput("line staff pool",
                                          "staff no")
        inOHStaff = merlin.ProcessInput("overhead staff pool",
                                        "staff no")

        self.inputs = {"line staff no": inLineStaff,
                       "overhead staff no": inOHStaff}

        self.add_property("Training time",
                          "trainingTime",
                          merlin.ProcessProperty.PropertyType.number_type,
                          1)
        self.add_property("max utilisation", "maxUtil",
                          merlin.ProcessProperty.PropertyType.number_type,
                          "0.8")


class StorageFacilityProcess(merlin.Process):

    def __init__(self, name):
        super(StorageFacilityProcess, self).__init__(name)

        # set up the output/s
        outFilesHandled = merlin.ProcessOutput('out_FilesHandled',
                                               'file count')
        outFilesStored = merlin.ProcessOutput('out_FilesStored',
                                              'file count')

        self.outputs = {"files stored": outFilesStored,
                        "files handled": outFilesHandled}

        # set up the input/s
        inLineStaff = merlin.ProcessInput('in_LineStaffBW',
                                          'FTE')
        inOHStaff = merlin.ProcessInput('in_OverheadStaffBW',
                                        'staff no')

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
        self.add_property("ratio storage to access",
                          "rStorageAccess",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)
        self.add_property("minimum line staff",
                          "min line staff",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)
        self.add_property("ratio line to overhead staff",
                          "rLineOverheadStaff",
                          merlin.ProcessProperty.PropertyType.number_type,
                          10)

        self.inputs = {"line staff bandwidth": inLineStaff,
                       "overhead staff bandwidth": inOHStaff,
                       "rent": inRent,
                       "maintenance": inMaintenance,
                       "operational costs": opCosts,
                       "file logistic bandwidth": fileLog}


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


def govRecordStorage():
    # this is the capability, right now

    sim = merlin.Simulation()
    sim.add_attributes(["branch", "capability", "deliverable",
                        "", ])
    sim.add_unit_types(["file count", "staff no", "$",
                        "ohFTE", "FTE"])

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
    sim.connect_entities(LineStaffRes, StorageFacility, "FTE")
    the_stor_fac_process = StorageFacilityProcess("storage facility process")
    StorageFacility.add_process(the_stor_fac_process)
    StorageFacility.attributes.add("asset")

    # these are the Entities providing budget and staff numbers
    # they are replaced by connections in the agency wide model
    TheLineStaff = merlin.Entity(sim, "line staff")
    sim.add_entity(TheLineStaff, is_source_entity=True)
    storage_e.add_child(TheLineStaff)
    lineStaff_proc = processes.ConstantProvider(name="line staff no",
                                                unit="staff no",
                                                amount=20)
    TheLineStaff.add_process(lineStaff_proc)
    sim.connect_entities(TheLineStaff, LineStaffRes, "staff no")

    TheOverheadStaff = merlin.Entity(sim, "overhead staff")
    sim.add_entity(TheOverheadStaff, is_source_entity=True)
    storage_e.add_child(TheOverheadStaff)
    overheadStaff_proc = processes.ConstantProvider(name="overhead staff no",
                                                    unit="ohFTE",
                                                    amount=3)
    TheOverheadStaff.add_child(overheadStaff_proc)
    sim.connect_entities(TheOverheadStaff, LineStaffRes, "ohFTE")
    sim.connect_entities(TheOverheadStaff, FileLogistics, "ohFTE")
    sim.connect_entities(TheOverheadStaff, StorageFacility, "ohFTE")

    TheMaintenance = merlin.Entity(sim, "maintenance budget")
    sim.add_entity(TheMaintenance, is_source_entity=True)
    storage_e.add_child(TheMaintenance)
    sim.connect_entities(TheMaintenance, StorageFacility, "$")
    maint_proc = processes.BudgetProcess(name="maintenance budget",
                                         start_amount=100000)
    TheMaintenance.add_process(maint_proc)

    TheOperationalCosts = merlin.Entity(sim, "operational costs")
    sim.add_entity(TheOperationalCosts, is_source_entity=True)
    storage_e.add_child(TheOperationalCosts)
    sim.connect_entities(TheOperationalCosts, StorageFacility, "$")
    sim.connect_entities(TheOperationalCosts, FileLogistics, "$")
    opcost_proc = processes.BudgetProcess(name="operational budget",
                                          start_amount=100000)
    TheOperationalCosts.add_process(opcost_proc)

    TheRent = merlin.Entity(sim, "rent costs")
    sim.add_entity(TheRent, is_source_entity=True)
    storage_e.add_child(TheRent)
    sim.connect_entities(TheRent, StorageFacility, "$")
    rent_proc = processes.BudgetProcess(name="rent budget",
                                        start_amount=100000)
    TheRent.add_process(rent_proc)

    # do these outputs go into a capability or branch?
    # need an expectation
    filesStored = merlin.Output("file count",
                                name="files stored")
    sim.outputs.add(filesStored)
    sim.connect_output(StorageFacility, filesStored)

    # need an expectation
    filesAccessed = merlin.Output("file count",
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
