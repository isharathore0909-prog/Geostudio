# -*- coding: utf-8 -*-
"""
GeoStudio - Algorithm Definition
Metadata descriptor for a single processing algorithm.
"""


class AlgorithmDefinition:
    """Metadata descriptor for a single processing algorithm."""
    def __init__(
        self,
        name: str,
        algo_id: str,
        category: str,
        subcategory: str,
        description: str,
        dialog_type: str,
        supports_gpu: bool = False,
        requires_halo: bool = False,
        halo_size: int = 0
    ):
        self.name = name
        self.algo_id = algo_id
        self.category = category
        self.subcategory = subcategory
        self.description = description
        self.dialog_type = dialog_type
        self.supports_gpu = supports_gpu
        self.requires_halo = requires_halo
        self.halo_size = halo_size

    @property
    def group(self) -> str:
        """Alias for category/subcategory group."""
        return f"{self.category} / {self.subcategory}" if self.subcategory else self.category
