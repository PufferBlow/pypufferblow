Realtime (protocol v1)
======================

The server speaks a command/event protocol on ``/ws?protocol=1``. Commands are acknowledged once
the work is committed; events are pushed for the channels you can see, in order per channel, at
least once. :class:`~pypufferblow.realtime.ProtocolClient` handles correlation, idempotent retries,
duplicate events and recovery after a gap or a reconnect.

.. code-block:: python

    async with client.realtime() as live:
        live.watch(channel_id)
        await live.create_message(channel_id, "hello")
        async for event in live.events():
            print(event.name, event.data)

Retrying a send
---------------

``create_message`` takes a ``nonce`` (generated when omitted). Retryable failures are retried with
the same nonce, so a message the server did commit is never posted twice.

Recovery
--------

Each event carries a per-channel sequence number and the server's epoch. A gap, or a new epoch after
a server restart, makes the client call ``events.resync`` for that channel and report the server's
recent messages to ``on_resync``. After a reconnect the channels added with ``watch`` are caught up
the same way.

API
---

.. automodule:: pypufferblow.realtime
   :members:

.. automodule:: pypufferblow.protocol
   :members:
