# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from functools import partial
from rosbridge_library.capability import Capability
from rosbridge_library.internal.services import ServiceCaller
import rospy


class CallService(Capability):

    call_service_msg_fields = [(True, "service", (str, unicode)),
           (False, "fragment_size", (int, type(None))), (False, "compression", (str, unicode))]

    

    def __init__(self, protocol):
        # Call superclas constructor
        Capability.__init__(self, protocol)

        self.protocol = protocol

        # Register the operations that this capability provides
        protocol.register_operation("call_service", self.call_service)

    def call_service(self, message):
        # Pull out the ID
        cid = message.get("id", None)
        
        # Typecheck the args
        self.basic_type_check(message, self.call_service_msg_fields)

        # Extract the args
        service = message["service"]
        if self.is_permitted(service,
                             self.protocol.service_wl,
                             self.protocol.service_bl):

            fragment_size = message.get("fragment_size", None)
            compression = message.get("compression", "none")
            args = message.get("args", [])
        
            # Check for deprecated service ID, eg. /rosbridge/topics#33
            cid = extract_id(service, cid)

            # Create the callbacks
            s_cb = partial(self._success, cid, service, fragment_size, compression)
            e_cb = partial(self._failure, cid)

            # Kick off the service caller thread
            ServiceCaller(trim_servicename(service), args, s_cb, e_cb).start()
        else:
            rospy.logwarn("dropping calling service %s. not allowed", service)

    def _success(self, cid, service, fragment_size, compression, message):
        outgoing_message = {
            "op": "service_response",
            "service": service,
            "values": message
        }
        if cid is not None:
            outgoing_message["id"] = cid
        # TODO: fragmentation, compression
        self.protocol.send(outgoing_message)

    def _failure(self, cid, exc):
        self.protocol.log("error", "call_service %s: %s" %
            (type(exc).__name__, str(exc)), cid)


def trim_servicename(service):
    if '#' in service:
        return service[:service.find('#')]
    return service


def extract_id(service, cid):
    if cid is not None:
        return cid
    elif '#' in service:
        return service[service.find('#') + 1:]
