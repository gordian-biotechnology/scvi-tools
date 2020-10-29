import copy
import logging
from typing import Optional

import anndata
import numpy as np
import torch
from torch.utils.data import DataLoader

from scvi import _CONSTANTS
from scvi.data._scvidataset import ScviDataset

logger = logging.getLogger(__name__)


class BatchSampler(torch.utils.data.sampler.Sampler):
    """
    Custom torch Sampler that returns a list of indices of size batch_size.

    Parameters
    ----------
    indices
        list of indices to sample from
    batch_size
        batch size of each iteration
    shuffle
        if ``True``, shuffles indices before sampling

    """

    def __init__(self, indices: np.ndarray, batch_size: int, shuffle: bool):
        self.indices = indices
        self.batch_size = batch_size
        self.shuffle = shuffle

    def __iter__(self):
        if self.shuffle is True:
            idx = torch.randperm(len(self.indices)).tolist()
        else:
            idx = torch.arange(len(self.indices)).tolist()

        data_iter = iter(
            [
                self.indices[idx[i : i + self.batch_size]]
                for i in range(0, len(idx), self.batch_size)
            ]
        )
        return data_iter

    def __len__(self):
        return len(self.indices) // self.batch_size


class ScviDataLoader(DataLoader):
    """
    Scvi Data Loader.

    A `ScviDataLoader` instance is instantiated with a model and a gene_dataset, and
    as well as additional arguments that for Pytorch's `DataLoader`. A subset of indices can be specified, for
    purposes such as splitting the data into train/test or labelled/unlabelled (for semi-supervised learning).
    Each trainer instance of the `Trainer` class can therefore have multiple `ScviDataLoader` instances to train a model.
    A `ScviDataLoader` instance also comes with methods to compute likelihood and other relevant training metrics.

    Parameters
    ----------
    adata
        An anndata instance
    shuffle
        Specifies if a `RandomSampler` or a `SequentialSampler` should be used
    indices
        Specifies how the data should be split with regards to train/test or labelled/unlabelled
    use_cuda
        Default: ``True``
    data_loader_kwargs
        Keyword arguments to passed into the `DataLoader`

    """

    def __init__(
        self,
        adata: anndata.AnnData,
        shuffle=False,
        indices=None,
        use_cuda=True,
        batch_size=128,
        data_loader_kwargs=dict(),
        data_and_attributes: Optional[dict] = None,
    ):

        if "_scvi" not in adata.uns.keys():
            raise ValueError("Please run setup_anndata() on your anndata object first.")

        if data_and_attributes is None:
            self._data_and_attributes = {
                _CONSTANTS.X_KEY: np.float32,
                _CONSTANTS.BATCH_KEY: np.int64,
                _CONSTANTS.LOCAL_L_MEAN_KEY: np.float32,
                _CONSTANTS.LOCAL_L_VAR_KEY: np.float32,
                _CONSTANTS.LABELS_KEY: np.int64,
            }
        else:
            self._data_and_attributes = data_and_attributes

        for key in self._data_and_attributes.keys():
            if key not in adata.uns["_scvi"]["data_registry"].keys():
                raise ValueError(
                    "{} required for model but not included when setup_anndata was run".format(
                        key
                    )
                )

        self.dataset = ScviDataset(adata, getitem_tensors=data_and_attributes)
        self.to_monitor = []
        self.use_cuda = use_cuda

        if indices is None:
            inds = np.arange(len(self.dataset))
            if shuffle:
                sampler_kwargs = {
                    "indices": inds,
                    "batch_size": batch_size,
                    "shuffle": True,
                }
            else:
                sampler_kwargs = {
                    "indices": inds,
                    "batch_size": batch_size,
                    "shuffle": False,
                }
        else:
            if hasattr(indices, "dtype") and indices.dtype is np.dtype("bool"):
                indices = np.where(indices)[0].ravel()
            indices = np.asarray(indices)
            sampler_kwargs = {
                "indices": indices,
                "batch_size": batch_size,
                "shuffle": True,
            }

        self.indices = indices
        self.sampler_kwargs = sampler_kwargs
        sampler = BatchSampler(**self.sampler_kwargs)
        self.data_loader_kwargs = copy.copy(data_loader_kwargs)
        # do not touch batch size here, sampler gives batched indices
        self.data_loader_kwargs.update({"sampler": sampler, "batch_size": None})

        super().__init__(self.dataset, **self.data_loader_kwargs)
