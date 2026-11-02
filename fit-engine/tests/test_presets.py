import pytest

from stylewise_fit.presets import SEXES, SHAPES, SIZES, classify, estimate, preset_id


@pytest.mark.parametrize("sex", SEXES)
@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("size", SIZES)
def test_prototype_lands_in_own_ffit_class(sex, shape, size):
    e = estimate(shape, size, sex)
    assert classify(e.chest_cm, e.waist_cm, e.hip_cm) == shape


def test_male_chart_is_larger_than_female():
    assert estimate("rectangle", "M", "male").chest_cm > estimate("rectangle", "M", "female").chest_cm


def test_male_heights_snap_to_male_grid():
    assert preset_id("oval", "2XL", 190, "male") == "male_oval_2XL_185"


def test_unknown_shape_rejected():
    with pytest.raises(ValueError):
        estimate("pear", "M")
