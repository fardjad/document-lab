import unittest

from application.slice_management.usecases.slice_commands import SliceCommands
from model.project import CropRectangle, CropSlice, ProjectId, ProjectSlices


class FakeStore:
    def __init__(self) -> None:
        self.value = ProjectSlices(1)

    def read_project_slices(self, project_id: ProjectId) -> ProjectSlices:
        return self.value

    def write_project_slices(self, project_id: ProjectId, slices: ProjectSlices) -> None:
        self.value = slices


class SliceCommandsTests(unittest.TestCase):
    def test_create_update_delete_allocates_nonreused_ids(self) -> None:
        store = FakeStore()
        commands = SliceCommands(store)
        rectangle = CropRectangle(0, 0, 10, 20)
        first = commands.create_slice("project", rectangle)
        commands.update_slice("project", first.id, "Renamed", rectangle, 90)
        commands.delete_slice("project", first.id)
        second = commands.create_slice("project", rectangle)
        self.assertEqual((1, 2), (first.id, second.id))
        self.assertEqual("Slice 2", second.name)


if __name__ == "__main__":
    unittest.main()
