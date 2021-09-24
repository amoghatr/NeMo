# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
# Copyright 2015 and onwards Google, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from nemo_text_processing.text_normalization.en.graph_utils import NEMO_DIGIT, GraphFst
from pynini.lib.rewrite import top_rewrite

try:
    import pynini
    from pynini.lib import pynutil

    delete_space = pynutil.delete(" ")

    PYNINI_AVAILABLE = True
except (ModuleNotFoundError, ImportError):
    PYNINI_AVAILABLE = False


class DecimalFst(GraphFst):
    """
    Finite state transducer for classifying decimal, e.g. 
        -12.5006 billion -> decimal { negative: "true" integer_part: "12"  fractional_part: "five o o six" quantity: "billion" }
        1 billion -> decimal { integer_part: "one" quantity: "billion" }

    cardinal: CardinalFst
    """

    def __init__(self, cardinal: GraphFst, deterministic: bool):
        super().__init__(name="decimal", kind="classify", deterministic=deterministic)

        filter_integer_part = cardinal.filter + pynini.accep(".") + pynini.closure(NEMO_DIGIT, 1)
        filter_fractional_part = pynini.closure(NEMO_DIGIT) + pynini.accep(".") + NEMO_DIGIT ** (4, ...)
        self.filter = filter_integer_part | filter_fractional_part

        graph = pynini.closure(
            pynutil.insert("integer_part: \"") + cardinal.single_digits_graph + pynutil.insert("\""), 0, 1
        )
        graph += pynini.cross(".", " ")
        graph += pynutil.insert("fractional_part: \"") + cardinal.single_digits_graph + pynutil.insert("\"")

        self.final_graph = pynini.compose(self.filter, graph).optimize()
        self.fst = self.add_tokens(self.final_graph.optimize())

        assert (
            top_rewrite("123.01891", self.final_graph)
            == 'integer_part: "one two three" fractional_part: "zero one eight nine one"'
        )