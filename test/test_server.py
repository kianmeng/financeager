import os.path
import tempfile
import unittest

from financeager import DEFAULT_TABLE, default_period_name, entries
from financeager import period as pd
from financeager import server


class AddEntryToServerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = server.Server()
        cls.server.run(
            "add",
            name="Hiking boots",
            value=-111.11,
            category="outdoors",
            period="0")

    def test_period_name(self):
        self.assertEqual("0", self.server._periods["0"].name)

    def test_periods(self):
        response = self.server.run("periods")
        self.assertListEqual(response["periods"], ["0"])

    def test_unknown_command(self):
        response = self.server.run("peace")
        self.assertIn("peace", response["error"])


class RecurrentEntryServerTestCase(unittest.TestCase):
    def setUp(self):
        self.server = server.Server()
        self.period = "2000"
        self.entry_id = self.server.run(
            "add",
            name="rent",
            value=-1000,
            table_name="recurrent",
            frequency="monthly",
            start="01-02",
            end="07-01",
            period=self.period)["id"]

    def test_recurrent_entries(self):
        elements = self.server.run(
            "list", period=self.period,
            filters={"name": "rent"})["elements"]["recurrent"][self.entry_id]
        self.assertEqual(len(elements), 6)

    def test_recurrent_copy(self):
        destination_period = "2001"
        response = self.server.run(
            "copy",
            source_period=self.period,
            table_name="recurrent",
            destination_period=destination_period,
            eid=self.entry_id)
        copied_entry_id = response["id"]
        # copied and added as first element, hence ID 1
        self.assertEqual(copied_entry_id, 1)

        source_entry = self.server.run(
            "get",
            period=self.period,
            table_name="recurrent",
            eid=self.entry_id)["element"]
        destination_entry = self.server.run(
            "get",
            table_name="recurrent",
            period=destination_period,
            eid=copied_entry_id)["element"]
        self.assertDictEqual(source_entry, destination_entry)


class FindEntryServerTestCase(unittest.TestCase):
    def setUp(self):
        self.server = server.Server()
        self.period = "0"
        self.entry_id = self.server.run(
            "add", name="Hiking boots", value=-111.11, period=self.period)["id"]

    def test_get_period(self):
        period = self.server._get_period(self.period)
        self.assertEqual(period.name, self.period)

        another_period = "foo"
        period = self.server._get_period(another_period)
        self.assertEqual(period.name, another_period)

        period = self.server._get_period(None)
        self.assertEqual(period.name, default_period_name())

    def test_query_and_reset_response(self):
        category = entries.CategoryEntry.DEFAULT_NAME
        response = self.server.run(
            "list", period=self.period, filters={"category": category})
        self.assertGreater(len(response), 0)
        self.assertIsInstance(response, dict)
        self.assertIsInstance(response["elements"], dict)
        self.assertIsInstance(response["elements"][DEFAULT_TABLE], dict)
        self.assertIsInstance(response["elements"]["recurrent"], dict)

    def test_response_is_none(self):
        response = self.server.run("get", period=self.period, eid=self.entry_id)
        self.assertIn("element", response)
        self.assertEqual(response["element"].eid, self.entry_id)

        response = self.server.run(
            "remove", period=self.period, eid=self.entry_id)
        self.assertEqual(response["id"], self.entry_id)

        response = self.server.run(
            "list",
            period=self.period,
            filters={
                "name": "Hiking boots",
                "category": entries.CategoryEntry.DEFAULT_NAME
            })
        self.assertDictEqual(response["elements"][DEFAULT_TABLE], {})
        self.assertDictEqual(response["elements"]["recurrent"], {})

    def test_update(self):
        new_category = "Outdoorsy shit"
        self.server.run(
            "update",
            eid=self.entry_id,
            period=self.period,
            category=new_category)
        element = self.server.run(
            "get", eid=self.entry_id, period=self.period)["element"]
        self.assertEqual(element["category"], new_category.lower())

    def test_copy(self):
        destination_period = "1"
        response = self.server.run(
            "copy",
            source_period=self.period,
            destination_period=destination_period,
            eid=self.entry_id)
        copied_entry_id = response["id"]
        # copied and added as first element, hence ID 1
        self.assertEqual(copied_entry_id, 1)

        source_entry = self.server.run(
            "get", period=self.period, eid=self.entry_id)["element"]
        destination_entry = self.server.run(
            "get", period=destination_period, eid=copied_entry_id)["element"]
        self.assertDictEqual(source_entry, destination_entry)

    def test_unsuccessful_copy(self):
        self.assertRaises(
            pd.PeriodException,
            self.server._copy_entry,
            source_period=self.period,
            destination_period="1",
            eid=42)


class JsonPeriodsServerTestCase(unittest.TestCase):
    def test_periods(self):
        tmp_dir = tempfile.mkdtemp()
        self.server = server.Server(data_dir=tmp_dir)

        self.assertDictEqual(self.server.run("periods"), {"periods": []})

        # Create dummy JSON files
        periods = ["1000", "1500"]
        for p in periods:
            open(os.path.join(tmp_dir, "{}.json".format(p)), "w").close()

        self.assertDictEqual(self.server.run("periods"), {"periods": periods})


if __name__ == '__main__':
    unittest.main()
