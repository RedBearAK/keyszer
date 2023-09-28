# This file has been autogenerated by the pywayland scanner

# Copyright © 2008-2011 Kristian Høgsberg
# Copyright © 2010-2011 Intel Corporation
# Copyright © 2012-2013 Collabora, Ltd.
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice (including the
# next paragraph) shall be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import enum

from pywayland.protocol_core import (
    Argument,
    ArgumentType,
    Global,
    Interface,
    Proxy,
    Resource,
)
from .wl_data_offer import WlDataOffer
from .wl_data_source import WlDataSource
from .wl_surface import WlSurface


class WlDataDevice(Interface):
    """Data transfer device

    There is one :class:`WlDataDevice` per seat which can be obtained from the
    global :class:`~pywayland.protocol.wayland.WlDataDeviceManager` singleton.

    A :class:`WlDataDevice` provides access to inter-client data transfer
    mechanisms such as copy-and-paste and drag-and-drop.
    """

    name = "wl_data_device"
    version = 3

    class error(enum.IntEnum):
        role = 0


class WlDataDeviceProxy(Proxy[WlDataDevice]):
    interface = WlDataDevice

    @WlDataDevice.request(
        Argument(ArgumentType.Object, interface=WlDataSource, nullable=True),
        Argument(ArgumentType.Object, interface=WlSurface),
        Argument(ArgumentType.Object, interface=WlSurface, nullable=True),
        Argument(ArgumentType.Uint),
    )
    def start_drag(self, source: WlDataSource | None, origin: WlSurface, icon: WlSurface | None, serial: int) -> None:
        """Start drag-and-drop operation

        This request asks the compositor to start a drag-and-drop operation on
        behalf of the client.

        The source argument is the data source that provides the data for the
        eventual data transfer. If source is NULL, enter, leave and motion
        events are sent only to the client that initiated the drag and the
        client is expected to handle the data passing internally. If source is
        destroyed, the drag-and-drop session will be cancelled.

        The origin surface is the surface where the drag originates and the
        client must have an active implicit grab that matches the serial.

        The icon surface is an optional (can be NULL) surface that provides an
        icon to be moved around with the cursor.  Initially, the top-left
        corner of the icon surface is placed at the cursor hotspot, but
        subsequent :func:`WlSurface.attach()
        <pywayland.protocol.wayland.WlSurface.attach>` request can move the
        relative position. Attach requests must be confirmed with
        :func:`WlSurface.commit()
        <pywayland.protocol.wayland.WlSurface.commit>` as usual. The icon
        surface is given the role of a drag-and-drop icon. If the icon surface
        already has another role, it raises a protocol error.

        The input region is ignored for wl_surfaces with the role of a drag-
        and-drop icon.

        :param source:
            data source for the eventual transfer
        :type source:
            :class:`~pywayland.protocol.wayland.WlDataSource` or `None`
        :param origin:
            surface where the drag originates
        :type origin:
            :class:`~pywayland.protocol.wayland.WlSurface`
        :param icon:
            drag-and-drop icon surface
        :type icon:
            :class:`~pywayland.protocol.wayland.WlSurface` or `None`
        :param serial:
            serial number of the implicit grab on the origin
        :type serial:
            `ArgumentType.Uint`
        """
        self._marshal(0, source, origin, icon, serial)

    @WlDataDevice.request(
        Argument(ArgumentType.Object, interface=WlDataSource, nullable=True),
        Argument(ArgumentType.Uint),
    )
    def set_selection(self, source: WlDataSource | None, serial: int) -> None:
        """Copy data to the selection

        This request asks the compositor to set the selection to the data from
        the source on behalf of the client.

        To unset the selection, set the source to NULL.

        :param source:
            data source for the selection
        :type source:
            :class:`~pywayland.protocol.wayland.WlDataSource` or `None`
        :param serial:
            serial number of the event that triggered this request
        :type serial:
            `ArgumentType.Uint`
        """
        self._marshal(1, source, serial)

    @WlDataDevice.request(version=2)
    def release(self) -> None:
        """Destroy data device

        This request destroys the data device.
        """
        self._marshal(2)
        self._destroy()


class WlDataDeviceResource(Resource):
    interface = WlDataDevice

    @WlDataDevice.event(
        Argument(ArgumentType.NewId, interface=WlDataOffer),
    )
    def data_offer(self, id: WlDataOffer) -> None:
        """Introduce a new :class:`~pywayland.protocol.wayland.WlDataOffer`

        The data_offer event introduces a new
        :class:`~pywayland.protocol.wayland.WlDataOffer` object, which will
        subsequently be used in either the data_device.enter event (for drag-
        and-drop) or the data_device.selection event (for selections).
        Immediately following the data_device.data_offer event, the new
        data_offer object will send out data_offer.offer events to describe the
        mime types it offers.

        :param id:
            the new data_offer object
        :type id:
            :class:`~pywayland.protocol.wayland.WlDataOffer`
        """
        self._post_event(0, id)

    @WlDataDevice.event(
        Argument(ArgumentType.Uint),
        Argument(ArgumentType.Object, interface=WlSurface),
        Argument(ArgumentType.Fixed),
        Argument(ArgumentType.Fixed),
        Argument(ArgumentType.Object, interface=WlDataOffer, nullable=True),
    )
    def enter(self, serial: int, surface: WlSurface, x: float, y: float, id: WlDataOffer | None) -> None:
        """Initiate drag-and-drop session

        This event is sent when an active drag-and-drop pointer enters a
        surface owned by the client.  The position of the pointer at enter time
        is provided by the x and y arguments, in surface-local coordinates.

        :param serial:
            serial number of the enter event
        :type serial:
            `ArgumentType.Uint`
        :param surface:
            client surface entered
        :type surface:
            :class:`~pywayland.protocol.wayland.WlSurface`
        :param x:
            surface-local x coordinate
        :type x:
            `ArgumentType.Fixed`
        :param y:
            surface-local y coordinate
        :type y:
            `ArgumentType.Fixed`
        :param id:
            source data_offer object
        :type id:
            :class:`~pywayland.protocol.wayland.WlDataOffer` or `None`
        """
        self._post_event(1, serial, surface, x, y, id)

    @WlDataDevice.event()
    def leave(self) -> None:
        """End drag-and-drop session

        This event is sent when the drag-and-drop pointer leaves the surface
        and the session ends.  The client must destroy the
        :class:`~pywayland.protocol.wayland.WlDataOffer` introduced at enter
        time at this point.
        """
        self._post_event(2)

    @WlDataDevice.event(
        Argument(ArgumentType.Uint),
        Argument(ArgumentType.Fixed),
        Argument(ArgumentType.Fixed),
    )
    def motion(self, time: int, x: float, y: float) -> None:
        """Drag-and-drop session motion

        This event is sent when the drag-and-drop pointer moves within the
        currently focused surface. The new position of the pointer is provided
        by the x and y arguments, in surface-local coordinates.

        :param time:
            timestamp with millisecond granularity
        :type time:
            `ArgumentType.Uint`
        :param x:
            surface-local x coordinate
        :type x:
            `ArgumentType.Fixed`
        :param y:
            surface-local y coordinate
        :type y:
            `ArgumentType.Fixed`
        """
        self._post_event(3, time, x, y)

    @WlDataDevice.event()
    def drop(self) -> None:
        """End drag-and-drop session successfully

        The event is sent when a drag-and-drop operation is ended because the
        implicit grab is removed.

        The drag-and-drop destination is expected to honor the last action
        received through :func:`WlDataOffer.action()
        <pywayland.protocol.wayland.WlDataOffer.action>`, if the resulting
        action is "copy" or "move", the destination can still perform
        :func:`WlDataOffer.receive()
        <pywayland.protocol.wayland.WlDataOffer.receive>` requests, and is
        expected to end all transfers with a :func:`WlDataOffer.finish()
        <pywayland.protocol.wayland.WlDataOffer.finish>` request.

        If the resulting action is "ask", the action will not be considered
        final. The drag-and-drop destination is expected to perform one last
        :func:`WlDataOffer.set_actions()
        <pywayland.protocol.wayland.WlDataOffer.set_actions>` request, or
        :func:`WlDataOffer.destroy()
        <pywayland.protocol.wayland.WlDataOffer.destroy>` in order to cancel
        the operation.
        """
        self._post_event(4)

    @WlDataDevice.event(
        Argument(ArgumentType.Object, interface=WlDataOffer, nullable=True),
    )
    def selection(self, id: WlDataOffer | None) -> None:
        """Advertise new selection

        The selection event is sent out to notify the client of a new
        :class:`~pywayland.protocol.wayland.WlDataOffer` for the selection for
        this device.  The data_device.data_offer and the data_offer.offer
        events are sent out immediately before this event to introduce the data
        offer object.  The selection event is sent to a client immediately
        before receiving keyboard focus and when a new selection is set while
        the client has keyboard focus.  The data_offer is valid until a new
        data_offer or NULL is received or until the client loses keyboard
        focus.  Switching surface with keyboard focus within the same client
        doesn't mean a new selection will be sent.  The client must destroy the
        previous selection data_offer, if any, upon receiving this event.

        :param id:
            selection data_offer object
        :type id:
            :class:`~pywayland.protocol.wayland.WlDataOffer` or `None`
        """
        self._post_event(5, id)


class WlDataDeviceGlobal(Global):
    interface = WlDataDevice


WlDataDevice._gen_c()
WlDataDevice.proxy_class = WlDataDeviceProxy
WlDataDevice.resource_class = WlDataDeviceResource
WlDataDevice.global_class = WlDataDeviceGlobal
