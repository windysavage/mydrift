from typing import Protocol

import numpy as np


class EncoderProtocol(Protocol):
    def encode(
        self, sentences: list[str], show_progress_bar: bool = False
    ) -> np.ndarray: ...
