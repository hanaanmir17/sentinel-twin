import json
import tempfile
import unittest
from pathlib import Path

from sentinel_twin import DigitalTwin


class DigitalTwinTests(unittest.TestCase):
    def make_twin(self):
        topology = {
            "roots": ["edge"],
            "nodes": [
                {"id": "edge", "criticality": 10},
                {"id": "core", "criticality": 8},
                {"id": "client", "criticality": 2},
            ],
            "links": [
                {"from": "edge", "to": "core", "bidirectional": True},
                {"from": "core", "to": "client", "bidirectional": True},
            ],
        }
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(topology, tmp)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return DigitalTwin.from_file(tmp.name)

    def test_no_failure_reaches_everything(self):
        twin = self.make_twin()
        result = twin.simulate()
        self.assertEqual(result["unreachable_devices"], [])
        self.assertEqual(result["blast_radius_score"], 0)

    def test_core_failure_isolates_client(self):
        twin = self.make_twin()
        result = twin.simulate({"core"})
        self.assertEqual(result["unreachable_devices"], ["client"])
        self.assertEqual(result["blast_radius_score"], 10)


if __name__ == "__main__":
    unittest.main()
