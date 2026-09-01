"""The bands, the switch and the coefficients each band turns into.

The arithmetic is worth testing directly rather than only through its sound,
because a filter that is subtly wrong still makes a noise. What is asserted
here is the shape of the answer: a band left alone produces no section at all,
a band with nowhere to act produces none either; a lift and a cut of the same
size undo one another exactly.
"""

from __future__ import annotations

import cmath
import itertools
import math

import pytest

from stellody.domain.equalising import (
    BAND_COUNT,
    BAND_FREQUENCIES,
    FLAT_DB,
    MAXIMUM_GAIN_DB,
    MINIMUM_GAIN_DB,
    Equalisation,
    as_text,
    cascade,
    from_text,
    peaking,
)

CD_RATE = 44100
LIFT_DB = 6.0


def response_db(section, frequency: int, sample_rate: int) -> float:
    """How much this section lifts or cuts that frequency, in decibels.

    The transfer function evaluated on the unit circle, which is the only
    honest way to ask what a set of coefficients actually does.
    """
    angle = 2 * math.pi * frequency / sample_rate
    z = cmath.exp(-1j * angle)
    numerator = section.b0 + section.b1 * z + section.b2 * z * z
    denominator = 1.0 + section.a1 * z + section.a2 * z * z
    return 20.0 * math.log10(abs(numerator / denominator))


def lifted(band: int = 0, gain_db: float = LIFT_DB) -> Equalisation:
    """A switched-on equalisation with one band moved off nought."""
    return Equalisation(enabled=True).with_band(band, gain_db)


class TestTheBandsThemselves:
    def test_there_are_ten_of_them_at_the_octave_centres(self) -> None:
        """Ten octaves is what an octave-wide filter divides hearing into."""
        assert len(BAND_FREQUENCIES) == BAND_COUNT
        for lower, upper in itertools.pairwise(BAND_FREQUENCIES):
            assert upper == pytest.approx(lower * 2, rel=0.02), "an octave apart"

    def test_a_new_equalisation_is_flat_and_switched_off(self) -> None:
        """A fresh install shapes nothing until somebody asks it to."""
        setting = Equalisation()
        assert setting.gains_db == (FLAT_DB,) * BAND_COUNT
        assert setting.enabled is False
        assert setting.flat is True

    def test_a_curve_needs_one_gain_for_every_band(self) -> None:
        """A short tuple would silently leave the top of the range unshaped."""
        with pytest.raises(ValueError):
            Equalisation(gains_db=(FLAT_DB,))

    @pytest.mark.parametrize("gain", (MAXIMUM_GAIN_DB + 1, MINIMUM_GAIN_DB - 1))
    def test_a_band_cannot_be_set_past_what_the_sliders_offer(self, gain) -> None:
        """The range is the range; a stored value out of it is not honoured."""
        with pytest.raises(ValueError):
            Equalisation(enabled=True).with_band(0, gain)


class TestWhetherItDoesAnything:
    def test_a_switched_off_curve_is_flat_however_it_is_set(self) -> None:
        """Off means off, whatever the sliders were left at."""
        assert lifted().switched(False).flat is True

    def test_a_switched_on_curve_at_nought_is_flat_too(self) -> None:
        """Nothing to do is nothing to do, so nothing is done."""
        assert Equalisation(enabled=True).flat is True

    def test_a_switched_on_curve_with_a_band_moved_is_not_flat(self) -> None:
        """This is the one case that costs anything at all."""
        assert lifted().flat is False

    def test_switching_off_keeps_the_curve_for_when_it_comes_back(self) -> None:
        """Comparing on against off must not cost somebody their settings."""
        assert lifted().switched(False).gains_db == lifted().gains_db

    def test_flattening_keeps_the_switch_where_it_was(self) -> None:
        """The two are separate answers, so one does not move the other."""
        levelled = lifted().levelled()
        assert levelled.enabled is True
        assert levelled.gains_db == (FLAT_DB,) * BAND_COUNT


class TestTheSectionsThatComeOut:
    def test_a_flat_curve_produces_no_sections_at_all(self) -> None:
        """Which is what lets it cost nothing rather than little."""
        assert cascade(Equalisation(), CD_RATE) == ()
        assert cascade(Equalisation(enabled=True), CD_RATE) == ()

    def test_only_the_bands_that_were_moved_produce_one(self) -> None:
        """A band at nought is exactly the identity, so it is dropped."""
        assert len(cascade(lifted(), CD_RATE)) == 1

    def test_a_band_with_nothing_above_it_to_act_on_is_dropped(self) -> None:
        """At eight kilohertz sampled, the top bands are past half the rate."""
        every_band = Equalisation(gains_db=(LIFT_DB,) * BAND_COUNT, enabled=True)
        sections = cascade(every_band, 8000)
        assert len(sections) == sum(1 for f in BAND_FREQUENCIES if f < 4000)

    def test_a_band_lifts_its_own_frequency_by_what_was_asked(self) -> None:
        """The response is evaluated rather than the coefficients eyeballed.

        This is what "the bands change what is heard" means arithmetically: a
        band asked for six decibels gives six decibels at its centre.
        """
        centre = BAND_FREQUENCIES[4]
        section = peaking(centre, LIFT_DB, CD_RATE)
        assert response_db(section, centre, CD_RATE) == pytest.approx(LIFT_DB, abs=0.01)

    def test_a_band_leaves_a_distant_frequency_alone(self) -> None:
        """An octave-wide band must not drag the whole spectrum with it."""
        section = peaking(BAND_FREQUENCIES[4], LIFT_DB, CD_RATE)
        assert response_db(section, BAND_FREQUENCIES[0], CD_RATE) < 0.5

    def test_a_lift_and_a_cut_of_the_same_size_undo_one_another(self) -> None:
        """Cascaded, they are the identity, which a mistyped exponent breaks."""
        centre = BAND_FREQUENCIES[4]
        up = peaking(centre, LIFT_DB, CD_RATE)
        down = peaking(centre, -LIFT_DB, CD_RATE)
        for frequency in (100, 1000, 5000):
            together = response_db(up, frequency, CD_RATE) + response_db(
                down, frequency, CD_RATE
            )
            assert together == pytest.approx(0.0, abs=1e-9)

    def test_a_band_left_at_nought_is_the_identity(self) -> None:
        """Not approximately: the numerator and denominator are the same."""
        section = peaking(BAND_FREQUENCIES[3], FLAT_DB, CD_RATE)
        assert section.b0 == pytest.approx(1.0)
        assert section.b1 == pytest.approx(section.a1)
        assert section.b2 == pytest.approx(section.a2)


class TestStoringIt:
    def test_a_curve_survives_being_written_down_and_read_back(self) -> None:
        """A switch that forgets itself is the same as not having one."""
        setting = lifted(band=2, gain_db=-3.0)
        assert from_text(as_text(setting), setting.enabled) == setting

    def test_nothing_stored_reads_as_flat_rather_than_raising(self) -> None:
        """A fresh install has nothing there at all."""
        assert from_text("", False) == Equalisation()

    def test_a_meddled_setting_costs_a_curve_rather_than_the_player(self) -> None:
        """Unreadable is not a reason to refuse to start."""
        assert from_text("loud,louder", True) == Equalisation(enabled=True)
