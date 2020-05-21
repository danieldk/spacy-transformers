from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, List, Dict

import torch
import numpy
from transformers.tokenization_utils import BatchEncoding
from thinc.types import Ragged, Floats3d, FloatsXd
from thinc.api import get_array_module, xp2torch, torch2xp
from spacy.tokens import Span

from .util import slice_hf_tokens
from .align import get_token_positions


@dataclass
class TransformerData:
    """Transformer tokens and outputs for one Doc object."""

    tokens: Dict
    tensors: List[FloatsXd]
    align: Ragged

    @classmethod
    def empty(cls) -> "TransformerData":
        align = Ragged(numpy.zeros((0,), dtype="i"), numpy.zeros((0,), dtype="i"))
        return cls(tokens={}, tensors=[], align=align)

    @property
    def width(self) -> int:
        for tensor in reversed(self.tensors):
            if len(tensor.shape) == 3:
                return tensor.shape[-1]
        else:
            raise ValueError("Cannot find last hidden layer")


@dataclass
class FullTransformerBatch:
    spans: List[Span]
    tokens: BatchEncoding
    tensors: List[torch.Tensor]
    align: Ragged
    _doc_data: Optional[List[TransformerData]] = None

    @property
    def doc_data(self) -> List[TransformerData]:
        if self._doc_data is None:
            self._doc_data = self.split_by_doc()
        return self._doc_data

    def unsplit_by_doc(self, arrays: List[List[Floats3d]]) -> "FullTransformerBatch":
        xp = get_array_module(arrays[0][0])
        return FullTransformerBatch(
            spans=self.spans,
            tokens=self.tokens,
            tensors=[xp2torch(xp.vstack(x)) for x in transpose_list(arrays)],
            align=self.align,
        )

    def split_by_doc(self) -> List["TransformerData"]:
        """Split a TransformerData that represents a batch into a list with
        one TransformerData per Doc.
        """
        spans_by_doc = defaultdict(list)
        for span in self.spans:
            spans_by_doc[id(span.doc)].append(span)
        token_positions = get_token_positions(self.spans)
        outputs = []
        start = 0
        for doc_spans in spans_by_doc.values():
            start_i = token_positions[doc_spans[0][0]]
            end_i = token_positions[doc_spans[-1][-1]] + 1
            end = start + len(doc_spans)
            outputs.append(
                TransformerData(
                    tokens=slice_hf_tokens(self.tokens, start, end),
                    tensors=[torch2xp(t[start:end]) for t in self.tensors],  # type: ignore
                    align=self.align[start_i:end_i],
                )
            )
            start += len(doc_spans)
        return outputs


def transpose_list(nested_list):
    output = []
    for i, entry in enumerate(nested_list):
        while len(output) < len(entry):
            output.append([None] * len(nested_list))
        for j, x in enumerate(entry):
            output[j][i] = x
    return output