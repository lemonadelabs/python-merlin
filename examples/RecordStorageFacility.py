'''
Created on 14/04/2016

..code-author:: Achim Gaedke <Achim.Gaedke@lemonadelabs.io>

'''

from pymerlin import merlin


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


def govRecordStorage():

    sim = merlin.Simulation()
    sim.add_unit_types(["file count", "staff no", "$",
                        "ohFTE", "FTE"])

    # add a branch
    branch_e = merlin.Entity(sim, "the branch")
    sim.add_entity(branch_e, parent=None)

    # add the govRecordStorage capability
    storage_e = merlin.Entity("the storage")
    sim.add_entity(storage_e, parent=branch_e)
    branch_e.add_child(storage_e)

    lineStaff = merlin.InputConnector("staff no",
                                      storage_e,
                                      "storage line staff")

    overheadStaff = merlin.InputConnector("staff no",
                                          storage_e,
                                          "storage overhead staff")

    rent = merlin.InputConnector("$",
                                 storage_e,
                                 "storage rent")
    opCosts = merlin.InputConnector("$",
                                    storage_e,
                                    "storage operation costs")
    maintenanceCosts = merlin.InputConnector("$",
                                             storage_e,
                                             "storage maintenance costs")
    # add entities and their processes

    FileLogistics = merlin.Entity(sim, "file logistics")
    storage_e.add_child(FileLogistics)
    sim.connect_input(opCosts, FileLogistics, "$")
    sim.connect_input(overheadStaff, FileLogistics, "ohFTE")

    LineStaffRes = merlin.Entity(sim, "line staff resource")
    storage_e.add_child(LineStaffRes)
    sim.connect_input(lineStaff, LineStaffRes, "staff no")
    sim.connect_input(overheadStaff, LineStaffRes, "ohFTE")

    StorageFacility = merlin.Entity(sim, "storage facility")
    storage_e.add_child(StorageFacility)
    sim.connect_entities(FileLogistics, StorageFacility, "file count")
    sim.connect_input(overheadStaff, StorageFacility, "ohFTE")
    sim.connect_entities(LineStaffRes, StorageFacility, "FTE")
    sim.connect_input(opCosts, StorageFacility, "$")
    sim.connect_input(rent, StorageFacility, "$")
    sim.connect_input(maintenanceCosts, StorageFacility, "$")

    # do these outputs go into a capability or branch?
    # need an expectation
    filesStored = merlin.Output("file count",
                                name="files stored")
    storage_e.add_child(filesStored)
    sim.outputs.add(filesStored)
    sim.connect_output(StorageFacility, filesStored)

    # need an expectation
    filesAccessed = merlin.Output("file count",
                                  name="files accessed")
    storage_e.add_child(filesAccessed)
    sim.outputs.add(filesAccessed)
    sim.connect_output(StorageFacility, filesAccessed)

    the_line_staff_process = LineStaffProcess()
    LineStaffRes.add_process(the_line_staff_process)

    the_stor_fac_process = StorageFacilityProcess()
    StorageFacility.add_process(the_stor_fac_process)

    the_file_log_process = FileLogisticsProcess()
    FileLogistics.add_process(the_file_log_process)

    # todo add another capability
    # add the govRecordStorage capability
    printer_e = merlin.Entity("the printer")
    sim.add_entity(printer_e, parent=branch_e)
    branch_e.add_child(printer_e)

    return sim

if __name__ == "__main__":

    sim = govRecordStorage()
