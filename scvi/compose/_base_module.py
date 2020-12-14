from abc import abstractmethod
from typing import Tuple, Optional

import torch
import torch.nn as nn

from ._decorators import auto_move_data


class SCVILoss:
    def __init__(self, loss, reconstruction_loss, kl_local, kl_global):

        self._loss = loss if isinstance(loss, dict) else dict(loss=loss)
        self._reconstruction_loss = (
            reconstruction_loss
            if isinstance(reconstruction_loss, dict)
            else dict(reconstruction_loss=reconstruction_loss)
        )
        self._kl_local = (
            kl_local if isinstance(kl_local, dict) else dict(kl_local=kl_local)
        )
        self._kl_global = (
            kl_global if isinstance(kl_global, dict) else dict(kl_global=kl_global)
        )

    @staticmethod
    def _get_dict_sum(dictionary):
        sum = 0.0
        for value in dictionary.values():
            sum += value
        return sum

    @property
    def loss(self):
        return self._get_dict_sum(self._loss)

    @property
    def reconstruction_loss(self):
        return self._get_dict_sum(self._reconstruction_loss)

    @property
    def kl_local(self):
        return self._get_dict_sum(self._kl_local)

    @property
    def kl_global(self):
        return self._get_dict_sum(self._kl_global)

    @property
    def elbo(self):
        return


class AbstractVAE(nn.Module):
    def __init__(
        self,
    ):
        super().__init__()

    @auto_move_data
    def forward(
        self,
        tensors,
        get_inference_input_kwargs: Optional[dict] = None,
        get_generative_input_kwargs: Optional[dict] = None,
        inference_kwargs: Optional[dict] = None,
        generative_kwargs: Optional[dict] = None,
        loss_kwargs: Optional[dict] = None,
        compute_loss=True,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through the network.

        Parameters
        ----------
        tensors
            tensors to pass through
        get_inference_input_kwargs
            Keyword args for `_get_inference_input()`
        get_generative_input_kwargs
            Keyword args for `_get_generative_input()`
        inference_kwargs
            Keyword args for `inference()`
        generative_kwargs
            Keyword args for `generative()`
        loss_kwargs
            Keyword args for `loss()`
        compute_loss
            Whether to compute loss on forward pass. This adds
            another return value.
        """
        inference_kwargs = _get_dict_if_none(inference_kwargs)
        generative_kwargs = _get_dict_if_none(generative_kwargs)
        loss_kwargs = _get_dict_if_none(loss_kwargs)
        get_inference_input_kwargs = _get_dict_if_none(get_inference_input_kwargs)
        get_generative_input_kwargs = _get_dict_if_none(get_generative_input_kwargs)

        inference_inputs = self._get_inference_input(
            tensors, **get_inference_input_kwargs
        )
        inference_outputs = self.inference(**inference_inputs, **inference_kwargs)
        generative_inputs = self._get_generative_input(
            tensors, inference_outputs, **get_generative_input_kwargs
        )
        generative_outputs = self.generative(**generative_inputs, **generative_kwargs)
        if compute_loss:
            losses = self.loss(
                tensors, inference_outputs, generative_outputs, **loss_kwargs
            )
            return inference_outputs, generative_outputs, losses
        else:
            return inference_outputs, generative_outputs

    @abstractmethod
    def _get_inference_input(self, tensors, **kwargs):
        pass

    @abstractmethod
    def _get_generative_input(self, tensors, inference_outputs, **kwargs):
        pass

    @abstractmethod
    def inference(
        self,
        *args,
        **kwargs,
    ):
        pass

    @abstractmethod
    def generative(self, *args, **kwargs):
        pass

    @abstractmethod
    def loss(self, *args, **kwargs):
        pass

    @abstractmethod
    def sample(self, *args, **kwargs):
        pass


def _get_dict_if_none(param):
    param = {} if not isinstance(param, dict) else param

    return param
