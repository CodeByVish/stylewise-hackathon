import numpy as np
import pytest
import trimesh

from stylewise_fit.body import Measurements, landmark_heights_m, mannequin_mesh
from stylewise_fit.measure import circumference_at_height, ellipse_perimeter, height_cm


@pytest.mark.parametrize("r", [0.10, 0.15, 0.20])
def test_cylinder_circumference(r):
    mesh = trimesh.creation.cylinder(radius=r, height=1.0, sections=256)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    got = circumference_at_height(mesh, 0.0)
    assert got == pytest.approx(2 * np.pi * r * 100, rel=0.005)


@pytest.mark.parametrize("a,b", [(0.16, 0.11), (0.14, 0.10), (0.18, 0.13)])
def test_ellipse_cylinder_circumference(a, b):
    mesh = trimesh.creation.cylinder(radius=1.0, height=1.0, sections=512)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    mesh.apply_scale([a, 1.0, b])
    got = circumference_at_height(mesh, 0.0)
    assert got == pytest.approx(ellipse_perimeter(a, b) * 100, rel=0.005)


def test_ellipse_perimeter_circle_exact():
    assert ellipse_perimeter(0.1, 0.1) == pytest.approx(2 * np.pi * 0.1, rel=1e-9)


def test_no_slice_returns_zero():
    mesh = trimesh.creation.box([0.1, 0.1, 0.1])
    assert circumference_at_height(mesh, 5.0) == 0.0


@pytest.mark.parametrize("m", [
    Measurements(165, 90, 74, 98),
    Measurements(178, 104, 90, 102),
    Measurements(155, 84, 68, 92),
])
def test_mannequin_reproduces_targets(m):
    mesh = mannequin_mesh(m)
    assert height_cm(mesh) == pytest.approx(m.height_cm, abs=0.1)
    for name, y in landmark_heights_m(m.height_cm).items():
        target = getattr(m, f"{name}_cm")
        assert circumference_at_height(mesh, y) == pytest.approx(target, rel=0.005), name
