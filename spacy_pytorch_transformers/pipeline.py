import spacy.pipeline
from thinc.neural.util import get_array_module
from thinc.api import layerize, chain, flatten_add_lengths
from thinc.t2v import Pooling, mean_pool
from thinc.v2v import Softmax


class PyTT_TextCategorizer(spacy.pipeline.TextCategorizer):
    """Subclass of spaCy's built-in TextCategorizer component that supports
    using the features assigned by the PyTorch-Transformers models via the token
    vector encoder. It requires the PyTT_TokenVectorEncoder to run before it in
    the pipeline.
    """

    name = "pytt_textcat"

    @classmethod
    def from_nlp(cls, nlp, **cfg):
        """Factory to add to Language.factories via entry point."""
        return cls(nlp.vocab, **cfg)

    @classmethod
    def Model(cls, nr_class, exclusive_classes=False, **cfg):
        """Create a text classification model using a PyTorch-Transformers model
        for token vector encoding.

        nr_class (int): Number of classes.
        width (int): The width of the tensors being assigned.
        exclusive_classes (bool): Make categories mutually exclusive.
        **cfg: Optional config parameters.
        RETURNS (thinc.neural.Model): The model.
        """
        return chain(
            get_pytt_class_tokens,
            flatten_add_lengths,
            Pooling(mean_pool),
            Softmax(nr_class, cfg["token_vector_width"]),
        )


@layerize
def get_pytt_class_tokens(docs, drop=0.0):
    """Output a List[array], where the array is the class vector
    for each sentence in the document. To backprop, we increment the values
    in the doc._.pytt_d_last_hidden_state array.
    """
    xp = get_array_module(docs[0]._.pytt_last_hidden_state)
    outputs = []
    for doc in docs:
        wp_tensor = doc._.pytt_last_hidden_state
        class_vectors = []
        for sent in doc.sents:
            if sent._.pytt_start is not None:
                class_vectors.append(wp_tensor[sent._.pytt_start])
            else:
                class_vectors.append(xp.zeros((wp_tensor.shape[-1],), dtype="f"))
        Y = xp.vstack(class_vectors)
        outputs.append(Y)

    def backprop_pytt_class_tokens(d_outputs, sgd=None):
        for doc, dY in zip(docs, d_outputs):
            if doc._.pytt_d_last_hidden_state is None:
                xp = get_array_module(doc._.pytt_last_hidden_state)
                grads = xp.zeros(doc._.pytt_last_hidden_state.shape, dtype="f")
                doc._.pytt_d_last_hidden_state = grads
            for i, sent in enumerate(doc.sents):
                if sent._.pytt_start is not None:
                    doc._.pytt_d_last_hidden_state[sent._.pytt_start] += dY[i]
        return None

    return outputs, backprop_pytt_class_tokens


@layerize
def get_pytt_last_hidden(docs, drop=0.0):
    """Output a List[array], where the array is the last hidden vector vector
    for each document. To backprop, we increment the values
    in the doc._.pytt_d_last_hidden_state array.
    """
    outputs = [doc._.pytt_last_hidden_state for doc in docs]
    for out in outputs:
        assert out is not None

    def backprop_pytt_last_hidden(d_outputs, sgd=None):
        for doc, d_last_hidden_state in zip(docs, d_outputs):
            if doc._.pytt_d_last_hidden_state is None:
                doc._.pytt_d_last_hidden_state = d_last_hidden_state
            else:
                doc._.pytt_d_last_hidden_state += d_last_hidden_state
        return None

    return outputs, backprop_pytt_last_hidden
