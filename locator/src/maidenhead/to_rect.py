import typing as T

from . import to_location


def to_rect(maiden: str) -> T.Tuple[float, float, float, float, float, float]:
    """
    convert Maidenhead grid to a tuple containing north, south, west, east values of the limits and the location of the center of the given square
    of the given locator.

    Parameters
    ----------

    maiden : str
        Maidenhead grid locator of length 2 to 8

    Returns
    -------

    latLon : tuple of float
        Geographic latitude, longitude
    """

    maiden = maiden.strip().upper()

    N = len(maiden)
    if not 12 >= N >= 2 and N % 2 == 0:
        raise ValueError("Maidenhead locator requires 2-8 characters, even number of characters")

    north, west = to_location(maiden)

    if N == 2:
        east = west + 20
        south = north + 10

        return north, south, west, east, south - 5, west + 10
    if N == 4:
        east = west + 2
        south = north + 1

        return north, south, west, east, south - 1, west + 0.5

    if N == 6:
        east = west + 5.0 / 60
        south = north + 2.5 / 60

        return north, south, west, east, south - 2.5 / 120, west + 5.0 / 120

    if N == 8:
        east = west + 5.0 / 600
        south = north + 2.5 / 600

        return north, south, west, east, south - 2.5 / 1200, west + 5.0 / 1200

    if N == 10:
        east = west + 5.0 / 600 / 24
        south = north + 2.5 / 600 / 24

        return north, south, west, east, south - 2.5 / 600 / 24 / 2, west + 5.0 / 600 / 24 / 2

    if N == 12:
        east = west + 5.0 / 600 / 240
        south = north + 2.5 / 600 / 240

        return north, south, west, east, south - 2.5 / 600 / 240 / 2, west + 5.0 / 600 / 240 / 2
