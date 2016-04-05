'''
Created on 5/04/2016

@author: achim
'''

import pytest
import numpy.testing as npt
from pymerlin import merlin


@pytest.fixture()
def OutputConnector_with_Endpoints():

    outEntity = merlin.Entity()

    # set no biases, rely on defaults
    out = merlin.OutputConnector("$", outEntity, "testOut")

    for i in range(4):
        out.add_input(merlin.InputConnector("$",
                                            outEntity,
                                            "testIn{:d}".format(i)))

    return out


class TestApportioning:

    def test_default(self, OutputConnector_with_Endpoints):
        out = OutputConnector_with_Endpoints

        out_value = 1.0
        out.write(out_value)
        # expect something
        values = []
        biases = []
        for ep, bias in out.get_endpoints():
            values.append(ep.value)
            biases.append(bias)

        npt.assert_allclose(
                    values,
                    (out_value/len(values),)*len(values),
                    err_msg="expected the same value on all end-points")

        npt.assert_allclose(
                    biases,
                    (biases[0],)*len(biases),
                    err_msg="expected the same biases on all end-points")

        npt.assert_allclose(
                        [sum(values)],
                        [out_value],
                        err_msg="sum of endpoints expected the same as output")

    def test_zero_biases(self, OutputConnector_with_Endpoints):
        out = OutputConnector_with_Endpoints

        # set the rule and biases
        out.apportioning = merlin.OutputConnector.apportioningRules.weighted
        out.set_endpoint_biases([(ep, 0.0) for ep, _ in out.get_endpoints()])

        out_value = 10.0
        out.write(out_value)
        # expect something
        values = []
        biases = []
        for ep, bias in out.get_endpoints():
            values.append(ep.value)
            biases.append(bias)

        npt.assert_allclose(
                    values,
                    (out_value/len(values),)*len(values),
                    err_msg="expected the same value on all end-points")

        npt.assert_allclose(
                    biases,
                    (0.0,)*len(biases),
                    err_msg="expected the same biases on all end-points")

        npt.assert_allclose(
                    [sum(values)],
                    [out_value],
                    err_msg="sum of end-points expected the same as output")

    def test_copy_write(self, OutputConnector_with_Endpoints):
        out = OutputConnector_with_Endpoints

        # set the rule and biases
        out.apportioning = merlin.OutputConnector.apportioningRules.copy_write

        out_value = 1.0
        out.write(out_value)
        # expect something
        values = []
        biases = []
        for ep, bias in out.get_endpoints():
            values.append(ep.value)
            biases.append(bias)

        npt.assert_allclose(
                    values,
                    (out_value,)*len(values),
                    err_msg="expected the same value on all end-points")

    def test_absolute_apportioning(self, OutputConnector_with_Endpoints):
        out = OutputConnector_with_Endpoints

        out.apportioning = merlin.OutputConnector.apportioningRules.absolute

        # get an ordered version of the endpoints set
        endpoints = list(sorted((ep for ep, _ in out.get_endpoints()),
                                key=lambda e: e.name)
                         )

        bias_values = (0.5, 0.3, 0.1, 0.2)
        # expect, that 0.1 doesn't get anything
        expected_output = (0.5, 0.3, 0.0, 0.2)
        out.set_endpoint_biases(list(zip(endpoints, bias_values)))

        out_value = 1.0
        out.write(out_value)
        # expect something
        values = []
        biases = []
        for ep, bias in sorted(out.get_endpoints(),
                               key=lambda e: e[0].name):
            values.append(ep.value)
            biases.append(bias)

        npt.assert_allclose(
                    values,
                    expected_output,
                    err_msg="unexpected values on end-points")

        npt.assert_allclose(
                    biases,
                    bias_values,
                    err_msg="expected the preset biases on all end-points")

        npt.assert_allclose(
                        [sum(values)],
                        [out_value],
                        err_msg="sum of endpoints expected the same as output")

    def test_weighted_apportioning(self, OutputConnector_with_Endpoints):
        out = OutputConnector_with_Endpoints

        out.apportioning = merlin.OutputConnector.apportioningRules.weighted

        # get an ordered version of the endpoints set
        endpoints = list(sorted((ep for ep, _ in out.get_endpoints()),
                                key=lambda e: e.name)
                         )

        bias_values = (0.5, 0.3, 0.1, 0.2)
        out_value = 3.0

        expected_output = [b/sum(bias_values)*out_value for b in bias_values]
        out.set_endpoint_biases(list(zip(endpoints, bias_values)))

        out.write(out_value)
        # expect something
        values = []
        biases = []
        for ep, bias in sorted(out.get_endpoints(),
                               key=lambda e: e[0].name):
            values.append(ep.value)
            biases.append(bias)

        npt.assert_allclose(
                    values,
                    expected_output,
                    err_msg="unexpected values on end-points")

        npt.assert_allclose(
                    biases,
                    bias_values,
                    err_msg="expected the preset biases on all end-points")

        npt.assert_allclose(
                        [sum(values)],
                        [out_value],
                        err_msg="sum of endpoints expected the same as output")
