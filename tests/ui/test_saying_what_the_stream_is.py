"""The line beside the clock saying what the device actually took.

The report has existed since the exclusive path was written and nothing on
screen read it, which ARCHITECTURE.md recorded as the missing half of the
feature. Without it a listener presses the switch and has no way of learning
that the device refused, which is the one case they most need told.

The wording is pure, so it is checked here without a screen. That the position
bar shows it is checked in `test_the_position_bar.py`; that the poll keeps it
current is checked with the rest of the transport's showing.
"""

from __future__ import annotations

import pytest

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.ui.stream_words import rate_text, stream_text

CD_RATE = 44100
STUDIO_RATE = 96000
DVD_RATE = 48000
DEPTH = 24
MIXER_DEPTH = 32
NO_DEPTH = 0


def report(
    mode: OutputMode = OutputMode.EXCLUSIVE,
    rate: int = CD_RATE,
    depth: int = DEPTH,
    asked: OutputMode | None = None,
    reason: str = "",
    file_depth: int = DEPTH,
) -> OutputReport:
    """One stream as the device answered for it."""
    return OutputReport(
        request=OutputRequest(
            sample_rate=rate, bit_depth=file_depth, mode=asked or mode
        ),
        mode=mode,
        sample_rate=rate,
        bit_depth=depth,
        fallback_reason=reason,
    )


class TestSayingTheRate:
    @pytest.mark.parametrize(
        ("rate", "said"),
        [
            (CD_RATE, "44.1 kHz"),
            (DVD_RATE, "48 kHz"),
            (STUDIO_RATE, "96 kHz"),
            (88200, "88.2 kHz"),
            (192000, "192 kHz"),
        ],
    )
    def test_it_reads_as_the_number_people_use(self, rate: int, said: str) -> None:
        """48 rather than 48.0; 44.1 rather than 44.1000."""
        assert rate_text(rate) == said


class TestSayingTheStream:
    def test_nothing_open_says_nothing_at_all(self) -> None:
        """An empty line rather than the words "no stream" taking up room."""
        assert stream_text(None) == ""

    def test_an_exclusive_stream_says_so_with_its_rate_and_depth(self) -> None:
        assert stream_text(report()) == "exclusive, 44.1 kHz, 24 bit, bit perfect"

    def test_a_shared_stream_is_never_claimed_bit_perfect(self) -> None:
        """The mixer resamples by definition, which is the whole point."""
        said = stream_text(
            report(mode=OutputMode.SHARED, depth=MIXER_DEPTH, asked=OutputMode.SHARED)
        )
        assert said == "shared, 44.1 kHz, 32 bit"

    def test_a_lossy_file_is_not_claimed_bit_perfect_either(self) -> None:
        """Nothing a device does un-decodes an MP3."""
        said = stream_text(report(file_depth=NO_DEPTH))
        assert "bit perfect" not in said

    def test_a_refusal_is_not_reported_here_at_all(self) -> None:
        """Oliver ruled on 2026-09-18 that the switch stands down instead.

        By the time this line is drawn the application really is in shared
        mode, so there is nothing left to qualify. The refusal is said once
        along the status line, which `test_the_output_switch.py` holds.
        """
        said = stream_text(
            report(
                mode=OutputMode.SHARED,
                depth=MIXER_DEPTH,
                asked=OutputMode.EXCLUSIVE,
                reason="the device is in use",
            )
        )
        assert said == "shared, 44.1 kHz, 32 bit"
        assert "refused" not in said

    def test_a_stream_that_fell_back_reads_like_one_nobody_asked_about(
        self,
    ) -> None:
        """Both really are the mixer, so both say the mixer and no more."""
        chosen = stream_text(
            report(mode=OutputMode.SHARED, depth=MIXER_DEPTH, asked=OutputMode.SHARED)
        )
        fell_back = stream_text(
            report(
                mode=OutputMode.SHARED,
                depth=MIXER_DEPTH,
                asked=OutputMode.EXCLUSIVE,
                reason="the device is in use",
            )
        )
        assert chosen == fell_back
