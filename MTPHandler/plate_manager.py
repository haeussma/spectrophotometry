from __future__ import annotations

import warnings
from typing import Literal, Optional, Tuple, get_args

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from MTPHandler.model import Molecule, Plate, Protein, Species, Well
from MTPHandler.units import UnitDefinition

ASSIGN_CASE = Literal["rows", "columns", "all", "all except"]
ASSIGN_CASE_VALUES: Tuple[ASSIGN_CASE, ...] = get_args(ASSIGN_CASE)


class PlateManager(BaseModel):
    plate: Plate = Field(..., description="Plate object")

    # Adders for species, molecules and proteins
    def add_species(
        self,
        ld_id: Optional[str],
        id: Optional[str],
        name: Optional[str],
    ) -> Species:
        params = {
            "ld_id": ld_id,
            "id": id,
            "name": name,
        }

        if not ld_id:
            warnings.warn("""
            No linked-data ID provided. Use UniProt, ChEBI or PubChem URL to uniquely identify the species.
            """)
            unique_id = id
        else:
            unique_id = ld_id

        for species in self.plate.species:
            if not isinstance(species, Species):
                continue

            if species.id == unique_id or species.ld_id == unique_id:
                species.__dict__.update(params)
                return species

        species = self.plate.add_species_to_species(**params)
        return species

    def add_molecule(
        self,
        ld_id: Optional[str],
        id: Optional[str],
        name: Optional[str],
        smiles: Optional[str],
        inchi_key: Optional[str],
    ) -> Molecule:
        params = {
            "ld_id": ld_id,
            "id": id,
            "name": name,
            "smiles": smiles,
            "inchi_key": inchi_key,
        }

        if not ld_id:
            warnings.warn("""
            No linked-data ID provided. Use ChEBI or PubChem URL to uniquely identify the molecule.
            """)
            unique_id = id
        else:
            unique_id = ld_id

        for molecule in self.plate.species:
            if not isinstance(molecule, Molecule):
                continue

            if molecule.id == unique_id or molecule.ld_id == unique_id:
                molecule.__dict__.update(params)
                return molecule

        molecule = self.plate.add_molecule_to_species(**params)
        return molecule

    def add_protein(
        self,
        ld_id: Optional[str],
        id: Optional[str],
        name: Optional[str],
        sequence: Optional[str],
        organism: Optional[str],
        organism_tax_id: Optional[int],
    ) -> Protein:
        params = {
            "ld_id": ld_id,
            "id": id,
            "name": name,
            "sequence": sequence,
            "organism": organism,
            "organism_tax_id": organism_tax_id,
        }

        if not ld_id:
            warnings.warn("""
            No linked-data ID provided. Use UniProt URL to uniquely identify the protein.
            """)
            unique_id = id
        else:
            unique_id = ld_id

        for protein in self.plate.species:
            if not isinstance(protein, Protein):
                continue

            if protein.id == unique_id or protein.ld_id == unique_id:
                protein.__dict__.update(params)
                return protein

        protein = self.plate.add_protein_to_species(**params)
        return protein

    # Assign species and conditions to wells

    def assign_species(
        self,
        species: Species | Molecule | Protein | str,
        init_conc: float | list[float],
        conc_unit: UnitDefinition,
        to: ASSIGN_CASE,
        ids: Optional[str | int | list[str] | list[int]] = None,
        contributes_to_signal: Optional[bool] = None,
    ):
        """
        Assigns a species to specific wells on the plate based on the provided criteria.

        Args:
            species (Species | Molecule | Protein | str): The species to assign to the wells.
            init_conc (Union[float, List[float]]): The initial concentration(s) of the species.
            conc_unit (str): The unit of concentration.
            to (Literal["all", "rows", "columns", "all except"]): The target location(s) for assigning the species.
                This can be individual or multiple wells as well as individual or multiple rows or columns.
            ids (Union[str, List[str], int, List[int]], optional): The ID(s) of the target wells, rows or columns.
            contributes_to_signal (bool, optional): Indicates if the assigned species contributes to the signal.
                Defaults to None.

        Raises:
            AttributeError: If the 'species' argument does not reference an `id` of a Species listed in `species`.
            AttributeError: If the 'to' argument is not one of ["all", "rows", "columns", "all_except"].

        Returns:
            None
        """
        # Handle species
        if isinstance(species, str):
            species = self.get_species(species)
        elif isinstance(species, Species):
            pass
        else:
            raise AttributeError(
                """Argument 'species' must reference an `id` of a Species listed in `species`."""
            )

        if to not in ASSIGN_CASE_VALUES:
            raise AttributeError(f"Argument 'to' must be one of {ASSIGN_CASE_VALUES}.")

        if not isinstance(init_conc, list):
            init_conc = [init_conc]

        if not isinstance(ids, list) and isinstance(ids, (int, str)):
            ids = [ids]  # type: ignore

        if to == "all":
            if isinstance(init_conc, list):
                if len(init_conc) == 1:
                    init_conc = init_conc[0]

            assert isinstance(init_conc, float)

            self.assign_to_all(
                species=species,
                init_conc=init_conc,
                conc_unit=conc_unit,
                contributes_to_signal=contributes_to_signal,
            )

        elif to == "columns":
            assert (
                isinstance(ids, list) and all(isinstance(i, int) for i in ids)
            ), "Argument 'ids' must be a list of integers when 'to' is set to 'columns'."

            self.assign_to_columns(
                column_ids=ids,  # type: ignore
                species=species,
                init_concs=init_conc,
                conc_unit=conc_unit,
                contributes_to_signal=contributes_to_signal,
            )

        elif to == "rows":
            assert isinstance(ids, list) and all(
                isinstance(i, str) for i in ids
            ), "Argument 'ids' must be a list of strings when 'to' is set to 'rows'."

            self.assign_species_to_rows(
                row_ids=ids,  # type: ignore
                species=species,
                init_concs=init_conc,
                conc_unit=conc_unit,
                contributes_to_signal=contributes_to_signal,
            )

        else:
            if isinstance(init_conc, list):
                if len(init_conc) == 1:
                    init_conc = init_conc[0]

            assert isinstance(
                init_conc, float
            ), "Argument 'init_conc' must be a float when 'to' is set to 'all_except'."

            self.assign_species_to_all_except(
                well_ids=ids,  # type: ignore
                species=species,
                init_conc=init_conc,
                conc_unit=conc_unit,
                contributes_to_signal=contributes_to_signal,
            )

    def assign_to_all(
        self,
        species: Species | Molecule | Protein,
        init_conc: float,
        conc_unit: UnitDefinition,
        contributes_to_signal: bool | None,
    ):
        for well in self.plate.wells:
            well.add_to_init_conditions(
                species_id=species.id,
                init_conc=init_conc,
                conc_unit=conc_unit,
            )

            self._handle_blank_status(
                well, species.id, init_conc, contributes_to_signal
            )

        print(
            f"Assigned [bold magenta]{species.name}[/] ({species.id}) with"
            f" {init_conc} {conc_unit} to all wells."
        )

    def assign_to_columns(
        self,
        column_ids: list[int],
        species: Species | Molecule | Protein,
        init_concs: list[float],
        conc_unit: UnitDefinition,
        contributes_to_signal: bool | None,
    ):
        # Handle column_ids
        if not all([isinstance(column_id, int) for column_id in column_ids]):
            raise AttributeError("Argument 'column_ids' must be a list of integers.")

        columns = []
        for column_id in column_ids:
            wells = [well for well in self.plate.wells if well.x_pos + 1 == column_id]
            wells = sorted(wells, key=lambda x: x.y_pos)
            columns.append(wells)

        # assert thal all columns are the same size
        assert all([len(column) == len(columns[0]) for column in columns]), (
            "All columns must be the same size. " ""
        )

        # Handle init_concs
        if len(init_concs) == 1:
            init_concs = init_concs * len(columns[0])

        for wells in columns:
            assert len(init_concs) == len(wells), f"""
            Number of initial concentrations ({len(init_concs)}) does not match number
            of wells ({len(wells)}) in columns ({column_ids}).
            """

            for well, init_conc in zip(wells, init_concs):
                well.add_to_init_conditions(
                    species_id=species.id,
                    init_conc=init_conc,
                    conc_unit=conc_unit,
                )

                self._handle_blank_status(
                    well, species.id, init_conc, contributes_to_signal
                )

        print(
            f"Assigned [bold magenta]{species.name}[/] ({species.id}) with"
            f" concentrations of {init_concs} {conc_unit} to columns {column_ids}."
        )

    def assign_species_to_rows(
        self,
        row_ids: list[str],
        species: Species | Molecule | Protein,
        init_concs: list[float],
        conc_unit: UnitDefinition,
        contributes_to_signal: bool | None,
    ):
        # Handle row_ids

        if isinstance(row_ids, str):
            row_ids = [row_ids]

        if not all([isinstance(row_id, str) for row_id in row_ids]):
            raise AttributeError("Argument 'row_ids' must be a list of strings.")

        rows = []
        for row_id in row_ids:
            wells = [well for well in self.plate.wells if row_id in well.id]
            wells = sorted(wells, key=lambda x: x.x_pos)
            rows.append(wells)

        for wells in rows:
            assert len(init_concs) == len(wells), f"""
            Number of initial concentrations ({len(init_concs)}) does not match number
            of wells ({len(wells)}) in rows ({row_ids}).
            """

            for well, init_conc in zip(wells, init_concs):
                well.add_to_init_conditions(
                    species_id=species.id,
                    init_conc=init_conc,
                    conc_unit=conc_unit,
                )

                self._handle_blank_status(
                    well, species.id, init_conc, contributes_to_signal
                )

        print(
            f"Assigned [bold magenta]{species.name}[/] ({species.id}) with"
            f" {init_concs} {conc_unit} to rows {row_ids}."
        )

    @staticmethod
    def _handle_blank_status(
        well: Well,
        species_id: str,
        init_conc: float,
        contributes_to_signal: bool | None,
    ):
        if contributes_to_signal is None:
            if init_conc == 0:
                contributes = False
            else:
                contributes = True
        else:
            contributes = contributes_to_signal

        for measurement in well.measurements:
            measurement.add_to_blank_states(
                species_id=species_id,
                contributes_to_signal=contributes,
            )

    def assign_species_to_all_except(
        self,
        well_ids: list[str],
        species: Species | Molecule | Protein,
        init_conc: float,
        conc_unit: UnitDefinition,
        contributes_to_signal: bool | None,
    ):
        # validate all well_id exist
        for well_id in well_ids:
            if not self._well_id_exists(well_id):
                raise AttributeError(f"Well ID '{well_id}' not found on the plate.")

        wells = (well for well in self.plate.wells if well.id not in well_ids)
        for well in wells:
            well.add_to_init_conditions(
                species_id=species.id,
                init_conc=init_conc,
                conc_unit=conc_unit,
            )

            self._handle_blank_status(
                well, species.id, init_conc, contributes_to_signal
            )

        print(
            f"Assigned [bold magenta]{species.name}[/] ({species.id}) with"
            f" {init_conc} {conc_unit} to all wells except {well_ids}."
        )

    def assign_species_from_spreadsheet(
        self,
        species: Species | Molecule | Protein,
        conc_unit: UnitDefinition,
        path: str,
        sheet_name: Optional[str] = None,
        header: int = 0,
        index: int = 0,
        contributes_to_signal: Optional[bool] = None,
    ):
        """Allows to read in a spreadsheet harboring a plate map describing the
        initial concentrations of a species in the wells of the plate.
        The parser expects the first row to contain the row ids numbered from 1 to 12.
        The first column should contain the column ids labeled from A to H.
        If additional columns or rows are present, adjust the `header` and `index`
        arguments accordingly.

        Args:
            species (Species): Species object to assign initial concentrations to.
            conc_unit (str): Unit of the concentration.
            path (str): Path to the spreadsheet.
            sheet_name (str | None, optional): Name of the sheet containing the plate map.
                Defaults to None.
            header (int, optional): Number of columns before the header starts.
                Defaults to 0.
            index (int, optional): Number of columns before the index column starts.
                Defaults to 0.
            contributes_to_signal (bool | None, optional): Whether the species contributes
                to the signal. Defaults to None.
        """
        df = pd.read_excel(path, sheet_name=sheet_name, header=header, index_col=index)

        if isinstance(species, str):
            species = self.get_species(species)

        for well in self.plate.wells:
            row = well.id[0]
            column = int(well.id[1:])
            init_conc = df.loc[row, column]  # type: ignore

            if np.isnan(init_conc):
                continue

            well.add_to_init_conditions(
                species_id=species.id,
                init_conc=init_conc,
                conc_unit=conc_unit,
            )

            self._handle_blank_status(
                well, species.id, init_conc, contributes_to_signal
            )

        print(
            f"Assigned initial concentrations for [bold magenta]{species.name}[/]"
            f" ({species.id}) from {path}."
        )

    def get_well(self, id: str) -> Well:
        for well in self.plate.wells:
            if well.id == id:
                return well

        raise ValueError(f"Well {id} not found")

    def get_species(self, id: str) -> Species | Protein | Molecule:
        for species in self.plate.species:
            if species.id == id:
                return species

        raise ValueError(f"Species {id} not found")

    def _well_id_exists(self, well_id: str) -> bool:
        """Check if a well with the given id exists in the plate."""
        return any([well_id in well.id for well in self.plate.wells])

    @classmethod
    def read_magellan(
        cls,
        path: str,
        wavelength: float,
        ph: Optional[float] = None,
    ) -> PlateManager:
        """Create a PlateManager object from a Magellan .xlsx file"""
        from MTPHandler.readers import read_magellan as reader

        return cls(plate=reader(path, wavelength, ph))


if __name__ == "__main__":
    pm = PlateManager(plate=Plate())
