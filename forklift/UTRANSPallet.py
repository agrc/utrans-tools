from forklift.models import Pallet
from pathlib import Path


class UTRANSPallet(Pallet):
    def __init__(self):
        super().__init__()

    def build(self, configuration):
        utrans = Path(self.garage) / "UTRANS.sde"
        sgid = Path(self.garage) / "SGID.sde"

        for source in [sgid, utrans]:
            if not source.exists():
                raise RuntimeError(f"{source.name} not found in {self.garage}")

        self.add_crates(
            [
                "Counties",
                "Municipalities",
                "ZipCodes",
                "NationalGrid",
                "AddressSystemQuadrants",
            ],
            {"source_workspace": str(sgid), "destination_workspace": str(utrans)},
        )
