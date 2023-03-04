# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring
# type: ignore
import pytest

from tests import common
from yaas_common import request

_TEST_SCALE_REQUEST: request.ScaleRequest = common.create_scale_request(original_json_event="TEST_ORIGINAL_JSON_EVENT")


class TestScaleRequestCollection:
    @pytest.mark.parametrize("remove_original_json_event", [True, False])
    def test_from_lst_ok(self, remove_original_json_event: bool):
        # Given
        value = [_TEST_SCALE_REQUEST, _TEST_SCALE_REQUEST]
        # When
        result = request.ScaleRequestCollection.from_lst(value, remove_original_json_event=remove_original_json_event)
        # Then
        assert len(result.collection) == len(value)
        for res, exp in zip(result.collection, value):
            if remove_original_json_event:
                assert res.original_json_event is None
                assert res == exp.clone(original_json_event=None)
            else:
                assert res == exp

    def test_from_lst_nok_non_iterable(self):
        with pytest.raises(TypeError):
            request.ScaleRequestCollection.from_lst(_TEST_SCALE_REQUEST)

    def test_from_lst_nok_wrong_type_element(self):
        with pytest.raises(TypeError):
            request.ScaleRequestCollection.from_lst([_TEST_SCALE_REQUEST, "", _TEST_SCALE_REQUEST])
