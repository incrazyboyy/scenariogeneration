"""
scenariogeneration
https://github.com/pyoscx/scenariogeneration

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.

Copyright (c) 2022 The scenariogeneration Authors.


  This is a collection methods and classes not related to OpenDRIVE, but relates to automation of lane creations

"""

import copy
from typing import Optional, Union

import numpy as np

from .lane import Lane, Lanes, LaneSection, RoadLine, RoadMark, RoadMarkType
from .links import LaneLinker
from .utils import get_coeffs_for_poly3


def std_roadmark_solid() -> RoadMark:
    """Create a standard solid roadmark.

    This function generates a solid roadmark with a default width of 0.2.

    Returns
    -------
    RoadMark
        A `RoadMark` object representing a solid roadmark.
    """
    return RoadMark(RoadMarkType.solid, 0.2)


def std_roadmark_broken() -> RoadMark:
    """Create a standard broken roadmark.

    This function generates a broken roadmark with a default width of 0.2
    and a specific road line pattern.

    Returns
    -------
    RoadMark
        A `RoadMark` object representing a broken roadmark.
    """
    roadmark = RoadMark(RoadMarkType.broken, 0.2)
    roadmark.add_specific_road_line(RoadLine(0.15, 3, 9, 0, 0))
    return roadmark


def std_roadmark_broken_long_line() -> RoadMark:
    """Create a standard broken roadmark with a long line pattern.

    This function generates a broken roadmark with a default width of 0.2
    and a specific road line pattern where the line is longer than the
    gap.

    Returns
    -------
    RoadMark
        A `RoadMark` object representing a broken roadmark with a long
        line.
    """
    roadmark = RoadMark(RoadMarkType.broken, 0.2)
    roadmark.add_specific_road_line(RoadLine(0.15, 9, 3, 0, 0))
    return roadmark


def std_roadmark_broken_tight() -> RoadMark:
    """Create a standard broken roadmark with a tight line pattern.

    This function generates a broken roadmark with a default width of 0.2
    and a specific road line pattern where the line and gap are of equal
    length.

    Returns
    -------
    RoadMark
        A `RoadMark` object representing a broken roadmark with a tight
        line pattern.
    """
    roadmark = RoadMark(RoadMarkType.broken, 0.2)
    roadmark.add_specific_road_line(RoadLine(0.15, 3, 3, 0, 0))
    return roadmark


def std_roadmark_broken_broken() -> RoadMark:
    """Create a standard broken-broken roadmark.

    This function generates a broken-broken roadmark with two parallel
    broken lines, each with a default width of 0.2.

    Returns
    -------
    RoadMark
        A `RoadMark` object representing a broken-broken roadmark.
    """
    roadmark = RoadMark(RoadMarkType.broken_broken)
    roadmark.add_specific_road_line(RoadLine(0.2, 3, 3, 0.2, 0))
    roadmark.add_specific_road_line(RoadLine(0.2, 3, 3, -0.2, 0))
    return roadmark


def std_roadmark_solid_solid() -> RoadMark:
    """Create a standard solid-solid roadmark.

    This function generates a solid-solid roadmark with two parallel solid
    lines, each with a default width of 0.2.

    Returns
    -------
    RoadMark
        A `RoadMark` object representing a solid-solid roadmark.
    """
    roadmark = RoadMark(RoadMarkType.solid_solid)
    roadmark.add_specific_road_line(RoadLine(0.2, 0, 0, 0.2, 0))
    roadmark.add_specific_road_line(RoadLine(0.2, 0, 0, -0.2, 0))
    return roadmark


def std_roadmark_solid_broken() -> RoadMark:
    """Create a standard solid-broken roadmark.

    This function generates a solid-broken roadmark with two parallel
    lines: one solid and one broken, each with a default width of 0.2.

    Returns
    -------
    RoadMark
        A `RoadMark` object representing a solid-broken roadmark.
    """
    roadmark = RoadMark(RoadMarkType.solid_broken)
    roadmark.add_specific_road_line(RoadLine(0.2, 0, 0, 0.2, 0))
    roadmark.add_specific_road_line(RoadLine(0.2, 3, 3, -0.2, 0))
    return roadmark


def std_roadmark_broken_solid() -> RoadMark:
    """Create a standard broken-solid roadmark.

    This function generates a broken-solid roadmark with two paralle
    lines: one broken and one solid, each with a default width of 0.2.

    Returns
    -------
    RoadMark
        A `RoadMark` object representing a broken-solid roadmark.
    """
    roadmark = RoadMark(RoadMarkType.broken_solid)
    roadmark.add_specific_road_line(RoadLine(0.2, 3, 3, 0.2, 0))
    roadmark.add_specific_road_line(RoadLine(0.2, 0, 0, -0.2, 0))
    return roadmark


def create_lanes_merge_split(
    right_lane_def: Union[list["LaneDef"], int],
    left_lane_def: Union[list["LaneDef"], int],
    road_length: float,
    center_road_mark: RoadMark,
    lane_width: float,
    lane_width_end: Optional[float] = None,
) -> Lanes:
    """Create lanes for a road with one or more lane merges or splits.

    This function generates the lanes of a road that can contain one or
    more lane merges or splits. It has the following constraints:
    - Left and right merges must occur at the same location (or one per
    lane).
      This will be fixed with the `singleSide` attribute in the future.
    - The lane change is modeled as a 3rd-degree polynomial with zero
      derivatives at both the start and end.

    Note
    ----
    The merges and splits are defined in the road direction, not the
    driving direction.

    Parameters
    ----------
    right_lane_def : list of LaneDef or int
        A list of lane definitions for the right side of the road, or an
        integer specifying a constant number of lanes.
    left_lane_def : list of LaneDef or int
        A list of lane definitions for the left side of the road, or an
        integer specifying a constant number of lanes.
    road_length : float
        The total length of the road.
    center_road_mark : RoadMark
        The roadmark for the center line.
    lane_width : float
        The width of the lanes.
    lane_width_end : float, optional
        The width of the lanes at the end of the road. Default is None.

    Returns
    -------
    Lanes
        A `Lanes` object representing the lanes of the road.
    """

    lanesections = []
    # expand the lane list
    right_lane, left_lane = _create_lane_lists(
        right_lane_def, left_lane_def, road_length, lane_width
    )

    # create the lanesections needed
    for ls in range(len(left_lane)):
        lc = Lane(a=0)
        lc.add_roadmark(copy.deepcopy(center_road_mark))
        lsec = LaneSection(left_lane[ls].s_start, lc)
        # do the right lanes
        for i in range(
            max(right_lane[ls].n_lanes_start, right_lane[ls].n_lanes_end)
        ):
            # add broken roadmarks for all lanes, except for the outer lane where a solid line is added
            if (
                i
                == max(
                    right_lane[ls].n_lanes_start, right_lane[ls].n_lanes_end
                )
                - 1
            ):
                rm = std_roadmark_solid()
            else:
                rm = std_roadmark_broken()

            # check if the number of lanes should change or not
            if (
                right_lane[ls].n_lanes_start > right_lane[ls].n_lanes_end
                and i == np.abs(right_lane[ls].sub_lane) - 1
            ):
                # lane merge
                coeff = get_coeffs_for_poly3(
                    right_lane[ls].s_end - right_lane[ls].s_start,
                    right_lane[ls].lane_start_widths[i],
                    False,
                    right_lane[ls].lane_end_widths[i],
                )
                rightlane = Lane(
                    a=coeff[0], b=coeff[1], c=coeff[2], d=coeff[3]
                )
                rightlane.add_roadmark(rm)
            elif (
                right_lane[ls].n_lanes_start < right_lane[ls].n_lanes_end
                and i == np.abs(right_lane[ls].sub_lane) - 1
            ):
                # lane split
                coeff = get_coeffs_for_poly3(
                    right_lane[ls].s_end - right_lane[ls].s_start,
                    right_lane[ls].lane_start_widths[i],
                    True,
                    right_lane[ls].lane_end_widths[i],
                )
                rightlane = Lane(
                    a=coeff[0], b=coeff[1], c=coeff[2], d=coeff[3]
                )
                rightlane.add_roadmark(rm)
            elif (lane_width_end is not None) and (
                lane_width != lane_width_end
            ):
                coeff = get_coeffs_for_poly3(
                    right_lane[ls].s_end - right_lane[ls].s_start,
                    lane_width,
                    False,
                    lane_width_end=lane_width_end,
                )
                rightlane = Lane(
                    a=coeff[0], b=coeff[1], c=coeff[2], d=coeff[3]
                )
                rightlane.add_roadmark(rm)
            elif right_lane[ls].lane_start_widths:
                coeff = get_coeffs_for_poly3(
                    right_lane[ls].s_end - right_lane[ls].s_start,
                    right_lane[ls].lane_start_widths[i],
                    False,
                    lane_width_end=right_lane[ls].lane_end_widths[i],
                )
                rightlane = Lane(
                    a=coeff[0], b=coeff[1], c=coeff[2], d=coeff[3]
                )
                rightlane.add_roadmark(rm)
            else:
                rightlane = Lane(lane_width)
                rightlane.add_roadmark(rm)
            lsec.add_right_lane(rightlane)

        # do the left lanes
        for i in range(
            max(left_lane[ls].n_lanes_start, left_lane[ls].n_lanes_end)
        ):
            # add broken roadmarks for all lanes, except for the outer lane where a solid line is added
            if (
                i
                == max(left_lane[ls].n_lanes_start, left_lane[ls].n_lanes_end)
                - 1
            ):
                rm = std_roadmark_solid()
            else:
                rm = std_roadmark_broken()

            # check if the number of lanes should change or not
            if (
                left_lane[ls].n_lanes_start < left_lane[ls].n_lanes_end
                and i == left_lane[ls].sub_lane - 1
            ):
                # lane split
                coeff = get_coeffs_for_poly3(
                    left_lane[ls].s_end - left_lane[ls].s_start,
                    left_lane[ls].lane_start_widths[i],
                    True,
                    left_lane[ls].lane_end_widths[i],
                )
                leftlane = Lane(a=coeff[0], b=coeff[1], c=coeff[2], d=coeff[3])
                leftlane.add_roadmark(rm)
            elif (
                left_lane[ls].n_lanes_start > left_lane[ls].n_lanes_end
                and i == left_lane[ls].sub_lane - 1
            ):
                # lane merge
                coeff = get_coeffs_for_poly3(
                    left_lane[ls].s_end - left_lane[ls].s_start,
                    left_lane[ls].lane_start_widths[i],
                    False,
                    left_lane[ls].lane_end_widths[i],
                )
                leftlane = Lane(a=coeff[0], b=coeff[1], c=coeff[2], d=coeff[3])
                leftlane.add_roadmark(rm)
            elif (lane_width_end is not None) and (
                lane_width != lane_width_end
            ):
                coeff = get_coeffs_for_poly3(
                    left_lane[ls].s_end - left_lane[ls].s_start,
                    lane_width,
                    False,
                    lane_width_end=lane_width_end,
                )
                leftlane = Lane(a=coeff[0], b=coeff[1], c=coeff[2], d=coeff[3])
                leftlane.add_roadmark(rm)
            elif left_lane[ls].lane_start_widths:
                coeff = get_coeffs_for_poly3(
                    left_lane[ls].s_end - left_lane[ls].s_start,
                    left_lane[ls].lane_start_widths[i],
                    False,
                    lane_width_end=left_lane[ls].lane_end_widths[i],
                )
                leftlane = Lane(a=coeff[0], b=coeff[1], c=coeff[2], d=coeff[3])
                leftlane.add_roadmark(rm)
            else:
                leftlane = Lane(lane_width)
                leftlane.add_roadmark(rm)
            lsec.add_left_lane(leftlane)

        lanesections.append(lsec)

    # create the lane linker to link the lanes correctly
    lanelinker = LaneLinker()
    for i in range(1, len(right_lane)):
        if right_lane[i].n_lanes_end > right_lane[i].n_lanes_start:
            # lane split
            for j in range(0, right_lane[i - 1].n_lanes_end + 1):
                # adjust for the new lane
                if right_lane[i].sub_lane < -(j + 1):
                    lanelinker.add_link(
                        lanesections[i - 1].rightlanes[j],
                        lanesections[i].rightlanes[j],
                    )
                elif right_lane[i].sub_lane > -(j + 1):
                    lanelinker.add_link(
                        lanesections[i - 1].rightlanes[j - 1],
                        lanesections[i].rightlanes[j],
                    )
        elif right_lane[i - 1].n_lanes_end < right_lane[i - 1].n_lanes_start:
            # lane merge
            for j in range(0, right_lane[i - 1].n_lanes_end + 1):
                # adjust for the lost lane
                if right_lane[i - 1].sub_lane < -(j + 1):
                    lanelinker.add_link(
                        lanesections[i - 1].rightlanes[j],
                        lanesections[i].rightlanes[j],
                    )
                elif right_lane[i - 1].sub_lane > -(j + 1):
                    lanelinker.add_link(
                        lanesections[i - 1].rightlanes[j],
                        lanesections[i].rightlanes[j - 1],
                    )

        else:
            # same number of lanes, just add the links
            for j in range(right_lane[i - 1].n_lanes_end):
                lanelinker.add_link(
                    lanesections[i - 1].rightlanes[j],
                    lanesections[i].rightlanes[j],
                )

    for i in range(1, len(left_lane)):
        if left_lane[i].n_lanes_end > left_lane[i].n_lanes_start:
            # lane split
            for j in range(0, left_lane[i - 1].n_lanes_end + 1):
                # adjust for the new lane
                if left_lane[i].sub_lane < (j + 1):
                    lanelinker.add_link(
                        lanesections[i - 1].leftlanes[j - 1],
                        lanesections[i].leftlanes[j],
                    )
                elif left_lane[i].sub_lane > (j + 1):
                    lanelinker.add_link(
                        lanesections[i - 1].leftlanes[j],
                        lanesections[i].leftlanes[j],
                    )
        elif left_lane[i - 1].n_lanes_end < left_lane[i - 1].n_lanes_start:
            # lane merge
            for j in range(0, left_lane[i - 1].n_lanes_end + 1):
                # adjust for the lost lane
                if left_lane[i - 1].sub_lane < (j + 1):
                    lanelinker.add_link(
                        lanesections[i - 1].leftlanes[j],
                        lanesections[i].leftlanes[j - 1],
                    )
                elif left_lane[i - 1].sub_lane > (j + 1):
                    lanelinker.add_link(
                        lanesections[i - 1].leftlanes[j],
                        lanesections[i].leftlanes[j],
                    )

        else:
            # same number of lanes, just add the links
            for j in range(left_lane[i - 1].n_lanes_end):
                lanelinker.add_link(
                    lanesections[i - 1].leftlanes[j],
                    lanesections[i].leftlanes[j],
                )

    # Add the lanesections to the lanes struct together the lanelinker
    lanes = Lanes()
    for ls in lanesections:
        lanes.add_lanesection(ls, lanelinker)
    return lanes


class LaneDef:
    """Helper class to define a lane merge or split.

    This class is not part of the OpenDRIVE standard but is used as a
    helper for the xodr module to handle lane merges or splits.

    Parameters
    ----------
    s_start : float
        The `s` coordinate of the start of the change.
    s_end : float
        The `s` coordinate of the end of the change.
    n_lanes_start : int
        The number of lanes at `s_start`.
    n_lanes_end : int
        The number of lanes at `s_end`.
    sub_lane : int, optional
        The lane that should be created (split) or removed (merge).
        Default is None.
    lane_start_widths : list of float, optional
        The widths of lanes at the start. Must be empty or the same length
        as `n_lanes_start`. Default is an empty list.
    lane_end_widths : list of float, optional
        The widths of lanes at the end. Must be empty or the same length
        as `n_lanes_end`. Default is the same as `lane_start_widths`.

    Attributes
    ----------
    s_start : float
        The `s` coordinate of the start of the change.
    s_end : float
        The `s` coordinate of the end of the change.
    n_lanes_start : int
        The number of lanes at `s_start`.
    n_lanes_end : int
        The number of lanes at `s_end`.
    sub_lane : int
        The lane that should be created (split) or removed (merge).
    lane_start_widths : list of float
        The widths of lanes at the start.
    lane_end_widths : list of float
        The widths of lanes at the end.
    """

    def __init__(
        self,
        s_start: float,
        s_end: float,
        n_lanes_start: int,
        n_lanes_end: int,
        sub_lane: Optional[int] = None,
        lane_start_widths: Optional[list[float]] = [],
        lane_end_widths: Optional[list[float]] = [],
    ) -> None:
        """Initialize a `LaneDef` instance.

        Parameters
        ----------
        s_start : float
            The `s` coordinate of the start of the change.
        s_end : float
            The `s` coordinate of the end of the change.
        n_lanes_start : int
            The number of lanes at `s_start`.
        n_lanes_end : int
            The number of lanes at `s_end`.
        sub_lane : int, optional
            The lane that should be created (split) or removed (merge).
            Default is None.
        lane_start_widths : list of float, optional
            The widths of lanes at the start. Must be empty or the same
            length as `n_lanes_start`. Default is an empty list.
        lane_end_widths : list of float, optional
            The widths of lanes at the end. Must be empty or the same
            length as `n_lanes_end`. Default is the same as
            `lane_start_widths`.

        Returns
        -------
        None
        """
        self.s_start = s_start
        self.s_end = s_end
        self.n_lanes_start = n_lanes_start
        self.n_lanes_end = n_lanes_end
        self.sub_lane = sub_lane
        self.lane_start_widths = lane_start_widths
        if lane_end_widths == []:
            self.lane_end_widths = self.lane_start_widths.copy()
        else:
            self.lane_end_widths = lane_end_widths

    def _adjust_lane_widths(self) -> None:
        """Adjust lane widths for merges or splits.

        This method ensures that the lane widths are consistent when a
        laneis created (split) or removed (merge).

        Returns
        -------
        None
        """
        if self.sub_lane:
            if (
                self.lane_end_widths
                and len(self.lane_end_widths) < self.n_lanes_start
            ):
                # mergeo
                self.lane_end_widths.insert(abs(self.sub_lane) - 1, 0)
            elif (
                self.lane_start_widths
                and len(self.lane_start_widths) < self.n_lanes_end
            ):
                # split
                self.lane_start_widths.insert(abs(self.sub_lane) - 1, 0)
        # TODO: add some checks here?


def _create_lane_lists(
    right: Union[list[LaneDef], int],
    left: Union[list[LaneDef], int],
    tot_length: float,
    default_lane_width: float,
) -> tuple[list[LaneDef], list[LaneDef]]:
    """Expand the list of `LaneDef` objects for lane creation.

    This function is used by `create_lanes_merge_split` to expand the list
    of `LaneDef` objects for the right and left lanes, ensuring that the
    entire road length is covered.

    Parameters
    ----------
    right : list of LaneDef or int
        The list of `LaneDef` objects for the right lanes, or an integer
        specifying a constant number of lanes.
    left : list of LaneDef or int
        The list of `LaneDef` objects for the left lanes, or an integer
        specifying a constant number of lanes.
    tot_length : float
        The total length of the road.
    default_lane_width : float
        The default lane width to use if not defined in `LaneDef`.

    Returns
    -------
    tuple of (list of LaneDef, list of LaneDef)
        A tuple containing:
        - A list of `LaneDef` objects for the right lanes.
        - A list of `LaneDef` objects for the left lanes.
    """

    # TODO: implement for left and right lanesection...
    def _check_lane_widths(lane: LaneDef) -> None:
        """Ensure lane widths are defined for a `LaneDef`.

        Parameters
        ----------
        lane : LaneDef
            The `LaneDef` object to check and adjust.
        """
        if lane.lane_start_widths == []:
            lane.lane_start_widths = [
                default_lane_width for x in range(lane.n_lanes_start)
            ]
        if lane.lane_end_widths == []:
            lane.lane_end_widths = [
                default_lane_width for x in range(lane.n_lanes_end)
            ]

    const_right_lanes = None
    const_left_lanes = None

    retlanes_right = []
    retlanes_left = []
    present_s = 0

    r_it = 0
    l_it = 0
    # some primariy checks to handle int instead of LaneDef

    if not isinstance(right, list):
        const_right_lanes = right
        right = []

    if not isinstance(left, list):
        const_left_lanes = left
        left = []

    while present_s < tot_length:
        if r_it < len(right):
            # check if there is still a right LaneDef to be used, and is the next one to add
            if right[r_it].s_start == present_s:
                add_right = True
            else:
                next_right = right[r_it].s_start
                add_right = False
                n_r_lanes = right[r_it].n_lanes_start
        else:
            # no more LaneDefs, just add new right lanes with the const/or last number of lanes
            add_right = False
            next_right = tot_length
            if const_right_lanes or const_right_lanes == 0:
                n_r_lanes = const_right_lanes
            else:
                n_r_lanes = right[-1].n_lanes_end

        if l_it < len(left):
            # check if there is still a left LaneDef to be used, and is the next one to add
            if left[l_it].s_start == present_s:
                add_left = True
            else:
                next_left = left[l_it].s_start
                add_left = False
                n_l_lanes = left[l_it].n_lanes_start
        else:
            # no more LaneDefs, just add new left lanes with the const/or last number of lanes
            add_left = False
            next_left = tot_length
            if const_left_lanes or const_left_lanes == 0:
                n_l_lanes = const_left_lanes
            else:
                n_l_lanes = left[-1].n_lanes_end

        # create and add the requiered LaneDefs
        if not add_left and not add_right:
            # no LaneDefs, just add same amout of lanes
            s_end = min(next_left, next_right)
            if const_right_lanes is not None:
                retlanes_right.append(
                    LaneDef(
                        present_s,
                        s_end,
                        n_r_lanes,
                        n_r_lanes,
                        lane_start_widths=[
                            default_lane_width for x in range(n_r_lanes)
                        ],
                        lane_end_widths=[
                            default_lane_width for x in range(n_r_lanes)
                        ],
                    )
                )
            else:
                lane_start_widths = [
                    default_lane_width for x in range(n_r_lanes)
                ]
                lane_end_widths = [
                    default_lane_width for x in range(n_r_lanes)
                ]
                if r_it == len(right):
                    if right[r_it - 1].lane_end_widths:
                        lane_start_widths = right[
                            r_it - 1
                        ].lane_end_widths.copy()
                        lane_end_widths = right[
                            r_it - 1
                        ].lane_end_widths.copy()
                elif right[r_it].lane_start_widths:
                    lane_start_widths = right[r_it].lane_start_widths.copy()
                    lane_end_widths = right[r_it].lane_start_widths.copy()
                retlanes_right.append(
                    LaneDef(
                        present_s,
                        s_end,
                        n_r_lanes,
                        n_r_lanes,
                        lane_start_widths=lane_start_widths,
                        lane_end_widths=lane_end_widths,
                    )
                )
            if const_left_lanes is not None:
                retlanes_left.append(
                    LaneDef(
                        present_s,
                        s_end,
                        n_l_lanes,
                        n_l_lanes,
                        lane_start_widths=[
                            default_lane_width for x in range(n_l_lanes)
                        ],
                        lane_end_widths=[
                            default_lane_width for x in range(n_l_lanes)
                        ],
                    )
                )
            else:
                lane_start_widths = [
                    default_lane_width for x in range(n_l_lanes)
                ]
                lane_end_widths = [
                    default_lane_width for x in range(n_l_lanes)
                ]
                if l_it == len(left):
                    if left[l_it - 1].lane_end_widths:
                        lane_start_widths = left[
                            l_it - 1
                        ].lane_end_widths.copy()
                        lane_end_widths = left[l_it - 1].lane_end_widths.copy()
                elif left[l_it].lane_start_widths:
                    lane_start_widths = left[l_it].lane_start_widths.copy()
                    lane_end_widths = left[l_it].lane_start_widths.copy()

                retlanes_left.append(
                    LaneDef(
                        present_s,
                        s_end,
                        n_l_lanes,
                        n_l_lanes,
                        lane_start_widths=lane_start_widths,
                        lane_end_widths=lane_end_widths,
                    )
                )

            present_s = s_end
        elif add_left and add_right:
            # Both have changes in the amount of lanes,
            _check_lane_widths(left[l_it])
            _check_lane_widths(right[r_it])
            retlanes_left.append(left[l_it])
            retlanes_right.append(right[r_it])
            present_s = left[l_it].s_end
            r_it += 1
            l_it += 1
        elif add_right:
            # only the right lane changes the amount of lanes, and add a LaneDef with the same amount of lanes to the left
            _check_lane_widths(right[r_it])
            retlanes_right.append(right[r_it])
            retlanes_left.append(
                LaneDef(
                    present_s,
                    right[r_it].s_end,
                    n_l_lanes,
                    n_l_lanes,
                    lane_start_widths=[
                        default_lane_width for x in range(n_l_lanes)
                    ],
                    lane_end_widths=[
                        default_lane_width for x in range(n_l_lanes)
                    ],
                )
            )
            present_s = right[r_it].s_end
            r_it += 1
        elif add_left:
            # only the left lane changes the amount of lanes, and add a LaneDef with the same amount of lanes to the right
            _check_lane_widths(left[l_it])
            retlanes_left.append(left[l_it])
            retlanes_right.append(
                LaneDef(
                    present_s,
                    left[l_it].s_end,
                    n_r_lanes,
                    n_r_lanes,
                    lane_start_widths=[
                        default_lane_width for x in range(n_r_lanes)
                    ],
                    lane_end_widths=[
                        default_lane_width for x in range(n_r_lanes)
                    ],
                )
            )
            present_s = left[l_it].s_end
            l_it += 1
    [x._adjust_lane_widths() for x in retlanes_right]
    [x._adjust_lane_widths() for x in retlanes_left]
    return retlanes_right, retlanes_left
